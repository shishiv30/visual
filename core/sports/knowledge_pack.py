"""Reader for the imported ski knowledge pack (design §9).

``content/ski/knowledge/kb.v1.json`` is produced by
``scripts/import_ski_knowledge.py`` from the wiki curriculum. It is *content*,
not UI copy: every string is already bilingual and coach-reviewed, so nothing
here goes through ``core.i18n``.

Two rules shape this module.

**Never raise.** The pack is large and ships alongside the app, so a missing,
truncated or malformed file is a deployment accident, not a reason to lose the
whole report. Every accessor returns ``None`` or an empty tuple and the caller
(``core.sports.assess``) then simply omits the knowledge chapters. The one place
that must notice is the report: ``StageReport.knowledge_ref`` stays ``None``, so
a client can tell "no pack" from "pack with nothing to say".

**Reference, do not copy.** Chapters 7-11 render from the pack on the client
side, keyed by ``knowledge_ref.kb_stage``. Only the *selection* derived from
this skier's own metrics (``KnowledgeFocus``) is stored in the report.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "content" / "ski" / "knowledge"
PACK_PATH = KNOWLEDGE_DIR / "kb.v1.json"

LANGS = ("en", "zh")
DEFAULT_LANG = "en"

#: Fault ``risk`` value that blocks advancement (design §6, advance rule).
INJURY_RISK = "injury-risk"


def _normalize_lang(lang: str | None) -> str:
    code = (lang or DEFAULT_LANG).strip().lower().split("-", 1)[0]
    return code if code in LANGS else DEFAULT_LANG


@lru_cache(maxsize=1)
def load_pack(path: Path | None = None) -> dict | None:
    """Parsed pack, or ``None`` when it is missing or unusable.

    Cached: the pack is ~700 KB of JSON and every report reads it.
    """
    target = path or PACK_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    stages = data.get("stages")
    level_map = data.get("level_map")
    if not isinstance(stages, dict) or not stages:
        return None
    if not isinstance(level_map, dict):
        return None
    return data


def pack_version() -> str:
    """``provenance.source_version``, or ``""`` when there is no pack.

    This is the staleness handle: a report records the version it rendered
    against, so a pack imported later is detectable in a stored report.
    """
    pack = load_pack()
    if pack is None:
        return ""
    provenance = pack.get("provenance")
    if not isinstance(provenance, dict):
        return ""
    return str(provenance.get("source_version") or "")


def gate_ids() -> tuple[str, ...]:
    pack = load_pack()
    if pack is None:
        return ()
    provenance = pack.get("provenance")
    if not isinstance(provenance, dict):
        return ()
    raw = provenance.get("gate_ids")
    return tuple(str(item) for item in raw) if isinstance(raw, list) else ()


def stage_for_level(level_id: str, fallback: str = "") -> str:
    """``kb_stage`` for an app level id (the pack's own ``level_map``).

    ``fallback`` is the curriculum's ``kb_stage`` for that level, used when
    there is no pack or the level is not mapped, so the report can still name
    the stage bridge even with the pack absent.
    """
    pack = load_pack()
    if pack is not None:
        mapped = pack.get("level_map", {}).get(level_id)
        if isinstance(mapped, str) and mapped:
            return mapped
    return fallback


def stage_slice(kb_stage: str, lang: str | None = None) -> dict | None:
    """One stage of the pack in one language, or ``None``.

    Accepts either a ``kb_stage`` (``"st-06"``) or an app level id, so callers
    do not have to remember which they are holding.
    """
    pack = load_pack()
    if pack is None or not kb_stage:
        return None
    stages = pack.get("stages", {})
    stage_id = kb_stage if kb_stage in stages else stage_for_level(kb_stage, "")
    body = stages.get(stage_id)
    if not isinstance(body, dict):
        return None
    slice_ = body.get(_normalize_lang(lang))
    return slice_ if isinstance(slice_, dict) else None


def _entries(kb_stage: str, key: str, lang: str | None) -> tuple[dict, ...]:
    body = stage_slice(kb_stage, lang)
    if body is None:
        return ()
    raw = body.get(key)
    if not isinstance(raw, list):
        return ()
    return tuple(item for item in raw if isinstance(item, dict) and item.get("id"))


def skills(kb_stage: str, lang: str | None = None) -> tuple[dict, ...]:
    return _entries(kb_stage, "skills", lang)


def drills(kb_stage: str, lang: str | None = None) -> tuple[dict, ...]:
    return _entries(kb_stage, "drills", lang)


def faults(kb_stage: str, lang: str | None = None) -> tuple[dict, ...]:
    return _entries(kb_stage, "faults", lang)


def terrain(kb_stage: str, lang: str | None = None) -> dict:
    body = stage_slice(kb_stage, lang)
    if body is None:
        return {}
    value = body.get("terrain")
    return value if isinstance(value, dict) else {}


def module(module_id: str, lang: str | None = None) -> dict:
    """One ``aux_refs`` module (equipment / terrain-and-venues / snow)."""
    pack = load_pack()
    if pack is None or not module_id:
        return {}
    modules = pack.get("modules")
    if not isinstance(modules, dict):
        return {}
    body = modules.get(module_id)
    if not isinstance(body, dict):
        return {}
    value = body.get(_normalize_lang(lang))
    return value if isinstance(value, dict) else {}


def safety_hard_rules(lang: str | None = None) -> tuple[str, ...]:
    pack = load_pack()
    if pack is None:
        return ()
    rules = pack.get("safety_hard_rules")
    if not isinstance(rules, dict):
        return ()
    raw = rules.get(_normalize_lang(lang))
    if isinstance(raw, list):
        return tuple(str(item) for item in raw)
    return ()


def fault_by_id(kb_stage: str, fault_id: str, lang: str | None = None) -> dict | None:
    for item in faults(kb_stage, lang):
        if str(item.get("id")) == fault_id:
            return item
    return None


def fault_fix_drills(kb_stage: str, fault_id: str) -> tuple[str, ...]:
    """Drill ids a fault's ``fix`` points at, in pack order."""
    item = fault_by_id(kb_stage, fault_id, DEFAULT_LANG)
    if item is None:
        return ()
    fix = item.get("fix")
    if not isinstance(fix, dict):
        return ()
    raw = fix.get("drills")
    return tuple(str(x) for x in raw) if isinstance(raw, list) else ()


def summary(kb_stage: str, lang: str | None = None) -> dict[str, Any]:
    """Goal / why / core question, for the chapter-7 header."""
    body = stage_slice(kb_stage, lang)
    if body is None:
        return {}
    return {
        key: str(body.get(key) or "")
        for key in ("goal", "why_it_matters", "core_question", "one_line")
    }
