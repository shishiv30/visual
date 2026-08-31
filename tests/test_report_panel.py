from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel

from clients.windows.store.library import ClipStatus
from clients.windows.ui.list_page import report_button_enabled
from clients.windows.ui.report_charts import ScorePieChart, TurnStripChart
from clients.windows.ui.report_layout import (
    FrameSeekLink,
    ReportLink,
    SkillTreeRoute,
    SkillTreeView,
)
from clients.windows.ui.report_panel import (
    CHAPTERS,
    StageReportPanel,
    boot_flex_band,
    metric_state_text,
    ski_length_band,
)
from core.i18n import set_language
from schemas.stage_report import (
    Candidate,
    Classification,
    FilmingIssue,
    FrameScorePoint,
    KeypointResult,
    KeypointStatus,
    KnowledgeFocus,
    KnowledgeRef,
    MetricReport,
    MetricState,
    NodeState,
    PostureScores,
    ProfileSummary,
    Rubric,
    SceneSummary,
    StageReport,
    TreeNode,
    TreeNodeV3,
    TurnRecord,
    TurnSummary,
)

KNOWLEDGE_CHAPTERS = ("tutorial", "drills", "faults", "terrain", "equipment")


def _panel_text(widget) -> str:
    return " ".join(lab.text() for lab in widget.findChildren(QLabel))


def _sample_report() -> StageReport:
    """A stored 2.1.0-shaped report: no v3 blocks at all."""
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
                                "name": "Green run",
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


def _posture_report() -> StageReport:
    """The four-ring posture block: absent from every other fixture."""
    return _sample_report().model_copy(
        update={
            "posture": PostureScores(
                stability=71.0,
                coordination=63.0,
                control=58.0,
                balance=44.0,
            )
        }
    )


def _v3_metrics() -> list[MetricReport]:
    """One metric in each of the three states, plus a count-form gate."""
    return [
        MetricReport(
            id="stem_count",
            name="Stem at the transition",
            group="faults",
            state=MetricState.OK,
            value=3.0,
            display="3 of 22",
            unit="",
            score=68.0,
            rubric=Rubric.NOT_YET,
            reliability=0.82,
            is_gate=True,
            standard="at most 2 of 20",
            form="C",
            faulty_turns=3,
            total_turns=22,
            evidence_ms=1240.0,
        ),
        MetricReport(
            id="knee_valgus",
            name="Knee tracking",
            group="edging",
            state=MetricState.UNKNOWN,
            reason="view_too_profile",
            unit="ratio",
            is_gate=False,
        ),
        MetricReport(
            id="edge_angle_proxy",
            name="Edge angle",
            group="edging",
            state=MetricState.NOT_APPLICABLE,
            reason="carving is not assessed below age 13",
            unit="deg",
            is_gate=True,
        ),
        MetricReport(
            id="landmark_quality",
            name="Landmark quality",
            group="quality",
            state=MetricState.OK,
            value=0.91,
            display="91%",
            score=91.0,
            rubric=Rubric.PASS,
            reliability=0.9,
        ),
    ]


def _v3_tree() -> list[TreeNodeV3]:
    return [
        TreeNodeV3(
            id="pizza_glide",
            name="Wedge glide",
            kb_stage="st-02",
            branch="piste",
            state=NodeState.COMPLETED,
            score_best=88.0,
            gates_passed="3/3",
            depth=0,
            children=["parallel"],
        ),
        TreeNodeV3(
            id="parallel",
            name="Parallel skiing",
            kb_stage="st-06",
            branch="piste",
            state=NodeState.CURRENT,
            gates_passed="2/3",
            depth=1,
            parents=["pizza_glide"],
            children=["carve_long", "mogul_absorb"],
        ),
        TreeNodeV3(
            id="mogul_absorb",
            name="Mogul absorption",
            kb_stage="st-13",
            branch="moguls",
            state=NodeState.LOCKED,
            locked_reason="needs the sideslip gate ac-04-01",
            depth=2,
            parents=["parallel"],
        ),
        TreeNodeV3(
            id="powder",
            name="Powder and soft snow",
            kb_stage="st-14",
            tier="scene",
            branch="offpiste",
            state=NodeState.NOT_APPLICABLE,
            locked_reason="carving needs age 13+",
            depth=3,
            parents=["mogul_absorb"],
        ),
        TreeNodeV3(
            id="carve_long",
            name="Long-radius carve",
            kb_stage="st-10",
            branch="piste",
            state=NodeState.AVAILABLE,
            depth=2,
            parents=["parallel"],
        ),
        TreeNodeV3(
            id="specialization",
            name="Specialization and self-coaching",
            kb_stage="st-16",
            tier="catalog",
            branch="piste",
            state=NodeState.LOCKED,
            locked_reason="a catalog rung, never auto-detected",
            depth=3,
            parents=["carve_long"],
        ),
    ]


def _v3_report() -> StageReport:
    base = _sample_report()
    turns = [
        TurnRecord(
            index=i,
            side="left" if i % 2 == 0 else "right",
            t_start_ms=i * 400.0,
            t_end_ms=i * 400.0 + 380.0,
            duration_s=0.38,
            amplitude_deg=22.0,
            flags=["stem_count"] if i in (1, 4, 7) else [],
        )
        for i in range(10)
    ]
    return base.model_copy(
        update={
            "stage_id": "parallel",
            "stage_name": "Parallel skiing",
            "kb_stage": "st-06",
            "tier": "full",
            "classification": Classification(
                method="scored_candidates",
                chosen_id="parallel",
                confidence=0.62,
                separation=0.21,
                quality_factor=0.88,
                candidates=[
                    Candidate(
                        stage_id="parallel",
                        stage_name="Parallel skiing",
                        score=0.71,
                        fit=0.74,
                        gate_ratio=0.66,
                        prior=0.6,
                        tier="full",
                    ),
                    Candidate(
                        stage_id="wedge_christie",
                        stage_name="Wedge christie",
                        score=0.52,
                        fit=0.55,
                        gate_ratio=0.5,
                        prior=0.5,
                        tier="full",
                        separating_metric_id="stem_count",
                        separating_metric_name="Stem at the transition",
                        rejected_reason="the stem disappears in most transitions",
                    ),
                ],
            ),
            "metrics": _v3_metrics(),
            "turns": TurnSummary(
                count=10,
                left_count=5,
                right_count=5,
                mean_duration_s=0.38,
                duration_cv=0.14,
                turns=turns,
                fault_counts={"stem_count": 3},
            ),
            "tree": _v3_tree(),
            "knowledge_ref": KnowledgeRef(
                kb_stage="st-06", pack_version="1.0.0", level_id="parallel"
            ),
            "knowledge_focus": KnowledgeFocus(
                fault_ids=["ft-06-03"],
                drill_ids=["dr-06-02"],
                skill_ids=["sk-06-02"],
                weakest_metric_id="stem_count",
                weakest_metric_name="Stem at the transition",
            ),
            "scene": SceneSummary(
                snow_surface="hardpack",
                slope_band="blue",
                view_class="quarter",
                view_azimuth_deg=41.0,
                camera_motion="static",
                fps_effective=29.97,
                missing=["snow_surface"],
            ),
            "profile_summary": ProfileSummary(
                age_band="age-18-39",
                age_years=34.0,
                sex="female",
                height_cm=168.0,
                weight_kg=62.0,
                ski_cm=158.0,
                is_complete=True,
                effects=["Stance width normalized by leg length."],
                overlays=["phys-female-adult"],
            ),
            "filming": [
                FilmingIssue(
                    code="view_too_profile",
                    message="Film from three-quarter, not from the side.",
                    severity="warn",
                )
            ],
        }
    )


def test_report_button_enabled() -> None:
    assert report_button_enabled(ClipStatus.DONE, True) is True
    assert report_button_enabled(ClipStatus.DONE, False) is False
    assert report_button_enabled(ClipStatus.PROCESSING, True) is False
    assert report_button_enabled(ClipStatus.PENDING, True) is False


def test_chapter_list_is_data_driven() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    ids = [chapter_id for chapter_id, _t, _f, _c in CHAPTERS]
    assert len(CHAPTERS) == 12
    assert len(set(ids)) == len(ids)
    for chapter_id, title_key, fill_name, _collapsible in CHAPTERS:
        assert panel.chapter(chapter_id) is not None
        assert callable(getattr(panel, fill_name))
        assert panel.chapter(chapter_id).title() == title_key
        assert not title_key[:1].isdigit()
        assert "." not in title_key
    # the titles that survived the five-chapter layout are untouched
    assert panel.chapter("summary").title() == "Summary"
    assert panel.chapter("checkpoints").title() == "Checkpoints"
    assert panel.chapter("skill_tree").title() == "Skill tree"
    assert panel.chapter("filming").title() == "Filming and disclaimer"
    del app


def test_v3_report_renders_all_twelve_chapters() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_v3_report())
    assert panel.visible_chapter_ids() == [c[0] for c in CHAPTERS]
    why = _panel_text(panel.chapter("why_stage"))
    assert "Wedge christie" in why
    assert "Stem at the transition" in why
    assert "Three-quarter view" in why
    turns = _panel_text(panel.chapter("turns"))
    assert "3 of 10 transitions" in turns
    assert panel.chapter("turns").findChildren(TurnStripChart)
    tutorial = _panel_text(panel.chapter("tutorial"))
    assert "Goal" in tutorial
    equipment = _panel_text(panel.chapter("equipment"))
    assert "Ski length band" in equipment
    del app


def test_legacy_report_degrades_without_v3_blocks() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_sample_report())
    assert panel.visible_chapter_ids() == [
        "summary",
        "checkpoints",
        "skill_tree",
        "filming",
    ]
    checkpoints = _panel_text(panel.chapter("checkpoints"))
    assert "Hockey stop" in checkpoints
    assert "Green run" in checkpoints
    assert panel.chapter("skill_tree").findChildren(SkillTreeRoute)
    panel.set_report(_ready_report())
    tree_text = _panel_text(panel.chapter("skill_tree"))
    assert "Mogul absorption" in tree_text or "Mogul field" in tree_text
    panel.set_report(None)
    panel.show()
    assert not panel.chapter("summary").isVisible()
    assert panel._empty.isVisible()
    del app


def test_metric_states_render_as_states_not_zeros() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.set_report(_v3_report())
    chapter = panel.chapter("core_metrics")
    text = _panel_text(chapter)
    assert "Not measured" in text
    assert "Not applicable" in text
    assert "view_too_profile" in text
    assert "carving is not assessed below age 13" in text
    # a state is never drawn as a zero ring
    for pie in chapter.findChildren(ScorePieChart):
        assert pie._score not in (0.0,)
    metrics = _v3_metrics()
    assert metric_state_text(metrics[0]) == ""
    assert metric_state_text(metrics[1]) == "Not measured"
    assert metric_state_text(metrics[2]) == "Not applicable"
    assert "3 of 22" in text
    assert "at most 2 of 20" in text
    del app


def test_locked_tree_node_shows_its_reason() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.set_report(_v3_report())
    chapter = panel.chapter("skill_tree")
    views = chapter.findChildren(SkillTreeView)
    assert views
    assert views[0].node_count() == 6
    text = _panel_text(chapter)
    assert "needs the sideslip gate ac-04-01" in text
    assert "carving needs age 13+" in text
    assert "Locked" in text
    assert "Not applicable" in text
    assert "Moguls" in text and "Off-piste" in text
    assert "Specialization and self-coaching" in text
    del app


def test_knowledge_chapters_collapse_by_default() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_v3_report())
    defaults = {chapter_id: flag for chapter_id, _t, _f, flag in CHAPTERS}
    for chapter_id in KNOWLEDGE_CHAPTERS:
        assert defaults[chapter_id] is True
        box = panel.chapter(chapter_id)
        assert box.is_collapsible()
        assert box.is_expanded() is False
        assert box.grid().isVisibleTo(box) is False
        box.set_expanded(True)
        assert box.grid().isVisibleTo(box) is True
    for chapter_id in ("summary", "why_stage", "core_metrics", "turns", "checkpoints", "skill_tree", "filming"):
        box = panel.chapter(chapter_id)
        assert box.is_collapsible() is False
        assert box.is_expanded() is True
    del app


def test_turn_strip_seek_and_flags() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    seen: list[int] = []
    panel.seekRequested.connect(seen.append)
    panel.set_report(_v3_report())
    strips = panel.chapter("turns").findChildren(TurnStripChart)
    assert strips
    strip = strips[0]
    strip.resize(400, 88)
    strip.set_reveal(1.0)
    cells = strip._cells()
    assert len(cells) == 10
    assert sum(1 for _rect, turn in cells if turn.flags) == 3
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(cells[4][0].center().x(), 30.0),
        QPointF(cells[4][0].center().x(), 30.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    strip.mousePressEvent(event)
    assert seen and seen[-1] == 1600
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


def _send_click(widget) -> tuple[bool, bool]:
    """Real press + release through the event system; returns accepted flags.

    ``clicked.emit()`` cannot see the actual bug: a widget that ignores the
    press never receives the release, because Qt routes the rest of the
    sequence to the scroll viewport that did accept it.
    """
    pos = QPointF(widget.rect().center())
    flags: list[bool] = []
    for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        event = QMouseEvent(
            kind,
            pos,
            QPointF(widget.mapToGlobal(pos.toPoint())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton if kind == QEvent.Type.MouseButtonPress
            else Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(widget, event)
        flags.append(event.isAccepted())
    return flags[0], flags[1]


def test_report_links_accept_the_press_so_the_release_arrives() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    seen: list[int] = []
    panel.seekRequested.connect(seen.append)
    panel.set_seek_enabled(True)
    panel.set_report(_sample_report())

    seek_links = panel.findChildren(FrameSeekLink)
    assert seek_links
    for widget in (seek_links[0], seek_links[0]._text):
        widget.resize(120, 44)
        pressed, released = _send_click(widget)
        # An ignored press is what made every frame-seek link dead.
        assert pressed is True
        assert released is True
    assert seen
    assert seen[0] == 1240
    del app


def test_stale_cards_are_dropped_when_a_legacy_report_replaces_a_v3_one() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_v3_report())
    for chapter_id, _title, _fill, _collapsible in CHAPTERS:
        panel.chapter(chapter_id).set_expanded(True)
    assert "Stem at the transition" in _panel_text(panel)

    panel.set_report(_sample_report())
    for chapter_id, _title, _fill, _collapsible in CHAPTERS:
        panel.chapter(chapter_id).set_expanded(True)
    text = _panel_text(panel)
    for v3_only in (
        "Stem at the transition",
        "Wedge christie",
        "needs the sideslip gate ac-04-01",
        "Parallel skiing",
    ):
        assert v3_only not in text, v3_only
    assert panel.visible_chapter_ids() == [
        "summary",
        "checkpoints",
        "skill_tree",
        "filming",
    ]
    del app


def test_posture_rings_and_their_heuristics_disclaimer() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    panel.show()
    panel.set_report(_posture_report())
    summary = panel.chapter("summary")
    text = _panel_text(summary)
    assert "coach heuristics" in text
    assert "not lab biomechanics" in text
    captions = {pie._caption for pie in summary.findChildren(ScorePieChart)}
    for label in ("Stability", "Coordination", "Control", "Balance"):
        assert label in captions, label
    scores = {
        pie._caption: pie._score for pie in summary.findChildren(ScorePieChart)
    }
    assert scores["Stability"] == 71.0
    assert scores["Balance"] == 44.0
    # chapter 1 is stage / score / confidence / posture / terrain only: the
    # checkpoint rings belong to chapter 5 and must not be duplicated here.
    assert "Hockey-stop capacity" not in captions
    assert "Hockey-stop capacity" in _panel_text(panel.chapter("checkpoints"))
    del app


def test_missing_knowledge_pack_hides_the_pack_chapters() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    from clients.windows.ui import report_knowledge

    original = report_knowledge.load_pack
    report_knowledge.reset_cache()
    report_knowledge.load_pack = lambda: None
    try:
        panel = StageReportPanel()
        panel.show()
        panel.set_report(_v3_report())
        visible = panel.visible_chapter_ids()
    finally:
        report_knowledge.load_pack = original
        report_knowledge.reset_cache()
    for chapter_id in ("tutorial", "drills", "faults", "terrain"):
        assert chapter_id not in visible, chapter_id
    for chapter_id in ("summary", "checkpoints", "skill_tree", "filming"):
        assert chapter_id in visible, chapter_id
    # chapter 11 survives a missing pack on its profile-derived lines alone
    assert "equipment" in visible
    del app


def test_report_labels_have_no_newline_layout() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    panel = StageReportPanel()
    for report in (_sample_report(), _ready_report(), _v3_report()):
        panel.set_report(report)
        for chapter_id, _title, _fill, _collapsible in CHAPTERS:
            panel.chapter(chapter_id).set_expanded(True)
        for lab in panel.findChildren(QLabel):
            if lab.objectName() == "skillTreeRoute":
                continue
            assert "\n" not in lab.text(), lab.objectName() or lab.text()[:40]
    del app


def test_skill_tree_route_is_vertical_list() -> None:
    app = QApplication.instance() or QApplication([])
    route = SkillTreeRoute()
    route.set_route([])
    assert route.sizeHint().height() == SkillTreeRoute.ROW_H
    route.set_route(
        [
            TreeNode(id="a", name="Wedge glide"),
            TreeNode(id="b", name="Short skids", current=True),
            TreeNode(id="c", name="Parallel"),
        ]
    )
    assert route.sizeHint().height() == 3 * SkillTreeRoute.ROW_H
    panel = StageReportPanel()
    panel.set_report(_sample_report())
    trees = panel.findChildren(SkillTreeRoute)
    assert trees
    assert trees[0].sizeHint().height() >= 2 * SkillTreeRoute.ROW_H
    del app


def test_skill_tree_view_orders_branches_under_the_spine() -> None:
    from clients.windows.ui.report_layout import order_tree_rows

    rows = order_tree_rows(_v3_tree())
    ids = [node.id for node, _indent in rows]
    indents = {node.id: indent for node, indent in rows}
    assert ids[0] == "pizza_glide"
    assert indents["pizza_glide"] == 0
    assert indents["parallel"] == 0
    assert indents["mogul_absorb"] == 1
    assert indents["powder"] == 1
    assert ids.index("mogul_absorb") > ids.index("parallel")
    assert order_tree_rows([]) == []


def test_profile_equipment_bands() -> None:
    assert ski_length_band(168.0, "st-02") == (145, 155)
    assert ski_length_band(168.0, "st-06") == (155, 165)
    assert ski_length_band(168.0, "st-10") == (160, 175)
    assert boot_flex_band(62.0, "age-18-39") == (60, 80)
    assert boot_flex_band(30.0, "age-7-12") == (40, 60)


def test_spacing_tokens_drive_report_layout() -> None:
    from clients.windows.ui.report_layout import ReportCard, ReportChapter, ReportGrid
    from clients.windows.ui.theme import (
        PAGE_INSET,
        SPACE_CHAPTER,
        SPACE_PANEL,
        SPACE_TEXT,
        TAP_TARGET,
    )

    assert SPACE_CHAPTER == 36
    assert SPACE_PANEL == 24
    assert SPACE_TEXT == 16
    assert PAGE_INSET == 12
    assert TAP_TARGET == 44
    app = QApplication.instance() or QApplication([])
    card = ReportCard()
    assert card.body().spacing() == SPACE_TEXT
    assert card.body().contentsMargins().left() == PAGE_INSET
    chapter = ReportChapter()
    assert chapter.layout().spacing() == SPACE_TEXT
    collapsible = ReportChapter(collapsible=True)
    assert collapsible._button.minimumHeight() == TAP_TARGET
    grid = ReportGrid()
    assert grid.layout().spacing() == SPACE_PANEL
    panel = StageReportPanel()
    inner = panel._scroll.widget()
    assert inner.layout().spacing() == SPACE_CHAPTER
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
    assert terrain_diamond_colors("black") == [TERRAIN_BLACK]
    assert terrain_diamond_colors("double_black") == [TERRAIN_BLACK, TERRAIN_BLACK]
    assert TERRAIN_BLACK.name() == "#000000"


def test_report_state_colors_are_distinct() -> None:
    from clients.windows.ui.theme import (
        metric_state_color,
        rubric_color,
        severity_color,
        tree_node_color,
    )

    states = {
        tree_node_color("completed").name(),
        tree_node_color("current").name(),
        tree_node_color("available").name(),
        tree_node_color("locked").name(),
        tree_node_color("not_applicable").name(),
    }
    assert len(states) == 5
    assert tree_node_color("available", "catalog") == tree_node_color("locked")
    assert metric_state_color("unknown") != metric_state_color("not_applicable")
    assert metric_state_color("ok", 100.0) != metric_state_color("unknown")
    assert rubric_color("not_yet") != rubric_color("pass")
    assert rubric_color("strong") != rubric_color("pass")
    assert severity_color("blocker") != severity_color("info")
