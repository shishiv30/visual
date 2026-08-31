"""Read-side adapter over the imported ski knowledge pack (design doc §9).

Chapters 7-11 of the report are *data*, not prose written by the app: they are
rendered straight out of ``content/ski/knowledge/kb.v1.json``, which ships
pre-translated (``en``/``zh``) and coach-reviewed. This module is the only place
the UI touches that pack, so the panel stays free of JSON shape knowledge.

Loader resolution, in order:

1. ``core.sports.knowledge_pack`` — the dedicated pack reader. Any of
   ``load_pack`` / ``load_knowledge_pack`` / ``load_kb`` / ``load`` returning a
   dict with a ``stages`` map is accepted, so this survives a rename.
2. ``core.sports.knowledge.load_kb`` — the older loader, as a fallback.
3. Nothing: every accessor returns ``None`` / empty and chapters 7-11 simply do
   not render. A report must never fail to open because a pack is missing.

What this module adds on top of either loader is the *view* the panel needs:
one aggregate per ``kb_stage``, module sections filtered to the ones that name
this stage, and snow-condition ids resolved to their names.

Nothing here writes to ``core/``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.i18n import language

#: Pack languages. Anything else falls back to English pack content.
PACK_LANGS = ("en", "zh")

_MISSING = object()
_pack_cache: Any = _MISSING


def _import_pack_module() -> Any:
    try:
        from core.sports import knowledge_pack  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - loader not present yet
        return None
    return knowledge_pack


def _from_pack_module() -> dict | None:
    module = _import_pack_module()
    if module is None:
        return None
    for name in ("load_pack", "load_knowledge_pack", "load_kb", "load"):
        fn = getattr(module, name, None)
        if not callable(fn):
            continue
        try:
            data = fn()
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("stages"), dict):
            return data
    return None


def _from_knowledge_module() -> dict | None:
    try:
        from core.sports.knowledge import load_kb
    except Exception:
        return None
    try:
        data = load_kb()
    except Exception:
        return None
    if isinstance(data, dict) and isinstance(data.get("stages"), dict):
        return data
    return None


def load_pack() -> dict | None:
    """The whole pack, or ``None`` when no loader and no file are available."""
    global _pack_cache
    if _pack_cache is not _MISSING:
        return _pack_cache
    _pack_cache = _from_pack_module() or _from_knowledge_module()
    return _pack_cache


def reset_cache() -> None:
    """Test hook: forget the resolved pack."""
    global _pack_cache
    _pack_cache = _MISSING


def pack_lang(lang: str | None = None) -> str:
    code = (lang or language() or "en").split("-", 1)[0]
    return code if code in PACK_LANGS else "en"


def pack_version() -> str:
    pack = load_pack()
    if not pack:
        return ""
    provenance = pack.get("provenance") or {}
    return str(provenance.get("source_version") or pack.get("schema_version") or "")


def pretty_ref_id(ref: str) -> str:
    """``tr-black-groomed`` → ``Black groomed``. Pack ids, not UI copy."""
    body = str(ref)
    for prefix in ("tr-", "sn-", "ac-", "ft-", "dr-", "sk-", "st-"):
        if body.startswith(prefix):
            body = body[len(prefix) :]
            break
    body = body.replace("-", " ").replace("_", " ").strip()
    return body[:1].upper() + body[1:] if body else str(ref)


@dataclass(frozen=True)
class StageKnowledge:
    """One ``kb_stage`` slice, plus the module sections relevant to it."""

    kb_stage: str
    lang: str
    goal: str = ""
    why_it_matters: str = ""
    core_question: str = ""
    one_line: str = ""
    skills: list[dict] = field(default_factory=list)
    drills: list[dict] = field(default_factory=list)
    faults: list[dict] = field(default_factory=list)
    terrain: dict = field(default_factory=dict)
    tactics: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    equipment_sections: list[dict] = field(default_factory=list)
    terrain_sections: list[dict] = field(default_factory=list)
    snow_sections: list[dict] = field(default_factory=list)
    snow_names: dict[str, str] = field(default_factory=dict)

    def has_tutorial(self) -> bool:
        return bool(self.goal or self.skills)

    def has_drills(self) -> bool:
        return bool(self.drills)

    def has_faults(self) -> bool:
        return bool(self.faults)

    def has_terrain(self) -> bool:
        return bool(self.terrain or self.terrain_sections or self.snow_sections)

    def has_equipment(self) -> bool:
        return bool(self.equipment_sections)

    def snow_label(self, ref: str) -> str:
        return self.snow_names.get(ref) or pretty_ref_id(ref)


def _sections_for(pack: dict, module_id: str, lang: str, kb_stage: str) -> list[dict]:
    module = (pack.get("modules") or {}).get(module_id) or {}
    body = module.get(lang) or module.get("en") or {}
    sections = [s for s in (body.get("sections") or []) if isinstance(s, dict)]
    # No fallback: a module's first section is not "close enough" — it renders
    # another stage's terrain or equipment guidance as if it were this stage's.
    # An empty list lets the chapter hide honestly instead.
    return [s for s in sections if kb_stage in (s.get("relevant_stages") or [])]


def _snow_names(pack: dict, lang: str) -> dict[str, str]:
    reference = pack.get("reference") or {}
    body = reference.get(lang) or reference.get("en") or {}
    names: dict[str, str] = {}
    for item in body.get("snow_conditions") or []:
        if isinstance(item, dict) and item.get("id"):
            names[str(item["id"])] = str(item.get("name") or "")
    return names


def stage_knowledge(kb_stage: str, lang: str | None = None) -> StageKnowledge | None:
    """The pack slice for one ``kb_stage``, or ``None`` when unavailable."""
    if not kb_stage:
        return None
    pack = load_pack()
    if not pack:
        return None
    stage = (pack.get("stages") or {}).get(kb_stage)
    if not isinstance(stage, dict):
        return None
    code = pack_lang(lang)
    body = stage.get(code) or stage.get("en") or {}
    if not isinstance(body, dict) or not body:
        return None
    return StageKnowledge(
        kb_stage=kb_stage,
        lang=code,
        goal=str(body.get("goal") or ""),
        why_it_matters=str(body.get("why_it_matters") or ""),
        core_question=str(body.get("core_question") or ""),
        one_line=str(body.get("one_line") or ""),
        skills=[s for s in (body.get("skills") or []) if isinstance(s, dict)],
        drills=[d for d in (body.get("drills") or []) if isinstance(d, dict)],
        faults=[f for f in (body.get("faults") or []) if isinstance(f, dict)],
        terrain=body.get("terrain") if isinstance(body.get("terrain"), dict) else {},
        tactics=[str(x) for x in (body.get("tactics") or [])],
        safety_notes=[str(x) for x in (body.get("safety_notes") or [])],
        equipment_sections=_sections_for(pack, "mod-equipment", code, kb_stage),
        terrain_sections=_sections_for(pack, "mod-terrain-and-venues", code, kb_stage),
        snow_sections=_sections_for(pack, "mod-snow-and-weather", code, kb_stage),
        snow_names=_snow_names(pack, code),
    )


def order_by_ids(items: list[dict], first_ids: list[str]) -> list[dict]:
    """Reorder pack items so ``first_ids`` lead, keeping pack order after them."""
    if not first_ids:
        return list(items)
    by_id = {str(item.get("id") or ""): item for item in items}
    ordered: list[dict] = []
    seen: set[str] = set()
    for ref in first_ids:
        item = by_id.get(str(ref))
        if item is not None and str(ref) not in seen:
            ordered.append(item)
            seen.add(str(ref))
    for item in items:
        if str(item.get("id") or "") not in seen:
            ordered.append(item)
    return ordered
