"""Backend self-test for desktop_app/analysis.py.

Generates a synthetic 4/4 dance loop (strong kick on the downbeat, a C-major
pad for tonal content) and runs the full structural analysis, so we can confirm
the Essentia path (EDMA key + RhythmExtractor2013 + BeatsLoudness downbeats)
activates and produces sane numbers. Works headless; no real audio needed.
"""
import os
import tempfile

import numpy as np
import soundfile as sf

from desktop_app.analysis import analyze_structure, backends


def make_dance_wav(path: str, sr: int = 44100, bpm: float = 128.0, secs: float = 24.0) -> None:
    n = int(sr * secs)
    t = np.arange(n) / sr
    beat = 60.0 / bpm
    y = np.zeros(n, dtype=float)

    # Kick on every beat, louder on the downbeat (every 4th beat).
    dur = int(0.12 * sr)
    env = np.exp(-np.linspace(0, 8, dur))
    kick = np.sin(2 * np.pi * 55.0 * np.arange(dur) / sr) * env
    n_beats = int(secs / beat)
    for i in range(n_beats):
        start = int(i * beat * sr)
        end = min(start + dur, n)
        amp = 1.0 if i % 4 == 0 else 0.45
        y[start:end] += amp * kick[: end - start]

    # C-major triad pad (C-E-G) for key detection.
    for f in (261.63, 329.63, 392.00):
        y += 0.06 * np.sin(2 * np.pi * f * t)

    y = 0.8 * y / max(np.max(np.abs(y)), 1e-9)
    sf.write(path, y.astype(np.float32), sr)


if __name__ == "__main__":
    print("backends:", backends())
    wav = os.path.join(tempfile.gettempdir(), "wavemash_dance_test.wav")
    make_dance_wav(wav)

    a = analyze_structure(wav)
    print(f"bpm           : {a['bpm']}  (expected ~128)")
    print(f"key           : {a['key']}  camelot={a['camelot']}  conf={a['key_confidence']}")
    print(f"downbeats     : {len(a['downbeats'])}  first={a['downbeats'][:6]}")
    print(f"cue_in/cue_out: {a['cue_in']} / {a['cue_out']}")
    print(f"sections      : {[(s['label'], s['start'], s['end']) for s in a['sections']]}")

    ok = a["bpm"] > 0 and a["downbeats"] and a["key"] != "Unknown"
    print("RESULT        :", "OK" if ok else "CHECK OUTPUT")
