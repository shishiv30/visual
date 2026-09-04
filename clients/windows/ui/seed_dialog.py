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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.ui.qtutil import (
    apply_dialog_button_icons,
    bgr_to_pixmap,
    fit_image_display,
    image_point_to_widget,
)
from clients.windows.ui.theme import SPACE_PANEL
from core.i18n import t
from core.person_roi import first_frame_bgr


class SeedCanvas(QWidget):
    """Video canvas that scales with the widget while keeping image coordinates stable."""

    boxCommitted = Signal()

    def __init__(self, pixmap: QPixmap | None = None, parent=None) -> None:
        super().__init__(parent)
        self._source: QPixmap | None = pixmap
        self._box_norm: tuple[float, float, float, float] | None = None
        self._origin: QPoint | None = None
        self._drag_rect = QRect()
        self.setMinimumSize(320, 180)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setStyleSheet("background:#000;")
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_frame(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._origin = None
        self._drag_rect = QRect()
        self.update()

    def set_box_norm(self, box: tuple[float, float, float, float] | None) -> None:
        self._box_norm = box
        self.update()

    def box_norm(self) -> tuple[float, float, float, float] | None:
        if self._drag_rect.width() >= 2 and self._drag_rect.height() >= 2:
            return self._widget_rect_to_norm(self._drag_rect.normalized())
        return self._box_norm

    def _transform(self):
        if self._source is None or self._source.isNull():
            return None
        return fit_image_display(
            self._source.width(),
            self._source.height(),
            self.width(),
            self.height(),
        )

    def _widget_rect_to_norm(self, rect: QRect) -> tuple[float, float, float, float] | None:
        transform = self._transform()
        if transform is None:
            return None
        scale, x_offset, y_offset, _, _, image_w, image_h = transform
        if scale <= 0 or image_w <= 0 or image_h <= 0:
            return None
        left = (rect.left() - x_offset) / scale
        top = (rect.top() - y_offset) / scale
        right = (rect.right() - x_offset) / scale
        bottom = (rect.bottom() - y_offset) / scale
        left = max(0.0, min(float(image_w), left))
        top = max(0.0, min(float(image_h), top))
        right = max(0.0, min(float(image_w), right))
        bottom = max(0.0, min(float(image_h), bottom))
        if right - left < 8 or bottom - top < 8:
            return None
        return (
            left / image_w,
            top / image_h,
            right / image_w,
            bottom / image_h,
        )

    def _norm_to_widget_rect(self, box: tuple[float, float, float, float]) -> QRect:
        transform = self._transform()
        if transform is None:
            return QRect()
        scale, x_offset, y_offset, _, _, image_w, image_h = transform
        x1, y1, x2, y2 = box
        wx1, wy1 = image_point_to_widget(
            x1 * image_w,
            y1 * image_h,
            scale=scale,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        wx2, wy2 = image_point_to_widget(
            x2 * image_w,
            y2 * image_h,
            scale=scale,
            x_offset=x_offset,
            y_offset=y_offset,
        )
        return QRect(
            int(round(wx1)),
            int(round(wy1)),
            max(1, int(round(wx2 - wx1))),
            max(1, int(round(wy2 - wy1))),
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = event.position().toPoint()
        self._drag_rect = QRect(self._origin, self._origin)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._origin is None:
            return
        self._drag_rect = QRect(self._origin, event.position().toPoint())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._origin is None:
            return
        self._drag_rect = QRect(self._origin, event.position().toPoint())
        self._origin = None
        self.update()
        if self._widget_rect_to_norm(self._drag_rect.normalized()) is not None:
            self._box_norm = self._widget_rect_to_norm(self._drag_rect.normalized())
            self._drag_rect = QRect()
            self.boxCommitted.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._source is None or self._source.isNull():
            return
        transform = self._transform()
        if transform is None:
            return
        scale, x_offset, y_offset, display_w, display_h, _, _ = transform
        scaled = self._source.scaled(
            int(round(display_w)),
            int(round(display_h)),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(int(round(x_offset)), int(round(y_offset)), scaled)
        box_rect = QRect()
        if self._drag_rect.width() >= 2 and self._drag_rect.height() >= 2:
            box_rect = self._drag_rect.normalized()
        elif self._box_norm is not None:
            box_rect = self._norm_to_widget_rect(self._box_norm)
        if box_rect.width() >= 2 and box_rect.height() >= 2:
            painter.setPen(QPen(Qt.GlobalColor.green, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(box_rect)


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
        layout.addWidget(self._canvas, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
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
