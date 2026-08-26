"""Load ski knowledge catalogs (signals, body tokens, expert tree)."""

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
def load_expert(path: Path | None = None) -> dict:
    target = path or (KNOWLEDGE_DIR / "expert.json")
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data.get("tree_next"), dict):
        raise ValueError("expert.json missing tree_next")
    return data


def signal_ids() -> frozenset[str]:
    return frozenset(load_signals())


def body_tokens() -> frozenset[str]:
    return frozenset(load_body()["tokens"])
