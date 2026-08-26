"""BGR ndarray → QImage; bundled button icons."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QDialogButtonBox, QWidget

from core.i18n import t

ICONS_DIR = Path(__file__).resolve().parent / "icons"


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


def apply_dialog_button_icons(box: QDialogButtonBox) -> None:
    ok = box.button(QDialogButtonBox.StandardButton.Ok)
    cancel = box.button(QDialogButtonBox.StandardButton.Cancel)
    if ok is not None:
        set_button_icon(ok, "ok")
        ok.setText(t("ok"))
    if cancel is not None:
        set_button_icon(cancel, "cancel")
        cancel.setText(t("cancel"))


def bgr_to_pixmap(bgr: np.ndarray, max_width: int | None = None) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
    pix = QPixmap.fromImage(image)
    if max_width is not None and pix.width() > max_width:
        pix = pix.scaledToWidth(max_width)
    return pix


def format_duration_ms(duration_ms: int, *, image: bool = False) -> str:
    if image or duration_ms <= 0:
        return "--"
    total = int(round(duration_ms / 1000.0))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


button_icon = button_icon
apply_dialog_button_icons = apply_dialog_button_icons
format_duration_ms = format_duration_ms
