"""Card grid, section headers, and link labels for the stage report."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.ui.qtutil import _svg_pixmap
from clients.windows.ui.theme import LINK_CYAN, SPACE_PANEL, SPACE_TEXT
from schemas.stage_report import TreeNode


def add_text_stack(
    layout: QVBoxLayout,
    texts: list[str],
    *,
    object_name: str | None = None,
) -> None:
    """Add one word-wrapped QLabel per paragraph. Never join with newlines."""
    for text in texts:
        if not text:
            continue
        lab = QLabel(text)
        lab.setWordWrap(True)
        if object_name:
            lab.setObjectName(object_name)
        layout.addWidget(lab)


class ReportCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(12, 12, 12, 12)
        self._body.setSpacing(SPACE_TEXT)

    def body(self) -> QVBoxLayout:
        return self._body


class ReportGrid(QWidget):
    """Flow panels into rows with 1, 2, or 3 columns."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(SPACE_PANEL)
        self._pending_row: QHBoxLayout | None = None
        self._pending_slots = 0

    def clear(self) -> None:
        self._pending_row = None
        self._pending_slots = 0
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            row = item.layout()
            if row is not None:
                self._clear_layout(row)

    def _clear_layout(self, layout: QLayout) -> None:
        while layout.count():
            taken = layout.takeAt(0)
            widget = taken.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            child = taken.layout()
            if child is not None:
                self._clear_layout(child)

    def _flush_row(self) -> None:
        if self._pending_row is not None:
            self._layout.addLayout(self._pending_row)
            self._pending_row = None
            self._pending_slots = 0

    def add(self, widget: QWidget, *, per_row: int = 1) -> None:
        per_row = max(1, min(3, per_row))
        if per_row == 1:
            self._flush_row()
            self._layout.addWidget(widget)
            return
        if self._pending_row is None or self._pending_slots <= 0:
            self._pending_row = QHBoxLayout()
            self._pending_row.setSpacing(SPACE_PANEL)
            self._pending_slots = per_row
        self._pending_row.addWidget(widget, stretch=1)
        self._pending_slots -= 1
        if self._pending_slots <= 0:
            self._flush_row()

    def finish(self) -> None:
        self._flush_row()


class ReportChapter(QWidget):
    """Chapter block: gray 32px title, 16px gap, then panel grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportChapter")
        self._title = QLabel()
        self._title.setObjectName("reportChapterTitle")
        self._title.setWordWrap(True)
        self._grid = ReportGrid()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_TEXT)
        layout.addWidget(self._title)
        layout.addWidget(self._grid)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def title(self) -> str:
        return self._title.text()

    def grid(self) -> ReportGrid:
        return self._grid


class IconTextRow(QWidget):
    """Leading icon(s) + text on one row."""

    def __init__(
        self,
        icons: list[tuple[str, QColor]],
        text: str,
        *,
        object_name: str = "reportMeta",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("reportIconTextRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for name, color in icons:
            icon = QLabel()
            icon.setPixmap(_svg_pixmap(name, color, 18))
            icon.setFixedSize(18, 18)
            row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        lab = QLabel(text)
        lab.setObjectName(object_name)
        lab.setWordWrap(True)
        row.addWidget(lab, stretch=1)


class ReportSectionHeader(QWidget):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportSectionHeader")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 4)
        row.setSpacing(8)
        bar = QFrame()
        bar.setObjectName("reportSectionBar")
        bar.setFixedWidth(4)
        bar.setFixedHeight(18)
        self._title = QLabel(title)
        self._title.setObjectName("reportSectionTitle")
        row.addWidget(bar, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._title, stretch=1)

    def set_title(self, title: str) -> None:
        self._title.setText(title)


class ReportLink(QLabel):
    clicked = Signal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportLink")
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWordWrap(True)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class FrameSeekLink(QWidget):
    """Stopwatch icon + cyan link text for playback seek."""

    clicked = Signal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("frameSeekLink")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(_svg_pixmap("stopwatch", LINK_CYAN, 16))
        icon.setFixedSize(16, 16)
        self._text = ReportLink(text)
        self._text.clicked.connect(self.clicked.emit)
        row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)
        row.addWidget(self._text, stretch=1)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class SkillTreeRoute(QLabel):
    """Full progression route: completed bold, current highlighted, pending gray."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skillTreeRoute")
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def set_route(self, nodes: list[TreeNode]) -> None:
        if not nodes:
            self.setText("—")
            return
        current_i = next((i for i, node in enumerate(nodes) if node.current), len(nodes) - 1)
        parts: list[str] = []
        for i, node in enumerate(nodes):
            name = node.name.replace("&", "&amp;").replace("<", "&lt;")
            if node.current:
                parts.append(
                    f'<span style="color:#E1BEE7;font-weight:700;">{name}</span>'
                )
            elif i < current_i:
                parts.append(
                    f'<span style="color:#CE93D8;font-weight:700;">{name}</span>'
                )
            else:
                parts.append(f'<span style="color:#757575;">{name}</span>')
            if i < len(nodes) - 1:
                parts.append('<span style="color:#616161;"> → </span>')
        self.setText("".join(parts))
