"""BPM/Key metadata refresh jobs for the main window."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon

from library import apply_track_metadata, needs_bpm_key_update
from desktop_app.archive_store import save_archive

if TYPE_CHECKING:
    from desktop_app.app import MainWindow

TrackJob = tuple[str, str, str, str, str]


class MetadataController:
    def __init__(self, window: MainWindow) -> None:
        self.w = window

    @property
    def job(self):
        return self.w._metadata_job

    @job.setter
    def job(self, value) -> None:
        self.w._metadata_job = value

    def _tracks_from_records(self, recs: list[dict[str, Any]]) -> list[TrackJob]:
        tracks: list[TrackJob] = []
        for rec in recs:
            path = str(rec.get("path", ""))
            if path and os.path.isfile(path):
                tracks.append((
                    str(rec.get("id", "")),
                    str(rec.get("artist", "")),
                    str(rec.get("title", "")),
                    str(rec.get("url", "")),
                    path,
                ))
        return tracks

    def start_refresh(self, *, quiet: bool = False, only_missing: bool = True) -> None:
        if self.job is not None:
            msg = "상세정보 업데이트가 이미 진행 중입니다."
            if quiet:
                self.w.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Information, 2500)
            else:
                self.w.status.setText(msg)
            return

        selected = self.w.selected_records()
        if selected:
            recs = [r for r in selected if needs_bpm_key_update(r)] if only_missing else selected
        else:
            recs = (
                [r for r in self.w.records if needs_bpm_key_update(r)]
                if only_missing
                else list(self.w.records)
            )

        tracks = self._tracks_from_records(recs)
        if not tracks:
            msg = "업데이트할 곡이 없습니다. (BPM·Key가 모두 채워져 있음)"
            if quiet:
                self.w.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Information, 3000)
            else:
                QMessageBox.information(self.w, "WaveMash", msg)
            return

        self._run_job(tracks, quiet=quiet, finished_handler=self.on_finished)

    def start_full_mik_sync(self, *, quiet: bool = False) -> None:
        if self.job is not None:
            msg = "메타데이터 작업이 이미 진행 중입니다."
            if quiet:
                self.w.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Information, 2500)
            else:
                self.w.status.setText(msg)
            return

        selected = self.w.selected_records()
        recs = selected if selected else list(self.w.records)
        tracks = self._tracks_from_records(recs)
        if not tracks:
            msg = "동기화할 WAV 파일이 없습니다."
            if quiet:
                self.w.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Warning, 3000)
            else:
                QMessageBox.information(self.w, "WaveMash", msg)
            return

        from mik_metadata import invalidate_mik_cache

        invalidate_mik_cache()
        self._run_job(
            tracks,
            quiet=quiet,
            status_prefix="MIK 동기화",
            tray_start=f"Mixed In Key 동기화 {len(tracks)}곡 시작",
            finished_handler=self.on_mik_finished,
        )

    def _run_job(
        self,
        tracks: list[TrackJob],
        *,
        quiet: bool,
        status_prefix: str = "BPM/Key 조회",
        tray_start: str = "",
        finished_handler,
    ) -> None:
        self.w._metadata_refresh_total = len(tracks)
        self.w.status.setText(f"{status_prefix} 중... (0/{len(tracks)})")
        job = self.w.pool.start_metadata_refresh(tracks, force=True)
        self.job = job
        job.signals.progress.connect(self.on_progress)
        job.signals.one_done.connect(self.on_one_done)
        job.signals.finished.connect(finished_handler)
        job.signals.failed.connect(self.on_failed)
        if quiet and tray_start:
            self.w.tray.showMessage(
                "WaveMash",
                tray_start,
                QSystemTrayIcon.Information,
                2500,
            )

    def on_progress(self, p: float, message: str) -> None:
        self.w.progress.setValue(int(max(0.0, min(1.0, p)) * 100))
        self.w.status.setText(message)

    def on_failed(self, error: str) -> None:
        self.job = None
        self.w.status.setText(f"상세정보 업데이트 실패: {error}")
        self.w.tray.showMessage(
            "WaveMash",
            f"상세정보 업데이트 실패: {error}",
            QSystemTrayIcon.Warning,
            4000,
        )

    def on_one_done(self, track_id: str, payload: object) -> None:
        rec = next(
            (r for r in self.w.records if str(r.get("id")) == str(track_id)),
            None,
        )
        if rec is None or not isinstance(payload, dict):
            return
        energy = payload.get("energy_level")
        if apply_track_metadata(
            rec,
            bpm=payload.get("bpm"),
            key=payload.get("key"),
            camelot_key=str(payload.get("camelot_key") or payload.get("camelot") or ""),
            energy_level=int(energy) if energy else None,
            bpm_source=str(payload.get("source") or ""),
            beat_offset_sec=payload.get("beat_offset_sec"),
        ):
            for deck_id in ("a", "b"):
                loaded = self.w._deck_records.get(deck_id)
                if loaded and str(loaded.get("id")) == str(track_id):
                    self.w._set_deck_cover(deck_id, rec)

    def _finish_common(self, count: int, *, ok_msg: str, fail_msg: str) -> None:
        self.job = None
        save_archive(self.w.records)
        total = getattr(self.w, "_metadata_refresh_total", 0)
        if count:
            msg = ok_msg.format(count=count, total=total)
            icon = QSystemTrayIcon.Information
        else:
            msg = fail_msg
            icon = QSystemTrayIcon.Warning
        self.w.status.setText(msg)
        self.w.progress.setValue(100)
        self.w.render_table()
        self.w.tray.showMessage("WaveMash", msg, icon, 4000)

    def on_finished(self, count: int) -> None:
        self._finish_common(
            count,
            ok_msg="상세정보 업데이트 완료: {count}/{total}곡",
            fail_msg=(
                "BPM/Key를 찾지 못했습니다. "
                "WAV 경로·MIK 분석·GETSONGBPM_API_KEY를 확인하세요."
            ),
        )

    def on_mik_finished(self, count: int) -> None:
        self._finish_common(
            count,
            ok_msg="MIK 동기화 완료: {count}/{total}곡",
            fail_msg=(
                "MIK에서 가져온 메타데이터가 없습니다. "
                "MIK에서 폴더/플리를 분석했는지 확인하세요."
            ),
        )
