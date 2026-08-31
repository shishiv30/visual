"""Recorded-fixture guard for ``assess_clip`` (design §10).

``assess`` exists three times — Python, ``Assess.swift``, ``Assess.kt`` — with no
shared fixtures, so a threshold change diverges silently between desktop and
phone. These files are the shared contract: each one holds a recorded
``ClipAnalysis`` input, the athlete/scene/history context, and the expected
``StageReport`` output.

The expected block is a **projection**, not a whole report: a full 3.0.0 report
carries every drill and venue of the stage and the next stage, which is tens of
kilobytes of curriculum content that the curriculum's own tests already cover.
What is recorded here is what the algorithm decides — stage, tier, score,
confidence, candidates and the separating metric, every metric's state / rubric
/ score, the count-form *N of M*, the turn tally, the tree states, the knowledge
selection, the filming codes and the profile effects. A port that reproduces
this block has reproduced the classifier and the scorer.

Regenerate after a deliberate threshold change with::

    python -m tests.test_assess_v3 --write

and read the diff: every changed number is a change in what the app tells a
skier.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from core.sports.assess import assess_clip
from core.sports.history import StageHistory
from core.sports.report_cases import (
    CARVE,
    PARALLEL,
    PISTE_HISTORY,
    PROFILE_VIEW,
    WEDGE_GLIDE,
    Skier,
    synth_clip,
)
from core.sports.report_cases import _empty_core as empty_core
from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.stage_report import StageReport

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "stage_report"

#: Absolute tolerance for a recorded score (0-100) and a recorded 0-1 quantity.
SCORE_TOL = 0.15
UNIT_TOL = 0.005

#: Nodes whose tree state every fixture records. Chosen to cover the branches:
#: the spine, the mogul branch, the off-piste branch and a catalog rung.
TREE_PROBES = (
    "pizza_glide",
    "parallel",
    "dynamic_parallel",
    "carve_long",
    "skid_short",
    "mogul_absorb",
    "powder",
    "trees",
    "first_slide",
)

#: A child, for whom the curriculum marks carving not applicable (§2.3).
CHILD = {
    "age_years": 9.0,
    "height_m": 1.35,
    "mass_kg": 30.0,
    "sex": "female",
    "ski_cm": 110.0,
}


def _short(skier: Skier, **kw: Any) -> Skier:
    """Ten frames a second: enough for the 2 Hz filter, small enough to read."""
    return replace(skier, fps=10.0, **kw)


CASES: dict[str, dict[str, Any]] = {
    "wedge_glide": {
        "skier": _short(WEDGE_GLIDE, frames=40),
        "note": "Wedge glide, no turns: the turn-form metrics stay unknown.",
    },
    "parallel_linked": {
        "skier": _short(PARALLEL, frames=70, turn_hz=0.3),
        "note": "Linked round parallel turns: stem and back-seat counts are 0 of N.",
    },
    "carve_with_history": {
        "skier": _short(CARVE, frames=70, turn_hz=0.3),
        "history": PISTE_HISTORY,
        "note": "High edge angle plus history: the adjacency prior picks carve_long.",
    },
    "profile_view": {
        "skier": _short(PROFILE_VIEW, frames=60, turn_hz=0.3),
        "note": "Filmed side-on: lateral metrics unknown, classification ambiguous.",
    },
    "child_carving_not_applicable": {
        "skier": _short(CARVE, frames=70, turn_hz=0.3),
        "athlete": CHILD,
        "note": "Age 9: banking_index is not_applicable, never a pass.",
    },
    "firm_snow_scene": {
        "skier": _short(CARVE, frames=70, turn_hz=0.3),
        "scene": {"snow_surface": "hardpack", "slope_band": "blue", "terrain_type": "piste"},
        "history": PISTE_HISTORY,
        "note": "Scene supplied: firm_snow becomes a candidate and nothing is missing.",
    },
}


# ---------------------------------------------------------------------------
# projection
# ---------------------------------------------------------------------------


def _round(value: float | None, places: int = 3) -> float | None:
    return None if value is None else round(float(value), places)


def project(report: StageReport) -> dict:
    """The part of a report a port has to reproduce."""
    block = report.classification
    focus = report.knowledge_focus
    tree = {node.id: node for node in report.tree}
    return {
        "stage_id": report.stage_id,
        "category_id": report.category_id,
        "kb_stage": report.kb_stage,
        "tier": report.tier,
        "terrain_id": report.terrain_id,
        "score_0_100": _round(report.score_0_100, 1),
        "confidence": _round(report.confidence),
        "ready_for_next_stage": report.ready_for_next_stage,
        "weakest_checkpoint_id": report.weakest_checkpoint_id,
        "next_level_ids": list(report.next_level_ids),
        "classification": None
        if block is None
        else {
            "method": block.method,
            "chosen_id": block.chosen_id,
            "ambiguous": block.ambiguous,
            "unusable_reason": block.unusable_reason,
            "separation": _round(block.separation),
            "quality_factor": _round(block.quality_factor),
            "candidates": [
                {
                    "stage_id": item.stage_id,
                    "score": _round(item.score),
                    "fit": _round(item.fit),
                    "gate_ratio": _round(item.gate_ratio),
                    "prior": _round(item.prior),
                    "separating_metric_id": item.separating_metric_id,
                    "rejected_reason": item.rejected_reason,
                }
                for item in block.candidates
            ],
        },
        "metrics": [
            {
                "id": row.id,
                "state": row.state.value,
                "rubric": row.rubric.value,
                "is_gate": row.is_gate,
                "form": row.form,
                "value": _round(row.value),
                "score": _round(row.score, 1),
                "reliability": _round(row.reliability, 2),
                "faulty_turns": row.faulty_turns,
                "total_turns": row.total_turns,
                "standard": row.standard,
                "reason": row.reason,
                "side": row.side,
                "left_value": _round(row.left_value),
                "right_value": _round(row.right_value),
            }
            for row in report.metrics
        ],
        "turns": None
        if report.turns is None
        else {
            "count": report.turns.count,
            "left_count": report.turns.left_count,
            "right_count": report.turns.right_count,
            "mean_duration_s": _round(report.turns.mean_duration_s, 2),
            "fault_counts": dict(report.turns.fault_counts),
            "flags": [list(item.flags) for item in report.turns.turns],
        },
        "tree": {
            probe: (tree[probe].state.value if probe in tree else None)
            for probe in TREE_PROBES
        },
        "tree_path": [node.id for node in report.tree_path],
        "knowledge": None
        if focus is None
        else {
            "fault_ids": list(focus.fault_ids),
            "drill_ids": list(focus.drill_ids),
            "skill_ids": list(focus.skill_ids),
            "weakest_metric_id": focus.weakest_metric_id,
        },
        "scene": None
        if report.scene is None
        else {
            "snow_surface": report.scene.snow_surface,
            "slope_band": report.scene.slope_band,
            "view_class": report.scene.view_class,
            "camera_motion": report.scene.camera_motion,
            "fps_effective": _round(report.scene.fps_effective, 2),
            "missing": list(report.scene.missing),
        },
        "profile_summary": None
        if report.profile_summary is None
        else {
            "age_band": report.profile_summary.age_band,
            "is_complete": report.profile_summary.is_complete,
            "overlays": list(report.profile_summary.overlays),
            "effect_count": len(report.profile_summary.effects),
        },
        "filming": [item.code for item in report.filming],
    }


# ---------------------------------------------------------------------------
# fixtures on disk
# ---------------------------------------------------------------------------


def fixture_path(case_id: str) -> Path:
    return FIXTURE_DIR / f"{case_id}.json"


#: The landmarks the v2 signal layer and the v3 catalog actually read: nose,
#: shoulders, elbows, wrists, hips, knees, ankles, heels, foot_index. The other
#: sixteen BlazePose points are never touched, so recording them would be 16
#: columns of noise in a file meant to be read by a human.
LANDMARK_IDS = (0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)
DEFAULT_CONF = 0.95


def encode_clip(clip: ClipAnalysis) -> dict:
    """Compact, human-readable encoding of a clip.

    A ``ClipAnalysis`` dumped as-is is ~250 KB per fixture: 33 landmarks a frame
    plus a per-frame ``CoreInferenceResult`` envelope that carries no pose
    information. §10 asks for recorded ``ClipAnalysis`` inputs and for fixtures
    that stay small and hand-checkable, and those pull in opposite directions,
    so what is recorded is the *pose* — one row per frame,
    ``[t_ms, x, y, x, y, ...]`` over :data:`LANDMARK_IDS`, one decimal place —
    and :func:`decode_clip` rebuilds the real ``ClipAnalysis`` from it. A port
    needs the same twenty-line decoder; the numbers it decodes are the contract.
    """
    rows: list[list[float]] = []
    for frame in clip.frames:
        row = [round(frame.t_ms, 1)]
        joints = frame.blaze33 or []
        for index in LANDMARK_IDS:
            joint = joints[index]
            row.append(round(joint.x, 1))
            row.append(round(joint.y, 1))
        rows.append(row)
    return {
        "clip_id": clip.clip_id,
        "fps": clip.fps,
        "frame_count": clip.frame_count,
        "scene": clip.scene,
        "athlete": clip.athlete,
        "confidence": DEFAULT_CONF,
        "landmark_ids": list(LANDMARK_IDS),
        "rows": rows,
    }


def decode_clip(block: dict) -> ClipAnalysis:
    """Rebuild a ``ClipAnalysis`` from :func:`encode_clip`'s output.

    Landmarks not listed carry confidence 0, which is how the measurement layer
    is told they are absent — never coordinate 0, which would be a fake point at
    the top-left corner.
    """
    ids = [int(value) for value in block["landmark_ids"]]
    conf = float(block.get("confidence", DEFAULT_CONF))
    frames: list[AnalyzedFrame] = []
    for row in block["rows"]:
        joints = [
            BlazeJoint(x=0.0, y=0.0, z=0.0, confidence=0.0) for _ in range(33)
        ]
        for position, index in enumerate(ids):
            joints[index] = BlazeJoint(
                x=float(row[1 + 2 * position]),
                y=float(row[2 + 2 * position]),
                z=0.0,
                confidence=conf,
            )
        frames.append(
            AnalyzedFrame(
                t_ms=float(row[0]), result=empty_core(), blaze33=joints
            )
        )
    return ClipAnalysis(
        clip_id=str(block["clip_id"]),
        fps=float(block["fps"]),
        frame_count=len(frames),
        frames=frames,
        scene=block.get("scene"),
        athlete=block.get("athlete"),
    )


def build_fixture(case_id: str) -> dict:
    case = CASES[case_id]
    clip = synth_clip(
        case["skier"],
        clip_id=f"fx-{case_id}",
        scene=case.get("scene"),
        athlete=case.get("athlete"),
    )
    block = encode_clip(clip)
    # Assess the *decoded* clip, so the recorded expectation belongs to the
    # recorded (rounded) numbers rather than to the generator's full precision.
    report = assess_clip(
        decode_clip(block), lang="en", history=_history(case.get("history"))
    )
    return {
        "case_id": case_id,
        "note": case["note"],
        "passed_levels": list(case.get("history") or ()),
        "clip": block,
        "expected": project(report),
    }


def _history(levels: tuple[str, ...] | None) -> StageHistory:
    return StageHistory.from_reports(
        [
            {
                "stage_id": level_id,
                "ready_for_next_stage": True,
                "score_0_100": 88.0,
                "keypoints": [],
            }
            for level_id in levels or ()
        ]
    )


def load_fixture(case_id: str) -> dict:
    return json.loads(fixture_path(case_id).read_text(encoding="utf-8"))


def actual(case_id: str) -> dict:
    """Assess the fixture's *recorded input* and project the result.

    Every property test below used to read ``load_fixture(case_id)["expected"]``
    and so asserted things about a JSON file rather than about the code: the
    file would have had to be hand-edited for one of them to fail. They run the
    pipeline instead, and
    :func:`test_recorded_input_reproduces_recorded_report` remains the guard
    that ties what the pipeline produces to what is recorded.
    """
    fixture = load_fixture(case_id)
    return project(
        assess_clip(
            decode_clip(fixture["clip"]),
            lang="en",
            history=_history(tuple(fixture["passed_levels"])),
        )
    )


def write_fixtures() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for case_id in CASES:
        payload = build_fixture(case_id)
        fixture_path(case_id).write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------


def _diff(expected: Any, actual: Any, path: str, out: list[str]) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            out.append(f"{path}: expected an object, got {type(actual).__name__}")
            return
        for key in expected:
            if key not in actual:
                out.append(f"{path}.{key}: missing")
                continue
            _diff(expected[key], actual[key], f"{path}.{key}", out)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list):
            out.append(f"{path}: expected a list, got {type(actual).__name__}")
            return
        if len(expected) != len(actual):
            out.append(f"{path}: length {len(actual)} != {len(expected)}")
            return
        for index, (want, got) in enumerate(zip(expected, actual)):
            _diff(want, got, f"{path}[{index}]", out)
        return
    if isinstance(expected, bool) or expected is None:
        if expected != actual:
            out.append(f"{path}: {actual!r} != {expected!r}")
        return
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        tol = SCORE_TOL if abs(expected) > 1.5 else UNIT_TOL
        if abs(float(expected) - float(actual)) > tol:
            out.append(f"{path}: {actual!r} != {expected!r}")
        return
    if expected != actual:
        out.append(f"{path}: {actual!r} != {expected!r}")


def compare(expected: dict, actual: dict) -> list[str]:
    out: list[str] = []
    _diff(expected, actual, "expected", out)
    return out


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_fixture_file_exists(case_id: str) -> None:
    path = fixture_path(case_id)
    assert path.is_file(), (
        f"missing fixture {path}; regenerate with "
        f"`python -m tests.test_assess_v3 --write`"
    )


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_recorded_input_reproduces_recorded_report(case_id: str) -> None:
    fixture = load_fixture(case_id)
    clip = decode_clip(fixture["clip"])
    report = assess_clip(
        clip, lang="en", history=_history(tuple(fixture["passed_levels"]))
    )
    issues = compare(fixture["expected"], project(report))
    assert issues == [], f"{case_id}: " + "; ".join(issues[:8])


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_generator_still_produces_the_recorded_input(case_id: str) -> None:
    """The archetypes and the recorded inputs must not drift apart."""
    fixture = load_fixture(case_id)
    rebuilt = build_fixture(case_id)
    assert rebuilt["clip"]["rows"] == fixture["clip"]["rows"]


def test_every_metric_state_is_covered_by_the_fixtures() -> None:
    """ok / unknown / not_applicable must each appear in at least one fixture."""
    seen: set[str] = set()
    for case_id in CASES:
        for row in actual(case_id)["metrics"]:
            seen.add(row["state"])
    assert {"ok", "unknown", "not_applicable"} <= seen


def test_unmeasured_metrics_never_carry_a_number_or_a_rubric() -> None:
    for case_id in CASES:
        for row in actual(case_id)["metrics"]:
            if row["state"] == "ok":
                continue
            assert row["score"] is None, f"{case_id}/{row['id']} scored"
            assert row["value"] is None, f"{case_id}/{row['id']} valued"
            assert row["rubric"] == "not_rated", f"{case_id}/{row['id']} rated"
            assert row["reason"], f"{case_id}/{row['id']} has no reason"


def test_count_metrics_record_n_of_m_and_an_allowance() -> None:
    found = 0
    for case_id in CASES:
        for row in actual(case_id)["metrics"]:
            if row["form"] != "C" or row["state"] != "ok":
                continue
            found += 1
            assert row["total_turns"], f"{case_id}/{row['id']} has no total"
            assert row["faulty_turns"] is not None
            assert "at most" in row["standard"]
    assert found, "no count-form metric in any fixture"


def test_carving_is_not_applicable_for_the_child_fixture() -> None:
    child = actual("child_carving_not_applicable")
    rows = {row["id"]: row for row in child["metrics"]}
    banking = rows["banking_index"]
    assert banking["state"] == "not_applicable"
    assert banking["score"] is None
    profile = child["profile_summary"]
    assert profile["age_band"] == "age-7-12"
    assert profile["effect_count"] >= 1


def test_scene_fixture_has_nothing_missing_and_the_others_do() -> None:
    with_scene = actual("firm_snow_scene")["scene"]
    assert with_scene["snow_surface"] == "hardpack"
    assert with_scene["missing"] == []
    without = actual("parallel_linked")["scene"]
    assert set(without["missing"]) == {"snow_surface", "slope_band", "terrain_type"}


def test_asymmetry_is_scored_separately_and_names_the_weaker_side() -> None:
    """Design §6.3: both legs scored independently, weaker side named."""
    rows = {row["id"]: row for row in actual("parallel_linked")["metrics"]}
    asym = rows["asymmetry_index"]
    assert asym["state"] == "ok"
    assert asym["side"] in ("left", "right")
    paired = rows["hip_over_foot"]
    assert paired["left_value"] is not None
    assert paired["right_value"] is not None


def test_profile_view_fixture_is_ambiguous_with_two_candidates() -> None:
    expected = actual("profile_view")
    block = expected["classification"]
    assert block["ambiguous"] is True
    assert len(block["candidates"]) == 2
    assert block["candidates"][1]["separating_metric_id"]
    assert "view_too_profile" in expected["filming"]


if __name__ == "__main__":  # pragma: no cover - fixture maintenance
    import sys

    if "--write" in sys.argv:
        write_fixtures()
        print(f"wrote {len(CASES)} fixtures to {FIXTURE_DIR}")
    else:
        print(__doc__)
