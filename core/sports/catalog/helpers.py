"""Curriculum factory helpers (Chinese copy only; English from glossary)."""

from __future__ import annotations

from core.sports.translator import loc as L


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
        "threshold": th,
        "heuristic_not_fis_carve": heuristic,
        "drills": drills,
    }


def level(
    lid: str,
    name: str,
    desc: str,
    checkpoints: list[str],
    session: list[str],
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
    }
