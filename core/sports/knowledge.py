"""Load ski knowledge catalogs (signals, metrics, body tokens, expert tree)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "content" / "ski" / "knowledge"


@lru_cache(maxsize=1)
def load_body(path: Path | None = None) -> dict:
    target = path or (KNOWLEDGE_DIR / "body.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    tokens = data.get("tokens")
    if not isinstance(tokens, dict) or not tokens:
        raise ValueError("body.json must have tokens")
    return data


@lru_cache(maxsize=1)
def load_signals(path: Path | None = None) -> dict:
    target = path or (KNOWLEDGE_DIR / "signals.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("signals.json empty")
    return data


@lru_cache(maxsize=1)
def load_metrics(path: Path | None = None) -> dict:
    """v3 metric catalog (design doc §3.4). Superset of the v2 signals."""
    target = path or (KNOWLEDGE_DIR / "metrics.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("metrics.json empty")
    return data


@lru_cache(maxsize=1)
def load_expert(path: Path | None = None) -> dict:
    target = path or (KNOWLEDGE_DIR / "expert.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data.get("tree_next"), dict):
        raise ValueError("expert.json missing tree_next")
    return data


@lru_cache(maxsize=1)
def load_kb(path: Path | None = None) -> dict:
    """Imported wiki knowledge pack (design doc §9)."""
    target = path or (KNOWLEDGE_DIR / "kb.v1.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data.get("stages"), dict):
        raise ValueError("kb pack missing stages")
    return data


def expert_view(schema_version: str, expert: dict | None = None) -> dict:
    """Resolve the expert tree for a curriculum schema version.

    ``expert.json`` keeps the 2.1.0 tree at the top level (the shipped
    ``curriculum.v2.json`` is still the runtime bundle) and the v3 stage model
    under ``"v3"``. A 3.x curriculum reads the v3 overrides layered on top of
    the shared constants (pass scores, proxy checkpoints).
    """
    data = expert if expert is not None else load_expert()
    if not schema_version.startswith("3."):
        return data
    override = data.get("v3")
    if not isinstance(override, dict):
        raise ValueError("expert.json missing v3 block")
    return {**data, **override}


def signal_ids() -> frozenset[str]:
    return frozenset(load_signals())


def metric_ids() -> frozenset[str]:
    return frozenset(load_metrics())


def body_tokens() -> frozenset[str]:
    return frozenset(load_body()["tokens"])
