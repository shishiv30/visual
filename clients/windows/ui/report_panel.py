"""Twelve-chapter ski stage report (design doc §7).

The chapter list is data: :data:`CHAPTERS` is iterated to build the panel, so a
thirteenth chapter is one tuple entry plus one ``_fill_*`` method. Each fill
method returns ``True`` when it produced content; a chapter that produced
nothing is hidden, which is how a stored 2.1.0 report degrades to the four
chapters it can actually fill (1 Summary, 5 Checkpoints, 6 Skill tree,
12 Filming) without a single version check in the render path.

Chapters 1-6 are diagnosis, 7-11 come from the knowledge pack, 12 is
housekeeping. Chapters 7-11 start collapsed so the diagnosis stays above the
fold.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.store.library import list_reports_for_athlete
from clients.windows.ui.correction_dialog import CorrectionDialog
from core.sports.curriculum import load_curriculum
from core.sports.history import StageHistory
from core.sports.tree import build_tree
from clients.windows.ui.report_charts import (
    ScorePieChart,
    ScoreTimelineChart,
    TurnStripChart,
)
from clients.windows.ui.report_knowledge import (
    StageKnowledge,
    order_by_ids,
    pretty_ref_id,
    stage_knowledge,
)
from clients.windows.ui.report_layout import (
    FrameSeekLink,
    IconTextRow,
    ReportCard,
    ReportChapter,
    ReportGrid,
    SkillTreeRoute,
    SkillTreeView,
    add_chip_rows,
    add_text_stack,
)
from clients.windows.ui.theme import (
    SPACE_CHAPTER,
    level_medal_color,
    score_purple,
    terrain_diamond_colors,
)
from core.i18n import t
from schemas.stage_report import (
    KeypointResult,
    KeypointStatus,
    MetricReport,
    MetricState,
    ProfileSummary,
    Rubric,
    StageReport,
)

#: ``(chapter_id, title_key, fill_method_name, collapsible_default)``.
#:
#: ``collapsible_default`` true means the chapter gets a disclosure header and
#: starts collapsed. Titles for the chapters that survived the five-chapter
#: layout are unchanged.
CHAPTERS: tuple[tuple[str, str, str, bool], ...] = (
    ("summary", "Summary", "_fill_summary", False),
    ("why_stage", "Why this stage", "_fill_why_stage", False),
    ("core_metrics", "Core metrics", "_fill_core_metrics", False),
    ("turns", "Turn-by-turn", "_fill_turns", False),
    ("checkpoints", "Checkpoints", "_fill_checkpoints", False),
    ("skill_tree", "Skill tree", "_fill_skill_tree", False),
    ("tutorial", "Stage tutorial", "_fill_tutorial", True),
    ("drills", "Drills", "_fill_drills", True),
    ("faults", "Faults and fixes", "_fill_faults", True),
    ("terrain", "Terrain and venue", "_fill_terrain", True),
    ("equipment", "Equipment", "_fill_equipment", True),
    ("filming", "Filming and disclaimer", "_fill_filming", False),
)

RUBRIC_LABELS = {
    Rubric.NOT_YET.value: "Not yet",
    Rubric.PASS.value: "Pass",
    Rubric.STRONG.value: "Strong",
    Rubric.NOT_RATED.value: "Not rated",
}

METRIC_STATE_LABELS = {
    MetricState.UNKNOWN.value: "Not measured",
    MetricState.NOT_APPLICABLE.value: "Not applicable",
}

VIEW_LABELS = {
    "profile": "Profile view",
    "quarter": "Three-quarter view",
    "frontal": "Front view",
}

MOTION_LABELS = {
    "static": "Static camera",
    "panning": "Panning camera",
    "follow": "Follow camera",
}

SNOW_LABELS = {
    "corduroy": "Corduroy",
    "packed": "Packed powder",
    "hardpack": "Hardpack",
    "ice": "Ice",
    "soft": "Soft snow",
    "powder": "Powder",
    "crud": "Crud",
    "slush": "Slush",
}

SLOPE_LABELS = {
    "green": "Green",
    "blue": "Blue",
    "black": "Black",
    "double-black": "Double black",
    "double_black": "Double black",
}

SCENE_FACT_LABELS = {
    "snow_surface": "Snow surface",
    "slope_band": "Slope band",
    "view": "Camera view",
    "camera_motion": "Camera motion",
}

#: Count-form fault metric ids → coaching English, for the turn callouts.
FAULT_LABELS = {
    "stem_count": "Stem",
    "backseat_count": "Back seat",
    "rotation_count": "Upper-body rotation",
    "braking_count": "Braking at the finish",
    "asymmetry_index": "Left-right asymmetry",
}

SEVERITY_LABELS = {
    "info": "Note",
    "warn": "Warning",
    "blocker": "Blocker",
}

#: Observability tier (design doc §1.1) → what it means for the reader.
TIER_LABELS = {
    "full": "Scorable from the clip",
    "scene": "Needs a scene fact",
    "catalog": "Not judged from a clip",
}

SIDE_LABELS = {"left": "Left", "right": "Right"}

#: Knowledge-module sections rendered in full before the rest are listed.
MAX_SECTIONS = 3
#: Table rows rendered before the table is summarised.
MAX_TABLE_ROWS = 8


def _sorted_keypoints(items: list[KeypointResult]) -> list[KeypointResult]:
    def key(item: KeypointResult) -> tuple[int, float]:
        score = item.score if item.score is not None else 101.0
        return (0 if item.status == KeypointStatus.FAIL else 1, score)

    return sorted(items, key=key)


def format_evidence_ms(t_ms: float) -> str:
    total = max(0.0, t_ms / 1000.0)
    minutes = int(total // 60)
    seconds = total - minutes * 60
    return f"{minutes}:{seconds:04.1f}"


def _fmt_number(value: float) -> str:
    if abs(value) >= 100.0 or float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:.2f}"


def _enum_value(value: object) -> str:
    return getattr(value, "value", value) if value is not None else ""


def metric_state(metric: MetricReport) -> str:
    return str(_enum_value(metric.state) or MetricState.UNKNOWN.value)


def metric_state_text(metric: MetricReport) -> str:
    """Explicit state copy for a metric that has no usable number."""
    key = METRIC_STATE_LABELS.get(metric_state(metric), "")
    return t(key) if key else ""


def metric_has_ring(metric: MetricReport) -> bool:
    """A score ring is only honest for a measured metric with a score."""
    return metric_state(metric) == MetricState.OK.value and metric.score is not None


def metric_value_text(metric: MetricReport) -> str:
    if metric.display:
        return metric.display
    if not metric_has_ring(metric) and metric.value is None:
        return metric_state_text(metric) or t("—")
    if metric.value is None:
        return t("—")
    number = _fmt_number(float(metric.value))
    return f"{number} {metric.unit}".strip() if metric.unit else number


def rubric_chip(metric: MetricReport) -> tuple[str, str]:
    rubric = str(_enum_value(metric.rubric) or Rubric.NOT_RATED.value)
    return t(RUBRIC_LABELS.get(rubric, "Not rated")), rubric


def fault_label(fault_id: str, metrics: list[MetricReport]) -> str:
    """Prefer the metric's own name; fall back to the coaching label."""
    for metric in metrics:
        if metric.id == fault_id and metric.name:
            return metric.name
    key = FAULT_LABELS.get(fault_id)
    return t(key) if key else pretty_ref_id(fault_id)


def faulty_turn_sentence(label: str, faulty: int, total: int) -> str:
    """The gate wording the curriculum uses: "stem in 3 of 22 transitions"."""
    return t(
        "{fault} in {n} of {total} transitions",
        fault=label,
        n=faulty,
        total=total,
    )


def _stage_number(kb_stage: str) -> int:
    digits = "".join(ch for ch in str(kb_stage) if ch.isdigit())
    return int(digits) if digits else 0


def _round5(value: float) -> int:
    return int(round(value / 5.0) * 5)


def ski_length_band(height_cm: float, kb_stage: str) -> tuple[int, int]:
    """Starting length range in cm, from height and how far up the ladder.

    Chin-to-nose while the wedge is still the tool, nose-to-brow through
    parallel, head height and above once the skier is carving.
    """
    stage = _stage_number(kb_stage)
    if stage and stage <= 5:
        low, high = height_cm - 25.0, height_cm - 15.0
    elif not stage or stage <= 9:
        low, high = height_cm - 15.0, height_cm - 5.0
    else:
        low, high = height_cm - 10.0, height_cm + 5.0
    return _round5(low), _round5(high)


def boot_flex_band(weight_kg: float, age_band: str) -> tuple[int, int]:
    """Starting flex index range. Junior shells are their own scale."""
    if age_band in ("age-3-6", "age-7-12"):
        return 40, 60
    if age_band == "age-13-17":
        return 60, 80
    low = min(120, max(60, _round5(weight_kg * 0.9)))
    high = min(140, max(low + 10, _round5(weight_kg * 1.3)))
    return low, high


def profile_equipment_lines(
    profile: ProfileSummary | None,
    kb_stage: str,
) -> list[str]:
    """Profile-derived equipment guidance. Guidance only — never a score."""
    if profile is None or not profile.is_complete:
        return []
    lines: list[str] = [
        t("Equipment guidance is a starting range from height and weight, not a boot fitting.")
    ]
    if profile.height_cm:
        low, high = ski_length_band(float(profile.height_cm), kb_stage)
        lines.append(t("Ski length band: {low}-{high} cm", low=low, high=high))
        if profile.ski_cm:
            own = _fmt_number(float(profile.ski_cm))
            if low <= float(profile.ski_cm) <= high:
                lines.append(
                    t("Your skis at {own} cm sit inside that band.", own=own)
                )
            else:
                lines.append(
                    t("Your skis at {own} cm sit outside that band.", own=own)
                )
    if profile.weight_kg:
        low, high = boot_flex_band(float(profile.weight_kg), profile.age_band)
        lines.append(t("Boot flex band: {low}-{high}", low=low, high=high))
    if profile.age_band in ("age-3-6", "age-7-12"):
        lines.append(t("Check the rental skis still have edges before the first run."))
    if profile.sex:
        lines.append(
            t("Sex is used only for fit guidance and the injury note; it never changes a score.")
        )
    return lines


def _score_card(pie: ScorePieChart) -> ReportCard:
    card = ReportCard()
    card.body().addWidget(pie)
    return card


def _detach(widget: QWidget) -> None:
    """Drop a chart the grid already scheduled for deletion, safely.

    ``ReportGrid.clear()`` calls ``deleteLater``, so a chart kept on the panel
    can outlive its C++ object when its chapter was skipped on the last render.
    """
    try:
        widget.setParent(None)
    except RuntimeError:
        pass


class StageReportPanel(QWidget):
    seekRequested = Signal(int)
    seekAndPlayRequested = Signal(int)
    correctionSaved = Signal()
    nodeClicked = Signal(str, str)  # (level_id, clip_id_best)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stageReportPanel")
        self._report: StageReport | None = None
        self._knowledge: StageKnowledge | None = None
        self._seek_enabled = True
        self._athlete_key: str | None = None
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._empty = QLabel()
        self._empty.setObjectName("reportEmpty")
        self._empty.setWordWrap(True)

        self._gauge = ScorePieChart()
        self._timeline = ScoreTimelineChart()
        self._timeline.seekRequested.connect(self.seekRequested.emit)
        self._turn_strip = TurnStripChart()
        self._turn_strip.seekRequested.connect(self.seekRequested.emit)

        inner = QWidget()
        body = QVBoxLayout(inner)
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(SPACE_CHAPTER)
        body.addWidget(self._empty)
        self._chapters: dict[str, ReportChapter] = {}
        for chapter_id, _title_key, _fill, collapsible in CHAPTERS:
            box = ReportChapter(collapsible=collapsible)
            self._chapters[chapter_id] = box
            body.addWidget(box)
        body.addStretch()

        self._scroll = QScrollArea()
        self._scroll.setObjectName("reportScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._scroll.setWidget(inner)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        self.retranslate()
        self.set_report(None)

    # --- public API -----------------------------------------------------

    def chapter(self, chapter_id: str) -> ReportChapter | None:
        return self._chapters.get(chapter_id)

    def visible_chapter_ids(self) -> list[str]:
        return [
            chapter_id
            for chapter_id, _title, _fill, _collapsible in CHAPTERS
            if self._chapters[chapter_id].isVisibleTo(self)
        ]

    def set_seek_enabled(self, enabled: bool) -> None:
        self._seek_enabled = enabled

    def set_scroll_max_height(self, height: int | None) -> None:
        if height is None:
            self._scroll.setMaximumHeight(16777215)
        else:
            self._scroll.setMaximumHeight(height)

    def set_athlete_key(self, key: str | None) -> None:
        self._athlete_key = key

    def retranslate(self) -> None:
        self._empty.setText(t("No stage report yet. Analyze a clip offline first."))
        for chapter_id, title_key, _fill, _collapsible in CHAPTERS:
            self._chapters[chapter_id].set_title(t(title_key))
        self.set_report(self._report)

    def set_report(self, report: StageReport | None) -> None:
        # A new report re-collapses chapters 7-11 so the diagnosis is above the
        # fold again. ``retranslate`` re-renders the *same* object, so a
        # language switch keeps whatever the user had expanded.
        is_new_report = report is not self._report
        self._report = report
        has = report is not None
        self._empty.setVisible(not has)
        for chapter_id, _title, _fill, _collapsible in CHAPTERS:
            self._chapters[chapter_id].grid().clear()
        if report is None:
            for box in self._chapters.values():
                box.setVisible(False)
            self._knowledge = None
            return
        self._knowledge = self._resolve_knowledge(report)
        for chapter_id, _title, fill_name, _collapsible in CHAPTERS:
            box = self._chapters[chapter_id]
            if is_new_report and box.is_collapsible():
                box.set_expanded(False)
            filled = bool(getattr(self, fill_name)(report))
            box.grid().finish()
            box.setVisible(filled)

    # --- knowledge pack -------------------------------------------------

    def _resolve_knowledge(self, report: StageReport) -> StageKnowledge | None:
        """Only an explicit ``kb_stage`` opens the curriculum chapters.

        A 2.1.0 report carries neither field, so chapters 7-11 stay closed
        rather than guessing a stage from the level id.
        """
        ref = report.knowledge_ref
        kb_stage = (ref.kb_stage if ref is not None else "") or report.kb_stage
        if not kb_stage:
            return None
        return stage_knowledge(kb_stage)

    # --- chapter 1: summary ---------------------------------------------

    def _fill_summary(self, report: StageReport) -> bool:
        grid = self._chapters["summary"].grid()
        overview = ReportCard()

        # Stage title row: trophy + name on the left, correction button on the right
        correct_btn = QPushButton(t("Correct result"))
        correct_btn.setObjectName("reportCorrectBtn")

        def _open_correction() -> None:
            dlg = CorrectionDialog(report, parent=self)
            if dlg.exec() == CorrectionDialog.DialogCode.Accepted:
                self.correctionSaved.emit()

        correct_btn.clicked.connect(_open_correction)

        title_row_widget = QWidget()
        title_row = QHBoxLayout(title_row_widget)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        classification = report.classification
        ambiguous = (
            classification is not None
            and classification.ambiguous
            and classification.candidates
        )
        if ambiguous:
            candidates = sorted(
                classification.candidates,
                key=lambda c: float(c.score),
                reverse=True,
            )[:2]
            names = [c.stage_name or c.stage_id for c in candidates]
            stage_title = f"{t('Possible stage')}: {' · '.join(names)}"
        else:
            stage_title = report.stage_name

        title_row.addWidget(
            IconTextRow(
                [("trophy", level_medal_color(report.stage_id))],
                stage_title,
                object_name="reportMeta",
            ),
            stretch=1,
        )
        title_row.addWidget(correct_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        overview.body().addWidget(title_row_widget)

        if report.stage_focus:
            focus = QLabel(report.stage_focus)
            focus.setObjectName("reportMeta")
            focus.setWordWrap(True)
            overview.body().addWidget(focus)
        grid.add(overview, per_row=1)

        terrain = ReportCard()
        gate = (
            t("Passed this level. Choose a next level on the skill tree.")
            if report.ready_for_next_stage
            else t("Not passed — train the lowest-scoring checkpoint.")
        )
        trail = report.terrain_name or t("—")
        terrain_line = f"{t('Suggested trail rating')}: {trail}"
        diamonds = [("diamond", c) for c in terrain_diamond_colors(report.terrain_id)]
        terrain.body().addWidget(
            IconTextRow(diamonds, terrain_line, object_name="reportAdvice")
        )
        if report.terrain_desc:
            desc = QLabel(report.terrain_desc)
            desc.setObjectName("reportMeta")
            desc.setWordWrap(True)
            terrain.body().addWidget(desc)
        # The gate sentence is its own paragraph: a label and a full sentence
        # never share one QLabel (a "·" join is still a joined paragraph).
        add_text_stack(terrain.body(), [gate], object_name="reportAdvice")
        grid.add(terrain, per_row=1)

        _detach(self._gauge)
        self._gauge = ScorePieChart()
        self._gauge.set_score(
            report.score_0_100,
            t("Heuristic score (0-100, not FIS)"),
            ring_color=score_purple(report.score_0_100),
        )
        grid.add(_score_card(self._gauge), per_row=2)

        conf_score = report.confidence * 100.0
        confidence = ScorePieChart()
        conf_caption = (
            t("Leading candidate")
            if ambiguous
            else t("Confidence")
        )
        confidence.set_score(
            conf_score,
            conf_caption,
            ring_color=score_purple(conf_score),
        )
        grid.add(_score_card(confidence), per_row=2)

        if report.posture is not None:
            note = ReportCard()
            add_text_stack(
                note.body(),
                [t("Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure.")],
                object_name="reportMeta",
            )
            grid.add(note, per_row=1)
            for key, label_key in (
                ("stability", "Stability"),
                ("coordination", "Coordination"),
                ("control", "Control"),
                ("balance", "Balance"),
            ):
                value = float(getattr(report.posture, key))
                pie = ScorePieChart()
                pie.set_score(value, t(label_key), ring_color=score_purple(value))
                grid.add(_score_card(pie), per_row=2)

        # No per-checkpoint rings here: design §7 fixes chapter 1 as stage /
        # score / confidence / posture / terrain. Chapter 5 owns the
        # checkpoints and renders the same rings with their chips and drills.
        timeline_card = ReportCard()
        caption = QLabel(t("Stability over time (time × frame score)"))
        caption.setObjectName("reportMeta")
        caption.setWordWrap(True)
        timeline_card.body().addWidget(caption)
        _detach(self._timeline)
        self._timeline = ScoreTimelineChart()
        if self._seek_enabled:
            self._timeline.seekRequested.connect(self.seekRequested.emit)
        else:
            self._timeline.setToolTip(
                t("Open the report on the player page to jump to this frame.")
            )
        self._timeline.set_points(report.score_series)
        timeline_card.body().addWidget(self._timeline)
        grid.add(timeline_card, per_row=1)

        return True

    # --- chapter 2: why this stage --------------------------------------

    def _fill_why_stage(self, report: StageReport) -> bool:
        classification = report.classification
        if classification is None:
            return False
        grid = self._chapters["why_stage"].grid()
        # Nothing in the schema guarantees the candidate list is sorted, and the
        # first card is labelled "Best match" — sort before slicing.
        candidates = sorted(
            classification.candidates, key=lambda c: float(c.score), reverse=True
        )[:2]

        head = ReportCard()
        lines: list[str] = []
        if classification.ambiguous:
            lines.append(
                t("Possible stage — confidence is below the gate, so both candidates are shown.")
            )
            names = [c.stage_name or c.stage_id for c in candidates]
            if names:
                lines.append(f"{t('Possible stage')}: {' · '.join(names)}")
        else:
            chosen = next(
                (
                    c.stage_name
                    for c in classification.candidates
                    if c.stage_id == classification.chosen_id and c.stage_name
                ),
                report.stage_name,
            )
            lines.append(f"{t('Stage')}: {chosen}")
        lines.append(
            t("Confidence {pct:.0f}% · separation {sep:.2f}",
              pct=classification.confidence * 100.0,
              sep=classification.separation)
        )
        if classification.unusable_reason:
            lines.append(
                f"{t('Clip could not be scored')}: {classification.unusable_reason}"
            )
        add_text_stack(head.body(), lines, object_name="reportAdvice")
        grid.add(head, per_row=1)

        for index, candidate in enumerate(candidates):
            card = ReportCard()
            title = candidate.stage_name or candidate.stage_id
            card.body().addWidget(
                IconTextRow(
                    [("trophy", level_medal_color(candidate.stage_id))],
                    title,
                    object_name="reportAdvice",
                )
            )
            chips: list[tuple[str, str]] = [
                (
                    t("Best match") if index == 0 else t("Runner-up"),
                    "pass" if index == 0 else "info",
                ),
            ]
            if candidate.tier:
                tier_label = TIER_LABELS.get(candidate.tier)
                if tier_label:
                    chips.append((t(tier_label), "info"))
            add_chip_rows(card.body(), chips, per_row=3)
            detail = [
                t("Match {fit:.0f}% · gates {gate:.0f}% · prior {prior:.0f}%",
                  fit=candidate.fit * 100.0,
                  gate=candidate.gate_ratio * 100.0,
                  prior=candidate.prior * 100.0),
            ]
            if candidate.separating_metric_name or candidate.separating_metric_id:
                metric = (
                    candidate.separating_metric_name
                    or pretty_ref_id(candidate.separating_metric_id)
                )
                detail.append(f"{t('Separated by')}: {metric}")
            if candidate.rejected_reason:
                detail.append(f"{t('Set aside because')}: {candidate.rejected_reason}")
            add_text_stack(card.body(), detail, object_name="reportMeta")
            grid.add(card, per_row=2)

        badges = ReportCard()
        add_text_stack(
            badges.body(),
            [t("What the clip itself could tell us")],
            object_name="reportAdvice",
        )
        add_chip_rows(badges.body(), self._quality_chips(report), per_row=3)
        grid.add(badges, per_row=1)
        return True

    def _quality_chips(self, report: StageReport) -> list[tuple[str, str]]:
        chips: list[tuple[str, str]] = []
        scene = report.scene
        classification = report.classification
        if scene is not None:
            if scene.view_class:
                label = VIEW_LABELS.get(scene.view_class, scene.view_class)
                kind = "pass" if scene.view_class in ("quarter", "frontal") else "not_yet"
                chips.append((t(label), kind))
            if scene.view_azimuth_deg is not None:
                chips.append(
                    (
                        t("View angle {deg:.0f}°", deg=scene.view_azimuth_deg),
                        "info",
                    )
                )
            if scene.camera_motion:
                label = MOTION_LABELS.get(scene.camera_motion, scene.camera_motion)
                kind = "pass" if scene.camera_motion == "static" else "not_yet"
                chips.append((t(label), kind))
            if scene.snow_surface:
                label = SNOW_LABELS.get(scene.snow_surface, scene.snow_surface)
                chips.append((f"{t('Snow surface')}: {t(label)}", "pass"))
            if scene.slope_band:
                label = SLOPE_LABELS.get(scene.slope_band, scene.slope_band)
                chips.append((f"{t('Slope band')}: {t(label)}", "pass"))
            for missing in scene.missing:
                label = SCENE_FACT_LABELS.get(missing, pretty_ref_id(missing))
                chips.append((f"{t('Missing')}: {t(label)}", "warn"))
            if scene.fps_effective is not None:
                chips.append(
                    (
                        t("Effective {fps:.1f} fps", fps=scene.fps_effective),
                        "info",
                    )
                )
        quality = next(
            (m for m in report.metrics if m.id == "landmark_quality"),
            None,
        )
        if quality is not None:
            chips.append(
                (f"{t('Landmark quality')}: {metric_value_text(quality)}", "info")
            )
        elif classification is not None:
            chips.append(
                (
                    t("Landmark quality {pct:.0f}%",
                      pct=classification.quality_factor * 100.0),
                    "info",
                )
            )
        return chips

    # --- chapter 3: core metrics ----------------------------------------

    def _fill_core_metrics(self, report: StageReport) -> bool:
        if not report.metrics:
            return False
        grid = self._chapters["core_metrics"].grid()
        legend = ReportCard()
        add_text_stack(
            legend.body(),
            [
                t("Gate metrics decide advancement; the rest are diagnostic."),
                t("A metric that could not be measured says so — it is never shown as a zero."),
            ],
            object_name="reportMeta",
        )
        grid.add(legend, per_row=1)
        for metric in report.metrics:
            grid.add(self._metric_card(metric), per_row=2)
        return True

    def _metric_card(self, metric: MetricReport) -> ReportCard:
        card = ReportCard()
        if metric.is_gate:
            card.setObjectName("reportGateCard")
        title = metric.name or pretty_ref_id(metric.id)
        add_text_stack(card.body(), [title], object_name="reportAdvice")
        chips: list[tuple[str, str]] = []
        if metric.is_gate:
            chips.append((t("Gate"), "gate"))
        else:
            chips.append((t("Diagnostic"), "info"))
        state = metric_state(metric)
        if state == MetricState.OK.value:
            rubric_text, rubric_kind = rubric_chip(metric)
            chips.append((rubric_text, rubric_kind))
        else:
            chips.append((metric_state_text(metric), state))
        side_label = SIDE_LABELS.get(metric.side)
        if side_label:
            chips.append((t(side_label), "info"))
        add_chip_rows(card.body(), chips, per_row=3)

        if metric_has_ring(metric):
            pie = ScorePieChart()
            pie.set_score(
                metric.score,
                metric_value_text(metric),
                ring_color=score_purple(metric.score),
            )
            card.body().addWidget(pie, alignment=Qt.AlignmentFlag.AlignHCenter)
        else:
            lines = [metric_state_text(metric)]
            if metric.reason:
                lines.append(f"{t('Reason')}: {metric.reason}")
            add_text_stack(card.body(), lines, object_name="reportAdvice")

        detail: list[str] = []
        if metric_has_ring(metric):
            detail.append(f"{t('Measured')}: {metric_value_text(metric)}")
        if metric.faulty_turns is not None and metric.total_turns:
            detail.append(
                faulty_turn_sentence(
                    metric.name or pretty_ref_id(metric.id),
                    int(metric.faulty_turns),
                    int(metric.total_turns),
                )
            )
        if metric.left_value is not None and metric.right_value is not None:
            detail.append(
                t("Left {left} · right {right}",
                  left=_fmt_number(float(metric.left_value)),
                  right=_fmt_number(float(metric.right_value)))
            )
        if metric.standard:
            detail.append(f"{t('Standard')}: {metric.standard}")
        if metric.reliability:
            detail.append(
                t("Reliability {pct:.0f}%", pct=float(metric.reliability) * 100.0)
            )
        add_text_stack(card.body(), detail, object_name="reportMeta")
        if metric.evidence_ms is not None:
            card.body().addWidget(
                self._frame_link(metric.evidence_ms),
                alignment=Qt.AlignmentFlag.AlignLeft,
            )
        return card

    # --- chapter 4: turn-by-turn ----------------------------------------

    def _fill_turns(self, report: StageReport) -> bool:
        turns = report.turns
        if turns is None:
            return False
        grid = self._chapters["turns"].grid()
        summary = ReportCard()
        lines = [
            t("{n} turns · {left} left / {right} right",
              n=turns.count,
              left=turns.left_count,
              right=turns.right_count)
        ]
        if turns.mean_duration_s is not None:
            lines.append(
                t("Mean turn {sec:.2f}s", sec=float(turns.mean_duration_s))
            )
        if turns.duration_cv is not None:
            lines.append(
                t("Rhythm variation {cv:.0f}%", cv=float(turns.duration_cv) * 100.0)
            )
        if not turns.turns and not turns.count:
            lines.append(t("No turns were segmented in this clip."))
        add_text_stack(summary.body(), lines, object_name="reportAdvice")
        grid.add(summary, per_row=1)

        strip_card = ReportCard()
        add_text_stack(
            strip_card.body(),
            [
                t("One cell per turn along the clip. Flagged turns are highlighted; click a turn to jump to it.")
            ],
            object_name="reportMeta",
        )
        _detach(self._turn_strip)
        self._turn_strip = TurnStripChart()
        if self._seek_enabled:
            self._turn_strip.seekRequested.connect(self.seekRequested.emit)
        else:
            self._turn_strip.setToolTip(
                t("Open the report on the player page to jump to this frame.")
            )
        self._turn_strip.set_turns(turns.turns)
        strip_card.body().addWidget(self._turn_strip)
        grid.add(strip_card, per_row=1)

        callouts = [
            faulty_turn_sentence(
                fault_label(fault_id, report.metrics), int(count), int(turns.count)
            )
            for fault_id, count in sorted(turns.fault_counts.items())
            if count and turns.count
        ]
        if callouts:
            card = ReportCard()
            add_text_stack(card.body(), callouts, object_name="reportAdvice")
            grid.add(card, per_row=1)
        return True

    # --- chapter 5: checkpoints -----------------------------------------

    def _fill_checkpoints(self, report: StageReport) -> bool:
        grid = self._chapters["checkpoints"].grid()
        head = ReportCard()
        lines = [
            t("Passed this level. Choose a next level on the skill tree.")
            if report.ready_for_next_stage
            else t("Not passed — train the lowest-scoring checkpoint.")
        ]
        weak = next(
            (k for k in report.keypoints if k.id == report.weakest_checkpoint_id),
            None,
        )
        if weak is not None:
            lines.append(f"{t('Weakest checkpoint')}: {weak.name or weak.id}")
        add_text_stack(head.body(), lines, object_name="reportAdvice")
        grid.add(head, per_row=1)

        per_row = 3 if len(report.keypoints) >= 5 else 2
        for item in _sorted_keypoints(report.keypoints):
            grid.add(self._checkpoint_card(item), per_row=per_row)
        return True

    def _checkpoint_card(self, item: KeypointResult) -> ReportCard:
        card = ReportCard()
        pie = ScorePieChart()
        pie.set_score(
            item.score,
            item.name or item.id,
            ring_color=score_purple(item.score),
        )
        card.body().addWidget(pie, alignment=Qt.AlignmentFlag.AlignHCenter)
        status = str(_enum_value(item.status))
        chips: list[tuple[str, str]] = []
        if status == KeypointStatus.PASS.value:
            chips.append((t("Pass"), "pass"))
        elif status == KeypointStatus.FAIL.value:
            chips.append((t("Not yet"), "not_yet"))
        else:
            chips.append((t("Not measured"), "unknown"))
        add_chip_rows(card.body(), chips, per_row=3)
        detail = [item.good if status == KeypointStatus.PASS.value else item.bad]
        if item.faulty_turns is not None and item.total_turns:
            detail.append(
                t("{n} of {total} turns carried this fault",
                  n=int(item.faulty_turns),
                  total=int(item.total_turns))
            )
        if item.allowance is not None:
            detail.append(t("The allowance is {n}", n=int(item.allowance)))
        add_text_stack(card.body(), detail, object_name="reportAdvice")
        add_text_stack(card.body(), self._drill_lines(item.drills), object_name="reportMeta")
        if item.evidence_ms is not None:
            card.body().addWidget(
                self._frame_link(item.evidence_ms),
                alignment=Qt.AlignmentFlag.AlignLeft,
            )
        return card

    # --- chapter 6: skill tree ------------------------------------------

    def _fill_skill_tree(self, report: StageReport) -> bool:
        grid = self._chapters["skill_tree"].grid()
        card = ReportCard()

        # Dynamically build the tree from all of this athlete's stored reports
        # so the skill tree always reflects the latest state across all clips.
        all_reports = list_reports_for_athlete(self._athlete_key)
        if all_reports:
            try:
                from core.i18n import language as current_language

                cur = load_curriculum()
                history = StageHistory.from_reports(all_reports)
                clip_id_map = history.clip_id_map()

                def _name_for(lid: str) -> str:
                    spec = cur.levels.get(lid)
                    if spec is None:
                        return lid
                    name_obj = spec.name
                    lang = current_language()
                    if hasattr(name_obj, lang):
                        return str(getattr(name_obj, lang) or lid)
                    if hasattr(name_obj, "en"):
                        return str(getattr(name_obj, "en") or lid)
                    return lid

                nodes = build_tree(
                    cur,
                    report.stage_id,
                    history=history,
                    lang=current_language(),
                    name_for=_name_for,
                )
                view = SkillTreeView()
                view.set_nodes(nodes, clip_id_map=clip_id_map)
                view.nodeClicked.connect(self.nodeClicked)
                card.body().addWidget(view)
            except Exception:
                # Fall back to the stored tree on any curriculum / i18n error
                if report.tree:
                    view = SkillTreeView()
                    view.set_nodes(report.tree)
                    view.nodeClicked.connect(self.nodeClicked)
                    card.body().addWidget(view)
                else:
                    route = SkillTreeRoute()
                    route.set_route(report.tree_path)
                    card.body().addWidget(route)
        elif report.tree:
            view = SkillTreeView()
            view.set_nodes(report.tree)
            view.nodeClicked.connect(self.nodeClicked)
            card.body().addWidget(view)
        else:
            route = SkillTreeRoute()
            route.set_route(report.tree_path)
            card.body().addWidget(route)

        if report.next_level_names:
            extra = QLabel(
                t("Next stage: {names}", names=" · ".join(report.next_level_names))
            )
            extra.setObjectName("reportMeta")
            extra.setWordWrap(True)
            card.body().addWidget(extra)
        grid.add(card, per_row=1)
        for plan in report.next_plans:
            grid.add(self._plan_card(plan), per_row=1)
        return True

    # --- chapter 7: stage tutorial --------------------------------------

    def _fill_tutorial(self, report: StageReport) -> bool:
        pack = self._knowledge
        if pack is None or not pack.has_tutorial():
            return False
        grid = self._chapters["tutorial"].grid()
        head = ReportCard()
        lines: list[str] = []
        if pack.goal:
            lines.append(f"{t('Goal')}: {pack.goal}")
        if pack.why_it_matters:
            lines.append(f"{t('Why it matters')}: {pack.why_it_matters}")
        if pack.core_question:
            lines.append(f"{t('The question to answer')}: {pack.core_question}")
        add_text_stack(head.body(), lines, object_name="reportAdvice")
        grid.add(head, per_row=1)

        focus = report.knowledge_focus
        skills = order_by_ids(pack.skills, focus.skill_ids if focus else [])
        for skill in skills:
            card = ReportCard()
            add_text_stack(
                card.body(),
                [str(skill.get("name") or pretty_ref_id(str(skill.get("id") or "")))],
                object_name="reportAdvice",
            )
            body: list[str] = []
            if skill.get("description"):
                body.append(str(skill["description"]))
            if skill.get("why"):
                body.append(f"{t('Why')}: {skill['why']}")
            for cue in (skill.get("cues") or [])[:2]:
                body.append(f"{t('Cue')}: {cue}")
            for wrong in skill.get("misconceptions") or []:
                body.append(f"{t('Common misconception')}: {wrong}")
            add_text_stack(card.body(), body, object_name="reportMeta")
            grid.add(card, per_row=2)
        return True

    # --- chapter 8: drills ----------------------------------------------

    def _fill_drills(self, report: StageReport) -> bool:
        pack = self._knowledge
        if pack is None or not pack.has_drills():
            return False
        grid = self._chapters["drills"].grid()
        focus = report.knowledge_focus
        if focus is not None and focus.weakest_metric_name:
            head = ReportCard()
            add_text_stack(
                head.body(),
                [
                    t("Ordered for your weakest metric first: {metric}",
                      metric=focus.weakest_metric_name)
                ],
                object_name="reportAdvice",
            )
            grid.add(head, per_row=1)
        drills = order_by_ids(pack.drills, focus.drill_ids if focus else [])
        for drill in drills:
            grid.add(self._pack_drill_card(drill, pack), per_row=2)
        return True

    def _pack_drill_card(self, drill: dict, pack: StageKnowledge) -> ReportCard:
        card = ReportCard()
        add_text_stack(
            card.body(),
            [str(drill.get("name") or pretty_ref_id(str(drill.get("id") or "")))],
            object_name="reportAdvice",
        )
        lines: list[str] = []
        if drill.get("purpose"):
            lines.append(f"{t('Purpose')}: {drill['purpose']}")
        if drill.get("setup"):
            lines.append(f"{t('Setup')}: {drill['setup']}")
        for step in drill.get("steps") or []:
            lines.append(f"• {step}")
        dose = _dose_text(drill.get("dose"))
        if dose:
            lines.append(f"{t('Dose')}: {dose}")
        if drill.get("success_indicator"):
            lines.append(f"{t('You have it when')}: {drill['success_indicator']}")
        terrain = [pretty_ref_id(ref) for ref in drill.get("terrain") or []]
        if terrain:
            lines.append(f"{t('Terrain')}: {' · '.join(terrain)}")
        add_text_stack(card.body(), lines, object_name="reportMeta")
        return card

    # --- chapter 9: faults and fixes ------------------------------------

    def _fill_faults(self, report: StageReport) -> bool:
        pack = self._knowledge
        if pack is None or not pack.has_faults():
            return False
        grid = self._chapters["faults"].grid()
        focus = report.knowledge_focus
        faults = order_by_ids(pack.faults, focus.fault_ids if focus else [])
        for fault in faults:
            card = ReportCard()
            add_text_stack(
                card.body(),
                [str(fault.get("name") or pretty_ref_id(str(fault.get("id") or "")))],
                object_name="reportAdvice",
            )
            if str(fault.get("risk") or "") == "injury-risk":
                add_chip_rows(
                    card.body(), [(t("Injury risk"), "blocker")], per_row=3
                )
            lines: list[str] = []
            if fault.get("symptom"):
                lines.append(f"{t('Symptom')}: {fault['symptom']}")
            if fault.get("looks_like"):
                lines.append(f"{t('Looks like')}: {fault['looks_like']}")
            for cause in fault.get("root_causes") or []:
                lines.append(f"{t('Likely cause')}: {cause}")
            if fault.get("diagnosis_test"):
                lines.append(f"{t('Test it')}: {fault['diagnosis_test']}")
            fix = fault.get("fix") if isinstance(fault.get("fix"), dict) else {}
            for cue in fix.get("cues") or []:
                lines.append(f"{t('Fix cue')}: {cue}")
            drills = [pretty_ref_id(ref) for ref in fix.get("drills") or []]
            if drills:
                lines.append(f"{t('Drills')}: {' · '.join(drills)}")
            add_text_stack(card.body(), lines, object_name="reportMeta")
            grid.add(card, per_row=2)
        return True

    # --- chapter 10: terrain and venue ----------------------------------

    def _fill_terrain(self, report: StageReport) -> bool:  # noqa: ARG002
        pack = self._knowledge
        if pack is None or not pack.has_terrain():
            return False
        grid = self._chapters["terrain"].grid()
        terrain = pack.terrain or {}
        card = ReportCard()
        lines: list[str] = []
        if terrain.get("ideal_description"):
            lines.append(f"{t('Ideal terrain')}: {terrain['ideal_description']}")
        required = [pretty_ref_id(ref) for ref in terrain.get("required") or []]
        if required:
            lines.append(f"{t('Terrain needed')}: {' · '.join(required)}")
        best = [pack.snow_label(ref) for ref in terrain.get("conditions_best") or []]
        if best:
            lines.append(f"{t('Best conditions')}: {' · '.join(best)}")
        bad = [pack.snow_label(ref) for ref in terrain.get("conditions_avoid") or []]
        if bad:
            lines.append(f"{t('Conditions to avoid')}: {' · '.join(bad)}")
        for avoid in terrain.get("avoid") or []:
            lines.append(f"{t('Avoid')}: {avoid}")
        add_text_stack(card.body(), lines, object_name="reportMeta")
        if lines:
            grid.add(card, per_row=1)

        if pack.tactics or pack.safety_notes:
            notes = ReportCard()
            add_text_stack(
                notes.body(),
                [f"{t('Tactic')}: {x}" for x in pack.tactics]
                + [f"{t('Safety')}: {x}" for x in pack.safety_notes],
                object_name="reportMeta",
            )
            grid.add(notes, per_row=1)

        self._add_sections(grid, pack.terrain_sections)
        self._add_sections(grid, pack.snow_sections)
        return True

    # --- chapter 11: equipment ------------------------------------------

    def _fill_equipment(self, report: StageReport) -> bool:
        pack = self._knowledge
        profile_lines = profile_equipment_lines(
            report.profile_summary, pack.kb_stage if pack else report.kb_stage
        )
        if (pack is None or not pack.has_equipment()) and not profile_lines:
            return False
        grid = self._chapters["equipment"].grid()
        if profile_lines:
            card = ReportCard()
            add_text_stack(card.body(), profile_lines, object_name="reportAdvice")
            profile = report.profile_summary
            if profile is not None and profile.effects:
                add_text_stack(card.body(), profile.effects, object_name="reportMeta")
            grid.add(card, per_row=1)
        if pack is not None:
            self._add_sections(grid, pack.equipment_sections)
        return True

    # --- chapter 12: filming and disclaimer -----------------------------

    def _fill_filming(self, report: StageReport) -> bool:
        grid = self._chapters["filming"].grid()
        if report.filming:
            for issue in report.filming:
                card = ReportCard()
                label = SEVERITY_LABELS.get(issue.severity, "Note")
                add_chip_rows(
                    card.body(), [(t(label), issue.severity)], per_row=3
                )
                add_text_stack(
                    card.body(),
                    [issue.message or pretty_ref_id(issue.code)],
                    object_name="reportAdvice",
                )
                grid.add(card, per_row=2)
        elif report.film_steps:
            card = ReportCard()
            add_text_stack(
                card.body(),
                [t("Filming checklist for the next clip")]
                + [f"• {step}" for step in report.film_steps],
                object_name="reportAdvice",
            )
            grid.add(card, per_row=1)

        card = ReportCard()
        lines = [report.disclaimer]
        if report.heuristic_not_fis_carve:
            lines.append(t("Carve points are heuristics, not FIS carving scores."))
        add_text_stack(card.body(), lines, object_name="reportDisclaimer")
        grid.add(card, per_row=1)
        return True

    # --- shared helpers -------------------------------------------------

    def _add_sections(self, grid: ReportGrid, sections: list[dict]) -> None:
        for section in sections[:MAX_SECTIONS]:
            grid.add(self._section_card(section), per_row=1)
        rest = [
            str(section.get("heading") or "")
            for section in sections[MAX_SECTIONS:]
            if section.get("heading")
        ]
        if rest:
            card = ReportCard()
            add_text_stack(
                card.body(),
                [t("Also in this module")] + [f"• {x}" for x in rest],
                object_name="reportMeta",
            )
            grid.add(card, per_row=1)

    def _section_card(self, section: dict) -> ReportCard:
        card = ReportCard()
        heading = str(section.get("heading") or "")
        if heading:
            add_text_stack(card.body(), [heading], object_name="reportAdvice")
        add_text_stack(
            card.body(),
            [str(p) for p in section.get("body") or []],
            object_name="reportMeta",
        )
        rules = [f"{t('Hard rule')}: {x}" for x in section.get("hard_rules") or []]
        add_text_stack(card.body(), rules, object_name="reportAdvice")
        checklist = [f"• {x}" for x in section.get("checklist") or []]
        add_text_stack(card.body(), checklist, object_name="reportMeta")
        notes = [
            f"{t('For your profile')}: {x}"
            for x in section.get("adaptation_notes") or []
        ]
        add_text_stack(card.body(), notes, object_name="reportMeta")
        for table in section.get("tables") or []:
            add_text_stack(
                card.body(), _table_lines(table), object_name="reportMeta"
            )
        return card

    def _frame_link(self, t_ms: float) -> FrameSeekLink:
        link = FrameSeekLink(format_evidence_ms(t_ms))
        self._wire_link(link, int(t_ms))
        return link

    def _wire_link(self, link: FrameSeekLink, t_ms: int) -> None:
        if self._seek_enabled:
            link.clicked.connect(lambda *, ms=t_ms: self.seekRequested.emit(ms))
            link.doubleClicked.connect(lambda *, ms=t_ms: self.seekAndPlayRequested.emit(ms))
        else:
            link.setToolTip(t("Open the report on the player page to jump to this frame."))

    def _plan_card(self, plan: dict) -> ReportCard:
        card = ReportCard()
        level_id = str(plan.get("level_id") or "")
        # ``next_plans`` is an untyped list[dict]: a null value would otherwise
        # render as the literal string "None".
        level_name = str(plan.get("level_name") or "")
        if level_name:
            card.body().addWidget(
                IconTextRow(
                    [("trophy", level_medal_color(level_id))],
                    level_name,
                    object_name="reportAdvice",
                )
            )
        lines = self._drill_lines(plan.get("drills") or [])
        for venue in plan.get("venues") or []:
            lines.append(f"{t('Training venue')}: {venue.get('name', '')}")
            if venue.get("desc"):
                lines.append(str(venue["desc"]))
            if venue.get("tips"):
                lines.append(str(venue["tips"]))
        add_text_stack(card.body(), lines, object_name="reportAdvice")
        return card

    def _drill_lines(self, drills: list[dict]) -> list[str]:
        lines: list[str] = []
        for drill in drills:
            lines.append(f"{t('Drills')}: {drill.get('title', '')}")
            if drill.get("desc"):
                lines.append(str(drill["desc"]))
            for step in drill.get("training") or drill.get("steps") or []:
                lines.append(f"• {step}")
            for venue in drill.get("venues") or []:
                lines.append(f"{t('Training venue')}: {venue.get('name', '')}")
                if venue.get("tips"):
                    lines.append(str(venue["tips"]))
        return lines


def _dose_text(dose: object) -> str:
    """Pack dose dict → one line: "3 sets · 5 reps · each side"."""
    if not isinstance(dose, dict):
        return ""
    parts: list[str] = []
    for key, label in (
        ("sets", "{n} sets"),
        ("reps", "{n} reps"),
        ("runs", "{n} runs"),
        ("sessions", "{n} sessions"),
        ("duration_min", "{n} min"),
    ):
        value = dose.get(key)
        if isinstance(value, (int, float)) and value:
            parts.append(t(label, n=_fmt_number(float(value))))
    if dose.get("per_side"):
        parts.append(t("each side"))
    if dose.get("notes"):
        parts.append(str(dose["notes"]))
    return " · ".join(parts)


def _table_lines(table: object) -> list[str]:
    """Render a pack table as paragraphs; the panel has no table widget."""
    if not isinstance(table, dict):
        return []
    lines: list[str] = []
    caption = str(table.get("caption") or "")
    if caption:
        lines.append(caption)
    columns = [str(c) for c in table.get("columns") or []]
    if columns:
        lines.append(" · ".join(columns))
    rows = [r for r in table.get("rows") or [] if isinstance(r, list)]
    for row in rows[:MAX_TABLE_ROWS]:
        lines.append(" · ".join(str(cell) for cell in row))
    if len(rows) > MAX_TABLE_ROWS:
        lines.append(
            t("{n} more rows in the full module", n=len(rows) - MAX_TABLE_ROWS)
        )
    return lines
