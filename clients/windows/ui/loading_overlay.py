"""Opaque spinning loader — no progress bar, no see-through background."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from clients.windows.ui.theme import BLUE, INK, SPACE_TEXT
from core.i18n import t


class LoadingSpinner(QWidget):
    def __init__(self, diameter: int = 48, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self.setFixedSize(diameter, diameter)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._angle = 0
        self.show()
        self._timer.start(16)

    def stop(self) -> None:
        self._timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self.start()

    def hideEvent(self, event) -> None:
        self.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = 5.0
        rect = QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset)
        arc = QPen(BLUE)
        arc.setWidth(4)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        painter.drawArc(rect, int((90 - self._angle) * 16), -90 * 16)


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._spinner = LoadingSpinner(56, self)
        self._caption = QLabel()
        self._caption.setObjectName("loadingCaption")
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_TEXT)
        layout.addStretch()
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._caption)
        layout.addStretch()
        self.hide()
        self.retranslate()

    def retranslate(self) -> None:
        if self.property("kind") == "import":
            self._caption.setText(t("Uploading and loading…"))
        else:
            self._caption.setText(t("Analyzing pose…"))

    def show_kind(self, kind: str) -> None:
        self.setProperty("kind", kind)
        self.retranslate()
        self.hide()
        self.show()
        self.raise_()
        self._spinner.start()

    def dismiss(self) -> None:
        self._spinner.stop()
        self.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), INK)
