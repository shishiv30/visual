"""Reviewer: twelve-chapter report layout and zh/en completeness.

The chapter numbering follows design §7: 1 summary, 2 why this stage,
3 core metrics, 4 turn-by-turn, 5 checkpoints, 6 skill tree, 7-11 the knowledge
chapters (rendered client-side from the pack, so only the *reference* and the
*selection* are audited here), 12 filming and disclaimer.

The bilingual audit checks the structure of the new blocks rather than their
copy: the v3 display keys live in ``locales/_v3_keys.assess.json`` awaiting the
translator review, not in ``locales/strings.json``, so ``t()`` still returns
English for them and a CJK assertion on a metric name would fail by design.
Stage names, terrain names, drills and film steps come from the curriculum and
are checked for CJK exactly as before.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from core.i18n import has_key, t
from core.sports.assess import assess_clip
from core.sports.curriculum import CURRICULUM_PATH, load_curriculum
from core.sports.knowledge_pack import load_pack
from core.sports.history import StageHistory
from core.sports.report_cases import CASES, ReportCase, clip_for, history_for
from schemas.stage_report import (
    KeypointStatus,
    MetricState,
    NodeState,
    Rubric,
    StageReport,
)

CJK = ("一", "鿿")
KNOWN_TERRAIN = {
    "green",
    "blue",
    "red",
    "black",
    "park",
    "mogul",
    "offpiste",
    "any",
}
KNOWN_TIERS = {"full", "scene", "catalog"}


def _has_cjk(text: str) -> bool:
    return any(CJK[0] <= ch <= CJK[1] for ch in text)


def audit_layout(
    report: StageReport, *, expect_stages: tuple[str, ...] | None = None
) -> list[str]:
    issues: list[str] = []
    issues += _audit_ch1_summary(report, expect_stages)
    issues += _audit_ch2_classification(report)
    issues += _audit_ch3_metrics(report)
    issues += _audit_ch4_turns(report)
    issues += _audit_ch5_checkpoints(report)
    issues += _audit_ch6_tree(report)
    issues += _audit_ch7_knowledge(report)
    issues += _audit_ch12_filming(report)
    issues += _audit_next_steps(report)
    return issues


def _audit_ch1_summary(
    report: StageReport, expect_stages: tuple[str, ...] | None
) -> list[str]:
    issues: list[str] = []
    if expect_stages is not None and report.stage_id not in expect_stages:
        issues.append(f"ch1 stage {report.stage_id} not in {expect_stages}")
    if not report.stage_name.strip():
        issues.append("ch1 missing stage_name")
    if not 0 <= report.score_0_100 <= 100:
        issues.append("ch1 score out of range")
    if not 0.0 <= report.confidence <= 1.0:
        issues.append("ch1 confidence out of range")
    if report.posture is not None:
        for name in ("stability", "coordination", "control", "balance"):
            value = getattr(report.posture, name)
            if not 0 <= value <= 100:
                issues.append(f"ch1 posture {name} out of range")
    if report.tier not in KNOWN_TIERS:
        issues.append(f"ch1 tier {report.tier!r}")
    if report.stage_id != "unknown":
        if report.terrain_id not in KNOWN_TERRAIN:
            issues.append(f"ch1 terrain {report.terrain_id!r}")
        if not report.terrain_name.strip():
            issues.append("ch1 missing terrain_name")
        if not report.stage_focus.strip():
            issues.append("ch1 missing stage_focus")
        if not report.kb_stage:
            issues.append("ch1 missing kb_stage bridge")
    return issues


def _audit_ch2_classification(report: StageReport) -> list[str]:
    issues: list[str] = []
    block = report.classification
    if block is None:
        issues.append("ch2 missing classification")
        return issues
    if report.stage_id == "unknown":
        if block.method != "unusable":
            issues.append("ch2 unknown stage without unusable method")
        if not block.unusable_reason:
            issues.append("ch2 unusable without a reason")
        return issues
    if block.chosen_id != report.stage_id:
        issues.append("ch2 chosen_id != stage_id")
    if abs(block.confidence - report.confidence) > 1e-6:
        issues.append("ch2 confidence disagrees with ch1")
    if not block.candidates:
        issues.append("ch2 no candidates")
    if not 0.0 <= block.quality_factor <= 1.0:
        issues.append("ch2 quality_factor out of range")
    for candidate in block.candidates[1:]:
        if candidate.rejected_reason:
            continue
        if not candidate.separating_metric_id:
            issues.append(f"ch2 {candidate.stage_id} has no separating metric")
    if block.ambiguous and len(block.candidates) < 2:
        issues.append("ch2 ambiguous but only one candidate offered")
    return issues


def _audit_ch3_metrics(report: StageReport) -> list[str]:
    issues: list[str] = []
    if report.stage_id == "unknown":
        # The unusable path asserts no stage, so there is no ordered core-metric
        # set and chapter 3 is empty by construction (``assess._unusable_report``
        # docstring). Returning unconditionally here is what let the docstring
        # and the code disagree unnoticed, so the contract is asserted instead:
        # no rows, and the "what could not be measured" story carried by the
        # filming chapter.
        if report.metrics:
            issues.append("ch3 metric rows on an unusable report")
        if not report.filming:
            issues.append("ch3 unusable report with no filming issue")
        return issues
    if not report.metrics:
        issues.append("ch3 no metrics")
    seen: set[str] = set()
    for row in report.metrics:
        if row.id in seen:
            issues.append(f"ch3 duplicate metric {row.id}")
        seen.add(row.id)
        if not row.name.strip():
            issues.append(f"ch3 {row.id} missing name")
        if row.state == MetricState.OK:
            if row.value is None and not row.display:
                issues.append(f"ch3 {row.id} ok with no value")
            if row.score is not None and not 0 <= row.score <= 100:
                issues.append(f"ch3 {row.id} score out of range")
            if not 0.0 <= row.reliability <= 1.0:
                issues.append(f"ch3 {row.id} reliability out of range")
        else:
            # The schema rule: never a number, never a rubric, always a reason.
            if row.score is not None:
                issues.append(f"ch3 {row.id} {row.state.value} but scored")
            if row.rubric != Rubric.NOT_RATED:
                issues.append(f"ch3 {row.id} {row.state.value} but rated")
            if not row.reason.strip():
                issues.append(f"ch3 {row.id} {row.state.value} with no reason")
        if row.form == "C" and row.state == MetricState.OK:
            if row.total_turns is None or row.faulty_turns is None:
                issues.append(f"ch3 {row.id} count form without N of M")
            if not row.standard:
                issues.append(f"ch3 {row.id} count form without a standard")
    if not report.gate_metrics():
        issues.append("ch3 no gate metric rows")
    return issues


def _audit_ch4_turns(report: StageReport) -> list[str]:
    issues: list[str] = []
    turns = report.turns
    if turns is None:
        issues.append("ch4 missing turn summary")
        return issues
    if turns.count != len(turns.turns):
        issues.append("ch4 turn count disagrees with the turn list")
    if turns.left_count + turns.right_count != turns.count:
        issues.append("ch4 left/right counts do not add up")
    for record in turns.turns:
        if record.t_end_ms < record.t_start_ms:
            issues.append(f"ch4 turn {record.index} ends before it starts")
        if record.duration_s <= 0.0:
            issues.append(f"ch4 turn {record.index} has no duration")
    return issues


def _audit_ch5_checkpoints(report: StageReport) -> list[str]:
    issues: list[str] = []
    if not report.keypoints:
        issues.append("ch5 no checkpoints")
    for item in report.keypoints:
        if not item.name.strip():
            issues.append(f"ch5 {item.id} missing name")
        if item.status != KeypointStatus.UNKNOWN and item.evidence_ms is None:
            issues.append(f"ch5 {item.id} missing evidence_ms")
        if item.total_turns is not None and item.faulty_turns is None:
            issues.append(f"ch5 {item.id} has M without N")
    return issues


def _audit_ch6_tree(report: StageReport) -> list[str]:
    issues: list[str] = []
    if not report.tree:
        issues.append("ch6 empty skill tree")
        return issues
    ids = {node.id for node in report.tree}
    for node in report.tree:
        if node.state == NodeState.LOCKED and not node.locked_reason:
            issues.append(f"ch6 {node.id} locked without a reason")
        if node.state == NodeState.NOT_APPLICABLE and not node.locked_reason:
            issues.append(f"ch6 {node.id} not applicable without a reason")
        if not node.name.strip():
            issues.append(f"ch6 {node.id} missing name")
        if node.tier not in KNOWN_TIERS:
            issues.append(f"ch6 {node.id} tier {node.tier!r}")
        for child in node.children:
            if child not in ids:
                issues.append(f"ch6 {node.id} child {child} not in the tree")
    current = [node for node in report.tree if node.state == NodeState.CURRENT]
    if report.stage_id == "unknown":
        if current:
            issues.append("ch6 unknown stage but a node is current")
    else:
        if len(current) != 1 or current[0].id != report.stage_id:
            issues.append("ch6 current node is not stage_id")
        if not report.tree_path:
            issues.append("ch6 empty 2.1.0 tree_path projection")
        else:
            legacy = [node for node in report.tree_path if node.current]
            if len(legacy) != 1 or legacy[0].id != report.stage_id:
                issues.append("ch6 tree_path current node is not stage_id")
    # Branch coverage: the whole progression, not just the spine (§8).
    branches = {node.branch for node in report.tree}
    for branch in ("piste", "moguls", "offpiste"):
        if branch not in branches:
            issues.append(f"ch6 branch {branch} missing from the tree")
    if not any(node.tier == "catalog" for node in report.tree):
        issues.append("ch6 catalog rungs missing from the tree")
    return issues


def _audit_ch7_knowledge(report: StageReport) -> list[str]:
    issues: list[str] = []
    if report.stage_id == "unknown" or load_pack() is None:
        return issues
    ref = report.knowledge_ref
    if ref is None:
        issues.append("ch7 missing knowledge_ref")
    else:
        if not ref.kb_stage:
            issues.append("ch7 knowledge_ref has no kb_stage")
        if ref.kb_stage != report.kb_stage:
            issues.append("ch7 knowledge_ref kb_stage != report kb_stage")
        if not ref.pack_version:
            issues.append("ch7 knowledge_ref has no pack version")
    focus = report.knowledge_focus
    if focus is None:
        issues.append("ch9 missing knowledge_focus")
        return issues
    if not focus.fault_ids:
        issues.append("ch9 no faults selected")
    if not focus.drill_ids:
        issues.append("ch8 no drills selected")
    if len(set(focus.fault_ids)) != len(focus.fault_ids):
        issues.append("ch9 duplicate fault ids")
    if len(set(focus.drill_ids)) != len(focus.drill_ids):
        issues.append("ch8 duplicate drill ids")
    measured = {row.id for row in report.measured_metrics()}
    if measured and not focus.weakest_metric_id:
        issues.append("ch9 metrics measured but no weakest metric named")
    if focus.weakest_metric_id and not focus.weakest_metric_name:
        issues.append("ch9 weakest metric not named for display")
    return issues


def _audit_ch12_filming(report: StageReport) -> list[str]:
    issues: list[str] = []
    if not report.film_steps:
        issues.append("ch12 missing film_steps")
    if not report.disclaimer.strip():
        issues.append("ch12 missing disclaimer")
    for issue in report.filming:
        if not issue.code:
            issues.append("ch12 filming issue without a code")
        if not issue.message.strip():
            issues.append(f"ch12 filming {issue.code} without a message")
    if report.stage_id == "unknown" and not any(
        issue.severity == "blocker" for issue in report.filming
    ):
        issues.append("ch12 unusable clip without a blocker note")
    if report.scene is None:
        issues.append("ch12 missing scene summary")
    if report.profile_summary is None:
        issues.append("ch12 missing profile summary")
    return issues


def _audit_next_steps(report: StageReport) -> list[str]:
    issues: list[str] = []
    if report.ready_for_next_stage:
        if not report.next_plans and report.next_level_ids:
            issues.append("ch6 ready but next_plans empty")
        for plan in report.next_plans:
            if not plan.get("level_name"):
                issues.append("ch6 plan missing level_name")
            drills = plan.get("drills") or []
            if not drills:
                issues.append(f"ch6 {plan.get('level_id')} missing drills")
            for drill in drills:
                if not (drill.get("training") or drill.get("steps")):
                    issues.append(f"ch6 drill {drill.get('id')} missing training")
            if not plan.get("venues"):
                issues.append(f"ch6 {plan.get('level_id')} missing venues")
        if report.weakest_checkpoint_id:
            issues.append("ch6 ready still has weakest_checkpoint_id")
    else:
        if report.next_plans:
            issues.append("ch6 not ready but next_plans set")
        if report.stage_id != "unknown" and not report.weakest_checkpoint_id:
            issues.append("ch6 missing weakest checkpoint")
        weak = next(
            (k for k in report.keypoints if k.id == report.weakest_checkpoint_id),
            None,
        )
        if weak is not None and weak.status == KeypointStatus.FAIL:
            if not weak.drills:
                issues.append("ch6 weakest has no drills")
            else:
                drill = weak.drills[0]
                if not (drill.get("training") or drill.get("steps")):
                    issues.append("ch6 weakest drill missing training")
                if not drill.get("venues"):
                    issues.append("ch6 weakest drill missing venues")
    if not report.training_focus.strip():
        issues.append("ch3 missing training_focus")
    if not report.how_to_advance.strip():
        issues.append("ch6 missing how_to_advance")
    return issues


def audit_bilingual(zh_report: StageReport, en_report: StageReport) -> list[str]:
    issues: list[str] = []
    if zh_report.stage_id != en_report.stage_id:
        issues.append("zh/en stage_id mismatch")
    if zh_report.ready_for_next_stage != en_report.ready_for_next_stage:
        issues.append("zh/en ready mismatch")
    if zh_report.terrain_id != en_report.terrain_id:
        issues.append("zh/en terrain mismatch")
    if zh_report.kb_stage != en_report.kb_stage:
        issues.append("zh/en kb_stage mismatch")
    zh_ids = [k.id for k in zh_report.keypoints]
    en_ids = [k.id for k in en_report.keypoints]
    if zh_ids != en_ids:
        issues.append("zh/en checkpoint ids mismatch")
    if [m.id for m in zh_report.metrics] != [m.id for m in en_report.metrics]:
        issues.append("zh/en metric ids mismatch")
    if [m.state for m in zh_report.metrics] != [
        m.state for m in en_report.metrics
    ]:
        issues.append("zh/en metric states mismatch")
    if [n.id for n in zh_report.tree] != [n.id for n in en_report.tree]:
        issues.append("zh/en tree ids mismatch")
    if [n.state for n in zh_report.tree] != [n.state for n in en_report.tree]:
        issues.append("zh/en tree states mismatch")
    if [f.code for f in zh_report.filming] != [
        f.code for f in en_report.filming
    ]:
        issues.append("zh/en filming codes mismatch")
    zh_focus = zh_report.knowledge_focus
    en_focus = en_report.knowledge_focus
    if (zh_focus is None) != (en_focus is None):
        issues.append("zh/en knowledge_focus presence mismatch")
    elif zh_focus is not None and en_focus is not None:
        if zh_focus.fault_ids != en_focus.fault_ids:
            issues.append("zh/en fault selection mismatch")
        if zh_focus.drill_ids != en_focus.drill_ids:
            issues.append("zh/en drill selection mismatch")
    if zh_report.stage_name == en_report.stage_name and zh_report.stage_id != "unknown":
        issues.append("zh/en stage_name not localized")
    if not _has_cjk(zh_report.stage_name):
        issues.append("zh stage_name has no CJK")
    if _has_cjk(en_report.stage_name):
        issues.append("en stage_name still has CJK")
    if not has_key(en_report.stage_name):
        issues.append(f"strings missing {en_report.stage_name}")
    elif t(en_report.stage_name, lang="zh") != zh_report.stage_name:
        issues.append("zh stage_name != strings catalog")
    if len(zh_report.next_plans) != len(en_report.next_plans):
        issues.append("zh/en next_plans length mismatch")
    if len(zh_report.film_steps) != len(en_report.film_steps):
        issues.append("zh/en film_steps length mismatch")
    for zh_step, en_step in zip(zh_report.film_steps, en_report.film_steps, strict=True):
        if _has_cjk(en_step):
            issues.append("en film_steps still has CJK")
            break
        if zh_step and not _has_cjk(zh_step):
            issues.append("zh film_steps has no CJK")
            break
    return issues


def audit_curriculum_i18n() -> list[str]:
    issues: list[str] = []
    raw = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "zh" in node and "en" in node and len(node) == 2:
                zh, en = str(node["zh"]), str(node["en"])
                if not zh.strip() or not en.strip():
                    issues.append("empty zh or en leaf")
                elif zh == en and _has_cjk(zh):
                    issues.append(f"untranslated {zh[:24]}")
                elif _has_cjk(en):
                    issues.append(f"en still CJK {en[:24]}")
                return
            for value in node.values():
                walk(value)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(raw)
    _ = load_curriculum()
    return issues


@dataclass(frozen=True)
class CaseReview:
    case_id: str
    stage_id: str
    ready: bool
    score: float
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def review_case(case: ReportCase) -> CaseReview:
    clip = clip_for(case)
    history = StageHistory.from_reports(history_for(case))
    zh_report = assess_clip(clip, lang="zh", history=history)
    en_report = assess_clip(clip, lang="en", history=history)
    issues = [
        *audit_layout(zh_report, expect_stages=case.expect_stages),
        *audit_layout(en_report, expect_stages=case.expect_stages),
        *audit_bilingual(zh_report, en_report),
    ]
    if case.expect_ready is not None and zh_report.ready_for_next_stage != case.expect_ready:
        issues.append(
            f"ready {zh_report.ready_for_next_stage} != {case.expect_ready}"
        )
    block = zh_report.classification
    if case.expect_unusable and (block is None or block.method != "unusable"):
        issues.append("expected an unusable classification")
    if (
        case.expect_ambiguous is not None
        and block is not None
        and block.ambiguous != case.expect_ambiguous
    ):
        issues.append(f"ambiguous {block.ambiguous} != {case.expect_ambiguous}")
    return CaseReview(
        case_id=case.case_id,
        stage_id=zh_report.stage_id,
        ready=zh_report.ready_for_next_stage,
        score=zh_report.score_0_100,
        issues=tuple(issues),
    )


def review_all_cases() -> list[CaseReview]:
    return [review_case(case) for case in CASES]


def review_issues() -> list[str]:
    issues = [f"curriculum: {item}" for item in audit_curriculum_i18n()]
    for result in review_all_cases():
        for item in result.issues:
            issues.append(f"{result.case_id}: {item}")
    return issues
