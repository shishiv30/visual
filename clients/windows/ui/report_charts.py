"""Animated radar and score-over-time charts for the stage report."""

from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from clients.windows.ui.theme import (
    CAPTION_GRAY,
    CHART_AXIS,
    CHART_GRID,
    CHART_TRACK,
    DEEP_PURPLE,
    LIGHT_PURPLE,
    PAPER,
    TURN_CLEAN,
    TURN_FAULTY,
    UNKNOWN_GRAY,
    WATERMELON,
)
from core.i18n import t
from schemas.stage_report import FrameScorePoint, KeypointResult, TurnRecord


def _score_frac(score: float | None) -> float:
    if score is None:
        return 0.0
    return max(0.0, min(1.0, score / 100.0))


class ScorePieChart(QWidget):
    """Donut chart with score centered and caption below."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._score: float | None = None
        self._caption = ""
        self._ring_color = DEEP_PURPLE
        self._reveal = 0.0
        self._anim = QPropertyAnimation(self, b"reveal")
        self._anim.setDuration(650)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumSize(96, 134)
        # The caption is a 9pt metric name that wraps to two or three lines;
        # a fixed 134px leaves ~40px for it and clips the tail.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(134)

    def get_reveal(self) -> float:
        return self._reveal

    def set_reveal(self, value: float) -> None:
        self._reveal = max(0.0, min(1.0, float(value)))
        self.update()

    reveal = Property(float, get_reveal, set_reveal)

    def set_score(
        self,
        score: float | None,
        caption: str,
        *,
        ring_color: QColor | None = None,
    ) -> None:
        self._score = score
        self._caption = caption
        self._ring_color = ring_color or DEEP_PURPLE
        self._anim.stop()
        self.set_reveal(0.0)
        if score is not None:
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        ring_h = 78.0
        cx = w / 2.0
        cy = ring_h / 2.0 + 6.0
        outer = min(w - 16.0, ring_h - 8.0)
        rect = QRectF(cx - outer / 2.0, cy - outer / 2.0, outer, outer)
        track = QPen(CHART_TRACK)
        track.setWidth(8)
        painter.setPen(track)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)
        if self._score is not None:
            span = int(360 * 16 * _score_frac(self._score) * self._reveal)
            accent = QPen(self._ring_color)
            accent.setWidth(8)
            accent.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(accent)
            painter.drawArc(rect, 90 * 16, -span)
            painter.setPen(PAPER)
            font = QFont(self.font())
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - outer / 2.0, cy - outer / 2.0, outer, outer),
                int(Qt.AlignmentFlag.AlignCenter),
                f"{self._score:.0f}",
            )
        else:
            painter.setPen(UNKNOWN_GRAY)
            font = QFont(self.font())
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - outer / 2.0, cy - outer / 2.0, outer, outer),
                int(Qt.AlignmentFlag.AlignCenter),
                t("—"),
            )
        caption_font = QFont(self.font())
        caption_font.setPointSize(9)
        painter.setFont(caption_font)
        painter.setPen(CAPTION_GRAY)
        painter.drawText(
            QRectF(4, ring_h + 16, w - 8, self.height() - ring_h - 16),
            int(Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap),
            self._caption,
        )


class RadarChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[KeypointResult] = []
        self._reveal = 0.0
        self._anim = QPropertyAnimation(self, b"reveal")
        self._anim.setDuration(700)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumSize(220, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(220)

    def get_reveal(self) -> float:
        return self._reveal

    def set_reveal(self, value: float) -> None:
        self._reveal = max(0.0, min(1.0, float(value)))
        self.update()

    reveal = Property(float, get_reveal, set_reveal)

    def set_items(self, items: list[KeypointResult]) -> None:
        self._items = list(items)
        self._anim.stop()
        self.set_reveal(0.0)
        if self._items:
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = max(3, len(self._items) or 3)
        cx = self.width() / 2.0
        cy = self.height() / 2.0 + 6.0
        radius = min(self.width(), self.height()) / 2.0 - 36.0
        for ring in (0.25, 0.5, 0.75, 1.0):
            pen = QPen(CHART_GRID)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), radius * ring, radius * ring)
        axes = []
        for i in range(n):
            angle = -math.pi / 2.0 + i * 2.0 * math.pi / n
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            axes.append((angle, x, y))
            painter.setPen(CHART_AXIS)
            painter.drawLine(QPointF(cx, cy), QPointF(x, y))
        if not self._items:
            return
        poly = QPolygonF()
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        for i, item in enumerate(self._items):
            angle, _, _ = axes[i]
            frac = _score_frac(item.score) * self._reveal
            px = cx + radius * frac * math.cos(angle)
            py = cy + radius * frac * math.sin(angle)
            poly.append(QPointF(px, py))
            lx = cx + (radius + 22.0) * math.cos(angle)
            ly = cy + (radius + 22.0) * math.sin(angle)
            label = (item.name or item.id)[:8]
            painter.setPen(CAPTION_GRAY)
            painter.drawText(
                QRectF(lx - 40, ly - 8, 80, 16),
                int(Qt.AlignmentFlag.AlignCenter),
                label,
            )
        fill = QColor(DEEP_PURPLE)
        fill.setAlpha(70)
        painter.setBrush(fill)
        pen = QPen(DEEP_PURPLE)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPolygon(poly)


class TurnStripChart(QWidget):
    """One cell per segmented turn, laid out along the clip (design doc §7.4).

    A cell is placed at the turn's own position in the clip, so gaps read as
    traverses. Colour is the fault flag, not the score: a turn either carried a
    fault flag or it did not. Clicking a cell seeks to that turn's start.
    """

    seekRequested = Signal(int)

    ROW_TOP = 18.0
    ROW_H = 40.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._turns: list[TurnRecord] = []
        self._reveal = 0.0
        self._anim = QPropertyAnimation(self, b"reveal")
        self._anim.setDuration(700)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumSize(220, 88)
        self.setFixedHeight(88)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def get_reveal(self) -> float:
        return self._reveal

    def set_reveal(self, value: float) -> None:
        self._reveal = max(0.0, min(1.0, float(value)))
        self.update()

    reveal = Property(float, get_reveal, set_reveal)

    def set_turns(self, turns: list[TurnRecord]) -> None:
        self._turns = list(turns)
        self._anim.stop()
        self.set_reveal(0.0)
        if self._turns:
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        self.update()

    def _span(self) -> tuple[float, float]:
        if not self._turns:
            return 0.0, 1.0
        t0 = min(turn.t_start_ms for turn in self._turns)
        t1 = max(turn.t_end_ms for turn in self._turns)
        return t0, max(t1 - t0, 1.0)

    def _geom(self) -> tuple[float, float]:
        return 4.0, max(1.0, self.width() - 8.0)

    def _cells(self) -> list[tuple[QRectF, TurnRecord]]:
        if not self._turns:
            return []
        x0, width = self._geom()
        t0, span = self._span()
        cells: list[tuple[QRectF, TurnRecord]] = []
        for turn in self._turns:
            left = x0 + width * ((turn.t_start_ms - t0) / span)
            right = x0 + width * ((turn.t_end_ms - t0) / span)
            cells.append(
                (
                    QRectF(left, self.ROW_TOP, max(3.0, right - left - 2.0), self.ROW_H),
                    turn,
                )
            )
        return cells

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        cells = self._cells()
        if not cells:
            painter.setPen(UNKNOWN_GRAY)
            painter.drawText(
                QRectF(0, 0, self.width(), self.height()),
                int(Qt.AlignmentFlag.AlignCenter),
                t("—"),
            )
            return
        x0, width = self._geom()
        painter.setPen(CHART_TRACK)
        painter.drawLine(
            QPointF(x0, self.ROW_TOP + self.ROW_H + 6.0),
            QPointF(x0 + width, self.ROW_TOP + self.ROW_H + 6.0),
        )
        shown = max(1, int(round(len(cells) * self._reveal))) if self._reveal else 0
        for i, (rect, turn) in enumerate(cells):
            if i >= shown:
                break
            faulty = bool(turn.flags)
            color = QColor(TURN_FAULTY if faulty else TURN_CLEAN)
            fill = QColor(color)
            fill.setAlpha(150 if faulty else 110)
            painter.setBrush(fill)
            pen = QPen(color)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 3.0, 3.0)
            side = (turn.side or "")[:1].upper()
            if side and rect.width() >= 12.0:
                painter.setPen(PAPER)
                painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), side)
        painter.setPen(UNKNOWN_GRAY)
        painter.drawText(
            QRectF(x0, 0, width, 14.0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            t("{n} turns", n=len(cells)),
        )
        faulty_total = sum(1 for _, turn in cells if turn.flags)
        painter.drawText(
            QRectF(x0, 0, width, 14.0),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            t("{n} flagged", n=faulty_total),
        )

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        for rect, turn in self._cells():
            hit = QRectF(rect.x(), 0.0, max(rect.width(), 6.0), float(self.height()))
            if hit.contains(pos):
                self.seekRequested.emit(int(turn.t_start_ms))
                return


class ScoreTimelineChart(QWidget):
    seekRequested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._points: list[FrameScorePoint] = []
        self._reveal = 0.0
        self._anim = QPropertyAnimation(self, b"reveal")
        self._anim.setDuration(900)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setMinimumSize(220, 140)
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def get_reveal(self) -> float:
        return self._reveal

    def set_reveal(self, value: float) -> None:
        self._reveal = max(0.0, min(1.0, float(value)))
        self.update()

    reveal = Property(float, get_reveal, set_reveal)

    def set_points(self, points: list[FrameScorePoint]) -> None:
        self._points = list(points)
        self._anim.stop()
        self.set_reveal(0.0)
        if self._points:
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
        self.update()

    def _geom(self) -> tuple[float, float, float, float]:
        left, top, right, bottom = 36.0, 10.0, 12.0, 24.0
        return left, top, self.width() - right, self.height() - bottom

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x0, y0, x1, y1 = self._geom()
        painter.setPen(CHART_GRID)
        painter.drawLine(QPointF(x0, y1), QPointF(x1, y1))
        painter.drawLine(QPointF(x0, y0), QPointF(x0, y1))
        painter.setPen(UNKNOWN_GRAY)
        font = QFont(self.font())
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(QRectF(2, y0, 32, 12), int(Qt.AlignmentFlag.AlignLeft), "100")
        painter.drawText(QRectF(2, y1 - 12, 32, 12), int(Qt.AlignmentFlag.AlignLeft), "0")
        if len(self._points) < 2:
            painter.setPen(UNKNOWN_GRAY)
            painter.drawText(
                QRectF(x0, y0, x1 - x0, y1 - y0),
                int(Qt.AlignmentFlag.AlignCenter),
                t("—"),
            )
            return
        t0 = self._points[0].t_ms
        t1 = self._points[-1].t_ms
        span = max(t1 - t0, 1.0)
        mapped: list[QPointF] = []
        for point in self._points:
            x = x0 + (x1 - x0) * ((point.t_ms - t0) / span)
            y = y1 - (y1 - y0) * max(0.0, min(1.0, point.score / 100.0))
            mapped.append(QPointF(x, y))
        count = max(2, int(round((len(mapped) - 1) * self._reveal)) + 1)
        visible = mapped[:count]
        mean = sum(p.score for p in self._points) / len(self._points)
        mean_y = y1 - (y1 - y0) * (mean / 100.0)
        dash = QPen(LIGHT_PURPLE)
        dash.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(dash)
        painter.drawLine(QPointF(x0, mean_y), QPointF(x1, mean_y))
        path = QPainterPath(visible[0])
        for pt in visible[1:]:
            path.lineTo(pt)
        fill_path = QPainterPath(path)
        fill_path.lineTo(visible[-1].x(), y1)
        fill_path.lineTo(visible[0].x(), y1)
        fill_path.closeSubpath()
        fill = QColor(DEEP_PURPLE)
        fill.setAlpha(50)
        painter.fillPath(fill_path, fill)
        line = QPen(DEEP_PURPLE)
        line.setWidth(2)
        painter.setPen(line)
        painter.drawPath(path)
        std = (
            sum((p.score - mean) ** 2 for p in self._points) / len(self._points)
        ) ** 0.5
        color = WATERMELON if std > 18.0 else LIGHT_PURPLE
        painter.setPen(color)
        painter.drawText(
            QRectF(x0, y1 + 2, x1 - x0, 18),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            t("{sec:.1f}s", sec=t0 / 1000.0),
        )
        painter.drawText(
            QRectF(x0, y1 + 2, x1 - x0, 18),
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
            t("{sec:.1f}s  σ {std:.0f}", sec=t1 / 1000.0, std=std),
        )

    def mousePressEvent(self, event) -> None:
        if len(self._points) < 2:
            return
        x0, _, x1, _ = self._geom()
        t0 = self._points[0].t_ms
        t1 = self._points[-1].t_ms
        span = max(t1 - t0, 1.0)
        frac = (event.position().x() - x0) / max(x1 - x0, 1.0)
        frac = max(0.0, min(1.0, frac))
        self.seekRequested.emit(int(t0 + frac * span))
