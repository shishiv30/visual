"""Compile runtime curriculum.v2.json from catalog + expert knowledge."""

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
from core.sports.knowledge import load_expert
from core.sports.translator import loc as L


def assemble() -> dict:
    expert = load_expert()
    drill_rows = drills()
    for item in drill_rows:
        item["venue_ids"] = DRILL_VENUES.get(item["id"], ["venue_green_groomer"])
    level_rows = levels()
    catalog = set(expert["catalog_no_score"])
    heuristic = set(expert["heuristic_levels"])
    for lv in level_rows:
        lid = lv["id"]
        lv["next_levels"] = list(expert["tree_next"][lid])
        lv["terrain"] = expert["level_terrain"][lid]
        lv["category_id"] = expert["level_category"][lid]
        lv["in_scope"] = lid not in catalog
        lv["heuristic_not_fis_carve"] = lid in heuristic
        lv["venue_ids"] = list(TERRAIN_VENUES[lv["terrain"]])
    scored = [lv["id"] for lv in level_rows if lv["in_scope"]]
    return {
        "schema_version": "2.1.0",
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
