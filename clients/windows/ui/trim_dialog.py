"""Trim a source video to at most 120 seconds."""

from __future__ import annotations

from pathlib import Path

import cv2
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
)

from clients.windows.pipeline.normalize import MAX_SECONDS, probe_duration_ms
from clients.windows.ui.qtutil import apply_dialog_button_icons, bgr_to_pixmap
from clients.windows.ui.theme import SPACE_PANEL
from core.i18n import t


class TrimDialog(QDialog):
    def __init__(self, src: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Trim video (max 2 minutes)"))
        self._src = src
        self._duration_s = max(probe_duration_ms(src) / 1000.0, 0.1)
        self._cap = cv2.VideoCapture(str(src))

        self._preview = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(480, 270)

        self._in = QSlider(Qt.Orientation.Horizontal)
        self._out = QSlider(Qt.Orientation.Horizontal)
        max_ms = int(self._duration_s * 1000)
        for slider in (self._in, self._out):
            slider.setRange(0, max_ms)
        self._in.setValue(0)
        window = min(int(MAX_SECONDS * 1000), max_ms)
        self._out.setValue(window)

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._in.valueChanged.connect(self._on_change)
        self._out.valueChanged.connect(self._on_change)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(self._preview)
        row = QHBoxLayout()
        self._in_label = QLabel()
        row.addWidget(self._in_label)
        row.addWidget(self._in)
        layout.addLayout(row)
        row2 = QHBoxLayout()
        self._out_label = QLabel()
        row2.addWidget(self._out_label)
        row2.addWidget(self._out)
        layout.addLayout(row2)
        layout.addWidget(self._label)
        layout.addWidget(self._buttons)
        apply_dialog_button_icons(self._buttons)
        self.retranslate()
        self._on_change()

    def retranslate(self) -> None:
        self.setWindowTitle(t("Trim video (max 2 minutes)"))
        self._in_label.setText(t("In"))
        self._out_label.setText(t("Out"))
        apply_dialog_button_icons(self._buttons)

    def start_s(self) -> float:
        lo, hi = self._range_s()
        return lo

    def duration_s(self) -> float:
        lo, hi = self._range_s()
        return hi - lo

    def _range_s(self) -> tuple[float, float]:
        a = self._in.value() / 1000.0
        b = self._out.value() / 1000.0
        if b < a:
            a, b = b, a
        if b - a > MAX_SECONDS:
            b = a + MAX_SECONDS
        if b - a < 0.2:
            b = min(self._duration_s, a + 0.2)
        return a, b

    def _on_change(self) -> None:
        lo, hi = self._range_s()
        self._label.setText(
            t("Clip {lo:.1f}s → {hi:.1f}s ({dur:.1f}s, max {max:.0f}s)", lo=lo, hi=hi, dur=hi - lo, max=MAX_SECONDS)
        )
        if self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_POS_MSEC, lo * 1000.0)
            ok, frame = self._cap.read()
            if ok and frame is not None:
                self._preview.setPixmap(bgr_to_pixmap(frame, max_width=640))

    def closeEvent(self, event) -> None:  # noqa: N802
        self._cap.release()
        super().closeEvent(event)
