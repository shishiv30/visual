"""Contract tests for the imported ski knowledge pack (design spec §9)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.import_ski_knowledge import DEFAULT_OUT, LEVEL_MAP, default_source_dir, main

# The app level ids of the v3 ladder, design doc §1.2, verbatim.
DESIGN_DOC_LEVELS = (
    "first_slide",
    "pizza_glide",
    "pizza",
    "sideslip",
    "wedge_christie",
    "parallel",
    "dynamic_parallel",
    "firm_snow",
    "skid_short",
    "carve_long",
    "carve_medium",
    "carve_short",
    "steeps",
    "mogul_absorb",
    "mogul_fallline",
    "powder",
    "trees",
    "specialization",
)

LANGS = ("en", "zh")


@pytest.fixture(scope="module")
def pack() -> dict:
    assert DEFAULT_OUT.is_file(), f"knowledge pack not committed: {DEFAULT_OUT}"
    return json.loads(Path(DEFAULT_OUT).read_text(encoding="utf-8"))


def test_pack_loads_with_sixteen_stages(pack: dict) -> None:
    provenance = pack["provenance"]
    assert provenance["stage_count"] == 16
    assert len(pack["stages"]) == 16
    assert provenance["langs"] == list(LANGS)
    assert provenance["source_version"]
    assert provenance["source_built"]
    assert provenance["imported_at"]
    assert provenance["gate_ids"], "gate ids are the staleness handle"
    assert all(gid.startswith("ac-") for gid in provenance["gate_ids"])


def test_every_design_doc_level_resolves_to_a_stage(pack: dict) -> None:
    level_map = pack["level_map"]
    assert set(level_map) == set(DESIGN_DOC_LEVELS)
    for level in DESIGN_DOC_LEVELS:
        stage_id = level_map[level]
        assert stage_id in pack["stages"], f"{level} -> {stage_id} missing from pack"
    assert level_map == LEVEL_MAP


@pytest.mark.parametrize("stage_id", [f"st-{n:02d}" for n in range(1, 17)])
def test_stage_has_both_languages_with_id_parity(pack: dict, stage_id: str) -> None:
    stage = pack["stages"][stage_id]
    assert set(stage) == set(LANGS)
    for lang in LANGS:
        body = stage[lang]
        for field in ("goal", "why_it_matters", "core_question", "one_line"):
            assert body[field].strip(), f"{stage_id}/{lang}: empty {field}"
        assert body["terrain"].get("required"), f"{stage_id}/{lang}: terrain.required"
        for array in ("skills", "drills", "faults"):
            assert body[array], f"{stage_id}/{lang}: empty {array}"

    for array in ("skills", "drills", "faults"):
        ids = {lang: [item["id"] for item in stage[lang][array]] for lang in LANGS}
        assert ids["en"] == ids["zh"], f"{stage_id}: {array} id parity broken"


@pytest.mark.parametrize("stage_id", [f"st-{n:02d}" for n in range(1, 17)])
def test_fault_fix_drills_resolve_within_the_stage(pack: dict, stage_id: str) -> None:
    for lang in LANGS:
        body = pack["stages"][stage_id][lang]
        drill_ids = {drill["id"] for drill in body["drills"]}
        for fault in body["faults"]:
            for drill_id in fault["fix"].get("drills", []):
                assert drill_id in drill_ids, (
                    f"{stage_id}/{lang}: fault {fault['id']} fix.drills references "
                    f"{drill_id}, not a drill of this stage"
                )


def test_dropped_sections_stay_dropped(pack: dict) -> None:
    body = pack["stages"]["st-06"]["en"]
    for dropped in ("assessment", "fitness_focus", "plateau", "duration", "prerequisites", "sources"):
        assert dropped not in body
    assert set(pack["modules"]) == {
        "mod-equipment",
        "mod-terrain-and-venues",
        "mod-snow-and-weather",
    }
    for lang in LANGS:
        assert pack["safety_hard_rules"][lang], "disclaimer chapter needs the hard rules"
        assert pack["reference"][lang]["glossary"]
        assert pack["reference"][lang]["snow_conditions"]


@pytest.mark.skipif(
    not default_source_dir().is_dir(),
    reason="curriculum source checkout not available on this machine",
)
def test_check_mode_passes_against_committed_pack() -> None:
    assert main(["--check"]) == 0
