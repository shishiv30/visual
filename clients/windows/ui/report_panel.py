"""Five-chapter ski stage report with card grid layout."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.ui.report_charts import ScorePieChart, ScoreTimelineChart
from clients.windows.ui.report_layout import (
    FrameSeekLink,
    IconTextRow,
    ReportCard,
    ReportChapter,
    SkillTreeRoute,
    add_text_stack,
)
from clients.windows.ui.theme import (
    SPACE_CHAPTER,
    level_medal_color,
    score_purple,
    terrain_diamond_colors,
)
from core.i18n import t
from schemas.stage_report import KeypointResult, KeypointStatus, StageReport


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


def _score_card(pie: ScorePieChart) -> ReportCard:
    card = ReportCard()
    card.body().addWidget(pie)
    return card


class StageReportPanel(QWidget):
    seekRequested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("stageReportPanel")
        self._report: StageReport | None = None
        self._seek_enabled = True
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._empty = QLabel()
        self._empty.setObjectName("reportEmpty")
        self._empty.setWordWrap(True)

        self._ch1 = ReportChapter()
        self._ch2 = ReportChapter()
        self._ch3 = ReportChapter()
        self._ch4 = ReportChapter()
        self._ch5 = ReportChapter()
        self._ch1_grid = self._ch1.grid()
        self._ch2_grid = self._ch2.grid()
        self._ch3_grid = self._ch3.grid()
        self._ch4_grid = self._ch4.grid()
        self._ch5_grid = self._ch5.grid()

        self._gauge = ScorePieChart()
        self._timeline = ScoreTimelineChart()
        self._timeline.seekRequested.connect(self.seekRequested.emit)

        inner = QWidget()
        body = QVBoxLayout(inner)
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(SPACE_CHAPTER)
        body.addWidget(self._empty)
        body.addWidget(self._ch1)
        body.addWidget(self._ch2)
        body.addWidget(self._ch3)
        body.addWidget(self._ch4)
        body.addWidget(self._ch5)
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

    def set_seek_enabled(self, enabled: bool) -> None:
        self._seek_enabled = enabled

    def set_scroll_max_height(self, height: int | None) -> None:
        if height is None:
            self._scroll.setMaximumHeight(16777215)
        else:
            self._scroll.setMaximumHeight(height)

    def retranslate(self) -> None:
        self._empty.setText(t("No stage report yet. Analyze a clip offline first."))
        self._ch1.set_title(t("Summary"))
        self._ch2.set_title(t("Checkpoints"))
        self._ch3.set_title(t("Next steps"))
        self._ch4.set_title(t("Skill tree"))
        self._ch5.set_title(t("Filming and scoring"))
        self.set_report(self._report)

    def set_report(self, report: StageReport | None) -> None:
        self._report = report
        has = report is not None
        self._empty.setVisible(not has)
        for box in (self._ch1, self._ch2, self._ch3, self._ch4, self._ch5):
            box.setVisible(has)
        self._ch1_grid.clear()
        self._ch2_grid.clear()
        self._ch3_grid.clear()
        self._ch4_grid.clear()
        self._ch5_grid.clear()
        if report is None:
            return
        self._fill_ch1(report)
        self._fill_ch2(report)
        self._fill_ch3(report)
        self._fill_ch4(report)
        self._fill_ch5(report)

    def _fill_ch1(self, report: StageReport) -> None:
        overview = ReportCard()
        overview.body().addWidget(
            IconTextRow(
                [("trophy", level_medal_color(report.stage_id))],
                report.stage_name,
                object_name="reportMeta",
            )
        )
        if report.stage_focus:
            focus = QLabel(report.stage_focus)
            focus.setObjectName("reportMeta")
            focus.setWordWrap(True)
            overview.body().addWidget(focus)
        self._ch1_grid.add(overview, per_row=1)

        terrain = ReportCard()
        gate = t("Passed this level. Choose a next level on the skill tree.") if report.ready_for_next_stage else t("Not passed — train the lowest-scoring checkpoint.")
        trail = report.terrain_name or t("—")
        terrain_line = f"{t('Suggested trail rating')}: {trail} · {gate}"
        diamonds = [("diamond", c) for c in terrain_diamond_colors(report.terrain_id)]
        terrain.body().addWidget(
            IconTextRow(diamonds, terrain_line, object_name="reportAdvice")
        )
        if report.terrain_desc:
            desc = QLabel(report.terrain_desc)
            desc.setObjectName("reportMeta")
            desc.setWordWrap(True)
            terrain.body().addWidget(desc)
        self._ch1_grid.add(terrain, per_row=1)

        self._gauge.setParent(None)
        self._gauge = ScorePieChart()
        self._gauge.set_score(
            report.score_0_100,
            t("Heuristic score (0-100, not FIS)"),
            ring_color=score_purple(report.score_0_100),
        )
        self._ch1_grid.add(_score_card(self._gauge), per_row=2)

        conf_score = report.confidence * 100.0
        confidence = ScorePieChart()
        confidence.set_score(
            conf_score,
            t("Confidence"),
            ring_color=score_purple(conf_score),
        )
        self._ch1_grid.add(_score_card(confidence), per_row=2)

        if report.posture is not None:
            note = ReportCard()
            add_text_stack(
                note.body(),
                [t("Four posture scores are coach heuristics (0–100), not lab biomechanics; they are not true speed, meter turn radius, or peak ski pressure.")],
                object_name="reportMeta",
            )
            self._ch1_grid.add(note, per_row=1)
            for key, label_key in (
                ("stability", "Stability"),
                ("coordination", "Coordination"),
                ("control", "Control"),
                ("balance", "Balance"),
            ):
                value = float(getattr(report.posture, key))
                pie = ScorePieChart()
                pie.set_score(value, t(label_key), ring_color=score_purple(value))
                self._ch1_grid.add(_score_card(pie), per_row=2)

        per_row = 3 if len(report.keypoints) >= 5 else 2
        for item in _sorted_keypoints(report.keypoints):
            pie = ScorePieChart()
            pie.set_score(
                item.score,
                item.name or item.id,
                ring_color=score_purple(item.score),
            )
            self._ch1_grid.add(_score_card(pie), per_row=per_row)

        timeline_card = ReportCard()
        caption = QLabel(t("Stability over time (time × frame score)"))
        caption.setObjectName("reportMeta")
        caption.setWordWrap(True)
        timeline_card.body().addWidget(caption)
        self._timeline.setParent(None)
        self._timeline = ScoreTimelineChart()
        self._timeline.seekRequested.connect(self.seekRequested.emit)
        self._timeline.set_points(report.score_series)
        timeline_card.body().addWidget(self._timeline)
        self._ch1_grid.add(timeline_card, per_row=1)
        self._ch1_grid.finish()

    def _fill_ch2(self, report: StageReport) -> None:
        per_row = 3 if len(report.keypoints) >= 5 else 2
        for item in _sorted_keypoints(report.keypoints):
            card = ReportCard()
            pie = ScorePieChart()
            pie.set_score(
                item.score,
                item.name or item.id,
                ring_color=score_purple(item.score),
            )
            card.body().addWidget(pie, alignment=Qt.AlignmentFlag.AlignHCenter)
            detail = item.good if item.status == KeypointStatus.PASS else item.bad
            add_text_stack(card.body(), [detail], object_name="reportAdvice")
            if item.evidence_ms is not None:
                card.body().addWidget(
                    self._frame_link(item.evidence_ms),
                    alignment=Qt.AlignmentFlag.AlignLeft,
                )
            self._ch2_grid.add(card, per_row=per_row)
        self._ch2_grid.finish()

    def _fill_ch3(self, report: StageReport) -> None:
        if report.ready_for_next_stage:
            ready = ReportCard()
            add_text_stack(ready.body(), [t("Passed this level. Choose a next level on the skill tree.")], object_name="reportAdvice")
            self._ch3_grid.add(ready, per_row=1)
            for plan in report.next_plans:
                self._ch3_grid.add(self._plan_card(plan), per_row=1)
            self._ch3_grid.finish()
            return

        summary = ReportCard()
        lines = [t("Not passed — train the lowest-scoring checkpoint.")]
        weak = next(
            (k for k in report.keypoints if k.id == report.weakest_checkpoint_id),
            None,
        )
        if weak is not None:
            lines.append(f"{t('Weakest checkpoint')}: {weak.name}")
            lines.append(weak.bad)
        add_text_stack(summary.body(), lines, object_name="reportAdvice")
        self._ch3_grid.add(summary, per_row=1)

        if weak is not None and weak.evidence_ms is not None:
            link_card = ReportCard()
            link = FrameSeekLink(
                f"{t('Problem frame')} {format_evidence_ms(weak.evidence_ms)}"
            )
            self._wire_link(link, int(weak.evidence_ms))
            link_card.body().addWidget(link)
            self._ch3_grid.add(link_card, per_row=1)

        if weak is not None:
            self._ch3_grid.add(self._drills_card(weak.drills, weak.name), per_row=1)

        fail_items = [
            item
            for item in _sorted_keypoints(report.keypoints)
            if item.status == KeypointStatus.FAIL
            and (weak is None or item.id != weak.id)
        ]
        per_row = 2 if len(fail_items) <= 4 else 1
        for item in fail_items:
            self._ch3_grid.add(
                self._drills_card(item.drills, item.name),
                per_row=per_row,
            )
        self._ch3_grid.finish()

    def _fill_ch4(self, report: StageReport) -> None:
        card = ReportCard()
        route = SkillTreeRoute()
        route.set_route(report.tree_path)
        card.body().addWidget(route)
        if report.ready_for_next_stage and report.next_level_names:
            extra = QLabel(t("Next stage") + ": " + " · ".join(report.next_level_names))
            extra.setObjectName("reportMeta")
            extra.setWordWrap(True)
            card.body().addWidget(extra)
        self._ch4_grid.add(card, per_row=1)
        self._ch4_grid.finish()

    def _fill_ch5(self, report: StageReport) -> None:
        film_lines = [report.disclaimer]
        if report.heuristic_not_fis_carve:
            film_lines.append(t("Carve points are heuristics, not FIS carving scores."))
        film_lines.extend(f"• {step}" for step in report.film_steps)
        card = ReportCard()
        add_text_stack(card.body(), film_lines, object_name="reportDisclaimer")
        self._ch5_grid.add(card, per_row=1)
        self._ch5_grid.finish()

    def _frame_link(self, t_ms: float) -> FrameSeekLink:
        link = FrameSeekLink(format_evidence_ms(t_ms))
        self._wire_link(link, int(t_ms))
        return link

    def _wire_link(self, link: FrameSeekLink, t_ms: int) -> None:
        if self._seek_enabled:
            link.clicked.connect(lambda *, ms=t_ms: self.seekRequested.emit(ms))
        else:
            link.setToolTip(t("Open the report on the player page to jump to this frame."))

    def _plan_card(self, plan: dict) -> ReportCard:
        card = ReportCard()
        level_id = str(plan.get("level_id") or "")
        level_name = str(plan.get("level_name", ""))
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

    def _drills_card(self, drills: list[dict], title: str = "") -> ReportCard:
        card = ReportCard()
        lines = [title] if title else []
        lines.extend(self._drill_lines(drills))
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
