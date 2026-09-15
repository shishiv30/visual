"""Card grid, section headers, chips, link labels and the skill tree.

The chapter list itself lives in :mod:`clients.windows.ui.report_panel`; this
module only supplies the reusable blocks it assembles (design doc §7).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.ui.qtutil import _diamond_pixmap, _svg_pixmap
from clients.windows.ui.theme import (
    LINK_CYAN,
    PAGE_INSET,
    SPACE_PANEL,
    SPACE_TEXT,
    SPINE_WHITE,
    STEEL,
    TAP_TARGET,
    TREE_COMPLETED,
    TREE_CURRENT,
    TREE_LOCKED,
    tree_node_color,
)
from core.i18n import t
from schemas.stage_report import NodeState, TreeNode, TreeNodeV3

#: state → chip kind, so the QSS chip palette carries the tree states too.
TREE_STATE_CHIPS: dict[str, tuple[str, str]] = {
    NodeState.COMPLETED.value: ("Completed", "pass"),
    NodeState.CURRENT.value: ("Current stage", "strong"),
    NodeState.INFERRED.value: ("Predicted passed", "pass"),
    NodeState.AVAILABLE.value: ("Available", "info"),
    NodeState.LOCKED.value: ("Locked", "unknown"),
    NodeState.NOT_APPLICABLE.value: ("Not applicable", "not_applicable"),
}

#: Branch order below the piste spine, design doc §8.
BRANCH_ORDER = ("piste", "moguls", "offpiste", "park", "race")

#: branch id → English display key.
BRANCH_LABELS = {
    "piste": "Piste",
    "moguls": "Moguls",
    "offpiste": "Off-piste",
    "park": "Park",
    "race": "Race",
}


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
        self._body.setContentsMargins(PAGE_INSET, PAGE_INSET, PAGE_INSET, PAGE_INSET)
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
                # ``takeAt`` detaches the row but leaves it parented to
                # ``_layout``; without this the empty QHBoxLayouts pile up on
                # every refill (every clip, every language switch).
                row.setParent(None)

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
            self._pending_row.setAlignment(Qt.AlignmentFlag.AlignTop)
            self._pending_slots = per_row
        # Pin content to top inside the card before placing it.
        if isinstance(widget, ReportCard):
            layout = widget.body()
            last = layout.itemAt(layout.count() - 1) if layout.count() else None
            if last is None or last.spacerItem() is None:
                layout.addStretch(1)
        self._pending_row.addWidget(widget, stretch=1)
        self._pending_slots -= 1
        if self._pending_slots <= 0:
            self._flush_row()

    def finish(self) -> None:
        self._flush_row()


def _chevron_pixmap(color: QColor, size: int = 16, *, down: bool = False) -> QPixmap:
    """Hand-painted disclosure chevron — no emoji, no new icon asset."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color)
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    lo = size * 0.3
    hi = size * 0.7
    mid = size * 0.5
    if down:
        painter.drawLine(QPoint(int(lo), int(lo)), QPoint(int(mid), int(hi)))
        painter.drawLine(QPoint(int(mid), int(hi)), QPoint(int(hi), int(lo)))
    else:
        painter.drawLine(QPoint(int(lo), int(lo)), QPoint(int(hi), int(mid)))
        painter.drawLine(QPoint(int(hi), int(mid)), QPoint(int(lo), int(hi)))
    painter.end()
    return pix


def _set_chevron_icon(button: QPushButton, size: int, expanded: bool) -> None:
    """Shared by every checkable disclosure button (chapter and branch)."""
    button.setIcon(QIcon(_chevron_pixmap(STEEL, size, down=expanded)))


class ReportChapter(QWidget):
    """Chapter block: gray 32px title, 16px gap, then panel grid.

    With ``collapsible=True`` the title becomes a 44px-tall disclosure button
    (design doc §7: chapters 7-11 start collapsed so the diagnosis stays above
    the fold). The title copy and its 32px gray styling are identical either
    way, so a collapsed chapter still reads as a chapter.
    """

    toggled = Signal(bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        collapsible: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("reportChapter")
        self._collapsible = collapsible
        self._grid = ReportGrid()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_TEXT)
        self._title: QLabel | None = None
        self._button: QPushButton | None = None
        if collapsible:
            button = QPushButton()
            button.setObjectName("chapterDisclosure")
            button.setCheckable(True)
            button.setMinimumHeight(TAP_TARGET)
            button.setIconSize(QSize(16, 16))
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            button.toggled.connect(self._on_toggled)
            self._button = button
            layout.addWidget(button)
        else:
            title = QLabel()
            title.setObjectName("reportChapterTitle")
            title.setWordWrap(True)
            self._title = title
            layout.addWidget(title)
        layout.addWidget(self._grid)
        if collapsible:
            self.set_expanded(False)

    def _on_toggled(self, checked: bool) -> None:
        self._grid.setVisible(checked)
        self._sync_chevron()
        self.toggled.emit(checked)

    def _sync_chevron(self) -> None:
        if self._button is None:
            return
        _set_chevron_icon(self._button, 16, self._button.isChecked())

    def is_collapsible(self) -> bool:
        return self._collapsible

    def is_expanded(self) -> bool:
        if self._button is None:
            return True
        return self._button.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        if self._button is None:
            return
        self._button.setChecked(bool(expanded))
        self._grid.setVisible(bool(expanded))
        self._sync_chevron()

    def set_title(self, title: str) -> None:
        if self._button is not None:
            self._button.setText(title)
            self._sync_chevron()
            return
        if self._title is not None:
            self._title.setText(title)

    def title(self) -> str:
        if self._button is not None:
            return self._button.text()
        return self._title.text() if self._title is not None else ""

    def grid(self) -> ReportGrid:
        return self._grid


class Chip(QLabel):
    """Small bordered state pill. Colour comes from the QSS ``kind`` property."""

    def __init__(
        self,
        text: str,
        kind: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("reportChip")
        self.setProperty("kind", kind or "info")
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)


class ChipRow(QWidget):
    """One row of chips, left aligned."""

    def __init__(
        self,
        chips: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("reportChipRow")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for text, kind in chips:
            if not text:
                continue
            row.addWidget(Chip(text, kind), alignment=Qt.AlignmentFlag.AlignTop)
        row.addStretch(1)


def add_chip_rows(
    layout: QVBoxLayout,
    chips: list[tuple[str, str]],
    *,
    per_row: int = 3,
) -> None:
    """Wrap chips into fixed-width rows; Qt has no flow layout in the stock set."""
    live = [(text, kind) for text, kind in chips if text]
    per_row = max(1, per_row)
    for start in range(0, len(live), per_row):
        layout.addWidget(ChipRow(live[start : start + per_row]))


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
            if name == "diamond":
                icon.setPixmap(_diamond_pixmap(color, 18))
            else:
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

    def mousePressEvent(self, event) -> None:
        # A QLabel ignores the press by default, which makes Qt route the whole
        # sequence to the scroll viewport — the release never arrives here.
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.clicked.emit()
            return
        super().mouseReleaseEvent(event)


class FrameSeekLink(QWidget):
    """Stopwatch icon + cyan link text for playback seek.

    Single-click: seek to the frame.
    Double-click: seek to the frame and start playing.
    """

    clicked = Signal()
    doubleClicked = Signal()

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("frameSeekLink")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(TAP_TARGET)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(_svg_pixmap("stopwatch", LINK_CYAN, 16))
        icon.setFixedSize(16, 16)
        self._text = ReportLink(text)
        self._text.clicked.connect(self.clicked.emit)
        row.addWidget(icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._text, stretch=1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.clicked.emit()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.doubleClicked.emit()
            return
        super().mouseDoubleClickEvent(event)


class SkillTreeRoute(QWidget):
    """Vertical list of skill nodes joined by a white dashed spine."""

    ROW_H = 32
    DOT_X = 8
    DOT_R = 5
    TEXT_GAP = 12
    CURRENT = TREE_CURRENT
    COMPLETED = TREE_COMPLETED
    PENDING = TREE_LOCKED
    LINE = SPINE_WHITE

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skillTreeRoute")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._nodes: list[TreeNode] = []

    def set_route(self, nodes: list[TreeNode]) -> None:
        self._nodes = list(nodes)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        n = max(1, len(self._nodes))
        return QSize(160, n * self.ROW_H)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        nodes = self._nodes
        if not nodes:
            painter.setPen(self.PENDING)
            painter.drawText(
                QRect(self.DOT_X + self.DOT_R + self.TEXT_GAP, 0, max(0, self.width() - 24), self.ROW_H),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                t("—"),
            )
            return
        current_i = next((i for i, node in enumerate(nodes) if node.current), len(nodes) - 1)
        cx = self.DOT_X
        if len(nodes) > 1:
            pen = QPen(self.LINE)
            pen.setWidth(1)
            pen.setDashPattern([3, 3])
            y0 = self.ROW_H // 2
            y1 = (len(nodes) - 1) * self.ROW_H + self.ROW_H // 2
            painter.setPen(pen)
            painter.drawLine(cx, y0, cx, y1)
        font = QFont(painter.font())
        for i, node in enumerate(nodes):
            cy = i * self.ROW_H + self.ROW_H // 2
            if node.current:
                color = self.CURRENT
                font.setBold(True)
                filled = True
            elif i < current_i:
                color = self.COMPLETED
                font.setBold(True)
                filled = True
            else:
                color = self.PENDING
                font.setBold(False)
                filled = False
            painter.setFont(font)
            painter.setPen(QPen(color, 1))
            if filled:
                painter.setBrush(color)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), self.DOT_R, self.DOT_R)
            painter.setPen(color)
            text_rect = QRect(
                cx + self.DOT_R + self.TEXT_GAP,
                i * self.ROW_H,
                max(0, self.width() - cx - self.DOT_R - self.TEXT_GAP - 4),
                self.ROW_H,
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                node.name,
            )


def _row_state(node: TreeNodeV3) -> str:
    return node.state.value if isinstance(node.state, NodeState) else str(node.state)


def order_tree_rows(nodes: list[TreeNodeV3]) -> list[tuple[TreeNodeV3, int]]:
    """Lay the whole progression out as rows: piste spine, branches indented.

    The piste line keeps the existing top-to-bottom spine idiom. A non-piste
    rung is emitted directly under the piste rung that leads into it (its first
    matching parent) and indented one column, so the mogul and off-piste
    branches are visible instead of being flattened into the spine. Nodes with
    no usable parent link fall back to branch order (design doc §8).
    """
    order = {node.id: i for i, node in enumerate(nodes)}

    def rank(node: TreeNodeV3) -> tuple[int, int]:
        return (int(node.depth), order.get(node.id, 0))

    def branch_of(node: TreeNodeV3) -> str:
        return node.branch or "piste"

    main = sorted((n for n in nodes if branch_of(n) == "piste"), key=rank)
    side = sorted((n for n in nodes if branch_of(n) != "piste"), key=rank)
    emitted: set[str] = set()
    rows: list[tuple[TreeNodeV3, int]] = []

    def emit_side(parent_id: str) -> None:
        for node in side:
            if node.id in emitted or parent_id not in (node.parents or []):
                continue
            emitted.add(node.id)
            rows.append((node, 1))
            emit_side(node.id)

    for node in main:
        if node.id in emitted:
            continue
        emitted.add(node.id)
        rows.append((node, 0))
        emit_side(node.id)

    leftovers = [n for n in side if n.id not in emitted]
    if leftovers:
        leftovers.sort(
            key=lambda n: (
                BRANCH_ORDER.index(branch_of(n))
                if branch_of(n) in BRANCH_ORDER
                else len(BRANCH_ORDER),
                rank(n),
            )
        )
        indent = 1 if rows else 0
        for node in leftovers:
            emitted.add(node.id)
            rows.append((node, indent))
    return rows


class _SpineCell(QWidget):
    """The dashed spine plus one state dot, painted for a single tree row."""

    INDENT = 20
    DOT_X = 8
    DOT_Y = 11
    DOT_R = 5

    def __init__(
        self,
        *,
        indent: int,
        color: QColor,
        state: str,
        has_above: bool,
        has_below: bool,
        elbow: bool,
        through: tuple[int, ...] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("skillTreeSpine")
        self._indent = max(0, int(indent))
        self._color = color
        self._state = state
        self._has_above = has_above
        self._has_below = has_below
        self._elbow = elbow
        self._through = through
        width = self.DOT_X + self._indent * self.INDENT + self.DOT_R + 4
        self.setFixedWidth(width)
        self.setMinimumHeight(self.DOT_Y + self.DOT_R + 4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _column_x(self, indent: int) -> int:
        return self.DOT_X + indent * self.INDENT

    def _dash_pen(self) -> QPen:
        pen = QPen(SPINE_WHITE)
        pen.setWidth(1)
        pen.setDashPattern([3, 3])
        return pen

    def paintEvent(self, event) -> None:  # noqa: ARG002
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = self.height()
        cx = self._column_x(self._indent)
        cy = self.DOT_Y
        pen = self._dash_pen()
        painter.setPen(pen)
        for indent in self._through:
            x = self._column_x(indent)
            painter.drawLine(x, 0, x, height)
        if self._has_above:
            painter.drawLine(cx, 0, cx, cy - self.DOT_R)
        if self._has_below:
            painter.drawLine(cx, cy + self.DOT_R, cx, height)
        if self._elbow and self._indent > 0:
            px = self._column_x(self._indent - 1)
            painter.drawLine(px, 0, px, cy)
            painter.drawLine(px, cy, cx - self.DOT_R, cy)
        dot_pen = QPen(self._color)
        dot_pen.setWidth(2)
        center = QPoint(cx, cy)
        if self._state in (NodeState.COMPLETED.value, NodeState.CURRENT.value):
            painter.setPen(dot_pen)
            painter.setBrush(self._color)
            painter.drawEllipse(center, self.DOT_R, self.DOT_R)
            if self._state == NodeState.CURRENT.value:
                ring = QPen(self._color)
                ring.setWidth(1)
                painter.setPen(ring)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, self.DOT_R + 3, self.DOT_R + 3)
            return
        if self._state == NodeState.LOCKED.value:
            dot_pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(dot_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self.DOT_R, self.DOT_R)
        if self._state == NodeState.NOT_APPLICABLE.value:
            slash = QPen(self._color)
            slash.setWidth(2)
            painter.setPen(slash)
            painter.drawLine(
                cx - self.DOT_R,
                cy + self.DOT_R,
                cx + self.DOT_R,
                cy - self.DOT_R,
            )


class _ClickableTreeRow(QWidget):
    """A skill-tree row that emits ``clicked(level_id, clip_id)`` on left-click."""

    clicked = Signal(str, str)

    def __init__(self, level_id: str, clip_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level_id = level_id
        self._clip_id = clip_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.clicked.emit(self._level_id, self._clip_id)
        else:
            super().mouseReleaseEvent(event)


class SkillTreeView(QWidget):
    """Branch-aware skill tree over ``StageReport.tree`` (design doc §8).

    Rows are real widgets rather than one painted canvas, so ``locked_reason``
    wraps like any other report paragraph and stays selectable and greppable.
    The dashed white spine is painted per row by :class:`_SpineCell`.
    """

    nodeClicked = Signal(str, str)  # (level_id, clip_id_best)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skillTreeView")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        # Rows touch so the dashed spine reads as one continuous line; the
        # breathing room lives inside each row's text column instead.
        self._layout.setSpacing(0)
        self._nodes: list[TreeNodeV3] = []
        self._rows: list[tuple[TreeNodeV3, int]] = []
        self._clip_id_map: dict[str, str] = {}

    def node_count(self) -> int:
        return len(self._rows)

    def rows(self) -> list[tuple[TreeNodeV3, int]]:
        return list(self._rows)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _branch_groups(self) -> list[tuple[str, list[int]]]:
        """Contiguous runs of side-branch rows (indent > 0), grouped by branch.

        ``order_tree_rows`` only ever produces indent 0 (piste) or indent 1
        (every side branch), so a branch never needs to nest inside another.
        """
        groups: list[tuple[str, list[int]]] = []
        branch: str | None = None
        indices: list[int] = []
        for i, (node, indent) in enumerate(self._rows):
            if indent == 0:
                if indices:
                    groups.append((branch or "piste", indices))
                    indices = []
                branch = None
                continue
            this_branch = node.branch or "piste"
            if this_branch != branch:
                if indices:
                    groups.append((branch or "piste", indices))
                branch = this_branch
                indices = []
            indices.append(i)
        if indices:
            groups.append((branch or "piste", indices))
        return groups

    def set_nodes(self, nodes: list[TreeNodeV3], clip_id_map: dict[str, str] | None = None) -> None:
        self._clip_id_map = clip_id_map or {}
        self._clear()
        self._nodes = list(nodes)
        self._rows = order_tree_rows(self._nodes)
        self._branch_rows: dict[int, list[QWidget]] = {}
        if not self._rows:
            empty = QLabel(t("—"))
            empty.setObjectName("reportTreeMeta")
            self._layout.addWidget(empty)
            self.updateGeometry()
            return
        indents = [indent for _, indent in self._rows]
        groups = self._branch_groups()
        group_of_index: dict[int, int] = {}
        expanded_by_group: dict[int, bool] = {}
        for gi, (_branch, idxs) in enumerate(groups):
            for idx in idxs:
                group_of_index[idx] = gi
            # Default: only the branch holding the current stage starts open
            # (the piste spine itself is indent 0 and never grouped here) —
            # readability follow-up, design doc §8.
            expanded_by_group[gi] = any(
                _row_state(self._rows[idx][0]) == NodeState.CURRENT.value
                for idx in idxs
            )

        for i, (node, indent) in enumerate(self._rows):
            has_above = i > 0 and indents[i - 1] >= indent
            has_below = i + 1 < len(indents) and indents[i + 1] >= indent
            elbow = indent > 0 and (i == 0 or indents[i - 1] < indent)
            through: tuple[int, ...] = ()
            if indent > 0 and any(d == 0 for d in indents[i + 1 :]):
                through = (0,)

            gi = group_of_index.get(i)
            if gi is not None and groups[gi][1][0] == i:
                branch_id, idxs = groups[gi]
                self._layout.addWidget(
                    self._branch_header_widget(
                        branch_id, idxs, gi, expanded_by_group[gi],
                        has_above=has_above, through=through,
                    )
                )
                # The header now owns the elbow into the branch; the first
                # row just continues the branch's own dashed column.
                elbow = False
                has_above = True

            row_widget = self._row_widget(node, indent, has_above, has_below, elbow, through)
            if indent > 0:
                gi = group_of_index[i]
                self._branch_rows.setdefault(gi, []).append(row_widget)
                row_widget.setVisible(expanded_by_group[gi])
            self._layout.addWidget(row_widget)
        self.updateGeometry()

    def _branch_header_widget(
        self,
        branch: str,
        idxs: list[int],
        group_index: int,
        expanded: bool,
        *,
        has_above: bool,
        through: tuple[int, ...],
    ) -> QWidget:
        lead_node = self._rows[idxs[0]][0]
        color = tree_node_color(_row_state(lead_node), lead_node.tier or "full")
        row = QWidget()
        row.setObjectName("skillTreeRow")
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addWidget(
            _SpineCell(
                indent=1,
                color=color,
                state=_row_state(lead_node),
                has_above=has_above,
                has_below=True,
                elbow=True,
                through=through,
            )
        )
        label = BRANCH_LABELS.get(branch, branch)
        button = QPushButton(f"{t(label)} · {t('{n} stages', n=len(idxs))}")
        button.setObjectName("branchDisclosure")
        button.setCheckable(True)
        button.setChecked(expanded)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setIconSize(QSize(14, 14))
        _set_chevron_icon(button, 14, expanded)
        button.toggled.connect(lambda checked, gi=group_index, btn=button: self._set_branch_expanded(gi, checked, btn))
        box.addWidget(button, stretch=1)
        return row

    def _set_branch_expanded(self, group_index: int, expanded: bool, button: QPushButton) -> None:
        _set_chevron_icon(button, 14, expanded)
        for widget in self._branch_rows.get(group_index, []):
            widget.setVisible(expanded)
        self.updateGeometry()

    def _row_widget(
        self,
        node: TreeNodeV3,
        indent: int,
        has_above: bool,
        has_below: bool,
        elbow: bool,
        through: tuple[int, ...],
    ) -> QWidget:
        state = _row_state(node)
        color = tree_node_color(state, node.tier or "full")
        clickable = state in ("completed", "current", "inferred")
        if clickable:
            clip_id = self._clip_id_map.get(node.id, "")
            row: QWidget = _ClickableTreeRow(node.id, clip_id)
            row.clicked.connect(self.nodeClicked)
        else:
            row = QWidget()
        row.setObjectName("skillTreeRow")
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        box.addWidget(
            _SpineCell(
                indent=indent,
                color=color,
                state=state,
                has_above=has_above,
                has_below=has_below,
                elbow=elbow,
                through=through,
            )
        )
        column = QVBoxLayout()
        column.setContentsMargins(0, 2, 0, 10)
        column.setSpacing(4)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        strong = state in ("completed", "current", "inferred") and (node.tier or "full") != "catalog"
        name = QLabel(node.name or node.id)
        name.setObjectName("reportTreeName" if strong else "reportTreeNameMuted")
        name.setWordWrap(True)
        head.addWidget(name, stretch=1)
        chip_key, chip_kind = TREE_STATE_CHIPS.get(state, ("Locked", "unknown"))
        head.addWidget(Chip(t(chip_key), chip_kind), alignment=Qt.AlignmentFlag.AlignTop)
        column.addLayout(head)
        meta: list[str] = []
        if node.branch and node.branch != "piste":
            label = BRANCH_LABELS.get(node.branch, node.branch)
            meta.append(f"{t('Branch')}: {t(label)}")
        if (node.tier or "full") == "catalog":
            meta.append(t("Progression rung — not judged from a clip."))
        elif (node.tier or "full") == "scene":
            meta.append(t("Needs a scene fact before it can be detected."))
        if node.gates_passed:
            meta.append(f"{t('Gates passed')}: {node.gates_passed}")
        if node.score_best is not None:
            meta.append(t("Best score {score:.0f}", score=node.score_best))
        if node.locked_reason:
            meta.append(f"{t('Locked because')}: {node.locked_reason}")
        if node.inferred_reason:
            meta.append(node.inferred_reason)
        add_text_stack(column, meta, object_name="reportTreeMeta")
        box.addLayout(column, stretch=1)
        return row
