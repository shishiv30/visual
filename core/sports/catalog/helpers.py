"""Curriculum factory helpers (English keys; zh from locales/strings.json)."""

from __future__ import annotations

from core.sports.translator import loc as L

# Adaptation overlay ids carried by the wiki curriculum (design doc §2.3).
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

CHILD_BANDS = ("age-3-6", "age-7-12")

WIDE_STANCE_OK = (
    "A wide stance is mechanically correct at this age; stance width is not penalized."
)
CARVE_NEEDS_MASS = (
    "Carving needs body mass to bend the ski; not applicable below age 13."
)


def drill(
    did: str,
    name: str,
    desc: str,
    training: list[str],
    venue_ids: list[str] | None = None,
) -> dict:
    return {
        "id": did,
        "name": L(name),
        "desc": L(desc),
        "training": [L(row) for row in training],
        "venue_ids": list(venue_ids or []),
    }


def checkpoint(
    cid: str,
    name: str,
    desc: str,
    body: list[str],
    signal: str,
    op: str,
    value: float,
    drills: list[str],
    *,
    hi: float | None = None,
    required: bool = True,
    heuristic: bool = False,
) -> dict:
    """v2 checkpoint: keyed to a whole-clip signal id from signals.json."""
    th: dict = {"op": op, "value": value}
    if hi is not None:
        th["hi"] = hi
    return {
        "id": cid,
        "name": L(name),
        "desc": L(desc),
        "body": body,
        "required": required,
        "signal": signal,
        "metric": None,
        "threshold": th,
        "heuristic_not_fis_carve": heuristic,
        "drills": drills,
    }


def metric_checkpoint(
    cid: str,
    name: str,
    desc: str,
    body: list[str],
    metric: str,
    op: str,
    value: float,
    drills: list[str],
    *,
    hi: float | None = None,
    required: bool = True,
    heuristic: bool = False,
) -> dict:
    """v3 checkpoint: keyed to a metric id from metrics.json (design doc §3.4).

    Thresholds on these are **first-pass expert estimates**; see the calibration
    note at the top of ``checkpoints.py``.
    """
    th: dict = {"op": op, "value": value}
    if hi is not None:
        th["hi"] = hi
    return {
        "id": cid,
        "name": L(name),
        "desc": L(desc),
        "body": body,
        "required": required,
        "signal": None,
        "metric": metric,
        "threshold": th,
        "heuristic_not_fis_carve": heuristic,
        "drills": drills,
    }


def adaptations(
    *,
    carving: bool = False,
    wide_stance_ok: bool = False,
) -> list[dict]:
    """Per-level adaptation overlay statuses (design doc §2.3 policy).

    Every overlay id is listed explicitly. A band that cannot be judged at this
    stage is stated as ``not_applicable`` with a reason — never as a silent pass.
    """
    rows: list[dict] = []
    for aid in ADAPTATION_IDS:
        if carving and aid in CHILD_BANDS:
            rows.append(
                {
                    "id": aid,
                    "status": "not_applicable",
                    "note": L(CARVE_NEEDS_MASS),
                }
            )
            continue
        note = None
        if wide_stance_ok and aid in CHILD_BANDS:
            note = L(WIDE_STANCE_OK)
        rows.append({"id": aid, "status": "applies", "note": note})
    return rows


def level(
    lid: str,
    name: str,
    desc: str,
    checkpoints: list[str],
    session: list[str],
    *,
    kb_stage: str,
    tier: str,
    requires_scene: list[str] | None = None,
    core_metrics: list[str] | None = None,
    gate_metrics: list[str] | None = None,
    prereq_levels: list[str] | None = None,
    prereq_checkpoints: list[str] | None = None,
    profile_notes: list[dict] | None = None,
) -> dict:
    return {
        "id": lid,
        "category_id": "alpine_piste",
        "in_scope": True,
        "heuristic_not_fis_carve": False,
        "name": L(name),
        "desc": L(desc),
        "checkpoints": checkpoints,
        "next_levels": [],
        "session_drills": session,
        "terrain": "green",
        "venue_ids": [],
        "kb_stage": kb_stage,
        "tier": tier,
        "requires_scene": list(requires_scene or []),
        "core_metrics": list(core_metrics or []),
        "gate_metrics": list(gate_metrics or []),
        "prerequisites": {
            "levels": list(prereq_levels or []),
            "checkpoints": list(prereq_checkpoints or []),
        },
        "profile_notes": list(profile_notes or []),
        "kb_refs": {
            "tutorial": None,
            "drills": [],
            "faults": [],
            "venue": None,
            "equipment": None,
        },
    }
