"""Compile the runtime curriculum JSON from catalog + expert knowledge."""

from __future__ import annotations

from core.sports.catalog.checkpoints import checkpoints
from core.sports.catalog.drills import drills
from core.sports.catalog.levels import levels
from core.sports.catalog.venues import (
    DRILL_VENUES,
    TERRAIN_VENUES,
    categories,
    terrains,
    venues,
)
from core.sports.knowledge import expert_view, load_kb
from core.sports.translator import loc as L

SCHEMA_VERSION = "3.0.0"


def _kb_refs(kb: dict, kb_stage: str, *, stage_content: bool) -> dict:
    """Point a level at its slice of the imported knowledge pack (§9)."""
    stage = kb["stages"].get(kb_stage) or {}
    payload = stage.get("en") or {}
    return {
        "tutorial": kb_stage,
        "drills": (
            [row["id"] for row in payload.get("drills") or []] if stage_content else []
        ),
        "faults": (
            [row["id"] for row in payload.get("faults") or []] if stage_content else []
        ),
        "venue": "mod-terrain-and-venues",
        "equipment": "mod-equipment",
    }


def assemble() -> dict:
    expert = expert_view(SCHEMA_VERSION)
    kb = load_kb()
    kb_level_map = kb.get("level_map") or {}
    drill_rows = drills()
    for item in drill_rows:
        item["venue_ids"] = DRILL_VENUES.get(item["id"], ["venue_green_groomer"])
    level_rows = levels()
    catalog = set(expert["catalog_no_score"])
    heuristic = set(expert["heuristic_levels"])
    scene = expert["scene_levels"]
    for lv in level_rows:
        lid = lv["id"]
        lv["next_levels"] = list(expert["tree_next"][lid])
        lv["terrain"] = expert["level_terrain"][lid]
        lv["category_id"] = expert["level_category"][lid]
        lv["in_scope"] = lid not in catalog
        lv["heuristic_not_fis_carve"] = lid in heuristic
        lv["venue_ids"] = list(TERRAIN_VENUES[lv["terrain"]])
        lv["requires_scene"] = list(scene.get(lid, lv["requires_scene"]))
        lv["kb_refs"] = _kb_refs(
            kb, lv["kb_stage"], stage_content=lid in kb_level_map
        )
    scored = [lv["id"] for lv in level_rows if lv["in_scope"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "disclaimer": L(
            "Coach heuristics, not FIS judging or medical advice. 2D pose can misread. Pain or prior injury: see a coach or clinician."
        ),
        "pass_score": float(expert["pass_score"]),
        "checkpoint_pass": float(expert["checkpoint_pass"]),
        "sys_drill": "drill_film",
        "categories": categories(),
        "terrains": terrains(),
        "venues": venues(),
        "level_ids": scored,
        "catalog_level_ids": [lv["id"] for lv in level_rows if not lv["in_scope"]],
        "drills": {d["id"]: d for d in drill_rows},
        "checkpoints": {c["id"]: c for c in checkpoints()},
        "levels": {lv["id"]: lv for lv in level_rows},
    }
