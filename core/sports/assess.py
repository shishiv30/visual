"""Map a ClipAnalysis to a StageReport 3.0.0 (design doc, all sections).

The orchestration, in order:

1. segment turns (``core.sports.turns``)
2. compute the metric catalog (``core.sports.metrics``)
3. classify against the candidate stages (``core.sports.classify``, §5)
4. score the chosen stage's metrics (``core.sports.score``, §6)
5. build the whole skill tree (``core.sports.tree``, §8)
6. select the knowledge slice from this skier's own failing metrics (§9)
7. assemble the report

Everything a 2.1.0 client reads is still produced by the v2 path — the legacy
``FeaturePack`` still drives the checkpoint list, the frame score series and the
posture composites — so the five old chapters render unchanged and stored
reports stay comparable. The v3 blocks are additions on top.

Two behaviours worth stating because they differ from v2:

* **A low-confidence clip is no longer thrown away.** v2 returned the "Re-film"
  report whenever confidence fell under 0.35. §5 step 6 wants the top two
  candidates offered instead, so an ambiguous clip now produces a full report on
  the leading candidate with ``classification.ambiguous`` set and the separating
  metric named. Only a clip that fails the *quality* gate — too few frames, no
  body scale, unusable landmarks — takes the unusable path.
* **``stage_focus`` / ``training_focus`` / ``how_to_advance`` are populated.**
  All three were dead fields rendered as empty strings (design §10, known bugs).
"""

from __future__ import annotations

from typing import Callable, Iterable, assert_never

import core.i18n as i18n
from core.i18n import t
from core.sports import knowledge_pack as kb
from core.sports.bands import Evaluation, band_for, evaluate
from core.sports.classify import (
    classify_legacy,
    classify_v3,
    missing_scene_facts,
)
from core.sports.curriculum import (
    CheckpointSpec,
    Curriculum,
    Drill,
    LevelSpec,
    Threshold,
    load_curriculum,
    level_by_id,
)
from core.sports.history import StageHistory
from core.sports.metrics import (
    BACKSEAT_RATIO,
    CAMERA_UNKNOWN,
    REASON_TOO_FRONTAL,
    REASON_TOO_PROFILE,
    ROTATION_DEG,
    STEM_WEDGE_DEG,
    MetricPack,
    build_athlete_context,
    compute_metrics,
    resolve_scene,
)
from core.sports.posture import posture_scores
from core.sports.profile import AthleteContext
from core.sports.scene import CameraMotion, SceneContext
from core.sports.score import (
    ScoredMetric,
    gate_summary,
    metric_name,
    ready_for_next_stage,
    score_level,
    stage_score,
    weakest,
)
from core.sports.signals import FeaturePack, FrameSample, extract_features, signal_value
from core.sports.tree import build_tree, tree_path_projection
from core.sports.turns import Turn, segment_turns
from schemas.clip_analysis import ClipAnalysis
from schemas.stage_report import (
    Classification,
    FilmingIssue,
    FrameScorePoint,
    KeypointResult,
    KeypointStatus,
    KnowledgeFocus,
    KnowledgeRef,
    ProfileSummary,
    SceneSummary,
    StageReport,
    TurnRecord,
    TurnSummary,
)

UNKNOWN = "unknown"
SYS_CATEGORY = "unknown"

#: v2 name, kept as an alias so existing callers and tests keep working. The
#: v2 ladder itself now lives in ``core.sports.classify``.
classify = classify_legacy


def _text(item: object, lang: str) -> str:
    """Resolve Localized or English key via i18n catalog."""
    if hasattr(item, "en"):
        return t(str(getattr(item, "en")), lang=lang)
    return t(str(item), lang=lang)


def _name_separating_metrics(
    classification: Classification, lang: str
) -> None:
    """Fill each candidate's ``separating_metric_name`` (chapter 2).

    ``classify_v3`` has no ``lang``, so it emits the metric id and leaves the
    name empty; without this the ports render ``turn_shape_index`` at the user.
    The resolver is the same one the chapter-3 metric rows use, so the two
    chapters name a metric identically.
    """
    for candidate in classification.candidates:
        if candidate.separating_metric_id and not candidate.separating_metric_name:
            candidate.separating_metric_name = metric_name(
                candidate.separating_metric_id, lang
            )


def _namer(cur: Curriculum, lang: str) -> Callable[[str], str]:
    def resolve(level_id: str) -> str:
        spec = cur.levels.get(level_id)
        return _text(spec.name, lang) if spec is not None else level_id

    return resolve


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def assess_clip(
    analysis: ClipAnalysis,
    *,
    curriculum: Curriculum | None = None,
    lang: str | None = None,
    athlete: AthleteContext | None = None,
    scene: SceneContext | None = None,
    history: Iterable[object] | StageHistory | None = None,
) -> StageReport:
    """Assess one clip against the v3 curriculum.

    ``athlete`` and ``scene`` are the §2.2 / §2.3 inputs and are now consumed:
    the profile changes normalization, threshold band selection and guidance
    (never a pass standard), and the scene decides whether the ``scene``-tier
    stages are candidates at all. Both stay optional — a clip with neither is
    assessed exactly as before, and the report says which facts were missing.

    ``history`` is this athlete's earlier reports, used for the classifier's
    adjacency prior and the tree's completed / locked states. It accepts a
    :class:`~core.sports.history.StageHistory` or any iterable of stored
    reports.
    """
    cur = curriculum or load_curriculum()
    lang_code = lang if lang is not None else i18n._lang
    hist = (
        history
        if isinstance(history, StageHistory)
        else StageHistory.from_reports(history)
    )
    resolve = _namer(cur, lang_code)

    legacy = extract_features(analysis)
    athlete_ctx = build_athlete_context(
        athlete if athlete is not None else getattr(analysis, "athlete", None)
    )
    scene_ctx = resolve_scene(
        scene if scene is not None else getattr(analysis, "scene", None)
    )
    turns = segment_turns(
        list(analysis.frames),
        _fps_effective(analysis, scene_ctx),
    )
    pack = compute_metrics(
        analysis, turns=turns, profile=athlete_ctx, scene=scene_ctx
    )
    classification = classify_v3(pack, cur, hist, name_for=resolve)
    _name_separating_metrics(classification, lang_code)
    stage = level_by_id(cur, classification.chosen_id)
    scene_summary = _scene_summary(pack, cur, scene_ctx)
    profile_summary = _profile_summary(athlete_ctx, stage, lang_code)
    filming = _filming(pack, analysis, classification, lang_code)

    if (
        classification.method == "unusable"
        or stage is None
        or not stage.in_scope
        or classification.chosen_id == UNKNOWN
    ):
        return _unusable_report(
            analysis.clip_id,
            cur,
            lang_code,
            legacy,
            pack,
            turns,
            classification,
            scene_summary,
            profile_summary,
            filming,
            hist,
        )

    confidence = float(classification.confidence)
    rows = score_level(pack, stage, lang_code)
    age_band = getattr(pack.athlete, "age_band", None)
    results: list[KeypointResult] = []
    heuristic = stage.heuristic_not_fis_carve
    for cid in stage.checkpoints:
        spec = cur.checkpoints[cid]
        item = _eval_checkpoint(
            spec,
            legacy,
            pack,
            cur,
            lang_code,
            level_id=stage.id,
            age_band=age_band,
        )
        results.append(item)
        heuristic = heuristic or spec.heuristic_not_fis_carve
    score = stage_score(rows, confidence, cur)
    ready = ready_for_next_stage(
        rows,
        confidence=confidence,
        score=score,
        curriculum=cur,
        pack=pack,
        level=stage,
    ) and _required_metric_ok(results, stage, cur)
    _, _, unmeasured_gates = gate_summary(rows)
    if unmeasured_gates:
        filming.append(
            FilmingIssue(
                code="gates_not_measured",
                message=t(
                    "Some checkpoints for this stage could not be measured in "
                    "this clip.",
                    lang=lang_code,
                ),
                severity="warn",
            )
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
            next_names.append(_text(nxt.name, lang_code))
            next_plans.append(_level_plan(nxt, cur, lang_code))
    weakest_row = weakest(rows)
    weak_checkpoint = _weakest_id(results)
    cat_loc = cur.categories.get(stage.category_id)
    cat_name = _text(cat_loc, lang_code) if cat_loc else stage.category_id
    terrain = cur.terrains.get(stage.terrain)
    sys_drill = cur.drills[cur.sys_drill]
    kb_stage = kb.stage_for_level(stage.id, stage.kb_stage)
    focus = _knowledge_focus(kb_stage, rows, weakest_row, lang_code)

    return StageReport(
        clip_id=analysis.clip_id,
        category_id=stage.category_id,
        stage_id=stage.id,
        category_name=cat_name,
        stage_name=_text(stage.name, lang_code),
        confidence=max(0.0, min(1.0, confidence)),
        ready_for_next_stage=ready,
        disclaimer=_text(cur.disclaimer, lang_code),
        stage_focus=_text(stage.desc, lang_code),
        training_focus=_training_focus(rows, weakest_row, results, lang_code),
        how_to_advance=_how_to_advance(
            ready, stage, cur, weakest_row, lang_code
        ),
        score_0_100=score,
        terrain_id=stage.terrain,
        terrain_name=_text(terrain.name, lang_code) if terrain else "",
        terrain_desc=_text(terrain.desc, lang_code) if terrain else "",
        weakest_checkpoint_id="" if ready else weak_checkpoint,
        next_level_ids=next_ids,
        next_level_names=next_names,
        next_plans=next_plans,
        session_plan=[
            _drill_payload(cur.drills[did], cur, lang_code)
            for did in stage.session_drills
            if did in cur.drills
        ],
        tree_path=tree_path_projection(cur, stage.id, resolve),
        film_steps=[_text(row, lang_code) for row in sys_drill.training],
        keypoints=results,
        score_series=_score_series(stage, legacy, cur),
        heuristic_not_fis_carve=heuristic,
        posture=posture_scores(legacy, results),
        kb_stage=kb_stage,
        tier=stage.tier or "full",
        classification=classification,
        metrics=[row.report for row in rows],
        turns=_turn_summary(pack, turns),
        tree=build_tree(
            cur,
            stage.id,
            hist,
            athlete_ctx,
            lang=lang_code,
            name_for=resolve,
        ),
        knowledge_ref=(
            KnowledgeRef(
                kb_stage=kb_stage,
                pack_version=kb.pack_version(),
                level_id=stage.id,
            )
            if kb.load_pack() is not None
            else None
        ),
        knowledge_focus=focus,
        scene=scene_summary,
        profile_summary=profile_summary,
        filming=filming,
    )


def _fps_effective(analysis: ClipAnalysis, scene: SceneContext) -> float:
    """The one sample rate everything downstream uses (§2.2, §3.3)."""
    recorded = scene.fps_effective or getattr(analysis, "fps_effective", None)
    if recorded and recorded > 0.0:
        return float(recorded)
    return float(analysis.fps) if analysis.fps and analysis.fps > 0 else 15.0


# ---------------------------------------------------------------------------
# v3 blocks
# ---------------------------------------------------------------------------


def _scene_summary(
    pack: MetricPack, cur: Curriculum, scene: SceneContext
) -> SceneSummary:
    view = pack.view
    return SceneSummary(
        snow_surface=getattr(scene.snow_surface, "value", "") or "",
        slope_band=getattr(scene.slope_band, "value", "") or "",
        view_class=str(getattr(getattr(view, "view_class", ""), "value", "")),
        view_azimuth_deg=(
            None
            if view is None or view.azimuth_deg is None
            else round(float(view.azimuth_deg), 1)
        ),
        camera_motion=pack.camera_motion,
        fps_effective=round(float(pack.fps_effective), 2),
        missing=missing_scene_facts(cur, scene),
    )


def _profile_summary(
    athlete: AthleteContext, stage: LevelSpec | None, lang: str
) -> ProfileSummary:
    """What the profile changed. Guidance only — never a score change (§2.3)."""
    from core.sports.bands import age_effects

    band = athlete.age_band
    effects = [t(note, lang=lang) for note in age_effects(band)]
    if athlete.height_m:
        effects.append(
            t(
                "Distances are normalized to this skier's leg length.",
                lang=lang,
            )
        )
    if stage is not None and band and any(
        note.id == band and note.status == "not_applicable"
        for note in stage.profile_notes
    ):
        effects.append(
            t(
                "Carving needs body mass to bend the ski; not applicable "
                "below age 13.",
                lang=lang,
            )
        )
    overlays = [band] if band else []
    if athlete.sex in ("female", "male") and band in (
        "age-18-39",
        "age-40-59",
        "age-60plus",
    ):
        overlays.append(f"phys-{athlete.sex}-adult")
    return ProfileSummary(
        age_band=band or "",
        age_years=None if athlete.age_years is None else round(athlete.age_years, 1),
        sex=athlete.sex or "",
        height_cm=None if athlete.height_m is None else round(athlete.height_m * 100, 1),
        weight_kg=athlete.mass_kg,
        ski_cm=athlete.ski_cm,
        is_complete=athlete.is_complete,
        effects=effects,
        overlays=overlays,
    )


#: Per-turn fault predicates, matching ``metrics._fault_counts`` exactly so the
#: per-turn flags and the reported counts can never disagree.
_FAULT_PREDICATES: tuple[tuple[str, Callable[[float], bool]], ...] = (
    ("stem_count", lambda value: value > STEM_WEDGE_DEG),
    ("backseat_count", lambda value: value < BACKSEAT_RATIO),
    ("rotation_count", lambda value: value >= ROTATION_DEG),
    ("braking_count", lambda value: value >= 0.5),
)


def _turn_summary(pack: MetricPack, turns: list[Turn]) -> TurnSummary:
    flags: dict[int, list[str]] = {index: [] for index in range(len(turns))}
    counts: dict[str, int] = {}
    for metric_id, predicate in _FAULT_PREDICATES:
        item = pack.get(metric_id)
        if item is None or item.state != "ok":
            continue
        counts[metric_id] = int(item.faulty_turns or 0)
        for index, value in enumerate(item.per_turn or []):
            if value is None or index not in flags:
                continue
            if predicate(float(value)):
                flags[index].append(metric_id)
    durations = [turn.duration_s for turn in turns if turn.duration_s > 0.0]
    mean_duration = sum(durations) / len(durations) if durations else None
    cv = pack.value("turn_duration_var")
    return TurnSummary(
        count=len(turns),
        # ``Turn.side`` is the segmenter's "L" / "R" label.
        left_count=sum(1 for turn in turns if turn.side == "L"),
        right_count=sum(1 for turn in turns if turn.side == "R"),
        mean_duration_s=None if mean_duration is None else round(mean_duration, 2),
        duration_cv=None if cv is None else round(float(cv), 3),
        turns=[
            TurnRecord(
                index=turn.index,
                side=turn.side,
                t_start_ms=round(turn.t_start_ms, 1),
                t_end_ms=round(turn.t_end_ms, 1),
                duration_s=round(turn.duration_s, 3),
                amplitude_deg=round(turn.amplitude_deg, 1),
                flags=flags.get(turn.index, []),
            )
            for turn in turns
        ],
        fault_counts=counts,
    )


#: Keyword lexicon mapping a knowledge-pack fault or skill to the metric that
#: measures it. The pack carries no metric ids (it is imported from the wiki
#: curriculum, which predates the catalog), so the link is made here over the
#: fault's English name, symptom and root causes. Scanned in order, first match
#: wins, so the more specific phrases come first.
FAULT_METRIC_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("bank", "banking_index"),
    ("stem", "stem_count"),
    ("wedge", "wedge_angle"),
    ("back seat", "hip_over_foot"),
    ("backseat", "hip_over_foot"),
    ("sit back", "hip_over_foot"),
    ("behind", "hip_over_foot"),
    ("rotat", "rotation_count"),
    ("shoulder", "separation_angle"),
    ("counter", "separation_angle"),
    ("separation", "separation_angle"),
    ("pole", "pole_touch_rate"),
    ("park-and-ride", "pressure_peak_phase"),
    ("static", "pressure_peak_phase"),
    ("pressure", "pressure_peak_phase"),
    ("rhythm", "turn_duration_var"),
    ("traverse", "turn_duration_var"),
    ("edge change", "edge_change_duration"),
    ("flat ski", "edge_change_duration"),
    ("edge", "edge_angle_proxy"),
    ("brak", "braking_count"),
    ("scrap", "braking_count"),
    ("skid", "turn_shape_index"),
    ("z-shape", "turn_shape_index"),
    ("straight leg", "flexion_range"),
    ("absor", "flexion_range"),
    ("flex", "flexion_range"),
    ("extend", "com_vertical_travel"),
    ("bounce", "com_vertical_travel"),
    ("up and down", "com_vertical_travel"),
    ("asymmetr", "asymmetry_index"),
    ("one-sided", "asymmetry_index"),
    ("one side", "asymmetry_index"),
    ("inside ski", "banking_index"),
    ("zipper", "turn_rate"),
    ("hand", "hands_in_view"),
    ("knee", "knee_valgus"),
    ("narrow", "stance_width"),
    ("wide", "stance_width"),
    ("stance", "stance_width"),
)


def _match_metric(text: str) -> str:
    for keyword, metric_id in FAULT_METRIC_KEYWORDS:
        if keyword in text:
            return metric_id
    return ""


def _fault_metric(entry: dict) -> str:
    """Metric id a pack fault or skill maps to, or ``""``.

    Two passes: the entry's *name* first, then its whole body. The name is a
    coach's label for exactly one thing ("Back seat at the turn finish"), while
    the body mentions many, so scanning the name alone first stops an incidental
    word in a symptom paragraph from capturing the entry.
    """
    by_name = _match_metric(str(entry.get("name") or "").lower())
    if by_name:
        return by_name
    haystack = " ".join(
        [
            str(entry.get("symptom") or ""),
            " ".join(str(item) for item in entry.get("root_causes") or ()),
            str(entry.get("description") or ""),
            str(entry.get("why") or ""),
        ]
    ).lower()
    return _match_metric(haystack)


def _knowledge_focus(
    kb_stage: str,
    rows: list[ScoredMetric],
    weakest_row: ScoredMetric | None,
    lang: str,
) -> KnowledgeFocus | None:
    """Faults, drills and skills chosen from this skier's own metrics (§9).

    The pack's own order is deliberately *not* used: each fault is mapped to the
    metric that measures it and the faults are then ordered by how badly this
    skier scored on that metric. Faults whose metric was not measured keep the
    pack's order behind the measured ones, so the chapter never goes empty.
    """
    if kb.load_pack() is None or not kb_stage:
        return None
    scores = {
        row.report.id: float(row.report.score)
        for row in rows
        if row.measured and row.report.score is not None
    }
    gate_scores = {
        row.report.id: float(row.report.score)
        for row in rows
        if row.measured and row.is_gate and row.report.score is not None
    }
    faults = kb.faults(kb_stage, "en")
    ranked: list[tuple[float, int, str]] = []
    for index, fault in enumerate(faults):
        metric_id = _fault_metric(fault)
        score = scores.get(metric_id)
        rank = score if score is not None else 1000.0 + index
        ranked.append((rank, index, str(fault["id"])))
    ranked.sort()
    fault_ids = [item[2] for item in ranked]

    weak_metric = ""
    if gate_scores:
        weak_metric = min(gate_scores, key=lambda key: gate_scores[key])
    elif weakest_row is not None:
        weak_metric = weakest_row.report.id

    weak_faults = [
        str(fault["id"])
        for fault in faults
        if weak_metric and _fault_metric(fault) == weak_metric
    ]
    # Drills targeting the weakest *gate* metric come first, then the drills
    # for the rest of the faults in the order this skier failed them, then
    # whatever the pack has left.
    drill_order: list[str] = []
    for fault_id in weak_faults + [f for f in fault_ids if f not in weak_faults]:
        for drill_id in kb.fault_fix_drills(kb_stage, fault_id):
            if drill_id not in drill_order:
                drill_order.append(drill_id)
    for drill in kb.drills(kb_stage, "en"):
        drill_id = str(drill["id"])
        if drill_id not in drill_order:
            drill_order.append(drill_id)
    skill_ids = [
        str(skill["id"])
        for skill in kb.skills(kb_stage, "en")
        if weak_metric and _fault_metric(skill) == weak_metric
    ]
    if not skill_ids:
        # The chapter must not go empty: fall back to the stage's first skill,
        # which the pack orders as the one the stage is built on.
        skill_ids = [str(skill["id"]) for skill in kb.skills(kb_stage, "en")[:1]]
    return KnowledgeFocus(
        fault_ids=fault_ids,
        drill_ids=drill_order,
        skill_ids=skill_ids,
        weakest_metric_id=weak_metric,
        weakest_metric_name=metric_name(weak_metric, lang) if weak_metric else "",
    )


#: Clips shorter than this cannot show linked turns (design §5 gate).
SHORT_CLIP_FRAMES = 20

#: Turn count the filming advice actually asks for. The classifier's own
#: ``MIN_TURNS_FOR_RHYTHM`` (4) is the point below which rhythm and count
#: metrics stop being trustworthy; this is the number the message tells the
#: skier to film. Gating the message on 4 while the copy says 8 left a five-turn
#: clip told nothing and a three-turn clip told to film 8, so the note is
#: emitted whenever the clip is short of what the copy asks for.
MIN_TURNS_ADVISED = 8


def _filming(
    pack: MetricPack,
    analysis: ClipAnalysis,
    classification: Classification,
    lang: str,
) -> list[FilmingIssue]:
    """Filming problems, from the reasons the metrics layer already returns."""
    issues: list[FilmingIssue] = []
    view = pack.view
    reason = getattr(view, "reason", None)
    if reason == REASON_TOO_PROFILE:
        issues.append(
            FilmingIssue(
                code=REASON_TOO_PROFILE,
                message=t(
                    "Filmed almost side-on: stance, edging and lean cannot be "
                    "measured. Film from a quarter angle, behind and to one "
                    "side.",
                    lang=lang,
                ),
                severity="warn",
            )
        )
    elif reason == REASON_TOO_FRONTAL:
        issues.append(
            FilmingIssue(
                code=REASON_TOO_FRONTAL,
                message=t(
                    "Filmed almost face-on: fore/aft balance cannot be "
                    "measured. Film from a quarter angle, behind and to one "
                    "side.",
                    lang=lang,
                ),
                severity="warn",
            )
        )
    motion = pack.camera_motion
    if motion == CameraMotion.FOLLOW.value:
        issues.append(
            FilmingIssue(
                code="camera_follow",
                message=t(
                    "The camera follows the skier, so turn rhythm is measured "
                    "from the body rather than the track.",
                    lang=lang,
                ),
                severity="info",
            )
        )
    elif motion == CameraMotion.PANNING.value:
        issues.append(
            FilmingIssue(
                code="camera_panning",
                message=t(
                    "The camera pans during the clip; a fixed camera measures "
                    "rhythm more reliably.",
                    lang=lang,
                ),
                severity="info",
            )
        )
    elif motion == CAMERA_UNKNOWN:
        issues.append(
            FilmingIssue(
                code="camera_motion_unknown",
                message=t(
                    "Camera motion could not be judged from this clip.",
                    lang=lang,
                ),
                severity="info",
            )
        )
    if pack.turn_count == 0:
        issues.append(
            FilmingIssue(
                code="no_turns",
                message=t(
                    "No linked turns were detected, so turn-by-turn "
                    "checkpoints are not scored. Film several linked turns.",
                    lang=lang,
                ),
                severity="warn",
            )
        )
    elif pack.turn_count < MIN_TURNS_ADVISED:
        issues.append(
            FilmingIssue(
                code="too_few_turns",
                message=t(
                    "Only {count} turns were detected; film at least 8 linked "
                    "turns for a rhythm score.",
                    lang=lang,
                    count=pack.turn_count,
                ),
                severity="warn",
            )
        )
    if pack.landmark_quality < 0.5:
        issues.append(
            FilmingIssue(
                code="low_landmark_quality",
                message=t(
                    "The skeleton is weak in this clip: get closer, keep the "
                    "skier unoccluded, and avoid flat light.",
                    lang=lang,
                ),
                severity="warn" if pack.landmark_quality >= 0.2 else "blocker",
            )
        )
    if pack.usable_frame_ratio < 0.6:
        issues.append(
            FilmingIssue(
                code="few_usable_frames",
                message=t(
                    "Hips or ankles are missing in much of the clip.",
                    lang=lang,
                ),
                severity="warn",
            )
        )
    if len(analysis.frames) < SHORT_CLIP_FRAMES:
        issues.append(
            FilmingIssue(
                code="short_clip",
                message=t(
                    "The clip is too short to judge rhythm. Film a whole run "
                    "of at least eight turns.",
                    lang=lang,
                ),
                severity="warn",
            )
        )
    if classification.unusable_reason:
        issues.append(
            FilmingIssue(
                code=classification.unusable_reason,
                message=t(
                    "Stage cannot be judged when the shot is unstable, "
                    "occluded, or out of curriculum scope.",
                    lang=lang,
                ),
                severity="blocker",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# v2 fields
# ---------------------------------------------------------------------------


def _training_focus(
    rows: list[ScoredMetric],
    weakest_row: ScoredMetric | None,
    results: list[KeypointResult],
    lang: str,
) -> str:
    """What to train next, from the weakest measured gate metric (§10 bug list)."""
    if weakest_row is not None:
        report = weakest_row.report
        if report.standard:
            return t(
                "Train {name}: the standard is {standard}.",
                lang=lang,
                name=report.name,
                standard=report.standard,
            )
        return t("Train {name}.", lang=lang, name=report.name)
    failing = [item for item in results if item.status == KeypointStatus.FAIL]
    if failing:
        return failing[0].bad
    unmeasured = [row for row in rows if not row.measured]
    if unmeasured:
        return t(
            "Nothing could be measured for this stage in this clip; re-film "
            "before training to a number.",
            lang=lang,
        )
    return ""


def _how_to_advance(
    ready: bool,
    stage: LevelSpec,
    cur: Curriculum,
    weakest_row: ScoredMetric | None,
    lang: str,
) -> str:
    if ready:
        return t(
            "Passed this level. Choose a next level on the skill tree.",
            lang=lang,
        )
    names = [
        _text(cur.levels[nid].name, lang)
        for nid in stage.next_levels
        if nid in cur.levels
    ]
    if weakest_row is not None and names:
        return t(
            "Reach the standard on {name}, then move to {next}.",
            lang=lang,
            name=weakest_row.report.name,
            next=names[0],
        )
    if weakest_row is not None:
        return t(
            "Reach the standard on {name} to advance.",
            lang=lang,
            name=weakest_row.report.name,
        )
    return t(
        "Re-film this stage so its checkpoints can be measured.", lang=lang
    )


def _required_metric_ok(
    results: list[KeypointResult],
    stage: LevelSpec,
    cur: Curriculum,
) -> bool:
    """v2's ``_required_ok``, restricted to the metric-backed checkpoints.

    The v3 bundle still carries the v2 signal-backed checkpoint rows for the
    legacy levels, and their thresholds are on the denominators design §3.2
    replaced — ``cp_par_stance`` divides the stance by *hip width*, which
    collapses with view angle and reads a correct quarter-view stance as too
    wide. Letting those rows veto advancement would put the bug v3 exists to
    fix back into the advance rule, so they stay in chapter 5 as diagnosis and
    the metric-backed rows are the ones that gate. A level with no
    metric-backed checkpoint is gated by its gate metrics alone (design §6).
    """
    by_id = {item.id: item for item in results}
    for cid in stage.checkpoints:
        spec = cur.checkpoints[cid]
        if not spec.required or not spec.metric:
            continue
        item = by_id.get(cid)
        if item is None or item.score is None:
            continue
        if item.score < cur.checkpoint_pass:
            return False
    # No metric-backed checkpoint at all is not a failure: the gate metrics
    # carry the decision.
    return True


def _weakest_id(results: list[KeypointResult]) -> str:
    known = [item for item in results if item.score is not None]
    if not known:
        return results[0].id if results else ""
    return min(known, key=lambda item: item.score or 0.0).id


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
        t_ = (value - lo) / max(mid - lo, 1e-6)
        return round(60.0 * t_, 1)
    t_ = (value - mid) / max(hi - mid, 1e-6)
    return round(60.0 + 40.0 * t_, 1)


def _eval_checkpoint(
    spec: CheckpointSpec,
    legacy: FeaturePack,
    pack: MetricPack,
    cur: Curriculum,
    lang: str,
    *,
    level_id: str = "",
    age_band: str | None = None,
) -> KeypointResult:
    """One checkpoint row.

    v2 rows read a ``signal`` off the legacy ``FeaturePack``; v3 rows read a
    ``metric`` off the new catalog (``CheckpointSpec.one_measurement_source``
    guarantees exactly one of the two). A metric-backed row also carries the
    *N of M* evidence for count-form gates.

    **Count-form metrics are scored by their band, not by the checkpoint's
    fixed threshold** (design §6.1). The curriculum phrases these gates as
    "20 consecutive turns, at most 2 faulty", so the allowance is proportional
    — ``max(min_allowance, ceil(ratio * total))`` — and a six-turn clip must not
    inherit an allowance sized for twenty. Feeding the raw faulty count to
    ``_continuous_score`` against the absolute checkpoint number did exactly
    that, and disagreed with the band the chapter-3 rubric already uses. The
    continuous path is untouched.
    """
    faulty: int | None = None
    total: int | None = None
    allowance: int | None = None
    evaluation: Evaluation | None = None
    score: float | None = None
    if spec.metric:
        item = pack.get(spec.metric)
        value = None if item is None or item.state != "ok" else item.value
        if item is not None and item.form == "C":
            band = band_for(level_id, spec.metric, age_band)
            evaluation = evaluate(band, item)
            faulty = (
                evaluation.faulty_turns
                if evaluation.faulty_turns is not None
                else item.faulty_turns
            )
            total = (
                evaluation.total_turns
                if evaluation.total_turns is not None
                else item.total_turns
            )
            allowance = evaluation.allowance
            if allowance is None and spec.threshold.op == "lte":
                allowance = int(spec.threshold.value)
        evidence_from_metric = (
            None if item is None or item.evidence_ms is None else float(item.evidence_ms)
        )
    else:
        value = signal_value(legacy, spec.signal or "")
        evidence_from_metric = None
    if evaluation is not None:
        score = evaluation.score
        if score is None:
            status = KeypointStatus.UNKNOWN
        else:
            status = (
                KeypointStatus.PASS
                if evaluation.passing
                else KeypointStatus.FAIL
            )
    elif value is None:
        status = KeypointStatus.UNKNOWN
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
        evidence = evidence_from_metric
        if evidence is None:
            evidence = _evidence_ms(
                spec, legacy, passing=status == KeypointStatus.PASS
            )
        if evidence is None and legacy.series:
            evidence = legacy.series[0].t_ms
    return KeypointResult(
        id=spec.id,
        name=_text(spec.name, lang),
        status=status,
        score=score,
        value=value,
        evidence_ms=evidence,
        good=_text(spec.desc, lang),
        bad=_text(spec.desc, lang),
        drills=drills,
        metric_id=spec.metric or "",
        faulty_turns=faulty,
        total_turns=total,
        allowance=allowance,
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
    signal = spec.signal or ""
    instant = []
    for sample in pack.series:
        value = _sample_signal(sample, signal)
        if value is None:
            continue
        instant.append((sample.t_ms, _continuous_score(value, spec.threshold)))
    if instant:
        if passing:
            return max(instant, key=lambda row: row[1])[0]
        return min(instant, key=lambda row: row[1])[0]
    if signal in {"turn_freq", "fall_line"}:
        scored = [
            (s.t_ms, abs((s.hip_x or 0.0) - pack.hip_x_mean))
            for s in pack.series
            if s.hip_x is not None
        ]
        if not scored:
            return pack.series[0].t_ms
        return max(scored, key=lambda row: row[1])[0]
    if signal in {"knee_flex_freq", "knee_flex_amp"}:
        scored = [
            (s.t_ms, s.knee_flex)
            for s in pack.series
            if s.knee_flex is not None
        ]
        if not scored:
            return pack.series[0].t_ms
        return max(scored, key=lambda row: row[1] or 0.0)[0]
    if signal == "stance_width_std":
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
        if cid in cur.checkpoints
        and cur.checkpoints[cid].required
        and cur.checkpoints[cid].signal
    ]
    points: list[FrameScorePoint] = []
    for sample in pack.series:
        scores: list[float] = []
        for spec in specs:
            value = _sample_signal(sample, spec.signal or "")
            if value is None:
                value = signal_value(pack, spec.signal or "")
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
        "name": _text(venue.name, lang),
        "desc": _text(venue.desc, lang),
        "tips": _text(venue.tips, lang),
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
        "title": _text(drill.name, lang),
        "name": _text(drill.name, lang),
        "desc": _text(drill.desc, lang),
        "steps": [_text(row, lang) for row in drill.training],
        "training": [_text(row, lang) for row in drill.training],
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
        "level_name": _text(stage.name, lang),
        "drills": drills,
        "venues": venues,
    }


# ---------------------------------------------------------------------------
# unusable clips
# ---------------------------------------------------------------------------


def _unusable_report(
    clip_id: str,
    cur: Curriculum,
    lang: str,
    legacy: FeaturePack,
    pack: MetricPack,
    turns: list[Turn],
    classification: Classification,
    scene: SceneSummary,
    profile: ProfileSummary,
    filming: list[FilmingIssue],
    history: StageHistory,
) -> StageReport:
    """No stage is asserted: the filming chapter carries the report instead.

    ``classification.unusable_reason`` says which gate failed. **No metric rows
    are emitted**: the ordered core-metric set is a property of a stage, and
    without a stage there is no set to order, so chapter 3 is empty here by
    construction rather than filled with 36 ``unknown`` rows in arbitrary
    order. The "what could not be measured" story is carried by the filming
    chapter (``filming``) plus ``scene.missing``, which is where a client
    should render it.
    """
    drill = cur.drills[cur.sys_drill]
    payload = _drill_payload(drill, cur, lang)
    if classification.method != "unusable":
        classification = Classification(
            method="unusable",
            confidence=0.0,
            unusable_reason=classification.unusable_reason or "out_of_scope",
            candidates=classification.candidates,
        )
    if not any(item.severity == "blocker" for item in filming):
        filming.append(
            FilmingIssue(
                code=classification.unusable_reason or "unusable",
                message=t(
                    "Stage cannot be judged when the shot is unstable, "
                    "occluded, or out of curriculum scope.",
                    lang=lang,
                ),
                severity="blocker",
            )
        )
    return StageReport(
        clip_id=clip_id,
        category_id=SYS_CATEGORY,
        stage_id=UNKNOWN,
        category_name=_text("Unknown", lang),
        stage_name=_text("Re-film", lang),
        confidence=max(0.0, min(pack.landmark_quality, 0.34)),
        ready_for_next_stage=False,
        disclaimer=_text(cur.disclaimer, lang),
        stage_focus=_text(
            "Unstable camera, occlusion, or out-of-scope terrain: no stage "
            "claim.",
            lang,
        ),
        training_focus=_text(
            "Stable follow-cam, one skier, side or rear-quarter.", lang
        ),
        how_to_advance=_text(
            "Re-film this stage so its checkpoints can be measured.", lang
        ),
        weakest_checkpoint_id="KP-SYS-01",
        film_steps=[_text(row, lang) for row in drill.training],
        keypoints=[
            KeypointResult(
                id="KP-SYS-01",
                name=_text(drill.name, lang),
                status=KeypointStatus.UNKNOWN,
                value=None,
                good=_text(drill.name, lang),
                bad=_text(
                    "Stage cannot be judged when the shot is unstable, "
                    "occluded, or out of curriculum scope.",
                    lang,
                ),
                drills=[payload],
            )
        ],
        posture=posture_scores(legacy, []),
        classification=classification,
        turns=_turn_summary(pack, turns),
        tree=build_tree(
            cur,
            "",
            history,
            pack.athlete,
            lang=lang,
            name_for=_namer(cur, lang),
        ),
        scene=scene,
        profile_summary=profile,
        filming=filming,
    )
