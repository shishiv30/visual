"""Import the wiki ski curriculum into a compact bilingual knowledge pack.

Design reference: docs/superpowers/specs/2026-08-30-ski-report-v3-design.md §9.

The curriculum lives in a different repo (`llm-wiki`) as one ~815 KB bundle per
language. Report chapters 7-11 need only a slice of it, so this script imports a
pack keyed by ``kb_stage`` with both languages inline:

    pack["stages"]["st-06"]["zh"]["skills"]

Run from the repo root::

    python scripts/import_ski_knowledge.py
    python scripts/import_ski_knowledge.py --check      # lint: pack up to date?
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_CURRICULUM_TAIL = Path("wiki") / "interests" / "skiing" / "curriculum" / "build"
# The curriculum repo is a sibling checkout; its exact location varies by
# machine, so fall back through the known layouts and let --source-dir or
# SKI_CURRICULUM_DIR override.
_SOURCE_CANDIDATES = (
    ROOT.parent / "llm-wiki" / _CURRICULUM_TAIL,
    ROOT.parent / "Documents" / "code" / "llm-wiki" / _CURRICULUM_TAIL,
)
DEFAULT_OUT = ROOT / "content" / "ski" / "knowledge" / "kb.v1.json"


def default_source_dir() -> Path:
    override = os.environ.get("SKI_CURRICULUM_DIR")
    if override:
        return Path(override)
    for candidate in _SOURCE_CANDIDATES:
        if candidate.is_dir():
            return candidate
    return _SOURCE_CANDIDATES[0]

PACK_SCHEMA_VERSION = "1.0.0"

# --- what we keep -----------------------------------------------------------

STAGE_TEXT_FIELDS = ("goal", "why_it_matters", "core_question", "one_line")
STAGE_LIST_FIELDS = ("tactics", "safety_notes")

SKILL_FIELDS = ("id", "name", "description", "why", "cues", "misconceptions")
DRILL_FIELDS = (
    "id",
    "name",
    "purpose",
    "terrain",
    "setup",
    "steps",
    "dose",
    "success_indicator",
    "targets_skills",
    "fixes_faults",
)
FAULT_FIELDS = (
    "id",
    "name",
    "symptom",
    "looks_like",
    "root_causes",
    "diagnosis_test",
    "risk",
)
FAULT_FIX_FIELDS = ("cues", "drills", "equipment_check")
TERRAIN_FIELDS = (
    "required",
    "ideal_description",
    "avoid",
    "conditions_best",
    "conditions_avoid",
)
OVERLAY_FIELDS = (
    "target",
    "applicability",
    "adjustments",
    "do_not",
    "equipment_notes",
    "criteria_modifications",
)

# Modules the report renders (chapters 10 and 11).
KEEP_MODULES = ("mod-equipment", "mod-terrain-and-venues", "mod-snow-and-weather")
# mod-safety contributes its hard rules only, for the disclaimer chapter (12).
SAFETY_MODULE = "mod-safety"
SECTION_FIELDS = (
    "id",
    "heading",
    "body",
    "tables",
    "checklist",
    "hard_rules",
    "relevant_stages",
    "adaptation_notes",
)

GLOSSARY_FIELDS = ("id", "term", "term_en", "definition")
SNOW_FIELDS = ("id", "name", "name_en", "description", "tactics", "difficulty")

# --- the app-level id -> kb_stage bridge (design doc §1.2) ------------------
# The importer owns this mapping so the app never hard-codes it in two places.
LEVEL_MAP: dict[str, str] = {
    "first_slide": "st-01",
    "pizza_glide": "st-02",
    "pizza": "st-03",
    "sideslip": "st-04",
    "wedge_christie": "st-05",
    "parallel": "st-06",
    "dynamic_parallel": "st-07",
    "firm_snow": "st-08",
    "skid_short": "st-09",
    "carve_long": "st-10",
    "carve_medium": "st-10",
    "carve_short": "st-11",
    "steeps": "st-12",
    "mogul_absorb": "st-13",
    "mogul_fallline": "st-13",
    "powder": "st-14",
    "trees": "st-15",
    "specialization": "st-16",
}


# --- helpers ----------------------------------------------------------------


def _pick(src: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Copy the named fields that are actually present (no null padding)."""
    return {name: src[name] for name in fields if src.get(name) is not None}


def _load_bundle(source_dir: Path, lang: str) -> dict[str, Any]:
    path = source_dir / f"curriculum.{lang}.json"
    if not path.is_file():
        raise SystemExit(f"source bundle not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lang") != lang:
        raise SystemExit(f"{path}: bundle lang is {data.get('lang')!r}, expected {lang!r}")
    return data


# --- reducers ---------------------------------------------------------------


def _reduce_stage(stage: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = _pick(stage, STAGE_TEXT_FIELDS + STAGE_LIST_FIELDS)
    out["skills"] = [_pick(s, SKILL_FIELDS) for s in stage.get("skills") or []]
    out["drills"] = [_pick(d, DRILL_FIELDS) for d in stage.get("drills") or []]

    faults: list[dict[str, Any]] = []
    for fault in stage.get("faults") or []:
        item = _pick(fault, FAULT_FIELDS)
        item["fix"] = _pick(fault.get("fix") or {}, FAULT_FIX_FIELDS)
        faults.append(item)
    out["faults"] = faults

    terrain = stage.get("terrain")
    if not isinstance(terrain, dict):
        raise SystemExit(f"{stage.get('id')}: terrain block is required")
    out["terrain"] = _pick(terrain, TERRAIN_FIELDS)

    out["adaptation_overlays"] = [
        _pick(o, OVERLAY_FIELDS) for o in stage.get("adaptation_overlays") or []
    ]
    return out


def _reduce_module(module: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": module.get("title", ""),
        "sections": [_pick(s, SECTION_FIELDS) for s in module.get("sections") or []],
    }


def _safety_hard_rules(module: dict[str, Any]) -> list[dict[str, Any]]:
    """mod-safety has no module-level hard_rules; collect the per-section ones."""
    out: list[dict[str, Any]] = []
    for section in module.get("sections") or []:
        rules = section.get("hard_rules") or []
        if rules:
            out.append(
                {
                    "section": section.get("id", ""),
                    "heading": section.get("heading", ""),
                    "hard_rules": list(rules),
                }
            )
    return out


def _reduce_reference(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "glossary": [_pick(g, GLOSSARY_FIELDS) for g in reference.get("glossary") or []],
        "snow_conditions": [
            _pick(s, SNOW_FIELDS) for s in reference.get("snow_conditions") or []
        ],
    }


def _gate_ids(bundle: dict[str, Any]) -> list[str]:
    """The ac-* criterion ids present in the source.

    The pack drops the assessment bodies (the app measures instead), so the ids
    are the only handle left for detecting a stale pack against a new bundle.
    """
    ids: set[str] = set()
    for stage in bundle["progression"]["stages"]:
        for criterion in (stage.get("assessment") or {}).get("criteria") or []:
            cid = criterion.get("id")
            if isinstance(cid, str) and cid.startswith("ac-"):
                ids.add(cid)
    return sorted(ids)


# --- pack build -------------------------------------------------------------


def build_pack(source_dir: Path, langs: list[str], imported_at: str) -> dict[str, Any]:
    bundles = {lang: _load_bundle(source_dir, lang) for lang in langs}
    primary = bundles[langs[0]]

    stage_ids = [s["id"] for s in primary["progression"]["stages"]]
    for lang, bundle in bundles.items():
        other = [s["id"] for s in bundle["progression"]["stages"]]
        if other != stage_ids:
            raise SystemExit(f"stage ids differ between {langs[0]} and {lang}")

    stages: dict[str, dict[str, Any]] = {sid: {} for sid in stage_ids}
    modules: dict[str, dict[str, Any]] = {mid: {} for mid in KEEP_MODULES}
    safety_hard_rules: dict[str, Any] = {}
    reference: dict[str, Any] = {}

    for lang, bundle in bundles.items():
        for stage in bundle["progression"]["stages"]:
            stages[stage["id"]][lang] = _reduce_stage(stage)

        by_id = {m["id"]: m for m in bundle.get("modules") or []}
        for mid in KEEP_MODULES:
            module = by_id.get(mid)
            if module is None:
                raise SystemExit(f"{lang}: module {mid} missing from source")
            modules[mid][lang] = _reduce_module(module)

        safety = by_id.get(SAFETY_MODULE)
        if safety is None:
            raise SystemExit(f"{lang}: module {SAFETY_MODULE} missing from source")
        safety_hard_rules[lang] = _safety_hard_rules(safety)

        reference[lang] = _reduce_reference(bundle.get("reference") or {})

    missing = sorted({sid for sid in LEVEL_MAP.values()} - set(stage_ids))
    if missing:
        raise SystemExit(f"level_map points at stages absent from the source: {missing}")

    meta = primary.get("meta") or {}
    return {
        "schema_version": PACK_SCHEMA_VERSION,
        "provenance": {
            "source_version": meta.get("version", ""),
            "source_built": meta.get("built", ""),
            "imported_at": imported_at,
            "langs": list(langs),
            "stage_count": len(stage_ids),
            "gate_ids": _gate_ids(primary),
        },
        "level_map": dict(LEVEL_MAP),
        "stages": stages,
        "modules": modules,
        "safety_hard_rules": safety_hard_rules,
        "reference": reference,
    }


def serialize(pack: dict[str, Any]) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _without_imported_at(pack: dict[str, Any]) -> str:
    """Serialization used for comparison: the wall clock is not content."""
    copy = dict(pack)
    provenance = dict(copy.get("provenance") or {})
    provenance.pop("imported_at", None)
    copy["provenance"] = provenance
    return serialize(copy)


def _lang_bytes(pack: dict[str, Any], lang: str) -> int:
    slice_ = {
        "stages": {sid: {lang: v[lang]} for sid, v in pack["stages"].items() if lang in v},
        "modules": {mid: {lang: v[lang]} for mid, v in pack["modules"].items() if lang in v},
        "safety_hard_rules": {lang: pack["safety_hard_rules"].get(lang)},
        "reference": {lang: pack["reference"].get(lang)},
    }
    return len(serialize(slice_).encode("utf-8"))


# --- cli --------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="directory holding curriculum.<lang>.json "
        "(default: ../llm-wiki/wiki/interests/skiing/curriculum/build, "
        "or $SKI_CURRICULUM_DIR)",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="pack path (default: %(default)s)"
    )
    parser.add_argument(
        "--langs", default="en,zh", help="comma-separated language codes (default: %(default)s)"
    )
    parser.add_argument(
        "--imported-at",
        default=None,
        help="stamp for provenance.imported_at (default: today, UTC)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed pack is up to date; exit non-zero if not",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    langs = [code.strip() for code in args.langs.split(",") if code.strip()]
    if not langs:
        raise SystemExit("--langs must name at least one language")

    source_dir = args.source_dir or default_source_dir()
    stamp = args.imported_at or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    pack = build_pack(source_dir, langs, stamp)

    existing: dict[str, Any] | None = None
    if args.out.is_file():
        existing = json.loads(args.out.read_text(encoding="utf-8"))

    # Content-identical reruns must not churn the file: keep the old stamp.
    if existing is not None and _without_imported_at(existing) == _without_imported_at(pack):
        pack["provenance"]["imported_at"] = (existing.get("provenance") or {}).get(
            "imported_at", stamp
        )

    text = serialize(pack)

    if args.check:
        if existing is None:
            print(f"knowledge pack missing: {args.out}", file=sys.stderr)
            return 1
        if _without_imported_at(existing) != _without_imported_at(pack):
            print(
                f"knowledge pack is stale: {args.out}\n"
                "re-run: python scripts/import_ski_knowledge.py",
                file=sys.stderr,
            )
            return 1
        print(f"knowledge pack up to date: {args.out}")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    total = len(text.encode("utf-8"))
    print(f"wrote {args.out} ({total / 1024:.1f} KB total, {len(pack['stages'])} stages)")
    for lang in langs:
        print(f"  {lang}: {_lang_bytes(pack, lang) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
