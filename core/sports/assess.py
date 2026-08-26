"""Map ClipAnalysis to StageReport using curriculum JSON."""

from __future__ import annotations

from typing import assert_never

import core.i18n as i18n
from core.sports.curriculum import (
    CheckpointSpec,
    Curriculum,
    Drill,
    LevelSpec,
    Threshold,
    load_curriculum,
    level_by_id,
)
from core.sports.signals import FeaturePack, FrameSample, extract_features, signal_value
from core.sports.translator import loc
from schemas.clip_analysis import ClipAnalysis
from schemas.stage_report import (
    FrameScorePoint,
    KeypointResult,
    KeypointStatus,
    StageReport,
    TreeNode,
)

UNKNOWN = "unknown"
SYS_CATEGORY = "unknown"
CONF_GATE = 0.35
QUALITY_GATE = 0.2


def _loc(zh: str, en: str, lang: str) -> str:
    return zh if lang.startswith("zh") else en


def _t(zh: str, lang: str) -> str:
    pair = loc(zh)
    return _loc(pair["zh"], pair["en"], lang)


def classify(pack: FeaturePack) -> tuple[str, str, float]:
    if pack.n < 4 or pack.quality < QUALITY_GATE:
        return SYS_CATEGORY, UNKNOWN, 0.0
    mogul = pack.knee_flex_amp > 35.0 and pack.knee_flex_freq > 0.6
    if mogul and pack.upper_quiet < 0.45:
        stage = "mogul_absorb"
        if pack.fall_line < 0.85 and pack.knee_flex_freq > 1.1:
            stage = "mogul_fallline"
        return "alpine_moguls", stage, min(1.0, 0.45 + pack.knee_flex_freq / 4.0)
    if pack.stance_width >= 1.2:
        conf = min(1.0, 0.4 + (pack.stance_width - 1.2))
        if pack.turn_freq < 0.18:
            return "alpine_piste", "pizza_glide", conf
        return "alpine_piste", "pizza", conf
    if pack.inward_lean >= 0.18 and pack.stance_width < 1.2:
        if pack.turn_freq >= 0.45:
            return "alpine_piste", "carve_short", 0.5
        if pack.turn_freq >= 0.32:
            return "alpine_piste", "carve_medium", 0.5
        return "alpine_piste", "carve_long", 0.5
    if (
        pack.stance_width_std >= 0.22
        and pack.stance_width >= 0.95
        and pack.inward_lean < 0.18
    ):
        return "alpine_piste", "wedge_christie", 0.55
    if pack.stance_width < 1.1 and pack.turn_freq >= 0.45:
        return "alpine_piste", "skid_short", 0.5
    if pack.stance_width < 1.1:
        return "alpine_piste", "parallel", 0.55
    return SYS_CATEGORY, UNKNOWN, 0.25


def assess_clip(
    analysis: ClipAnalysis,
    *,
    curriculum: Curriculum | None = None,
    lang: str | None = None,
) -> StageReport:
    cur = curriculum or load_curriculum()
    pack = extract_features(analysis)
    lang_code = lang if lang is not None else i18n._lang
    category_id, stage_id, confidence = classify(pack)
    stage = level_by_id(cur, stage_id)
    if (
        stage is None
        or not stage.in_scope
        or confidence < CONF_GATE
        or stage_id == UNKNOWN
    ):
        return _unknown_report(analysis.clip_id, cur, lang_code, pack)
    results: list[KeypointResult] = []
    heuristic = stage.heuristic_not_fis_carve
    for cid in stage.checkpoints:
        spec = cur.checkpoints[cid]
        item = _eval_checkpoint(spec, pack, cur, lang_code)
        results.append(item)
        heuristic = heuristic or spec.heuristic_not_fis_carve
    score = _stage_score(results, confidence, cur)
    required_ok = _required_ok(results, stage, cur)
    ready = (
        confidence >= CONF_GATE
        and score >= cur.pass_score
        and required_ok
    )
    next_ids: list[str] = []
    next_names: list[str] = []
    next_plans: list[dict] = []
    if ready:
        for nid in stage.next_levels:
            nxt = level_by_id(cur, nid)
            if nxt is None or not nxt.in_scope:
                continue
            next_ids.append(nid)
            next_names.append(_loc(nxt.name.zh, nxt.name.en, lang_code))
            next_plans.append(_level_plan(nxt, cur, lang_code))
    weakest = _weakest_id(results)
    cat_loc = cur.categories.get(stage.category_id)
    cat_name = (
        _loc(cat_loc.zh, cat_loc.en, lang_code) if cat_loc else category_id
    )
    terrain = cur.terrains.get(stage.terrain)
    sys_drill = cur.drills[cur.sys_drill]
    return StageReport(
        clip_id=analysis.clip_id,
        category_id=stage.category_id,
        stage_id=stage_id,
        category_name=cat_name,
        stage_name=_loc(stage.name.zh, stage.name.en, lang_code),
        confidence=confidence,
        ready_for_next_stage=ready,
        disclaimer=_loc(cur.disclaimer.zh, cur.disclaimer.en, lang_code),
        stage_focus=_loc(stage.desc.zh, stage.desc.en, lang_code),
        score_0_100=score,
        terrain_id=stage.terrain,
        terrain_name=(
            _loc(terrain.name.zh, terrain.name.en, lang_code) if terrain else ""
        ),
        terrain_desc=(
            _loc(terrain.desc.zh, terrain.desc.en, lang_code) if terrain else ""
        ),
        weakest_checkpoint_id="" if ready else weakest,
        next_level_ids=next_ids,
        next_level_names=next_names,
        next_plans=next_plans,
        session_plan=[
            _drill_payload(cur.drills[did], cur, lang_code)
            for did in stage.session_drills
            if did in cur.drills
        ],
        tree_path=_tree_path(cur, stage_id, lang_code),
        film_steps=[
            _loc(row.zh, row.en, lang_code) for row in sys_drill.training
        ],
        keypoints=results,
        score_series=_score_series(stage, pack, cur),
        heuristic_not_fis_carve=heuristic,
    )


def _required_ok(
    results: list[KeypointResult],
    stage,
    cur: Curriculum,
) -> bool:
    by_id = {item.id: item for item in results}
    scored = 0
    for cid in stage.checkpoints:
        spec = cur.checkpoints[cid]
        if not spec.required:
            continue
        item = by_id.get(cid)
        if item is None or item.score is None:
            continue
        scored += 1
        if item.score < cur.checkpoint_pass:
            return False
    return scored > 0


def _weakest_id(results: list[KeypointResult]) -> str:
    known = [item for item in results if item.score is not None]
    if not known:
        return results[0].id if results else ""
    return min(known, key=lambda item: item.score or 0.0).id


def _stage_score(
    results: list[KeypointResult], confidence: float, cur: Curriculum
) -> float:
    pts = [
        item.score
        for item in results
        if item.score is not None
        and cur.checkpoints[item.id].required
    ]
    if not pts:
        return 0.0
    raw = sum(pts) / len(pts)
    return round(raw * (0.8 + 0.2 * confidence), 1)


def _continuous_score(value: float, spec: Threshold) -> float:
    if spec.op == "gte":
        band = max(abs(spec.value) * 0.4, 0.08)
        return _piecewise(value, spec.value - band, spec.value, spec.value + band)
    if spec.op == "lte":
        band = max(abs(spec.value) * 0.4, 0.08)
        mirrored = spec.value - (value - spec.value)
        return _piecewise(
            mirrored, spec.value - band, spec.value, spec.value + band
        )
    if spec.op == "between":
        hi = spec.hi if spec.hi is not None else spec.value
        lo = spec.value
        if lo <= value <= hi:
            mid = 0.5 * (lo + hi)
            span = max((hi - lo) / 2.0, 1e-6)
            dist = abs(value - mid) / span
            return round(100.0 - 40.0 * dist, 1)
        outside = lo - value if value < lo else value - hi
        width = max(hi - lo, 0.08)
        return round(max(0.0, 60.0 * (1.0 - outside / width)), 1)
    assert_never(spec.op)


def _piecewise(value: float, lo: float, mid: float, hi: float) -> float:
    if value <= lo:
        return 0.0
    if value >= hi:
        return 100.0
    if value < mid:
        t = (value - lo) / max(mid - lo, 1e-6)
        return round(60.0 * t, 1)
    t = (value - mid) / max(hi - mid, 1e-6)
    return round(60.0 + 40.0 * t, 1)


def _eval_checkpoint(
    spec: CheckpointSpec, pack: FeaturePack, cur: Curriculum, lang: str
) -> KeypointResult:
    value = signal_value(pack, spec.signal)
    if value is None:
        status = KeypointStatus.UNKNOWN
        score: float | None = None
    else:
        score = _continuous_score(value, spec.threshold)
        status = (
            KeypointStatus.PASS
            if score >= cur.checkpoint_pass
            else KeypointStatus.FAIL
        )
    drills: list[dict] = []
    if status == KeypointStatus.FAIL:
        drills = [
            _drill_payload(cur.drills[did], cur, lang)
            for did in spec.drills
            if did in cur.drills
        ]
    evidence = None
    if status != KeypointStatus.UNKNOWN:
        evidence = _evidence_ms(
            spec, pack, passing=status == KeypointStatus.PASS
        )
    return KeypointResult(
        id=spec.id,
        name=_loc(spec.name.zh, spec.name.en, lang),
        status=status,
        score=score,
        value=value,
        evidence_ms=evidence,
        good=_loc(spec.desc.zh, spec.desc.en, lang),
        bad=_loc(spec.desc.zh, spec.desc.en, lang),
        drills=drills,
    )


def _sample_signal(sample: FrameSample, name: str) -> float | None:
    mapping = {
        "stance_width": sample.stance_width,
        "knee_flex_mean": sample.knee_flex,
        "inward_lean": None if sample.inward_lean is None else abs(sample.inward_lean),
        "backseat": sample.backseat,
        "knee_valgus": sample.knee_valgus,
        "hip_ir_proxy": sample.hip_ir_proxy,
        "hands_low": sample.hands_low,
        "gaze_ok": sample.gaze_ok,
        "upper_quiet": sample.quiet,
    }
    if name not in mapping:
        return None
    return mapping[name]


def _evidence_ms(
    spec: CheckpointSpec, pack: FeaturePack, *, passing: bool
) -> float | None:
    if not pack.series:
        return None
    instant = []
    for sample in pack.series:
        value = _sample_signal(sample, spec.signal)
        if value is None:
            continue
        instant.append((sample.t_ms, _continuous_score(value, spec.threshold)))
    if instant:
        if passing:
            return max(instant, key=lambda row: row[1])[0]
        return min(instant, key=lambda row: row[1])[0]
    if spec.signal in {"turn_freq", "fall_line"}:
        scored = [
            (s.t_ms, abs((s.hip_x or 0.0) - pack.hip_x_mean))
            for s in pack.series
            if s.hip_x is not None
        ]
        if not scored:
            return pack.series[0].t_ms
        return max(scored, key=lambda row: row[1])[0]
    if spec.signal in {"knee_flex_freq", "knee_flex_amp"}:
        scored = [
            (s.t_ms, s.knee_flex)
            for s in pack.series
            if s.knee_flex is not None
        ]
        if not scored:
            return pack.series[0].t_ms
        return max(scored, key=lambda row: row[1] or 0.0)[0]
    if spec.signal == "stance_width_std":
        scored = [
            (s.t_ms, abs((s.stance_width or pack.stance_width) - pack.stance_width))
            for s in pack.series
            if s.stance_width is not None
        ]
        if not scored:
            return pack.series[0].t_ms
        return max(scored, key=lambda row: row[1])[0]
    return pack.series[0].t_ms


def _score_series(
    stage: LevelSpec, pack: FeaturePack, cur: Curriculum
) -> list[FrameScorePoint]:
    specs = [
        cur.checkpoints[cid]
        for cid in stage.checkpoints
        if cid in cur.checkpoints and cur.checkpoints[cid].required
    ]
    points: list[FrameScorePoint] = []
    for sample in pack.series:
        scores: list[float] = []
        for spec in specs:
            value = _sample_signal(sample, spec.signal)
            if value is None:
                value = signal_value(pack, spec.signal)
            if value is None:
                continue
            scores.append(_continuous_score(value, spec.threshold))
        if not scores:
            continue
        points.append(
            FrameScorePoint(
                t_ms=sample.t_ms,
                score=round(sum(scores) / len(scores), 1),
            )
        )
    return points


def _venue_payload(cur: Curriculum, venue_id: str, lang: str) -> dict | None:
    venue = cur.venues.get(venue_id)
    if venue is None:
        return None
    return {
        "id": venue.id,
        "name": _loc(venue.name.zh, venue.name.en, lang),
        "desc": _loc(venue.desc.zh, venue.desc.en, lang),
        "tips": _loc(venue.tips.zh, venue.tips.en, lang),
        "terrain": venue.terrain,
    }


def _drill_payload(drill: Drill, cur: Curriculum, lang: str) -> dict:
    venues = [
        item
        for vid in drill.venue_ids
        if (item := _venue_payload(cur, vid, lang)) is not None
    ]
    return {
        "id": drill.id,
        "title": _loc(drill.name.zh, drill.name.en, lang),
        "name": _loc(drill.name.zh, drill.name.en, lang),
        "desc": _loc(drill.desc.zh, drill.desc.en, lang),
        "steps": [_loc(row.zh, row.en, lang) for row in drill.training],
        "training": [_loc(row.zh, row.en, lang) for row in drill.training],
        "venues": venues,
    }


def _level_plan(stage: LevelSpec, cur: Curriculum, lang: str) -> dict:
    drills = [
        _drill_payload(cur.drills[did], cur, lang)
        for did in stage.session_drills
        if did in cur.drills
    ]
    venues = [
        item
        for vid in stage.venue_ids
        if (item := _venue_payload(cur, vid, lang)) is not None
    ]
    return {
        "level_id": stage.id,
        "level_name": _loc(stage.name.zh, stage.name.en, lang),
        "drills": drills,
        "venues": venues,
    }


def _tree_path(cur: Curriculum, stage_id: str, lang: str) -> list[TreeNode]:
    parent: dict[str, str] = {}
    for lid, spec in cur.levels.items():
        for nid in spec.next_levels:
            parent.setdefault(nid, lid)
    chain: list[str] = []
    cursor = stage_id
    seen: set[str] = set()
    while cursor and cursor not in seen:
        seen.add(cursor)
        chain.append(cursor)
        cursor = parent.get(cursor, "")
    chain.reverse()
    nodes: list[TreeNode] = []
    for lid in chain:
        spec = cur.levels.get(lid)
        if spec is None:
            continue
        nodes.append(
            TreeNode(
                id=lid,
                name=_loc(spec.name.zh, spec.name.en, lang),
                current=lid == stage_id,
            )
        )
    cursor = stage_id
    seen_future: set[str] = {node.id for node in nodes}
    while True:
        spec = cur.levels.get(cursor)
        if spec is None or not spec.next_levels:
            break
        nxt = spec.next_levels[0]
        if nxt in seen_future:
            break
        next_spec = cur.levels.get(nxt)
        if next_spec is None:
            break
        nodes.append(
            TreeNode(
                id=nxt,
                name=_loc(next_spec.name.zh, next_spec.name.en, lang),
                current=False,
            )
        )
        seen_future.add(nxt)
        cursor = nxt
    return nodes


def _unknown_report(
    clip_id: str, cur: Curriculum, lang: str, pack: FeaturePack
) -> StageReport:
    drill = cur.drills[cur.sys_drill]
    payload = _drill_payload(drill, cur, lang)
    return StageReport(
        clip_id=clip_id,
        category_id=SYS_CATEGORY,
        stage_id=UNKNOWN,
        category_name=_t("未识别", lang),
        stage_name=_t("请重拍", lang),
        confidence=min(pack.quality, 0.34),
        ready_for_next_stage=False,
        disclaimer=_loc(cur.disclaimer.zh, cur.disclaimer.en, lang),
        weakest_checkpoint_id="KP-SYS-01",
        film_steps=[_loc(row.zh, row.en, lang) for row in drill.training],
        keypoints=[
            KeypointResult(
                id="KP-SYS-01",
                name=_loc(drill.name.zh, drill.name.en, lang),
                status=KeypointStatus.UNKNOWN,
                value=None,
                good=_loc(drill.name.zh, drill.name.en, lang),
                bad=_t(
                    "镜头不稳、遮挡或非本课程种类时不判定阶段。",
                    lang,
                ),
                drills=[payload],
            )
        ],
    )
