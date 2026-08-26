"""Seek, person box, and logical in/out before analysis."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clients.windows.pipeline.clip_range import play_window_ms
from clients.windows.store.library import ClipKind, ClipMeta, SeedMark, load_meta, media_path
from clients.windows.ui.qtutil import bgr_to_pixmap, format_duration_ms, set_button_icon
from clients.windows.ui.report_layout import add_text_stack
from clients.windows.ui.seed_dialog import SeedCanvas
from clients.windows.ui.theme import BLUE, SPACE_PANEL, SPACE_TEXT
from clients.windows.ui.timeline_strip import TimelineStrip
from core.i18n import t


class PreparePage(QWidget):
    back_requested = Signal()
    analysis_requested = Signal(str, list, int, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preparePage")
        self._meta: ClipMeta | None = None
        self._cap: cv2.VideoCapture | None = None
        self._fps = 30.0
        self._t_ms = 0.0
        self._frame_index = 0
        self._seeds: dict[int, SeedMark] = {}
        self._in_ms = 0
        self._out_ms: int | None = None

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        blank = np.zeros((180, 320, 3), dtype=np.uint8)
        self._canvas = SeedCanvas(bgr_to_pixmap(blank, max_width=720))
        self._canvas.boxCommitted.connect(self._on_box_committed)

        self._time = QLabel()
        self._timeline = TimelineStrip()
        self._timeline.playheadChanged.connect(self._on_playhead)
        self._timeline.rangeChanged.connect(self._on_range)

        self._start_btn = QPushButton()
        set_button_icon(self._start_btn, "ok", BLUE)
        self._start_btn.clicked.connect(self._start)
        self._back_btn = QPushButton()
        self._back_btn.clicked.connect(self._on_back)

        self._seed_list = QWidget()
        self._seed_list_layout = QVBoxLayout(self._seed_list)
        self._seed_list_layout.setContentsMargins(0, 0, 0, 0)
        self._seed_list_layout.setSpacing(SPACE_TEXT)
        self._range = QLabel()
        self._range.setWordWrap(True)

        bar = QHBoxLayout()
        bar.addWidget(self._back_btn)
        bar.addWidget(self._start_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(self._hint)
        layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._time)
        layout.addWidget(self._timeline)
        layout.addLayout(bar)
        layout.addWidget(self._range)
        layout.addWidget(self._seed_list)
        self.retranslate()

    def retranslate(self) -> None:
        self._hint.setText(t("seed_hint"))
        self._start_btn.setText(t("seed_start"))
        set_button_icon(self._start_btn, "ok", BLUE)
        self._back_btn.setText(t("back"))
        self._refresh_labels()

    def open_clip(self, clip_id: str) -> None:
        self._release()
        self._meta = load_meta(clip_id)
        loaded = list(self._meta.seeds)
        if not loaded and self._meta.seed_box is not None:
            loaded = [SeedMark(t_ms=0.0, box=self._meta.seed_box)]
        start, end = play_window_ms(self._meta)
        self._in_ms = int(self._meta.play_start_ms or 0)
        self._out_ms = self._meta.play_end_ms
        path = media_path(self._meta)
        if self._meta.kind == ClipKind.IMAGE:
            self._seeds = {0: loaded[0]} if loaded else {}
            bgr = cv2.imread(str(path))
            self._timeline.hide()
            if bgr is not None:
                self._show_bgr(bgr, 0.0, 0)
            self._refresh_labels()
            return
        self._timeline.show()
        self._cap = cv2.VideoCapture(str(path))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 30.0) or 30.0
        self._seeds = self._seeds_by_frame(loaded, self._fps)
        duration = int(self._meta.duration_ms) or 1
        self._timeline.bind_video(path, duration)
        if self._meta.play_end_ms is not None:
            self._out_ms = int(end)
        self._in_ms = int(start) if self._meta.play_start_ms else self._in_ms
        self._timeline.set_range(self._in_ms, self._out_ms)
        self._sync_keyframes()
        self._seek_ms(self._in_ms)
        self._refresh_labels()

    def _on_back(self) -> None:
        self._release()
        self.back_requested.emit()

    def _release(self) -> None:
        self._timeline.clear()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _on_playhead(self, t_ms: int) -> None:
        self._seek_ms(t_ms)

    def _on_range(self, in_ms: int, out_ms: int) -> None:
        self._in_ms = in_ms
        self._out_ms = out_ms
        self._refresh_labels()

    def _seek_ms(self, t_ms: int) -> None:
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_MSEC, float(max(0, t_ms)))
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            return
        shown = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        frame_index = max(0, int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        if shown <= 0.0:
            shown = float(t_ms)
        self._show_bgr(bgr, shown, frame_index)

    def _show_bgr(self, bgr, t_ms: float, frame_index: int) -> None:
        self._t_ms = t_ms
        self._frame_index = frame_index
        pix = bgr_to_pixmap(bgr, max_width=720)
        self._canvas.set_frame(pix)
        mark = self._seeds.get(frame_index) or self._seed_near(t_ms)
        self._canvas.set_box_norm(None if mark is None else mark.box)
        self._timeline.set_playhead_ms(int(t_ms))
        self._refresh_labels()

    def _seeds_by_frame(self, seeds: list[SeedMark], fps: float) -> dict[int, SeedMark]:
        frame_ms = 1000.0 / max(fps, 1.0)
        keyed: dict[int, SeedMark] = {}
        for item in seeds:
            keyed[int(round(item.t_ms / frame_ms))] = item
        return keyed

    def _seed_near(self, t_ms: float) -> SeedMark | None:
        hit: SeedMark | None = None
        best = 40.0
        for item in self._seeds.values():
            delta = abs(item.t_ms - t_ms)
            if delta <= best:
                best = delta
                hit = item
        return hit

    def _sync_keyframes(self) -> None:
        self._timeline.set_keyframes([int(item.t_ms) for item in self._seeds.values()])

    def _on_box_committed(self) -> None:
        box = self._canvas.box_norm()
        if box is None:
            return
        key = self._frame_index
        self._seeds[key] = SeedMark(t_ms=self._t_ms, box=box)
        self._sync_keyframes()
        self._refresh_labels()

    def _start(self) -> None:
        if self._meta is None:
            return
        if not self._seeds:
            QMessageBox.information(self, t("seed_empty_title"), t("seed_need_box"))
            return
        seeds = sorted(self._seeds.values(), key=lambda item: item.t_ms)
        self.analysis_requested.emit(
            self._meta.clip_id, seeds, self._in_ms, self._out_ms
        )

    def _refresh_labels(self) -> None:
        total = 0
        if self._meta is not None:
            total = self._meta.duration_ms
        self._time.setText(
            f"{format_duration_ms(int(self._t_ms))} / {format_duration_ms(total)}  f{self._frame_index}"
        )
        out = self._out_ms if self._out_ms is not None else total
        self._range.setText(
            t(
                "seed_range",
                lo=self._in_ms / 1000.0,
                hi=(out / 1000.0) if out else 0.0,
            )
        )
        while self._seed_list_layout.count():
            item = self._seed_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        if self._seeds:
            lines = [t("seed_list")]
            for mark in sorted(self._seeds.values(), key=lambda m: m.t_ms):
                lines.append(f"t={mark.t_ms:.0f}ms")
            add_text_stack(self._seed_list_layout, lines)
        else:
            add_text_stack(self._seed_list_layout, [t("seed_list") + " —"])
