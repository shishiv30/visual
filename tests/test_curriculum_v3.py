"""v3 stage model: double-entry checks against the design doc tables.

The expected values here are transcribed from
``docs/superpowers/specs/2026-08-30-ski-report-v3-design.md`` §1.2, §3.4 and §4.
They are deliberately a second copy of the spec: if the catalog and this file
disagree, one of them has drifted from the doc.
"""

from __future__ import annotations

import json

from core.sports.curriculum import CURRICULUM_V3_PATH, Curriculum
from core.sports.knowledge import KNOWLEDGE_DIR, load_kb, metric_ids
from core.sports.ski_expert import accept_curriculum

# --- design doc §3.4 -------------------------------------------------------
SCORED_METRICS = {
    "stance_width",
    "stance_width_var",
    "wedge_angle",
    "ski_wedge_angle",
    "ski_parallelism",
    "shin_angle_fore_aft",
    "hip_over_foot",
    "com_vertical_travel",
    "edge_angle_proxy",
    "inclination",
    "angulation",
    "banking_index",
    "separation_angle",
    "upper_body_quiet",
    "knee_valgus",
    "turn_rate",
    "turn_duration_var",
    "turn_amplitude",
    "turn_shape_index",
    "edge_change_duration",
    "flexion_range",
    "flexion_rate",
    "pressure_peak_phase",
    "stem_count",
    "backseat_count",
    "rotation_count",
    "braking_count",
    "asymmetry_index",
    "hands_in_view",
    "pole_touch_rate",
    "pole_touch_timing",
}
QUALITY_METRICS = {
    "view_azimuth_deg",
    "view_class",
    "landmark_quality",
    "usable_frame_ratio",
    "camera_motion",
    "fps_effective",
    "turn_count",
}
ALL_METRICS = SCORED_METRICS | QUALITY_METRICS

# --- design doc §1.2: id -> (name, kb_stage, tier, category, terrain, next)
LADDER: dict[str, tuple[str, str, str, str, str, list[str]]] = {
    "first_slide": (
        "First slide and equipment",
        "st-01",
        "catalog",
        "alpine_piste",
        "green",
        ["pizza_glide"],
    ),
    "pizza_glide": (
        "Wedge glide",
        "st-02",
        "full",
        "alpine_piste",
        "green",
        ["pizza"],
    ),
    "pizza": ("Wedge turns", "st-03", "full", "alpine_piste", "green", ["sideslip", "mogul_wedge"]),
    "mogul_wedge": (
        "Wedge mogul run",
        "st-13",
        "scene",
        "alpine_moguls",
        "mogul",
        ["mogul_absorb"],
    ),
    "sideslip": (
        "Sideslip and edge release",
        "st-04",
        "full",
        "alpine_piste",
        "green",
        ["wedge_christie"],
    ),
    "wedge_christie": (
        "Wedge christie",
        "st-05",
        "full",
        "alpine_piste",
        "green",
        ["parallel"],
    ),
    "parallel": (
        "Parallel skiing",
        "st-06",
        "full",
        "alpine_piste",
        "blue",
        ["dynamic_parallel"],
    ),
    "dynamic_parallel": (
        "Dynamic parallel: rhythm and poles",
        "st-07",
        "full",
        "alpine_piste",
        "blue",
        ["skid_short", "carve_long", "firm_snow"],
    ),
    "firm_snow": (
        "Firm snow and ice",
        "st-08",
        "scene",
        "alpine_piste",
        "blue",
        ["skid_short", "carve_long"],
    ),
    "skid_short": (
        "Short skidded turns",
        "st-09",
        "full",
        "alpine_piste",
        "blue",
        ["mogul_wedge", "steeps"],
    ),
    "carve_long": (
        "Long-radius carve",
        "st-10",
        "full",
        "alpine_piste",
        "blue",
        ["carve_medium"],
    ),
    "carve_medium": (
        "Medium-radius carve",
        "st-10",
        "full",
        "alpine_piste",
        "red",
        ["carve_short"],
    ),
    "carve_short": (
        "Short-radius carve",
        "st-11",
        "full",
        "alpine_piste",
        "red",
        [],
    ),
    "steeps": ("Steeps", "st-12", "scene", "alpine_piste", "black", ["powder"]),
    "mogul_absorb": (
        "Mogul absorption",
        "st-13",
        "scene",
        "alpine_moguls",
        "mogul",
        ["mogul_fallline"],
    ),
    "mogul_fallline": (
        "Mogul fall-line",
        "st-13",
        "scene",
        "alpine_moguls",
        "black",
        ["powder"],
    ),
    "powder": (
        "Powder and soft snow",
        "st-14",
        "scene",
        "alpine_offpiste",
        "offpiste",
        ["trees"],
    ),
    "trees": (
        "Crud, trees and complex terrain",
        "st-15",
        "catalog",
        "alpine_offpiste",
        "offpiste",
        ["specialization"],
    ),
    "specialization": (
        "Specialization and self-coaching",
        "st-16",
        "catalog",
        "alpine_piste",
        "any",
        [],
    ),
}
RETAINED_CATALOG = ("ollie", "park", "gates", "switch")

# --- design doc §4: id -> (core_metrics, gate_metrics) --------------------
_CARVE_LONG_CORE = [
    "edge_angle_proxy",
    "banking_index",
    "angulation",
    "turn_shape_index",
    "stance_width",
    "asymmetry_index",
]
_CARVE_LONG_GATES = ["edge_angle_proxy", "banking_index", "turn_shape_index"]
_MOGUL_CORE = [
    "flexion_range",
    "flexion_rate",
    "com_vertical_travel",
    "upper_body_quiet",
    "hands_in_view",
]
_MOGUL_GATES = ["flexion_range", "com_vertical_travel", "upper_body_quiet"]

STAGE_METRICS: dict[str, tuple[list[str], list[str]]] = {
    "pizza_glide": (
        [
            "stance_width",
            "wedge_angle",
            "shin_angle_fore_aft",
            "knee_valgus",
            "hip_over_foot",
        ],
        ["stance_width", "wedge_angle", "hip_over_foot"],
    ),
    "pizza": (
        [
            "turn_rate",
            "turn_amplitude",
            "stance_width",
            "wedge_angle",
            "separation_angle",
            "turn_shape_index",
            "asymmetry_index",
        ],
        ["stance_width", "wedge_angle", "turn_rate", "turn_shape_index", "asymmetry_index"],
    ),
    "sideslip": (
        [
            "edge_angle_proxy",
            "upper_body_quiet",
            "com_vertical_travel",
            "flexion_range",
            "hip_over_foot",
        ],
        ["edge_angle_proxy", "upper_body_quiet"],
    ),
    "wedge_christie": (
        ["wedge_angle", "stance_width_var", "knee_valgus", "separation_angle"],
        ["wedge_angle", "stance_width_var"],
    ),
    "parallel": (
        [
            "stem_count",
            "stance_width",
            "turn_shape_index",
            "hip_over_foot",
            "banking_index",
            "hands_in_view",
            "backseat_count",
        ],
        ["stem_count", "turn_shape_index", "hip_over_foot"],
    ),
    "dynamic_parallel": (
        [
            "flexion_range",
            "com_vertical_travel",
            "pressure_peak_phase",
            "pole_touch_rate",
            "pole_touch_timing",
            "turn_duration_var",
        ],
        ["pressure_peak_phase", "pole_touch_rate", "turn_duration_var"],
    ),
    "firm_snow": (
        [
            "edge_angle_proxy",
            "edge_change_duration",
            "turn_shape_index",
            "braking_count",
            "upper_body_quiet",
        ],
        ["edge_change_duration", "braking_count"],
    ),
    "skid_short": (
        [
            "turn_rate",
            "turn_duration_var",
            "separation_angle",
            "flexion_range",
            "pole_touch_rate",
            "upper_body_quiet",
        ],
        ["turn_rate", "turn_duration_var", "separation_angle"],
    ),
    "carve_long": (_CARVE_LONG_CORE, _CARVE_LONG_GATES),
    "carve_medium": (
        [*_CARVE_LONG_CORE, "turn_rate"],
        [*_CARVE_LONG_GATES, "turn_rate"],
    ),
    "carve_short": (
        [*_CARVE_LONG_CORE, "turn_rate", "edge_change_duration", "separation_angle"],
        [*_CARVE_LONG_GATES, "turn_rate", "edge_change_duration"],
    ),
    "steeps": (
        [
            "turn_rate",
            "edge_change_duration",
            "separation_angle",
            "com_vertical_travel",
            "braking_count",
        ],
        ["separation_angle", "braking_count"],
    ),
    "mogul_wedge": (
        ["flexion_range", "com_vertical_travel", "upper_body_quiet", "hands_in_view"],
        ["flexion_range", "com_vertical_travel"],
    ),
    "mogul_absorb": (_MOGUL_CORE, _MOGUL_GATES),
    "mogul_fallline": (
        [*_MOGUL_CORE, "turn_rate", "pressure_peak_phase"],
        [*_MOGUL_GATES, "turn_rate"],
    ),
    "powder": (
        [
            "stance_width",
            "com_vertical_travel",
            "flexion_rate",
            "turn_shape_index",
            "asymmetry_index",
        ],
        ["com_vertical_travel", "turn_shape_index"],
    ),
}

ADAPTATION_IDS = (
    "age-3-6",
    "age-7-12",
    "age-13-17",
    "age-18-39",
    "age-40-59",
    "age-60plus",
    "phys-female-adult",
    "phys-male-adult",
    "sp-heavier-skier",
)
CARVING_LEVELS = ("carve_long", "carve_medium", "carve_short")


def _bundle() -> Curriculum:
    return Curriculum.model_validate_json(
        CURRICULUM_V3_PATH.read_text(encoding="utf-8")
    )


def test_v3_bundle_loads_and_expert_accepts() -> None:
    bundle = _bundle()
    assert bundle.schema_version == "3.0.0"
    assert accept_curriculum(bundle) == []


def test_exclusion_rules_are_declared() -> None:
    bundle = _bundle()
    assert len(bundle.exclusion_rules) >= 1
    rule = bundle.exclusion_rules[0]
    assert rule.reason == "parallel_stance_detected"
    assert "pizza" in rule.reject_levels
    assert "stance_width_lte" in rule.when
    assert "wedge_angle_lte" in rule.when


def test_metric_catalog_matches_design_doc() -> None:
    catalog = json.loads(
        (KNOWLEDGE_DIR / "metrics.json").read_text(encoding="utf-8")
    )
    assert set(catalog) == ALL_METRICS
    assert metric_ids() == frozenset(ALL_METRICS)
    for mid in SCORED_METRICS:
        assert catalog[mid]["scored"] is True, mid
    for mid in QUALITY_METRICS:
        assert catalog[mid]["scored"] is False, mid


def test_every_level_has_kb_stage_and_tier() -> None:
    for lid, spec in _bundle().levels.items():
        assert spec.kb_stage, lid
        assert spec.tier in {"full", "scene", "catalog"}, lid


def test_ladder_matches_design_doc_table() -> None:
    bundle = _bundle()
    assert set(bundle.levels) == set(LADDER) | set(RETAINED_CATALOG)
    for lid, (name, kb_stage, tier, category, terrain, nxt) in LADDER.items():
        spec = bundle.levels[lid]
        assert spec.name.en == name, lid
        assert spec.kb_stage == kb_stage, lid
        assert spec.tier == tier, lid
        assert spec.category_id == category, lid
        assert spec.terrain == terrain, lid
        assert spec.next_levels == nxt, lid
    for lid in RETAINED_CATALOG:
        spec = bundle.levels[lid]
        assert spec.tier == "catalog", lid
        assert spec.in_scope is False, lid
        assert spec.next_levels == [], lid


def test_core_and_gate_metrics_match_design_doc() -> None:
    bundle = _bundle()
    for lid, (core, gates) in STAGE_METRICS.items():
        spec = bundle.levels[lid]
        assert spec.core_metrics == core, lid
        assert spec.gate_metrics == gates, lid


def test_metric_ids_are_real_and_gates_subset_of_core() -> None:
    for lid, spec in _bundle().levels.items():
        for mid in spec.core_metrics:
            assert mid in ALL_METRICS, f"{lid} {mid}"
            assert mid in SCORED_METRICS, f"{lid} {mid} is never scored"
        for mid in spec.gate_metrics:
            assert mid in ALL_METRICS, f"{lid} {mid}"
        assert set(spec.gate_metrics) <= set(spec.core_metrics), lid


def test_catalog_levels_carry_no_metrics_scene_levels_need_a_fact() -> None:
    for lid, spec in _bundle().levels.items():
        if spec.tier == "catalog":
            assert spec.core_metrics == [], lid
            assert spec.gate_metrics == [], lid
            assert spec.checkpoints == [], lid
        if spec.tier == "scene":
            assert spec.requires_scene, lid
            for token in spec.requires_scene:
                assert token.split(":", 1)[0] in {"snow_surface", "slope_band", "terrain_type"}, lid
        else:
            assert spec.requires_scene == [], lid


def test_requires_scene_matches_the_scene_module() -> None:
    # A plain import on purpose: this is a drift test, so an ImportError in the
    # module under test is the failure it exists to catch, not a reason to skip.
    from core.sports import scene

    bundle = _bundle()
    assert bundle.levels["firm_snow"].requires_scene == list(
        scene.REQUIRES_FIRM_SNOW
    )
    assert bundle.levels["steeps"].requires_scene == list(scene.REQUIRES_STEEPS)
    assert bundle.levels["powder"].requires_scene == list(scene.REQUIRES_POWDER)


def test_metric_catalog_matches_the_runtime_registry() -> None:
    from core.sports import metrics as runtime

    catalog = json.loads(
        (KNOWLEDGE_DIR / "metrics.json").read_text(encoding="utf-8")
    )
    assert set(runtime.metric_ids(include_sides=False)) == set(catalog)
    for spec in runtime.REGISTRY:
        assert catalog[spec.id]["scored"] == spec.scored, spec.id


def test_tree_targets_exist_and_have_no_cycles() -> None:
    bundle = _bundle()
    for lid, spec in bundle.levels.items():
        for nid in spec.next_levels:
            assert nid in bundle.levels, f"{lid} -> {nid}"
    state: dict[str, int] = {}

    def walk(node: str) -> None:
        if state.get(node) == 2:
            return
        assert state.get(node) != 1, f"cycle at {node}"
        state[node] = 1
        for nid in bundle.levels[node].next_levels:
            walk(nid)
        state[node] = 2

    for lid in bundle.levels:
        walk(lid)


def test_every_in_scope_level_is_reachable_from_first_slide() -> None:
    bundle = _bundle()
    seen: set[str] = set()
    stack = ["first_slide"]
    while stack:
        lid = stack.pop()
        if lid in seen:
            continue
        seen.add(lid)
        stack.extend(bundle.levels[lid].next_levels)
    for lid, spec in bundle.levels.items():
        if spec.in_scope:
            assert lid in seen, f"{lid} unreachable from first_slide"
    # the whole 16-stage ladder is reachable, catalog bookends included
    assert set(LADDER) <= seen


def test_prerequisites_resolve() -> None:
    bundle = _bundle()
    for lid, spec in bundle.levels.items():
        for pid in spec.prerequisites.levels:
            assert pid in bundle.levels, f"{lid} prereq level {pid}"
        for cid in spec.prerequisites.checkpoints:
            assert cid in bundle.checkpoints, f"{lid} prereq checkpoint {cid}"
    assert bundle.levels["first_slide"].prerequisites.levels == []
    assert bundle.levels["pizza"].prerequisites.levels == ["pizza_glide"]


def test_carving_is_not_applicable_below_age_13() -> None:
    bundle = _bundle()
    for lid in CARVING_LEVELS:
        notes = {row.id: row for row in bundle.levels[lid].profile_notes}
        assert set(notes) == set(ADAPTATION_IDS), lid
        for aid in ("age-3-6", "age-7-12"):
            assert notes[aid].status == "not_applicable", f"{lid} {aid}"
            assert notes[aid].note is not None, f"{lid} {aid} needs a reason"
        for aid in ("age-13-17", "age-18-39", "age-40-59", "age-60plus"):
            assert notes[aid].status == "applies", f"{lid} {aid}"


def test_profile_notes_cover_every_overlay_on_scored_levels() -> None:
    for lid, spec in _bundle().levels.items():
        if not spec.core_metrics:
            continue
        assert [row.id for row in spec.profile_notes] == list(ADAPTATION_IDS), lid
        for row in spec.profile_notes:
            assert row.status in {"applies", "not_applicable"}, lid
            if row.status == "not_applicable":
                assert row.note is not None, f"{lid} {row.id}"


def test_kb_refs_point_at_the_imported_pack() -> None:
    bundle = _bundle()
    kb = load_kb()
    level_map = kb["level_map"]
    modules = set(kb["modules"])
    for lid, spec in bundle.levels.items():
        assert spec.kb_refs.tutorial in kb["stages"], lid
        assert spec.kb_refs.tutorial == spec.kb_stage, lid
        assert spec.kb_refs.venue in modules, lid
        assert spec.kb_refs.equipment in modules, lid
        if lid in level_map:
            assert level_map[lid] == spec.kb_stage, lid
            stage = kb["stages"][spec.kb_stage]["en"]
            assert spec.kb_refs.drills == [row["id"] for row in stage["drills"]], lid
            assert spec.kb_refs.faults == [row["id"] for row in stage["faults"]], lid


def test_new_checkpoints_are_metric_backed_and_localized() -> None:
    bundle = _bundle()
    metric_cps = {
        cid: spec for cid, spec in bundle.checkpoints.items() if spec.metric
    }
    assert metric_cps, "expected v3 metric-backed checkpoints"
    for cid, spec in metric_cps.items():
        assert spec.signal is None, cid
        assert spec.metric in SCORED_METRICS, cid
        assert spec.name.zh and spec.name.zh != spec.name.en, cid
        assert spec.desc.zh and spec.desc.zh != spec.desc.en, cid
        assert spec.drills, cid
    # every gate metric of a new stage has a checkpoint that measures it
    for lid in ("sideslip", "dynamic_parallel", "firm_snow", "steeps", "powder"):
        spec = bundle.levels[lid]
        measured = {bundle.checkpoints[cid].metric for cid in spec.checkpoints}
        assert measured == set(spec.gate_metrics), lid


def test_new_levels_and_venues_are_localized() -> None:
    bundle = _bundle()
    for lid, spec in bundle.levels.items():
        assert spec.name.zh and spec.name.en, lid
        assert spec.desc.zh and spec.desc.en, lid
    offpiste = bundle.venues["venue_offpiste"]
    assert offpiste.terrain == "offpiste"
    assert bundle.terrains["offpiste"].name.zh
    assert "alpine_offpiste" in bundle.categories
    assert bundle.categories["alpine_offpiste"].zh
