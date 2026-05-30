"""DJ-grade structural analysis for tracks (Mixed In Key style).

Given a WAV file this computes, over the WHOLE track:
  - tempo (BPM) with octave-error correction
  - musical key + Camelot code + confidence
  - a beat grid and estimated downbeats (4/4 assumed)
  - structural section boundaries (Foote novelty over a self-similarity matrix)
  - per-section energy and a semantic label (intro / build / chorus / break / outro)
  - DJ cue points: cue_in (where to mix in) and cue_out (where to start mixing out)

Backend strategy (best available is chosen automatically, graceful fallback):
  - Key:    Essentia ``KeyExtractor`` (EDMA) > multi-profile (Shaath/Temperley/
            Krumhansl) over a high-resolution CQT chroma from AudioFlux > librosa.
            The Shaath profile is the one used by libKeyFinder, so even without
            the native library we reproduce its detection approach.
  - Rhythm: Essentia ``RhythmExtractor2013`` > librosa ``beat_track``.
  - Downbeats: Essentia ``BeatsLoudness`` (kick/bass band) phase > onset voting.
  - Chroma/onset features: AudioFlux (fast C core) > librosa.

  Essentia algorithms are calibrated for 44.1 kHz, so their inputs are
  resampled to 44100 even when the rest of the pipeline runs at 22050.

The output is a JSON-serializable dict stored under a record's ``analysis`` key.
"""

from __future__ import annotations

from typing import Any

import numpy as np

ANALYSIS_VERSION = 4

# --- Optional native backends (detected once at import) -------------------
try:  # MTG Essentia: best-in-class MIR (rarely available on Windows)
    import essentia.standard as _es  # type: ignore
    ESSENTIA_AVAILABLE = True
except Exception:
    _es = None
    ESSENTIA_AVAILABLE = False

try:  # AudioFlux: fast C-accelerated spectral features
    import audioflux as _af  # type: ignore
    AUDIOFLUX_AVAILABLE = True
except Exception:
    _af = None
    AUDIOFLUX_AVAILABLE = False


PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# --- Key profiles ---------------------------------------------------------
# Each is (major, minor). Correlation-based detection is robust to small
# differences, so we vote across several well-established profiles.
#
# Shaath = the profile used by libKeyFinder (Ibrahim Shaath). Including it makes
# this detector behave like libKeyFinder without needing the native build.
KEY_PROFILES = {
    # Essentia KeyExtractor EDMA — tuned for electronic / dance (Spotify DJ, Mixed In Key).
    "edma": (
        np.array([0.16519551, 0.04749026, 0.08293076, 0.06687112, 0.09994645,
                  0.09274123, 0.05294487, 0.13159476, 0.05218986, 0.07443653,
                  0.06940723, 0.0642515]),
        np.array([0.17235348, 0.05336489, 0.0761009, 0.10043649, 0.05621498,
                  0.08527853, 0.0497915, 0.13451001, 0.07458916, 0.05003023,
                  0.09187879, 0.05545106]),
    ),
    "shaath": (
        np.array([6.6, 2.0, 3.5, 2.3, 4.6, 4.0, 2.5, 5.2, 2.4, 3.7, 2.3, 3.4]),
        np.array([6.5, 2.7, 3.5, 5.4, 2.6, 3.5, 2.5, 5.2, 4.0, 2.7, 4.3, 3.2]),
    ),
    "temperley": (
        np.array([5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0]),
        np.array([5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0]),
    ),
    "krumhansl": (
        np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]),
        np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]),
    ),
}

# EDMA is weighted higher — matches Spotify / DJ-app key detection for club music.
KEY_PROFILE_WEIGHTS = {
    "edma": 2.5,
    "shaath": 1.0,
    "temperley": 0.75,
    "krumhansl": 0.75,
}

# Musical key -> Camelot wheel code (for harmonic mixing)
CAMELOT = {
    "B Major": "1B", "F# Major": "2B", "C# Major": "3B", "G# Major": "4B",
    "D# Major": "5B", "A# Major": "6B", "F Major": "7B", "C Major": "8B",
    "G Major": "9B", "D Major": "10B", "A Major": "11B", "E Major": "12B",
    "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A", "F Minor": "4A",
    "C Minor": "5A", "G Minor": "6A", "D Minor": "7A", "A Minor": "8A",
    "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A", "C# Minor": "12A",
}

# Enharmonic spellings Essentia may return -> our sharp-based naming
_ENHARMONIC = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}

BPM_MIN = 70.0
BPM_MAX = 175.0
RHYTHM_SR = 44100
RHYTHM_HOP = 256  # finer grid than 512@22050 — avoids ~129 BPM quantization bucket

BEATS_PER_BAR = 4
PHRASE_BARS = 8
PHRASE_BEATS = BEATS_PER_BAR * PHRASE_BARS


def backends() -> dict[str, bool]:
    return {"essentia": ESSENTIA_AVAILABLE, "audioflux": AUDIOFLUX_AVAILABLE}


def _octave_correct_bpm(bpm: float, lo: float = BPM_MIN, hi: float = BPM_MAX) -> float:
    if bpm <= 0:
        return 0.0
    while bpm < lo:
        bpm *= 2.0
    while bpm > hi:
        bpm /= 2.0
    return bpm


# ===========================================================================
# Key detection
# ===========================================================================
def _camelot(key: str) -> str:
    return CAMELOT.get(key, "")


def _detect_key_multiprofile(chroma: np.ndarray) -> tuple[str, float]:
    """Vote across key profiles on a mean chroma vector. Returns (key, confidence)."""
    mean = np.mean(chroma, axis=1)
    if mean.size != 12 or np.allclose(mean, 0):
        return "Unknown", 0.0

    # Aggregate correlation scores per (tonic, mode) across all profiles
    scores: dict[tuple[int, str], float] = {}
    weight_sum = 0.0
    for name, (major, minor) in KEY_PROFILES.items():
        w = KEY_PROFILE_WEIGHTS.get(name, 1.0)
        weight_sum += w
        for i in range(12):
            cmaj = np.corrcoef(mean, np.roll(major, i))[0, 1]
            cmin = np.corrcoef(mean, np.roll(minor, i))[0, 1]
            scores[(i, "Major")] = scores.get((i, "Major"), 0.0) + w * float(cmaj)
            scores[(i, "Minor")] = scores.get((i, "Minor"), 0.0) + w * float(cmin)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (idx, mode), best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    # Confidence = correlation strength of the winning key (0..1). Low values
    # (~0.4) flag tonally ambiguous tracks; strong matches sit around 0.8-0.95.
    confidence = max(0.0, min(1.0, best / max(weight_sum, 1.0)))
    # Penalise when the runner-up is nearly as strong (relative major/minor swaps).
    if best > 0:
        confidence *= max(0.35, min(1.0, (best - second) / best + 0.25))
    return f"{PITCH_CLASSES[idx]} {mode}", round(confidence, 3)


def _to_44100(y: np.ndarray, sr: int) -> np.ndarray:
    """Essentia algorithms assume 44.1 kHz; resample if the caller used another rate."""
    if sr == 44100:
        return y.astype(np.float32)
    import librosa
    return librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=44100)


def _detect_key_essentia(y: np.ndarray, sr: int) -> tuple[str, float] | None:
    if not ESSENTIA_AVAILABLE:
        return None
    try:
        # KeyExtractor's HPCP analysis is tuned for 44.1 kHz; feeding a lower
        # rate without correcting shifts the pitch bins and breaks detection.
        sig = _to_44100(y, sr)
        extractor = _es.KeyExtractor(profileType="edma", sampleRate=44100)
        key, scale, strength = extractor(sig)
        key = _ENHARMONIC.get(key, key)
        mode = "Major" if str(scale).lower().startswith("maj") else "Minor"
        return f"{key} {mode}", float(strength)
    except Exception:
        return None


# ===========================================================================
# Chroma for KEY detection: AudioFlux high-res CQT > librosa.
# (Only the time-averaged vector is used, so the frame grid need not match the
#  structure features.)
# ===========================================================================
def _chroma_for_key(y: np.ndarray, sr: int) -> np.ndarray:
    if AUDIOFLUX_AVAILABLE:
        try:
            cqt = _af.CQT(num=84, samplate=sr, bin_per_octave=12)
            spec = cqt.cqt(y.astype(np.float32))  # complex CQT
            chroma = np.asarray(cqt.chroma(spec), dtype=float)  # chroma() wants complex
            if chroma.shape[0] == 12 and chroma.shape[1] > 0:
                return chroma
        except Exception:
            pass
    import librosa
    return librosa.feature.chroma_cqt(y=y, sr=sr)


# ===========================================================================
# Rhythm (BPM + beats) with Essentia > librosa
# ===========================================================================
def _bpm_from_beat_times(beat_times: np.ndarray) -> float:
    """Median inter-beat interval BPM, rejecting obvious missed/double beats."""
    if len(beat_times) < 4:
        return 0.0
    ibis = np.diff(beat_times)
    med = float(np.median(ibis))
    if med <= 0:
        return 0.0
    good = ibis[(ibis > med * 0.9) & (ibis < med * 1.1)]
    if len(good) < 3:
        good = ibis
    return 60.0 / float(np.median(good))


def _pick_bpm(candidates: list[float], bpm_hint: float | None) -> float:
    """Choose a tempo from several estimators with octave correction."""
    if bpm_hint and bpm_hint > 0:
        return float(bpm_hint)
    corrected = [_octave_correct_bpm(float(c)) for c in candidates if c and c > 0]
    if not corrected:
        return 120.0
    med = float(np.median(corrected))
    best = min(corrected, key=lambda x: abs(x - med))
    return float(int(round(best)))


def _track_beats(onset_env: np.ndarray, sr: int, bpm: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (beat_times, beat_frames) locked to ``bpm``."""
    import librosa

    _, beats = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=RHYTHM_HOP,
        start_bpm=bpm,
        tightness=100,
    )
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=RHYTHM_HOP)
    return beat_times, beats


def _detect_rhythm(y: np.ndarray, sr: int, bpm_hint: float | None):
    """Return (bpm, beat_times, onset_env, beats_frames)."""
    import librosa

    if ESSENTIA_AVAILABLE:
        try:
            rex = _es.RhythmExtractor2013(method="multifeature")
            bpm_e, ticks, _conf, _est, _intervals = rex(_to_44100(y, sr))
            beat_times = np.asarray(ticks, dtype=float)
            onset_env = librosa.onset.onset_strength(
                y=_to_44100(y, sr), sr=RHYTHM_SR, hop_length=RHYTHM_HOP,
            )
            bpm = _pick_bpm([float(bpm_e), _bpm_from_beat_times(beat_times)], bpm_hint)
            beat_times, beats_frames = _track_beats(onset_env, RHYTHM_SR, bpm)
            if sr != RHYTHM_SR:
                beats_frames = librosa.time_to_frames(beat_times, sr=sr)
            return bpm, beat_times, onset_env, beats_frames
        except Exception:
            pass

    sig = _to_44100(y, sr)
    _, y_perc = librosa.effects.hpss(sig)
    onset_env = librosa.onset.onset_strength(y=y_perc, sr=RHYTHM_SR, hop_length=RHYTHM_HOP)

    candidates: list[float] = []
    start_bpms = [120.0, 128.0, 130.0, 132.0]
    if bpm_hint and bpm_hint > 0:
        start_bpms = [float(bpm_hint)] + [x for x in start_bpms if abs(x - bpm_hint) > 2]

    for start in start_bpms:
        _, beats = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=RHYTHM_SR,
            hop_length=RHYTHM_HOP,
            start_bpm=start,
            tightness=100,
        )
        beat_times = librosa.frames_to_time(beats, sr=RHYTHM_SR, hop_length=RHYTHM_HOP)
        if len(beat_times) > 4:
            candidates.append(_bpm_from_beat_times(beat_times))

    try:
        tempos = librosa.feature.rhythm.tempo(
            onset_envelope=onset_env,
            sr=RHYTHM_SR,
            hop_length=RHYTHM_HOP,
            aggregate=None,
            max_tempo=BPM_MAX,
            std_bpm=4,
        )
        if len(tempos):
            for idx in np.argsort(tempos)[-4:]:
                candidates.append(float(tempos[idx]))
    except Exception:
        pass

    bpm = _pick_bpm(candidates, bpm_hint)
    beat_times, beats_frames = _track_beats(onset_env, RHYTHM_SR, bpm)
    if sr != RHYTHM_SR:
        beats_frames = librosa.time_to_frames(beat_times, sr=sr)
    return bpm, beat_times, onset_env, beats_frames


# ===========================================================================
# Structure helpers
# ===========================================================================
def _essentia_downbeat_phase(y: np.ndarray, sr: int, beat_times: np.ndarray) -> int | None:
    """Downbeat phase (0..BEATS_PER_BAR-1) from Essentia per-beat bass loudness.

    In 4/4 dance music the downbeat lands on the kick, so the phase whose beats
    carry the most low-frequency (20-150 Hz) energy is the bar start. Returns
    None when Essentia is unavailable or the estimate can't be formed (caller
    then falls back to onset-based phase voting).
    """
    if not ESSENTIA_AVAILABLE or len(beat_times) < BEATS_PER_BAR:
        return None
    try:
        sig = _to_44100(y, sr)
        bl = _es.BeatsLoudness(
            sampleRate=44100,
            beats=np.asarray(beat_times, dtype=np.float32),
            # Bands kept under Nyquist; band[0] (20-150 Hz) isolates the kick.
            frequencyBands=[20.0, 150.0, 400.0, 3200.0, 7000.0, 13000.0],
        )
        loudness, band_ratio = bl(sig)
        loudness = np.asarray(loudness, dtype=float)
        band_ratio = np.asarray(band_ratio, dtype=float)
        if band_ratio.ndim != 2 or band_ratio.shape[0] < BEATS_PER_BAR:
            return None
        n = band_ratio.shape[0]
        bass = loudness[:n] * band_ratio[:, 0]  # absolute low-band energy per beat
        best_phase, best = 0, -np.inf
        for phase in range(BEATS_PER_BAR):
            score = float(np.sum(bass[phase::BEATS_PER_BAR]))
            if score > best:
                best, best_phase = score, phase
        return best_phase
    except Exception:
        return None


def _estimate_downbeat_phase(onset_env: np.ndarray, beats_frames: np.ndarray) -> int:
    if len(beats_frames) < BEATS_PER_BAR:
        return 0
    strengths = onset_env[np.clip(beats_frames, 0, len(onset_env) - 1)]
    best_phase, best_score = 0, -np.inf
    for phase in range(BEATS_PER_BAR):
        score = float(np.sum(strengths[phase::BEATS_PER_BAR]))
        if score > best_score:
            best_score, best_phase = score, phase
    return best_phase


def _self_similarity(feat: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(feat, axis=0, keepdims=True)
    norm[norm == 0] = 1e-9
    unit = feat / norm
    return np.clip(unit.T @ unit, -1.0, 1.0)


def _checkerboard_kernel(half: int) -> np.ndarray:
    axis = np.arange(-half, half)
    xx, yy = np.meshgrid(axis, axis)
    sign = np.sign(xx) * np.sign(yy)
    sigma = half / 2.0
    gauss = np.exp(-(xx ** 2 + yy ** 2) / (2.0 * sigma ** 2))
    return sign * gauss


def _foote_novelty(ssm: np.ndarray, half: int) -> np.ndarray:
    n = ssm.shape[0]
    kernel = _checkerboard_kernel(half)
    padded = np.pad(ssm, half, mode="edge")
    novelty = np.zeros(n)
    for i in range(n):
        window = padded[i:i + 2 * half, i:i + 2 * half]
        novelty[i] = float(np.sum(window * kernel))
    novelty -= novelty.min()
    peak = novelty.max()
    if peak > 0:
        novelty /= peak
    return novelty


def _pick_boundaries(novelty: np.ndarray, min_gap: int, delta: float) -> list[int]:
    boundaries: list[int] = []
    n = len(novelty)
    for i in range(1, n - 1):
        if novelty[i] < delta:
            continue
        lo = max(0, i - min_gap)
        hi = min(n, i + min_gap + 1)
        if novelty[i] >= novelty[lo:hi].max():
            if not boundaries or (i - boundaries[-1]) >= min_gap:
                boundaries.append(i)
    return boundaries


def _label_section(energy: float, lo: float = 0.33, hi: float = 0.6) -> str:
    if energy >= hi:
        return "chorus"
    if energy <= lo:
        return "break"
    return "verse"


def _first_sustained(mask: np.ndarray, run: int) -> int:
    count = 0
    for i, v in enumerate(mask):
        count = count + 1 if v else 0
        if count >= run:
            return i - run + 1
    return -1


def _last_sustained_end(mask: np.ndarray, run: int) -> int:
    count = 0
    end = -1
    for i, v in enumerate(mask):
        if v:
            count += 1
            if count >= run:
                end = i + 1
        else:
            count = 0
    return end


def _snap_to_phrase(beat_idx: int, phase: int) -> int:
    rel = beat_idx - phase
    snapped = round(rel / PHRASE_BEATS) * PHRASE_BEATS + phase
    return max(0, snapped)


def _derive_cues(energy_norm, beat_times, duration, phase, n_beats):
    if n_beats < BEATS_PER_BAR or len(beat_times) == 0:
        return 0.0, duration
    high = energy_norm >= 0.5
    run = BEATS_PER_BAR * 2

    intro_end_beat = _first_sustained(high, run)
    if intro_end_beat <= 0:
        intro_end_beat = min(PHRASE_BEATS, n_beats - 1)
    cue_in_beat = min(_snap_to_phrase(intro_end_beat, phase), max(0, n_beats - PHRASE_BEATS))

    outro_beat = _last_sustained_end(high, run)
    if outro_beat <= cue_in_beat or outro_beat >= n_beats:
        outro_beat = max(cue_in_beat + PHRASE_BEATS, n_beats - PHRASE_BEATS)
    cue_out_beat = min(max(_snap_to_phrase(outro_beat, phase), cue_in_beat + PHRASE_BEATS), n_beats - 1)

    cue_in = beat_times[min(cue_in_beat, len(beat_times) - 1)]
    cue_out = beat_times[min(cue_out_beat, len(beat_times) - 1)]
    if cue_out <= cue_in:
        cue_out = duration
    return float(cue_in), float(cue_out)


# ===========================================================================
# BPM / Key only (metadata refresh — faster than full structure pass)
# ===========================================================================
def analyze_bpm_key(
    file_path: str,
    *,
    bpm_hint: float | None = None,
    key_hint: str | None = None,
    max_duration: float = 90.0,
) -> dict[str, Any]:
    """Detect BPM and musical key from a local WAV (no sections/cues).

    Analyzes up to ``max_duration`` seconds for speed during batch refresh.
    """
    import librosa

    y, sr = librosa.load(file_path, sr=RHYTHM_SR, mono=True, duration=max_duration)
    duration = float(len(y) / sr) if sr else 0.0
    used = backends()

    empty = {
        "bpm": int(bpm_hint) if bpm_hint else 0,
        "key": key_hint or "Unknown",
        "camelot": _camelot(key_hint) if key_hint and key_hint != "Unknown" else "",
        "key_confidence": 0.0,
        "source": "local",
        "backends": used,
    }
    if duration <= 0 or len(y) < sr:
        return empty

    y_harm, _ = librosa.effects.hpss(y)
    key_result = _detect_key_essentia(y_harm, sr)
    if key_result is None:
        key, key_conf = _detect_key_multiprofile(_chroma_for_key(y_harm, sr))
    else:
        key, key_conf = key_result
    if (
        key_hint
        and key_hint not in ("", "Unknown")
        and ("Major" in key_hint or "Minor" in key_hint)
    ):
        key = key_hint
        if key_conf < 0.5:
            key_conf = 0.85

    bpm, _, _, _ = _detect_rhythm(y, sr, bpm_hint)

    return {
        "bpm": int(round(bpm)),
        "key": key,
        "camelot": _camelot(key),
        "key_confidence": key_conf,
        "source": "local",
        "backends": used,
    }


# ===========================================================================
# Main entry point
# ===========================================================================
def analyze_structure(
    file_path: str,
    sr: int = RHYTHM_SR,
    bpm_hint: float | None = None,
    key_hint: str | None = None,
) -> dict[str, Any]:
    """Full-track DJ analysis. Returns a JSON-serializable dict.

    ``bpm_hint`` / ``key_hint`` (e.g. from Spotify audio features) bias tempo and
    tonality. Beat tracking is always re-aligned to the chosen BPM so the grid
    matches what the user sees.
    Raises on unreadable audio; callers should catch and fall back.
    """
    import librosa

    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = float(len(y) / sr) if sr else 0.0
    used = backends()

    if duration <= 0 or len(y) < sr:
        return {
            "version": ANALYSIS_VERSION, "duration": duration,
            "bpm": int(bpm_hint) if bpm_hint else 0, "key": "Unknown",
            "camelot": "", "key_confidence": 0.0,
            "downbeats": [], "sections": [], "cue_in": 0.0, "cue_out": duration,
            "backends": used,
        }

    # --- Key: harmonic content + EDMA-weighted profiles (Essentia > multiprofile) ---
    y_harm, _ = librosa.effects.hpss(y)
    key_result = _detect_key_essentia(y_harm, sr)
    if key_result is None:
        key, key_conf = _detect_key_multiprofile(_chroma_for_key(y_harm, sr))
    else:
        key, key_conf = key_result
    if (
        key_hint
        and key_hint not in ("", "Unknown")
        and ("Major" in key_hint or "Minor" in key_hint)
    ):
        key = key_hint
        if key_conf < 0.5:
            key_conf = 0.85

    # --- Rhythm ---
    bpm, beat_times, onset_env, beats_frames = _detect_rhythm(y, sr, bpm_hint)
    # Prefer Essentia's bass-loudness downbeats; fall back to onset-energy voting.
    phase = _essentia_downbeat_phase(y, sr, beat_times)
    if phase is None:
        phase = _estimate_downbeat_phase(onset_env, np.asarray(beats_frames))
    downbeat_times = beat_times[phase::BEATS_PER_BAR] if len(beat_times) else np.array([])

    # --- Beat-synchronous features for structure (librosa chroma keeps the
    #     same frame grid as the beat frames used for syncing) ---
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    rms = librosa.feature.rms(y=y)[0]

    if len(beats_frames) >= 4:
        bf = np.asarray(beats_frames)
        # Clip beat frames to the chroma/mfcc frame range before syncing
        chroma_s = librosa.util.sync(chroma, np.clip(bf, 0, chroma.shape[1] - 1), aggregate=np.median)
        mfcc_s = librosa.util.sync(mfcc, np.clip(bf, 0, mfcc.shape[1] - 1), aggregate=np.mean)
        rms_s = librosa.util.sync(rms[np.newaxis, :], np.clip(bf, 0, len(rms) - 1), aggregate=np.mean)[0]
    else:
        chroma_s, mfcc_s, rms_s = chroma, mfcc, rms

    n_beats = chroma_s.shape[1]

    energy = rms_s.astype(float)
    e_min, e_max = float(energy.min()), float(energy.max())
    energy_norm = (energy - e_min) / (e_max - e_min) if e_max > e_min else np.zeros_like(energy)

    # --- Structural boundaries ---
    boundaries_beat: list[int] = [0]
    if n_beats >= 2 * PHRASE_BEATS:
        feat = np.vstack([
            librosa.util.normalize(chroma_s, axis=0),
            librosa.util.normalize(mfcc_s, axis=0),
        ])
        ssm = _self_similarity(feat)
        half = min(max(BEATS_PER_BAR * 2, n_beats // 16), PHRASE_BEATS)
        novelty = _foote_novelty(ssm, half)
        e_diff = np.abs(np.gradient(energy_norm))
        if e_diff.max() > 0:
            novelty = 0.7 * novelty + 0.3 * (e_diff / e_diff.max())
        boundaries_beat += [p for p in _pick_boundaries(novelty, PHRASE_BEATS // 2, 0.18) if p > 0]
    boundaries_beat.append(n_beats)
    boundaries_beat = sorted(set(boundaries_beat))

    db_beat_idx = set(range(phase, n_beats, BEATS_PER_BAR))
    snapped = []
    for b in boundaries_beat:
        if b in (0, n_beats):
            snapped.append(b)
        else:
            snapped.append(min(db_beat_idx, key=lambda d: abs(d - b)) if db_beat_idx else b)
    boundaries_beat = sorted(set(snapped))
    if boundaries_beat[0] != 0:
        boundaries_beat.insert(0, 0)
    if boundaries_beat[-1] != n_beats:
        boundaries_beat.append(n_beats)

    # --- Sections ---
    sections: list[dict[str, Any]] = []
    for start_b, end_b in zip(boundaries_beat[:-1], boundaries_beat[1:]):
        if end_b <= start_b:
            continue
        seg_energy = float(np.mean(energy_norm[start_b:end_b]))
        start_t = float(beat_times[start_b]) if start_b < len(beat_times) else duration
        end_t = float(beat_times[end_b]) if end_b < len(beat_times) else duration
        sections.append({
            "start": round(start_t, 3), "end": round(end_t, 3),
            "label": _label_section(seg_energy), "energy": round(seg_energy, 3),
        })

    if sections:
        loud_idx = [i for i, s in enumerate(sections) if s["label"] == "chorus"]
        if loud_idx:
            first_loud, last_loud = loud_idx[0], loud_idx[-1]
            for i, s in enumerate(sections):
                if s["label"] in ("break", "verse"):
                    if i < first_loud and s["start"] <= duration * 0.4:
                        s["label"] = "intro"
                    elif i > last_loud:
                        s["label"] = "outro"
        if sections[0]["label"] in ("break", "verse") and sections[0]["energy"] <= 0.5:
            sections[0]["label"] = "intro"
        if sections[-1]["label"] in ("break", "verse") and sections[-1]["energy"] <= 0.6:
            sections[-1]["label"] = "outro"

    cue_in, cue_out = _derive_cues(energy_norm, beat_times, duration, phase, n_beats)

    return {
        "version": ANALYSIS_VERSION,
        "duration": round(duration, 3),
        "bpm": int(round(bpm)),
        "key": key,
        "camelot": _camelot(key),
        "key_confidence": key_conf,
        "downbeats": [round(float(t), 3) for t in downbeat_times],
        "sections": sections,
        "cue_in": round(float(cue_in), 3),
        "cue_out": round(float(cue_out), 3),
        "backends": used,
    }
