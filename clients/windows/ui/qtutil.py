"""BGR ndarray → QImage; bundled button icons."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QDialogButtonBox, QPushButton, QWidget

from clients.windows.ui.theme import TERRAIN_BLACK
from core.i18n import t

ICONS_DIR = Path(__file__).resolve().parent / "icons"
FLOATING_BACK_MARGIN = 12
FLOATING_BACK_SIZE = 44


def _svg_pixmap(name: str, color: QColor, size: int = 16) -> QPixmap:
    renderer = QSvgRenderer(str(ICONS_DIR / f"{name}.svg"))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pix.rect(), color)
    painter.end()
    return pix


def _diamond_pixmap(color: QColor, size: int = 18) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    outlined = color == TERRAIN_BLACK
    width = 1.0 if outlined else 0.0
    inset = max(1.0, width / 2.0 + 0.5)
    cx = size / 2.0
    cy = size / 2.0
    radius = size / 2.0 - inset
    path = QPainterPath()
    path.moveTo(cx, cy - radius)
    path.lineTo(cx + radius, cy)
    path.lineTo(cx, cy + radius)
    path.lineTo(cx - radius, cy)
    path.closeSubpath()
    painter.setBrush(color)
    if outlined:
        painter.setPen(QPen(QColor("#FFFFFF"), width))
    else:
        painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(path)
    painter.end()
    return pix


def button_icon(name: str, widget: QWidget | None = None) -> QIcon:
    palette = widget.palette() if widget is not None else QPalette()
    role = widget.foregroundRole() if widget is not None else QPalette.ColorRole.ButtonText
    icon = QIcon()
    icon.addPixmap(
        _svg_pixmap(name, palette.color(QPalette.ColorGroup.Active, role)),
        QIcon.Mode.Normal,
    )
    icon.addPixmap(
        _svg_pixmap(name, palette.color(QPalette.ColorGroup.Disabled, role)),
        QIcon.Mode.Disabled,
    )
    return icon


def set_button_icon(
    button: QAbstractButton,
    name: str,
    color: QColor | None = None,
    *,
    restyle: bool = True,
) -> None:
    if color is None:
        button.setIcon(button_icon(name, button))
        if button.isEnabled():
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        return
    palette = button.palette()
    palette.setColor(QPalette.ColorRole.ButtonText, color)
    palette.setColor(QPalette.ColorRole.WindowText, color)
    button.setPalette(palette)
    if restyle:
        hover = QColor(color).lighter(118)
        button.setStyleSheet(
            f"""
            QPushButton {{
                color: #ffffff;
                background: {color.name()};
                border: 1px solid {color.name()};
                padding: 1px 8px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {hover.name()};
                color: #ffffff;
            }}
            QPushButton:checked {{
                border: 2px solid #ffffff;
            }}
            """
        )
    icon = QIcon()
    fg = QColor("#FFFFFF") if restyle else color
    icon.addPixmap(_svg_pixmap(name, fg), QIcon.Mode.Normal)
    icon.addPixmap(
        _svg_pixmap(name, palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText)),
        QIcon.Mode.Disabled,
    )
    button.setIcon(icon)
    if button.isEnabled():
        button.setCursor(Qt.CursorShape.PointingHandCursor)
    else:
        button.unsetCursor()


def make_floating_back(parent: QWidget) -> QPushButton:
    """Top-left floating back control shared by non-list pages."""
    button = QPushButton(parent)
    button.setObjectName("floatingBack")
    button.setFixedSize(FLOATING_BACK_SIZE, FLOATING_BACK_SIZE)
    button.raise_()
    place_floating_back(button, parent)
    return button


def place_floating_back(
    button: QPushButton,
    parent: QWidget,
    *,
    margin: int = FLOATING_BACK_MARGIN,
) -> None:
    button.move(margin, margin)
    button.raise_()


def style_floating_back(button: QPushButton, *, tooltip: str | None = None) -> None:
    button.setText("")
    if tooltip is not None:
        button.setToolTip(tooltip)
    set_button_icon(button, "back", QColor("#F5F5F5"), restyle=False)


def apply_dialog_button_icons(box: QDialogButtonBox) -> None:
    ok = box.button(QDialogButtonBox.StandardButton.Ok)
    cancel = box.button(QDialogButtonBox.StandardButton.Cancel)
    if ok is not None:
        set_button_icon(ok, "ok")
        ok.setText(t("OK"))
    if cancel is not None:
        set_button_icon(cancel, "cancel")
        cancel.setText(t("Cancel"))


def bgr_to_pixmap(bgr: np.ndarray, max_width: int | None = None) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
    pix = QPixmap.fromImage(image)
    if max_width is not None and pix.width() > max_width:
        pix = pix.scaledToWidth(max_width)
    return pix


def scaled_display_size(width: int, height: int, max_width: int | None) -> tuple[int, int]:
    """Match ``bgr_to_pixmap`` width/height after optional downscale."""
    if max_width is None or width <= max_width:
        return width, height
    scaled_w = max_width
    scaled_h = max(1, int(round(height * max_width / width)))
    return scaled_w, scaled_h


def fit_image_display(
    image_width: int,
    image_height: int,
    widget_width: int,
    widget_height: int,
) -> tuple[float, float, float, float, float, int, int]:
    """Return scale, x_offset, y_offset, display_w, display_h, image_w, image_h."""
    if image_width <= 0 or image_height <= 0 or widget_width <= 0 or widget_height <= 0:
        return (
            1.0,
            0.0,
            0.0,
            float(max(widget_width, 0)),
            float(max(widget_height, 0)),
            image_width,
            image_height,
        )
    scale = min(widget_width / image_width, widget_height / image_height)
    display_w = image_width * scale
    display_h = image_height * scale
    x_offset = (widget_width - display_w) / 2.0
    y_offset = (widget_height - display_h) / 2.0
    return scale, x_offset, y_offset, display_w, display_h, image_width, image_height


def widget_point_to_image(
    x: float,
    y: float,
    *,
    scale: float,
    x_offset: float,
    y_offset: float,
    display_width: float,
    display_height: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float] | None:
    """Map a widget click to full image pixels; None when outside the video area."""
    if scale <= 0:
        return None
    local_x = x - x_offset
    local_y = y - y_offset
    if local_x < 0 or local_y < 0 or local_x > display_width or local_y > display_height:
        return None
    image_x = local_x / scale
    image_y = local_y / scale
    if image_x < 0 or image_y < 0 or image_x > image_width or image_y > image_height:
        return None
    return round(image_x, 1), round(image_y, 1)


def image_point_to_widget(
    x: float,
    y: float,
    *,
    scale: float,
    x_offset: float,
    y_offset: float,
) -> tuple[float, float]:
    return x * scale + x_offset, y * scale + y_offset


def canvas_point_to_image(
    x: float,
    y: float,
    *,
    image_width: int,
    image_height: int,
    display_width: int,
    display_height: int,
) -> tuple[float, float]:
    """Map a click on a preview canvas back to full-resolution image pixels."""
    sx = image_width / max(1, display_width)
    sy = image_height / max(1, display_height)
    return round(x * sx, 1), round(y * sy, 1)


def format_duration_ms(duration_ms: int, *, image: bool = False) -> str:
    if image or duration_ms <= 0:
        return t("--")
    total = int(round(duration_ms / 1000.0))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


button_icon = button_icon
apply_dialog_button_icons = apply_dialog_button_icons
format_duration_ms = format_duration_ms
