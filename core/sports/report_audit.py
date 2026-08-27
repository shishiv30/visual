"""Reviewer: five-chapter report layout and zh/en completeness."""

from __future__ import annotations

import json
from dataclasses import dataclass

from core.i18n import has_key, t
from core.sports.assess import assess_clip
from core.sports.curriculum import CURRICULUM_PATH, load_curriculum
from core.sports.report_cases import CASES, ReportCase, clip_for
from schemas.stage_report import KeypointStatus, StageReport

CJK = ("\u4e00", "\u9fff")
KNOWN_TERRAIN = {"green", "blue", "red", "black", "park", "mogul"}


def _has_cjk(text: str) -> bool:
    return any(CJK[0] <= ch <= CJK[1] for ch in text)


def audit_layout(report: StageReport, *, expect_stages: tuple[str, ...] | None = None) -> list[str]:
    issues: list[str] = []
    if expect_stages is not None and report.stage_id not in expect_stages:
        issues.append(f"ch1 stage {report.stage_id} not in {expect_stages}")
    if not report.stage_name.strip():
        issues.append("ch1 missing stage_name")
    if not 0 <= report.score_0_100 <= 100:
        issues.append("ch1 score out of range")
    if report.posture is not None:
        for name in ("stability", "coordination", "control", "balance"):
            value = getattr(report.posture, name)
            if not 0 <= value <= 100:
                issues.append(f"ch1 posture {name} out of range")
    if report.stage_id != "unknown":
        if report.terrain_id not in KNOWN_TERRAIN:
            issues.append(f"ch1 terrain {report.terrain_id!r}")
        if not report.terrain_name.strip():
            issues.append("ch1 missing terrain_name")
        if not report.tree_path:
            issues.append("ch4 empty skill tree")
        else:
            current = [node for node in report.tree_path if node.current]
            if len(current) != 1 or current[0].id != report.stage_id:
                issues.append("ch4 current node is not stage_id")
    if not report.keypoints:
        issues.append("ch2 no checkpoints")
    for item in report.keypoints:
        if not item.name.strip():
            issues.append(f"ch2 {item.id} missing name")
        if item.status != KeypointStatus.UNKNOWN and item.evidence_ms is None:
            issues.append(f"ch2 {item.id} missing evidence_ms")
    if report.ready_for_next_stage:
        if not report.next_plans:
            if report.next_level_ids:
                issues.append("ch3 ready but next_plans empty")
        for plan in report.next_plans:
            if not plan.get("level_name"):
                issues.append("ch3 plan missing level_name")
            drills = plan.get("drills") or []
            if not drills:
                issues.append(f"ch3 {plan.get('level_id')} missing drills")
            for drill in drills:
                if not (drill.get("training") or drill.get("steps")):
                    issues.append(f"ch3 drill {drill.get('id')} missing training")
            if not plan.get("venues"):
                issues.append(f"ch3 {plan.get('level_id')} missing venues")
        if report.weakest_checkpoint_id:
            issues.append("ch3 ready still has weakest_checkpoint_id")
    else:
        if report.next_plans:
            issues.append("ch3 not ready but next_plans set")
        if report.stage_id != "unknown" and not report.weakest_checkpoint_id:
            issues.append("ch3 missing weakest checkpoint")
        weak = next(
            (k for k in report.keypoints if k.id == report.weakest_checkpoint_id),
            None,
        )
        if weak is not None and weak.status == KeypointStatus.FAIL:
            if not weak.drills:
                issues.append("ch3 weakest has no drills")
            else:
                drill = weak.drills[0]
                if not (drill.get("training") or drill.get("steps")):
                    issues.append("ch3 weakest drill missing training")
                if not drill.get("venues"):
                    issues.append("ch3 weakest drill missing venues")
    if not report.film_steps:
        issues.append("ch5 missing film_steps")
    if not report.disclaimer.strip():
        issues.append("ch5 missing disclaimer")
    return issues


def audit_bilingual(zh_report: StageReport, en_report: StageReport) -> list[str]:
    issues: list[str] = []
    if zh_report.stage_id != en_report.stage_id:
        issues.append("zh/en stage_id mismatch")
    if zh_report.ready_for_next_stage != en_report.ready_for_next_stage:
        issues.append("zh/en ready mismatch")
    if zh_report.terrain_id != en_report.terrain_id:
        issues.append("zh/en terrain mismatch")
    zh_ids = [k.id for k in zh_report.keypoints]
    en_ids = [k.id for k in en_report.keypoints]
    if zh_ids != en_ids:
        issues.append("zh/en checkpoint ids mismatch")
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
    zh_report = assess_clip(clip, lang="zh")
    en_report = assess_clip(clip, lang="en")
    issues = [
        *audit_layout(zh_report, expect_stages=case.expect_stages),
        *audit_layout(en_report, expect_stages=case.expect_stages),
        *audit_bilingual(zh_report, en_report),
    ]
    if case.expect_ready is not None and zh_report.ready_for_next_stage != case.expect_ready:
        issues.append(
            f"ready {zh_report.ready_for_next_stage} != {case.expect_ready}"
        )
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
