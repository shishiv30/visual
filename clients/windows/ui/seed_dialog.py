"""First-frame person box dialog."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from clients.windows.ui.qtutil import apply_dialog_button_icons, bgr_to_pixmap
from clients.windows.ui.theme import SPACE_PANEL
from core.i18n import t
from core.person_roi import first_frame_bgr


class SeedCanvas(QLabel):
    boxCommitted = Signal()

    def __init__(self, pixmap: QPixmap, parent=None) -> None:
        super().__init__(parent)
        self._pixmap = pixmap
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self._origin: QPoint | None = None
        self._rect = QRect()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_frame(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self._origin = None
        self._rect = QRect()
        self.update()

    def set_box_norm(self, box: tuple[float, float, float, float] | None) -> None:
        if box is None:
            self._rect = QRect()
            self.update()
            return
        width = max(1, self._pixmap.width())
        height = max(1, self._pixmap.height())
        x1, y1, x2, y2 = box
        self._rect = QRect(
            int(x1 * width),
            int(y1 * height),
            max(1, int((x2 - x1) * width)),
            max(1, int((y2 - y1) * height)),
        )
        self.update()

    def box_norm(self) -> tuple[float, float, float, float] | None:
        rect = self._rect.normalized()
        if rect.width() < 8 or rect.height() < 8:
            return None
        w = max(1, self._pixmap.width())
        h = max(1, self._pixmap.height())
        return (
            rect.left() / w,
            rect.top() / h,
            rect.right() / w,
            rect.bottom() / h,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.position().toPoint()
            self._rect = QRect(self._origin, self._origin)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is None:
            return
        self._rect = QRect(self._origin, event.position().toPoint())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._origin is None:
            return
        self._rect = QRect(self._origin, event.position().toPoint())
        self._origin = None
        self.update()
        if self.box_norm() is not None:
            self.boxCommitted.emit()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        rect = self._rect.normalized()
        if rect.width() < 2 or rect.height() < 2:
            return
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.green, 2, Qt.PenStyle.SolidLine))
        painter.drawRect(rect)


class SeedDialog(QDialog):
    def __init__(self, media: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("Select the person"))
        self._box: tuple[float, float, float, float] | None = None
        frame = first_frame_bgr(str(media))
        if frame is None:
            raise ValueError("cannot read first frame")
        pix = bgr_to_pixmap(frame, max_width=720)
        self._canvas = SeedCanvas(pix)
        hint = QLabel(t("Click the filmstrip to seek; green diamonds are saved boxes (click to jump). Drag the blue start/end edges to trim. Shift+wheel zooms. Draw a person box — it saves for this frame; draw again on the same frame to replace."))
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._accept)
        self._buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(hint)
        layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._buttons)
        apply_dialog_button_icons(self._buttons)

    def seed_box(self) -> tuple[float, float, float, float] | None:
        return self._box

    def _accept(self) -> None:
        box = self._canvas.box_norm()
        if box is None:
            QMessageBox.information(self, t("No box"), t("Draw a person box before confirming."))
            return
        self._box = box
        self.accept()
