"""Zoomable filmstrip timeline for the prepare page."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path
from typing import Never

import cv2
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QGuiApplication,
    QMouseEvent,
    QNativeGestureEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QScrollBar, QWidget

from clients.windows.ui.qtutil import bgr_to_pixmap
from clients.windows.ui.theme import BLUE, INK, PASS_GREEN
from clients.windows.ui.timeline_math import (
    clamp_range,
    clamp_scroll_x,
    clamp_zoom,
    content_width_px,
    format_ruler_time,
    max_scroll_x,
    ms_to_x,
    nearest_keyframe_ms,
    ruler_tick_ms,
    x_to_ms,
    zoom_keeping_ms,
)

RULER_H = 22
FILM_H = 56
CELL_W = 88
HANDLE_HIT = 14
PLAYHEAD_HIT = 8
PAN_SLOP = 6
PAPER = QColor("#F5F5F5")
DIM = QColor(0, 0, 0, 140)
TICK = QColor("#6f6f6f")
_ZOOM_CURSOR: QCursor | None = None


def zoom_in_out_cursor() -> QCursor:
    global _ZOOM_CURSOR
    if _ZOOM_CURSOR is None:
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(PAPER, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(3, 3, 18, 18)
        painter.drawLine(18, 18, 27, 27)
        painter.drawLine(12, 7, 12, 17)
        painter.drawLine(7, 12, 17, 12)
        painter.drawLine(7, 27, 17, 27)
        painter.end()
        _ZOOM_CURSOR = QCursor(pix, 12, 12)
    return _ZOOM_CURSOR


class _DragKind(Enum):
    NONE = auto()
    IN_HANDLE = auto()
    OUT_HANDLE = auto()
    PLAYHEAD = auto()
    PAN = auto()


class TimelineStrip(QWidget):
    playheadChanged = Signal(int)
    rangeChanged = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(RULER_H + FILM_H + 14)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.grabGesture(Qt.GestureType.PinchGesture)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._duration_ms = 1
        self._in_ms = 0
        self._out_ms = 1
        self._playhead_ms = 0
        self._zoom = 1.0
        self._scroll_x = 0.0
        self._path: Path | None = None
        self._cap: cv2.VideoCapture | None = None
        self._thumbs: dict[int, QPixmap] = {}
        self._keyframes_ms: list[int] = []
        self._drag = _DragKind.NONE
        self._press = QPointF()
        self._press_scroll = 0.0
        self._panning = False
        self._trim_enabled = True

        self._scroll = QScrollBar(Qt.Orientation.Horizontal, self)
        self._scroll.setVisible(False)
        self._scroll.valueChanged.connect(self._on_scroll_bar)

    def bind_video(self, path: Path, duration_ms: int) -> None:
        self._release_cap()
        self._path = path
        self._thumbs.clear()
        self._keyframes_ms = []
        self._duration_ms = max(1, duration_ms)
        self._in_ms = 0
        self._out_ms = self._duration_ms
        self._playhead_ms = 0
        self._zoom = 1.0
        self._scroll_x = 0.0
        self._cap = cv2.VideoCapture(str(path))
        self._sync_scroll_bar()
        self.update()
        self._refresh_hover_cursor()

    def clear(self) -> None:
        self._release_cap()
        self._path = None
        self._thumbs.clear()
        self._keyframes_ms = []
        self.update()

    def set_range(self, in_ms: int, out_ms: int | None) -> None:
        self._in_ms, self._out_ms = clamp_range(in_ms, out_ms, self._duration_ms)
        self.update()

    def set_playhead_ms(self, t_ms: int) -> None:
        self._playhead_ms = max(0, min(int(t_ms), self._duration_ms))
        self.update()

    def set_keyframes(self, times_ms: list[int]) -> None:
        self._keyframes_ms = sorted({int(t) for t in times_ms})
        self.update()

    def set_trim_enabled(self, enabled: bool) -> None:
        self._trim_enabled = enabled
        self.update()

    def in_ms(self) -> int:
        return self._in_ms

    def out_ms(self) -> int:
        return self._out_ms

    def _film_rect(self) -> QRectF:
        return QRectF(0, RULER_H, self.width(), FILM_H)

    def _viewport_w(self) -> int:
        return max(1, self.width())

    def _x_of(self, t_ms: float) -> float:
        return ms_to_x(
            t_ms, float(self._duration_ms), self._viewport_w(), self._zoom, self._scroll_x
        )

    def _ms_of(self, x: float) -> int:
        return int(
            round(
                x_to_ms(
                    x,
                    float(self._duration_ms),
                    self._viewport_w(),
                    self._zoom,
                    self._scroll_x,
                )
            )
        )

    def _hit(self, pos: QPointF) -> _DragKind:
        x = pos.x()
        if abs(x - self._x_of(self._playhead_ms)) <= PLAYHEAD_HIT:
            return _DragKind.PLAYHEAD
        if self._trim_enabled and abs(x - self._x_of(self._in_ms)) <= HANDLE_HIT:
            return _DragKind.IN_HANDLE
        if self._trim_enabled and abs(x - self._x_of(self._out_ms)) <= HANDLE_HIT:
            return _DragKind.OUT_HANDLE
        return _DragKind.NONE

    def _hit_keyframe(self, pos: QPointF) -> int | None:
        return nearest_keyframe_ms(
            pos.x(),
            self._keyframes_ms,
            float(self._duration_ms),
            self._viewport_w(),
            self._zoom,
            self._scroll_x,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press = event.position()
        self._press_scroll = self._scroll_x
        self._panning = False
        key_ms = self._hit_keyframe(event.position())
        if key_ms is not None:
            self._drag = _DragKind.NONE
            self._emit_playhead(key_ms)
            return
        hit = self._hit(event.position())
        if hit is _DragKind.NONE:
            self._drag = _DragKind.PLAYHEAD
            self._seek_to_x(event.position().x())
        else:
            self._drag = hit
            if hit is _DragKind.IN_HANDLE:
                self._emit_playhead(self._in_ms)
            elif hit is _DragKind.OUT_HANDLE:
                self._emit_playhead(self._out_ms)
            elif hit is _DragKind.PLAYHEAD:
                pass
            elif hit is _DragKind.PAN or hit is _DragKind.NONE:
                pass
            else:
                _never: Never = hit
                raise RuntimeError(_never)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is _DragKind.NONE:
            self._apply_hover_cursor(event.position(), event.modifiers())
            return
        dx = event.position().x() - self._press.x()
        if self._drag is _DragKind.PLAYHEAD and not self._panning:
            touch = bool(event.source() == Qt.MouseEventSource.MouseEventSynthesizedBySystem)
            if touch and abs(dx) > PAN_SLOP and self._zoom > 1.0 + 1e-6:
                self._drag = _DragKind.PAN
                self._panning = True
        if self._drag is _DragKind.PAN:
            self._set_scroll(self._press_scroll - dx)
            return
        t_ms = self._ms_of(event.position().x())
        match self._drag:
            case _DragKind.IN_HANDLE:
                self._in_ms, self._out_ms = clamp_range(
                    t_ms, self._out_ms, self._duration_ms
                )
                self._emit_playhead(self._in_ms)
                self.rangeChanged.emit(self._in_ms, self._out_ms)
            case _DragKind.OUT_HANDLE:
                self._in_ms, self._out_ms = clamp_range(
                    self._in_ms, t_ms, self._duration_ms
                )
                self._emit_playhead(self._out_ms)
                self.rangeChanged.emit(self._in_ms, self._out_ms)
            case _DragKind.PLAYHEAD:
                self._seek_to_x(event.position().x())
            case _DragKind.PAN | _DragKind.NONE:
                return
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = _DragKind.NONE
            self._panning = False
            self._apply_hover_cursor(event.position(), event.modifiers())

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            factor = 1.08 if delta > 0 else 1 / 1.08
            self._apply_zoom(self._zoom * factor, event.position().x())
        else:
            self._set_scroll(self._scroll_x - delta * 0.5)
        self._apply_hover_cursor(event.position(), event.modifiers())
        event.accept()

    def event(self, event) -> bool:
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            if self.underMouse():
                self._refresh_hover_cursor()
        if event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch is not None:
                if pinch.state() == Qt.GestureState.GestureUpdated:
                    center = self.mapFromGlobal(pinch.centerPoint().toPoint())
                    self._apply_zoom(self._zoom * pinch.scaleFactor(), float(center.x()))
                return True
        return super().event(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and self.underMouse():
            self._refresh_hover_cursor()
        return super().eventFilter(watched, event)

    def hoverMoveEvent(self, event) -> None:
        if self._drag is _DragKind.NONE:
            self._apply_hover_cursor(event.position(), QGuiApplication.keyboardModifiers())
        super().hoverMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.unsetCursor()
        super().leaveEvent(event)

    def nativeGestureEvent(self, event: QNativeGestureEvent) -> bool:
        kind = event.gestureType()
        if kind == Qt.NativeGestureType.ZoomNativeGesture:
            self._apply_zoom(self._zoom * (1.0 + event.value()), event.position().x())
            return True
        if kind == Qt.NativeGestureType.BeginNativeGesture:
            return True
        if kind == Qt.NativeGestureType.EndNativeGesture:
            return True
        if kind == Qt.NativeGestureType.PanNativeGesture:
            return False
        if kind == Qt.NativeGestureType.SmartZoomNativeGesture:
            return False
        if kind == Qt.NativeGestureType.RotateNativeGesture:
            return False
        if kind == Qt.NativeGestureType.SwipeNativeGesture:
            return False
        _never: Never = kind
        raise RuntimeError(_never)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        bar_h = 12
        self._scroll.setGeometry(0, RULER_H + FILM_H, self.width(), bar_h)
        self._scroll_x = clamp_scroll_x(self._scroll_x, self._viewport_w(), self._zoom)
        self._sync_scroll_bar()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), INK)
        if self._path is None:
            return
        self._paint_ruler(painter)
        self._paint_film(painter)
        self._paint_dim(painter)
        self._paint_trim_edge(painter, self._in_ms, start=True)
        self._paint_trim_edge(painter, self._out_ms, start=False)
        self._paint_keyframes(painter)
        x = self._x_of(self._playhead_ms)
        painter.setPen(QPen(PAPER, 2))
        painter.drawLine(QPointF(x, 0), QPointF(x, RULER_H + FILM_H))

    def _paint_ruler(self, painter: QPainter) -> None:
        painter.fillRect(QRectF(0, 0, self.width(), RULER_H), QColor("#1a1a1a"))
        span = float(self._duration_ms)
        step = ruler_tick_ms(span, self._viewport_w(), self._zoom)
        fine = step < 1000.0
        painter.setPen(TICK)
        t_ms = 0.0
        while t_ms <= span + 0.1:
            x = self._x_of(t_ms)
            if -40 <= x <= self.width() + 40:
                painter.drawLine(QPointF(x, RULER_H - 6), QPointF(x, RULER_H))
                painter.setPen(PAPER)
                painter.drawText(int(x) + 3, 14, format_ruler_time(t_ms, fine=fine))
                painter.setPen(TICK)
            t_ms += step
        end_x = self._x_of(span)
        if abs(end_x - self._x_of(max(0.0, t_ms - step))) > 40:
            painter.drawLine(QPointF(end_x, RULER_H - 6), QPointF(end_x, RULER_H))
            painter.setPen(PAPER)
            painter.drawText(int(end_x) - 36, 14, format_ruler_time(span, fine=fine))

    def _paint_film(self, painter: QPainter) -> None:
        film = self._film_rect()
        painter.fillRect(film, QColor("#242424"))
        content = content_width_px(self._viewport_w(), self._zoom)
        n = max(1, int(round(content / CELL_W)))
        cell_w = content / n
        start_i = max(0, int(self._scroll_x / cell_w) - 1)
        end_i = min(n, int((self._scroll_x + self._viewport_w()) / cell_w) + 2)
        for i in range(start_i, end_i):
            x0 = i * cell_w - self._scroll_x
            t_ms = (i + 0.5) / n * self._duration_ms
            pix = self._thumb_at(t_ms)
            dest = QRectF(x0, RULER_H, cell_w, FILM_H)
            if pix is None:
                painter.fillRect(dest, QColor("#2a2a2a"))
            else:
                scaled = pix.scaled(
                    int(cell_w),
                    FILM_H,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(dest.toRect(), scaled)
            painter.setPen(QColor("#121212"))
            painter.drawRect(dest)

    def _paint_dim(self, painter: QPainter) -> None:
        film = self._film_rect()
        left = QRectF(film.left(), film.top(), max(0.0, self._x_of(self._in_ms)), FILM_H)
        right_x = self._x_of(self._out_ms)
        right = QRectF(right_x, film.top(), max(0.0, film.right() - right_x), FILM_H)
        painter.fillRect(left, DIM)
        painter.fillRect(right, DIM)

    def _paint_trim_edge(self, painter: QPainter, t_ms: int, *, start: bool) -> None:
        x = self._x_of(t_ms)
        top = float(RULER_H)
        bot = float(RULER_H + FILM_H)
        painter.setPen(QPen(BLUE, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        painter.drawLine(QPointF(x, top), QPointF(x, bot))
        wing = 10.0
        if start:
            painter.drawLine(QPointF(x, top), QPointF(x + wing, top))
            painter.drawLine(QPointF(x, bot), QPointF(x + wing, bot))
        else:
            painter.drawLine(QPointF(x, top), QPointF(x - wing, top))
            painter.drawLine(QPointF(x, bot), QPointF(x - wing, bot))

    def _paint_keyframes(self, painter: QPainter) -> None:
        y = float(RULER_H + 8)
        for t_ms in self._keyframes_ms:
            x = self._x_of(t_ms)
            if x < -12 or x > self.width() + 12:
                continue
            path = QPainterPath()
            path.moveTo(x, y - 6)
            path.lineTo(x + 5, y)
            path.lineTo(x, y + 6)
            path.lineTo(x - 5, y)
            path.closeSubpath()
            painter.fillPath(path, PASS_GREEN)
            painter.setPen(QPen(INK, 1))
            painter.drawPath(path)

    def _thumb_at(self, t_ms: float) -> QPixmap | None:
        if self._cap is None or not self._cap.isOpened():
            return None
        key = int(round(t_ms / 80.0) * 80)
        cached = self._thumbs.get(key)
        if cached is not None:
            return cached
        self._cap.set(cv2.CAP_PROP_POS_MSEC, float(key))
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            return None
        pix = bgr_to_pixmap(bgr, max_width=CELL_W * 2)
        self._thumbs[key] = pix
        return pix

    def _seek_to_x(self, x: float) -> None:
        self._emit_playhead(self._ms_of(x))
        self.update()

    def _emit_playhead(self, t_ms: int) -> None:
        self._playhead_ms = max(0, min(t_ms, self._duration_ms))
        self.playheadChanged.emit(self._playhead_ms)

    def _apply_zoom(self, zoom: float, anchor_x: float) -> None:
        self._zoom, self._scroll_x = zoom_keeping_ms(
            zoom,
            anchor_x,
            float(self._duration_ms),
            self._viewport_w(),
            self._zoom,
            self._scroll_x,
        )
        self._zoom = clamp_zoom(self._zoom)
        self._sync_scroll_bar()
        self.update()

    def _set_scroll(self, scroll_x: float) -> None:
        self._scroll_x = clamp_scroll_x(scroll_x, self._viewport_w(), self._zoom)
        self._sync_scroll_bar()
        self.update()

    def _on_scroll_bar(self, value: int) -> None:
        self._scroll_x = float(value)
        self.update()

    def _sync_scroll_bar(self) -> None:
        maximum = int(round(max_scroll_x(self._viewport_w(), self._zoom)))
        self._scroll.blockSignals(True)
        self._scroll.setRange(0, maximum)
        self._scroll.setPageStep(self._viewport_w())
        self._scroll.setValue(int(round(self._scroll_x)))
        self._scroll.setVisible(maximum > 0)
        self._scroll.setCursor(Qt.CursorShape.SizeHorCursor)
        self._scroll.blockSignals(False)

    def _refresh_hover_cursor(self) -> None:
        if not self.underMouse():
            return
        pos = self.mapFromGlobal(QCursor.pos())
        self._apply_hover_cursor(QPointF(pos), QGuiApplication.keyboardModifiers())

    def _apply_hover_cursor(self, pos: QPointF, modifiers: Qt.KeyboardModifiers) -> None:
        self.setCursor(self._cursor_for(pos, modifiers))

    def _cursor_for(self, pos: QPointF, modifiers: Qt.KeyboardModifiers):
        if self._path is None:
            return Qt.CursorShape.ArrowCursor
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            return zoom_in_out_cursor()
        if self._hit_keyframe(pos) is not None:
            return Qt.CursorShape.PointingHandCursor
        hit = self._hit(pos)
        match hit:
            case _DragKind.PLAYHEAD:
                return Qt.CursorShape.PointingHandCursor
            case _DragKind.IN_HANDLE | _DragKind.OUT_HANDLE:
                return Qt.CursorShape.SizeHorCursor
            case _DragKind.NONE | _DragKind.PAN:
                if max_scroll_x(self._viewport_w(), self._zoom) > 0:
                    return Qt.CursorShape.SizeHorCursor
                return Qt.CursorShape.IBeamCursor

    def _release_cap(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def closeEvent(self, event) -> None:  # noqa: N802
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._release_cap()
        super().closeEvent(event)
