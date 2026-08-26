from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel

from clients.windows.store.library import ClipStatus
from clients.windows.ui.list_page import report_button_enabled
from clients.windows.ui.report_layout import ReportLink
from clients.windows.ui.report_panel import StageReportPanel
from core.i18n import set_language
from schemas.stage_report import FrameScorePoint, KeypointResult, KeypointStatus, StageReport, TreeNode


def _sample_report() -> StageReport:
    return StageReport(
        clip_id="c1",
        category_id="alpine_piste",
        stage_id="skid_short",
        category_name="Piste",
        stage_name="Short skids",
        confidence=0.6,
        ready_for_next_stage=False,
        disclaimer="heuristic",
        stage_focus="Short skidded turns",
        score_0_100=42.0,
        terrain_id="blue",
        terrain_name="Blue",
        terrain_desc="Suggested blue",
        weakest_checkpoint_id="cp_sk_hockey",
        next_level_ids=[],
        next_level_names=[],
        next_plans=[],
        tree_path=[
            TreeNode(id="pizza_glide", name="Wedge glide"),
            TreeNode(id="skid_short", name="Short skids", current=True),
        ],
        film_steps=["Follow-cam"],
        keypoints=[
            KeypointResult(
                id="cp_sk_hockey",
                name="Hockey-stop capacity",
                status=KeypointStatus.FAIL,
                score=20.0,
                value=4.0,
                evidence_ms=1240.0,
                good="stop",
                bad="cannot hockey stop",
                drills=[
                    {
                        "id": "drill_hockey",
                        "title": "Hockey stop",
                        "desc": "Matched-ski stop",
                        "training": ["8 each side"],
                        "venues": [
                            {
                                "id": "venue_green_groomer",
                                "name": "Green groomer",
                                "tips": "Easy pitch",
                            }
                        ],
                    }
                ],
            ),
            KeypointResult(
                id="cp_sk_rhythm",
                name="Cadence",
                status=KeypointStatus.PASS,
                score=80.0,
                value=0.5,
                evidence_ms=400.0,
                good="ok",
                bad="slow",
                drills=[],
            ),
        ],
        score_series=[
            FrameScorePoint(t_ms=0.0, score=40.0),
            FrameScorePoint(t_ms=400.0, score=55.0),
            FrameScorePoint(t_ms=800.0, score=38.0),
        ],
    )


def _ready_report() -> StageReport:
    report = _sample_report()
    return report.model_copy(
        update={
            "ready_for_next_stage": True,
            "score_0_100": 82.0,
            "weakest_checkpoint_id": "",
            "next_level_ids": ["mogul_absorb"],
            "next_level_names": ["Mogul absorption"],
            "next_plans": [
                {
                    "level_id": "mogul_absorb",
                    "level_name": "Mogul absorption",
                    "drills": [
                        {
                            "title": "Single-mogul absorption",
                            "desc": "Absorb",
                            "training": ["8 lines"],
                            "venues": [],
                        }
                    ],
                    "venues": [
                        {
                            "name": "Mogul field",
                            "desc": "Round bumps",
                            "tips": "Avoid jumps",
                        }
                    ],
                }
            ],
        }
    )


def test_report_button_enabled() -> None:
    assert report_button_enabled(ClipStatus.DONE, True) is True
    assert report_button_enabled(ClipStatus.DONE, False) is False
    assert report_button_enabled(ClipStatus.PROCESSING, True) is False
    assert report_button_enabled(ClipStatus.PENDING, True) is False


def test_stage_report_panel_five_chapters() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_sample_report())
    assert panel._gauge._score == 42.0
    assert panel._ch1.isVisible()
    assert panel._ch1.title() == "Summary"
    assert panel._ch5.title() == "Filming and scoring"
    assert "1." not in panel._ch1.title()
    assert "5." not in panel._ch5.title()
    ch3_text = " ".join(lab.text() for lab in panel._ch3.findChildren(QLabel))
    assert "Hockey stop" in ch3_text
    assert "Green groomer" in ch3_text
    panel.set_report(_ready_report())
    ch3_ready = " ".join(lab.text() for lab in panel._ch3.findChildren(QLabel))
    assert "Mogul absorption" in ch3_ready or "Mogul field" in ch3_ready
    panel.set_report(None)
    panel.show()
    assert not panel._ch1.isVisible()
    assert panel._empty.isVisible()
    del app


def test_report_charts_animate_and_timeline_seek() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    seen: list[int] = []
    panel.seekRequested.connect(seen.append)
    panel.set_report(_sample_report())
    assert panel._gauge._score == 42.0
    panel._gauge.set_reveal(1.0)
    assert panel._gauge.get_reveal() == 1.0
    panel._timeline.set_reveal(1.0)
    assert len(panel._timeline._points) == 3
    panel._timeline.resize(300, 150)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(150, 40),
        QPointF(150, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    panel._timeline.mousePressEvent(event)
    assert seen
    del app


def test_report_frame_link_emits_seek() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    seen: list[int] = []
    panel.seekRequested.connect(seen.append)
    panel.set_seek_enabled(True)
    panel.set_report(_sample_report())
    links = panel.findChildren(ReportLink)
    assert links
    links[0].clicked.emit()
    assert seen
    assert seen[0] == 1240
    del app


def test_report_labels_have_no_newline_layout() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.set_report(_sample_report())
    for lab in panel.findChildren(QLabel):
        if lab.objectName() == "skillTreeRoute":
            continue
        assert "\n" not in lab.text(), lab.objectName() or lab.text()[:40]
    panel.set_report(_ready_report())
    for lab in panel.findChildren(QLabel):
        if lab.objectName() == "skillTreeRoute":
            continue
        assert "\n" not in lab.text(), lab.objectName() or lab.text()[:40]
    del app


def test_score_purple_brighter_when_higher() -> None:
    from clients.windows.ui.theme import DEEP_PURPLE, LIGHT_PURPLE, score_purple

    low = score_purple(0.0)
    high = score_purple(100.0)
    mid = score_purple(50.0)
    assert low.name() == DEEP_PURPLE.name()
    assert high.name() == LIGHT_PURPLE.name()
    assert mid.lightness() > low.lightness()
    assert mid.lightness() < high.lightness()


def test_level_medal_and_terrain_diamonds() -> None:
    from clients.windows.ui.theme import (
        MEDAL_BEGINNER,
        MEDAL_ELITE,
        TERRAIN_BLACK,
        TERRAIN_BLUE,
        level_medal_color,
        terrain_diamond_colors,
    )

    assert level_medal_color("pizza_glide") == MEDAL_BEGINNER
    assert level_medal_color("carve_short") == MEDAL_ELITE
    assert terrain_diamond_colors("blue") == [TERRAIN_BLUE]
    assert terrain_diamond_colors("double_black") == [TERRAIN_BLACK, TERRAIN_BLACK]
