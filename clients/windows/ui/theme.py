"""Shared QSS tokens for the Windows client."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QAbstractButton, QApplication

from schemas.stage_report import MetricState, NodeState, Rubric

DEEP_PURPLE = QColor("#5E35B1")
LIGHT_PURPLE = QColor("#CE93D8")
LINK_CYAN = QColor("#4FC3F7")
PURPLE = QColor("#8E24AA")
BLUE = DEEP_PURPLE
PASS_GREEN = LIGHT_PURPLE
WATERMELON = QColor("#E94B6A")
UNKNOWN_GRAY = QColor("#9E9E9E")
INK = QColor("#121212")
PAPER = QColor("#F5F5F5")
CARD_RADIUS = 10
SPACE_CHAPTER = 36
SPACE_PANEL = 24
SPACE_TEXT = 16
PAGE_INSET = 12
TAP_TARGET = 44
MEDAL_BEGINNER = QColor("#43A047")
MEDAL_INTERMEDIATE = QColor("#1E88E5")
MEDAL_ADVANCED = QColor("#8E24AA")
MEDAL_ELITE = QColor("#FFC107")
TERRAIN_GREEN = QColor("#2E7D32")
TERRAIN_BLUE = QColor("#1565C0")
TERRAIN_RED = QColor("#C62828")
TERRAIN_BLACK = QColor("#000000")

# --- report v3 states (design doc §7, §8) -------------------------------------
SLATE = QColor("#546E7A")
DIM_GRAY = QColor("#616161")
STEEL = QColor("#B0BEC5")
SPINE_WHITE = PAPER
STATE_UNKNOWN = UNKNOWN_GRAY
STATE_NOT_APPLICABLE = SLATE
TREE_CURRENT = QColor("#E1BEE7")
TREE_COMPLETED = LIGHT_PURPLE
TREE_AVAILABLE = STEEL
TREE_LOCKED = DIM_GRAY
TREE_NOT_APPLICABLE = SLATE
TURN_CLEAN = LIGHT_PURPLE
TURN_FAULTY = WATERMELON

# --- chart chrome (report_charts painters; no private per-page palettes) ------
CHART_TRACK = QColor("#2a3544")
CHART_GRID = QColor("#424242")
CHART_AXIS = QColor("#3d3d3d")
CAPTION_GRAY = QColor("#B0BEC5")


def score_purple(score: float | None) -> QColor:
    """Dark purple at 0 → light purple at 100."""
    frac = 0.0 if score is None else max(0.0, min(1.0, float(score) / 100.0))
    r0, g0, b0, _ = DEEP_PURPLE.getRgb()
    r1, g1, b1, _ = LIGHT_PURPLE.getRgb()
    return QColor(
        int(r0 + (r1 - r0) * frac),
        int(g0 + (g1 - g0) * frac),
        int(b0 + (b1 - b0) * frac),
    )


def level_medal_color(stage_id: str) -> QColor:
    """Trophy tint by progression tier: green → blue → purple → gold."""
    match stage_id:
        case "pizza_glide" | "pizza" | "wedge_christie":
            return MEDAL_BEGINNER
        case "parallel" | "skid_short" | "carve_long" | "switch":
            return MEDAL_INTERMEDIATE
        case "carve_medium" | "mogul_absorb" | "gates":
            return MEDAL_ADVANCED
        case "carve_short" | "mogul_fallline" | "ollie" | "park":
            return MEDAL_ELITE
        case _:
            return MEDAL_INTERMEDIATE


def rubric_color(rubric: str) -> QColor:
    """not_yet → watermelon, pass → light purple, strong → gold."""
    match rubric:
        case Rubric.STRONG.value:
            return MEDAL_ELITE
        case Rubric.PASS.value:
            return LIGHT_PURPLE
        case Rubric.NOT_YET.value:
            return WATERMELON
        case _:
            return UNKNOWN_GRAY


def metric_state_color(state: str, score: float | None = None) -> QColor:
    """Colour a metric row. ``unknown``/``not_applicable`` never look like 0."""
    match state:
        case MetricState.OK.value:
            return score_purple(score)
        case MetricState.NOT_APPLICABLE.value:
            return STATE_NOT_APPLICABLE
        case _:
            return STATE_UNKNOWN


def tree_node_color(state: str, tier: str = "full") -> QColor:
    """Skill-tree rung colour by state; catalog rungs are always greyed."""
    if tier == "catalog" and state not in (
        NodeState.CURRENT.value,
        NodeState.COMPLETED.value,
    ):
        return TREE_LOCKED
    match state:
        case NodeState.CURRENT.value:
            return TREE_CURRENT
        case NodeState.COMPLETED.value:
            return TREE_COMPLETED
        case NodeState.AVAILABLE.value:
            return TREE_AVAILABLE
        case NodeState.NOT_APPLICABLE.value:
            return TREE_NOT_APPLICABLE
        case _:
            return TREE_LOCKED


def severity_color(severity: str) -> QColor:
    match severity:
        case "blocker":
            return WATERMELON
        case "warn":
            return MEDAL_ELITE
        case _:
            return UNKNOWN_GRAY


def terrain_diamond_colors(terrain_id: str) -> list[QColor]:
    match terrain_id:
        case "green":
            return [TERRAIN_GREEN]
        case "blue":
            return [TERRAIN_BLUE]
        case "red":
            return [TERRAIN_RED]
        case "black" | "mogul":
            return [TERRAIN_BLACK]
        case "double_black" | "black_double":
            return [TERRAIN_BLACK, TERRAIN_BLACK]
        case "park":
            return [PURPLE]
        case _:
            return [UNKNOWN_GRAY]


class PointerButtonFilter(QObject):
    """Windows native styles ignore QSS cursor; set it on every button."""

    def eventFilter(self, watched, event) -> bool:
        if isinstance(watched, QAbstractButton):
            kind = event.type()
            if kind in (
                QEvent.Type.Show,
                QEvent.Type.Polish,
                QEvent.Type.EnabledChange,
                QEvent.Type.Enter,
            ):
                if watched.isEnabled():
                    watched.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    watched.unsetCursor()
        return super().eventFilter(watched, event)


def apply_dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, INK)
    palette.setColor(QPalette.ColorRole.WindowText, PAPER)
    palette.setColor(QPalette.ColorRole.Base, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#242424"))
    palette.setColor(QPalette.ColorRole.Text, PAPER)
    palette.setColor(QPalette.ColorRole.Button, QColor("#2A2A2A"))
    palette.setColor(QPalette.ColorRole.ButtonText, PAPER)
    palette.setColor(QPalette.ColorRole.Highlight, DEEP_PURPLE)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2A2A2A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, PAPER)
    app.setPalette(palette)


def install_pointer_buttons(app: QApplication) -> None:
    filt = PointerButtonFilter(app)
    app.installEventFilter(filt)
    for widget in app.allWidgets():
        if isinstance(widget, QAbstractButton) and widget.isEnabled():
            widget.setCursor(Qt.CursorShape.PointingHandCursor)


def app_stylesheet() -> str:
    return """
    QMainWindow, QStackedWidget, QWidget#listPage, QWidget#capturePage, QWidget#playerPage, QWidget#preparePage {
        background: #121212;
        color: #f5f5f5;
    }
    QLabel { color: #f5f5f5; }
    QPushButton {
        padding: 1px 8px;
        border-radius: 4px;
        border: 1px solid #7e57c2;
        background: #5e35b1;
        color: #ffffff;
    }
    QPushButton:hover { background: #7e57c2; }
    QPushButton:disabled { color: #6f6f6f; background: #1e1e1e; border-color: #3d3d3d; }
    QComboBox {
        padding: 5px 10px;
        border-radius: 6px;
        border: 1px solid #3d3d3d;
        background: #2a2a2a;
        color: #f5f5f5;
        min-height: 28px;
    }
    QComboBox::drop-down {
        width: 20px;
        border: none;
    }
    QComboBox QAbstractItemView {
        background: #1e1e1e;
        color: #f5f5f5;
        selection-background-color: #5e35b1;
        padding: 4px 0;
        border: 1px solid #4d4d4d;
        border-radius: 6px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 12px;
        min-height: 28px;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #5e35b1;
    }
    QWidget#listPage {
        background: #121212;
    }
    QWidget#listToolbar {
        background: transparent;
    }
    QScrollArea#clipListScroll {
        border: none;
        background: transparent;
    }
    QScrollArea#clipListScroll QWidget#qt_scrollarea_viewport {
        background: transparent;
    }
    QListWidget {
        border: none;
        background: transparent;
        outline: none;
        color: #f5f5f5;
    }
    QListWidget::item {
        margin: 0;
        padding: 0;
        border-radius: 10px;
        background: transparent;
    }
    QListWidget::item:hover { background: transparent; }
    QListWidget::item:selected { background: transparent; }
    QWidget#clipRow {
        background: #1e1e1e;
        border-radius: 10px;
    }
    QLabel#thumb {
        border-top-left-radius: 10px;
        border-bottom-left-radius: 10px;
        background: #000000;
        color: #bdbdbd;
    }
    QLabel#statusChip {
        padding: 0;
        background: transparent;
        color: #b0bec5;
    }
    QLabel#statusChip[kind="pending"] { background: transparent; color: #9e9e9e; }
    QLabel#statusChip[kind="processing"] { background: transparent; color: #ce93d8; }
    QLabel#statusChip[kind="done"] { background: transparent; color: #ce93d8; }
    QWidget#playerChrome {
        background: transparent;
        border-radius: 0;
    }
    QWidget#playerChrome QPushButton, QWidget#playerChrome QComboBox, QWidget#playerChrome QLabel {
        color: #f5f5f5;
        background: transparent;
        border: none;
    }
    QWidget#playerChrome QPushButton:hover { background: rgba(255, 255, 255, 0.12); }
    QWidget#playerChrome QPushButton#frameLocator {
        color: #f5f5f5;
        background: transparent;
        border: 1px solid #f5f5f5;
        border-radius: 12px;
        padding: 2px 10px;
        min-height: 24px;
    }
    QWidget#playerChrome QPushButton#frameLocator:hover {
        background: rgba(255, 255, 255, 0.12);
    }
    QWidget#playerChrome QPushButton#likeVote:checked {
        background: transparent;
        border: none;
        border-bottom: 2px solid #CE93D8;
        border-radius: 0;
    }
    QWidget#playerChrome QPushButton#unlikeVote:checked {
        background: transparent;
        border: none;
        border-bottom: 2px solid #E94B6A;
        border-radius: 0;
    }
    QWidget#playerChrome QPushButton#skeletonVote:checked {
        background: transparent;
        border: none;
        border-bottom: 2px solid #9E9E9E;
        border-radius: 0;
    }
    QStatusBar { background: #000000; color: #bdbdbd; }
    QWidget#stageReportPanel {
        background: #1e1e1e;
        color: #f5f5f5;
    }
    QFrame#reportCard {
        background: #1a2433;
        border-radius: 12px;
        border: 1px solid #2a3544;
    }
    QFrame#reportGateCard {
        background: #1a2433;
        border-radius: 12px;
        border: 1px solid #5E35B1;
    }
    QLabel#reportChip {
        border: 1px solid #3d3d3d;
        border-radius: 10px;
        padding: 2px 8px;
        color: #b0bec5;
        background: transparent;
        font-weight: 600;
    }
    QLabel#reportChip[kind="strong"] { color: #FFC107; border-color: #FFC107; }
    QLabel#reportChip[kind="pass"] { color: #CE93D8; border-color: #CE93D8; }
    QLabel#reportChip[kind="not_yet"] { color: #E94B6A; border-color: #E94B6A; }
    QLabel#reportChip[kind="unknown"] { color: #9E9E9E; border-color: #9E9E9E; }
    QLabel#reportChip[kind="not_applicable"] { color: #546E7A; border-color: #546E7A; }
    QLabel#reportChip[kind="not_rated"] { color: #9E9E9E; border-color: #3d3d3d; }
    QLabel#reportChip[kind="gate"] { color: #CE93D8; border-color: #5E35B1; background: #221a35; }
    QLabel#reportChip[kind="blocker"] { color: #E94B6A; border-color: #E94B6A; }
    QLabel#reportChip[kind="warn"] { color: #FFC107; border-color: #FFC107; }
    QLabel#reportChip[kind="info"] { color: #9E9E9E; border-color: #9E9E9E; }
    QWidget#reportChipRow { background: transparent; }
    QPushButton#chapterDisclosure {
        min-height: 44px;
        text-align: left;
        padding: 0;
        border: none;
        background: transparent;
        color: #9e9e9e;
        font-size: 32px;
        font-weight: 600;
    }
    QPushButton#chapterDisclosure:hover { color: #b0bec5; background: transparent; }
    QPushButton#chapterDisclosure:disabled { color: #9e9e9e; background: transparent; }
    QWidget#skillTreeView { background: transparent; }
    QWidget#skillTreeRow { background: transparent; }
    QLabel#reportTreeName { color: #f5f5f5; font-weight: 600; }
    QLabel#reportTreeNameMuted { color: #9e9e9e; }
    QLabel#reportTreeMeta { color: #b0bec5; }
    QWidget#reportSectionHeader {
        background: transparent;
    }
    QFrame#reportSectionBar {
        background: #5E35B1;
        border-radius: 2px;
    }
    QLabel#reportLink {
        color: #4FC3F7;
        background: transparent;
        padding: 2px 0;
    }
    QLabel#reportLink:hover {
        color: #81D4FA;
    }
    QWidget#frameSeekLink {
        background: transparent;
    }
    QScrollArea#reportScroll {
        border: none;
        background: #1a1a1a;
        border-radius: 8px;
    }
    QScrollArea#reportScroll QWidget#qt_scrollarea_viewport {
        background: #1a1a1a;
    }
    QWidget#loadingOverlay {
        background: #121212;
    }
    QLabel#loadingCaption {
        color: #f5f5f5;
        font-weight: 600;
        padding-top: 8px;
    }
    QLabel#reportSectionTitle {
        color: #f5f5f5;
        font-weight: 600;
        padding-top: 6px;
    }
    QLabel#reportDisclaimer {
        color: #b0bec5;
    }
    QLabel#reportMeta {
        color: #e0e0e0;
    }
    QLabel#reportAdvice {
        color: #f5f5f5;
    }
    QLabel#reportEmpty {
        color: #9e9e9e;
    }
    QGroupBox#reportChapter {
        border: none;
        margin-top: 0;
        color: #f5f5f5;
        background: transparent;
        padding-top: 0;
    }
    QGroupBox#reportChapter::title {
        subcontrol-origin: margin;
        left: 0;
        padding: 0;
        color: #9e9e9e;
        font-size: 32px;
        font-weight: 600;
    }
    QWidget#reportChapter {
        background: transparent;
    }
    QLabel#reportChapterTitle {
        color: #9e9e9e;
        font-size: 32px;
        font-weight: 600;
        background: transparent;
    }
    QWidget#reportIconTextRow {
        background: transparent;
    }
    QPushButton#reportFrameLink {
        background: transparent;
        color: #4FC3F7;
        border: none;
        padding: 0;
        min-height: 0;
    }
    QPushButton#reportFrameLink:hover {
        color: #81D4FA;
    }
    QLabel#reportTerrainChip {
        font-weight: 600;
    }
    QPushButton#floatingBack {
        min-height: 44px;
        max-height: 44px;
        min-width: 44px;
        max-width: 44px;
        padding: 0;
        border-radius: 8px;
        background: rgba(30, 30, 30, 0.88);
        border: 1px solid #3d3d3d;
        color: #f5f5f5;
    }
    QPushButton#floatingBack:hover {
        background: rgba(255, 255, 255, 0.14);
    }
    QWidget#athleteForm QLineEdit,
    QWidget#athleteForm QComboBox,
    QWidget#athleteForm QDateEdit,
    QWidget#athleteForm QDoubleSpinBox,
    QWidget#sceneForm QComboBox {
        min-height: 44px;
        max-height: 44px;
        padding: 0 12px;
        border-radius: 8px;
        border: 1px solid #3d3d3d;
        background: #2a2a2a;
        color: #f5f5f5;
    }
    QWidget#athleteForm QComboBox::drop-down,
    QWidget#sceneForm QComboBox::drop-down {
        width: 28px;
        border: none;
    }
    QWidget#athleteForm QDateEdit::drop-down {
        width: 28px;
        border: none;
    }
    QWidget#preparePage QPushButton {
        min-height: 44px;
        max-height: 44px;
        border-radius: 8px;
        padding: 0 16px;
    }
    QGroupBox#reportEssay {
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        margin-top: 8px;
        color: #f5f5f5;
        background: #1a1a1a;
    }
    QGroupBox#reportEssay::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        color: #b0bec5;
    }
    """


app_stylesheet = app_stylesheet
