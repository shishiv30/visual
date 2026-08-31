"""v2 ladder and v3 assessment on the same curriculum bundle.

The ``classify`` tests below run the **legacy** ladder (``classify`` is an alias
for ``core.sports.classify.classify_legacy``) on the original static skeletons,
unchanged, so the v2 behaviour stays pinned.

The ``assess_clip`` tests run the **v3** pipeline, which reads turns, view
azimuth, edge angle and flexion — none of which a static skeleton has. They
therefore use the archetypes in ``core.sports.report_cases``: a skier that
actually travels and turns. The assertions are the same ones as before, on a
clip the v3 measurement layer can see.
"""

from __future__ import annotations

import numpy as np

from core.sports.assess import assess_clip, classify
from core.sports.curriculum import load_curriculum
from core.sports.scene import SceneContext, TerrainType
from core.sports.dtw import dtw_distance
from core.sports.history import StageHistory
from core.sports.report_cases import (
    CARVE,
    MOGUL,
    PARALLEL,
    PISTE_HISTORY,
    SIDESLIP,
    SKID_SHORT,
    WEDGE_GLIDE,
    WEDGE_TURNS,
    synth_clip,
)
from core.sports.signals import extract_features
from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)


def _empty_core() -> CoreInferenceResult:
    return CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=0.0,
            width=640,
            height=360,
        ),
        detections=[],
        poses=[],
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name="pose_landmarker_full.task",
            latency_ms=1.0,
            device="cpu",
        ),
        error=None,
    )


def _joints(
    *,
    hip_w: float = 40.0,
    stance: float = 1.5,
    knee_drop: float = 40.0,
    knee_in: float = 0.0,
    lean: float = 0.0,
    hip_x: float = 200.0,
) -> list[BlazeJoint]:
    mid = hip_x
    lh, rh = mid - hip_w / 2, mid + hip_w / 2
    ankle_span = hip_w * stance
    la, ra = mid - ankle_span / 2, mid + ankle_span / 2
    ls, rs = lh + lean * hip_w, rh + lean * hip_w
    pts = [(0.0, 0.0)] * 33
    pts[0] = (mid, 40.0)
    pts[11] = (ls, 80.0)
    pts[12] = (rs, 80.0)
    pts[15] = (ls, 140.0)
    pts[16] = (rs, 140.0)
    pts[23] = (lh, 160.0)
    pts[24] = (rh, 160.0)
    pts[25] = (lh + knee_in, 160.0 + knee_drop)
    pts[26] = (rh - knee_in, 160.0 + knee_drop)
    pts[27] = (la, 280.0)
    pts[28] = (ra, 280.0)
    pts[31] = (la, 300.0)
    pts[32] = (ra, 300.0)
    out: list[BlazeJoint] = []
    for i in range(33):
        x, y = pts[i]
        out.append(BlazeJoint(x=x, y=y, z=0.0, confidence=0.95))
    return out


def _clip(joints_seq: list[list[BlazeJoint]], clip_id: str = "c1") -> ClipAnalysis:
    frames = [
        AnalyzedFrame(t_ms=i * 66.0, result=_empty_core(), blaze33=joints)
        for i, joints in enumerate(joints_seq)
    ]
    return ClipAnalysis(
        clip_id=clip_id, fps=15.0, frame_count=len(frames), frames=frames
    )


def _piste_history() -> StageHistory:
    """A skier who has passed the piste spine up to dynamic parallel."""
    return StageHistory.from_reports(
        [
            {
                "stage_id": level_id,
                "ready_for_next_stage": True,
                "score_0_100": 88.0,
                "keypoints": [],
            }
            for level_id in PISTE_HISTORY
        ]
    )


def test_curriculum_loads() -> None:
    cur = load_curriculum()
    # v3 is the runtime bundle now (design doc §1.2): the ladder gained
    # sideslip, dynamic_parallel, firm_snow, steeps and powder, so `parallel`
    # routes to `dynamic_parallel` and the branches open one rung later.
    assert cur.schema_version == "3.0.0"
    assert "alpine_piste" in cur.categories
    assert "alpine_moguls" in cur.categories
    assert "alpine_offpiste" in cur.categories
    assert cur.level_ids[0] == "pizza_glide"
    assert cur.levels["pizza"].next_levels == ["sideslip", "mogul_wedge"]
    assert cur.levels["parallel"].next_levels == ["dynamic_parallel"]
    assert cur.levels["dynamic_parallel"].next_levels == [
        "skid_short",
        "carve_long",
        "firm_snow",
    ]
    assert cur.levels["skid_short"].next_levels == ["mogul_wedge", "steeps"]
    assert cur.levels["pizza_glide"].terrain == "green"
    assert cur.levels["parallel"].gate_metrics == [
        "stem_count",
        "turn_shape_index",
        "hip_over_foot",
    ]
    assert cur.levels["firm_snow"].tier == "scene"
    assert cur.levels["first_slide"].tier == "catalog"
    assert "venue_green_groomer" in cur.venues
    assert cur.drills["drill_hockey"].venue_ids
    assert "drill_hockey" in cur.checkpoints["cp_sk_hockey"].drills
    assert "drill_one_ski" in cur.checkpoints["cp_cv_oneski"].drills


def test_pizza_glide_from_wide_stance() -> None:
    seq = [_joints(stance=1.8, knee_drop=50.0) for _ in range(8)]
    pack = extract_features(_clip(seq))
    cat, stage, conf = classify(pack)
    assert cat == "alpine_piste"
    assert stage == "pizza_glide"
    assert conf >= 0.35
    clip = synth_clip(WEDGE_GLIDE, "glide")
    report = assess_clip(clip, lang="en")
    assert report.stage_id == "pizza_glide"
    assert report.stage_focus
    assert report.training_focus
    assert report.how_to_advance
    assert report.session_plan
    assert 0 <= report.score_0_100 <= 100
    ids = {k.id for k in report.keypoints}
    assert "cp_pg_stance" in ids
    duration = clip.frames[-1].t_ms
    for item in report.keypoints:
        if item.evidence_ms is not None:
            assert 0 <= item.evidence_ms <= duration
    assert report.terrain_id == "green"
    assert report.kb_stage == "st-02"
    assert report.tier == "full"
    assert report.score_series
    assert report.score_series[0].t_ms >= 0
    assert 0 <= report.score_series[0].score <= 100


def test_pizza_turns_from_wide_stance_with_path() -> None:
    seq = [
        _joints(stance=1.8, knee_drop=50.0, hip_x=180.0 + (i % 6) * 8.0)
        for i in range(12)
    ]
    cat, stage, _ = classify(extract_features(_clip(seq)))
    assert cat == "alpine_piste"
    assert stage == "pizza"
    report = assess_clip(synth_clip(WEDGE_TURNS, "pizza"), lang="en")
    assert report.stage_id == "pizza"
    ids = {k.id for k in report.keypoints}
    assert "cp_pz_stance" in ids
    assert report.turns is not None and report.turns.count >= 2


def test_parallel_not_pizza() -> None:
    seq = [_joints(stance=0.8, knee_drop=45.0) for _ in range(8)]
    cat, stage, _ = classify(extract_features(_clip(seq)))
    assert cat == "alpine_piste"
    assert stage == "parallel"


def test_carve_not_christie_when_lean_high_and_stance_varies() -> None:
    seq = [
        _joints(
            stance=0.92 + (i % 4) * 0.06,
            knee_drop=48.0,
            lean=0.4,
            hip_x=180.0 + (i % 6) * 10.0,
        )
        for i in range(16)
    ]
    cat, stage, _ = classify(extract_features(_clip(seq)))
    assert cat == "alpine_piste"
    assert stage in {"carve_long", "carve_medium", "carve_short"}
    seq = [
        _joints(stance=0.85, knee_drop=48.0, lean=0.35, hip_x=200.0 + (i % 8) * 2.0)
        for i in range(12)
    ]
    cat, stage, _ = classify(extract_features(_clip(seq)))
    assert cat == "alpine_piste"
    assert stage in {"carve_long", "carve_medium", "carve_short"}


def test_skid_low_score_points_at_hockey_drill() -> None:
    seq = [
        _joints(stance=0.9, knee_drop=45.0, hip_x=180.0 + (i % 4) * 18.0)
        for i in range(16)
    ]
    pack = extract_features(_clip(seq))
    cat, stage, _ = classify(pack)
    assert cat == "alpine_piste"
    assert stage == "skid_short"
    report = assess_clip(
        synth_clip(SKID_SHORT, "skid"), lang="en", history=_piste_history()
    )
    assert report.stage_id == "skid_short"
    assert report.ready_for_next_stage is False
    # The legacy `turn_freq` signal counts hip-x zero crossings, so it reads 0
    # on a skier who travels across the frame; the v3 `turn_rate` metric sees
    # the same turns correctly. That makes cp_sk_rhythm the weakest row.
    assert report.weakest_checkpoint_id == "cp_sk_rhythm"
    assert report.turns is not None and report.turns.count >= 4
    hockey = next(k for k in report.keypoints if k.id == "cp_sk_hockey")
    assert hockey.drills
    assert any(d.get("id") == "drill_hockey" for d in hockey.drills)
    assert hockey.evidence_ms is not None
    assert report.next_plans == []
    assert hockey.drills[0].get("venues")


def test_parallel_pass_offers_dynamic_parallel() -> None:
    report = assess_clip(synth_clip(PARALLEL, "par"), lang="en")
    assert report.stage_id == "parallel"
    assert report.ready_for_next_stage is True
    # v3 routes `parallel` to `dynamic_parallel`; the skid / carve fork moved
    # one rung up, to `dynamic_parallel` (design doc §1.2).
    assert report.next_level_ids == ["dynamic_parallel"]
    assert report.next_plans
    assert report.next_plans[0]["venues"]
    assert any(plan["drills"] for plan in report.next_plans)


def test_dynamic_parallel_is_the_fork() -> None:
    cur = load_curriculum()
    assert cur.levels["dynamic_parallel"].next_levels == [
        "skid_short",
        "carve_long",
        "firm_snow",
    ]


def test_glide_passes_banking_not_swept_at_wedge_stage() -> None:
    """``banking_index`` is in INJURY_RISK_METRICS but not in INJURY_RISK_SWEEP.

    On a wedge rung the index divides two noise-level angles, so it blocks
    advancement only where a stage names it as a core metric. pizza_glide does
    not list it, so every gate passes and the advance is allowed.
    """
    report = assess_clip(synth_clip(WEDGE_GLIDE, "glide-ok"), lang="en")
    assert report.stage_id == "pizza_glide"
    assert report.score_0_100 > 75.0
    assert report.ready_for_next_stage is True
    assert "pizza" in report.next_level_ids


def test_sideslip_is_reachable_between_pizza_and_christie() -> None:
    report = assess_clip(synth_clip(SIDESLIP, "sideslip"), lang="en")
    assert report.stage_id == "sideslip"
    assert report.kb_stage == "st-04"
    assert report.next_level_ids in ([], ["wedge_christie"])


def test_history_moves_a_carving_clip_off_parallel() -> None:
    """The §5 adjacency prior: a passed rung stops swallowing the next one."""
    clip = synth_clip(CARVE, "carve")
    without = assess_clip(clip, lang="en")
    with_history = assess_clip(clip, lang="en", history=_piste_history())
    assert without.stage_id == "parallel"
    assert with_history.stage_id == "carve_long"
    block = with_history.classification
    assert block is not None
    assert block.chosen_id == "carve_long"
    assert [c.stage_id for c in block.candidates][0] == "carve_long"
    assert block.candidates[1].separating_metric_id


def test_mogul_branch_needs_the_skid_rung() -> None:
    history = StageHistory.from_reports(
        [
            {
                "stage_id": level_id,
                "ready_for_next_stage": True,
                "score_0_100": 88.0,
                "keypoints": [],
            }
            for level_id in PISTE_HISTORY + ("mogul_wedge", "skid_short")
        ]
    )
    report = assess_clip(synth_clip(MOGUL, "mogul"), lang="en", history=history, scene=SceneContext(terrain_type=TerrainType.MOGUL))
    assert report.stage_id == "mogul_absorb"
    assert report.category_id == "alpine_moguls"
    assert report.terrain_id == "mogul"
    states = {node.id: node.state.value for node in report.tree}
    assert states["skid_short"] == "completed"
    assert states["mogul_absorb"] == "current"
    assert states["trees"] == "locked"


def test_mogul_absorption_stage() -> None:
    seq = []
    for i in range(16):
        seq.append(
            _joints(
                stance=0.85,
                knee_drop=40.0,
                knee_in=8.0 if i % 2 else 55.0,
                hip_x=200.0,
            )
        )
    cat, stage, conf = classify(extract_features(_clip(seq)))
    assert cat == "alpine_moguls"
    assert stage in {"mogul_absorb", "mogul_fallline"}
    assert conf >= 0.35


def test_mogul_beats_wide_stance_when_torso_shaken() -> None:
    """Real mogul clips often look wide + noisy upper body; still mogul."""
    seq = []
    for i in range(24):
        seq.append(
            _joints(
                stance=2.4,
                knee_drop=35.0,
                knee_in=5.0 if i % 2 else 70.0,
                lean=0.15 + (i % 5) * 0.08,
                hip_x=200.0 + (i % 3) * 4.0,
            )
        )
    pack = extract_features(_clip(seq, "mogul-wide"))
    assert pack.knee_flex_amp > 30.0
    assert pack.knee_flex_freq > 0.6
    cat, stage, conf = classify(pack)
    assert cat == "alpine_moguls"
    assert stage in {"mogul_absorb", "mogul_fallline"}
    assert conf >= 0.35
    report = assess_clip(_clip(seq, "mogul-wide"), lang="zh", scene=SceneContext(terrain_type=TerrainType.MOGUL))
    assert report.stage_id in {"mogul_absorb", "mogul_fallline"}
    assert report.terrain_id == "mogul"
    assert "雪包" in report.terrain_name or "mogul" in report.terrain_name.lower()


def test_green_piste_carve_not_mogul() -> None:
    """Groomed carve: moderate knee work + lean must stay alpine_piste."""
    seq = []
    for i in range(24):
        seq.append(
            _joints(
                stance=1.05,
                knee_drop=42.0 + (8.0 if i % 2 else 0.0),
                knee_in=4.0 if i % 2 else 18.0,
                lean=0.45,
                hip_x=200.0 + (i % 6) * 12.0,
            )
        )
    pack = extract_features(_clip(seq, "green-carve"))
    cat, stage, _ = classify(pack)
    assert cat == "alpine_piste"
    assert stage in {"carve_long", "carve_medium", "carve_short"}
    assert stage not in {"mogul_absorb", "mogul_fallline"}
    report = assess_clip(_clip(seq, "green-carve"), lang="zh")
    assert report.category_id == "alpine_piste"
    assert report.terrain_id in {"green", "blue", "red"}


def test_missing_feet_unknown_stance_point() -> None:
    seq = []
    for _ in range(8):
        joints = _joints(stance=1.8)
        for idx in (27, 28, 31, 32):
            joints[idx] = BlazeJoint(x=0.0, y=0.0, z=0.0, confidence=0.0)
        seq.append(joints)
    report = assess_clip(_clip(seq, "nofoot"), lang="en")
    stance = next((k for k in report.keypoints if k.id == "cp_pz_stance"), None)
    if report.stage_id == "pizza" and stance is not None:
        assert stance.status.value == "unknown"


def test_dtw_identical_is_zero() -> None:
    a = np.array([[0.0, 1.0], [1.0, 1.0], [2.0, 0.0]])
    assert dtw_distance(a, a) == 0.0
