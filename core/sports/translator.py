"""Chinese–English glossary for ski curriculum copy (translator role)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

GLOSSARY_PATH = (
    Path(__file__).resolve().parents[2] / "content" / "ski" / "glossary.zh-en.json"
)


class MissingTranslationError(KeyError):
    pass


@lru_cache(maxsize=1)
def load_glossary(path: Path | None = None) -> dict:
    target = path or GLOSSARY_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    phrases = data.get("phrases")
    terms = data.get("terms")
    if not isinstance(phrases, dict) or not isinstance(terms, dict):
        raise ValueError("glossary must have phrases and terms objects")
    return data


def en_for(zh: str, *, path: Path | None = None) -> str:
    phrases: dict[str, str] = load_glossary(path)["phrases"]
    if zh not in phrases:
        raise MissingTranslationError(zh)
    en = phrases[zh]
    if not isinstance(en, str) or not en.strip():
        raise MissingTranslationError(zh)
    return en


def loc(zh: str, *, path: Path | None = None) -> dict[str, str]:
    return {"zh": zh, "en": en_for(zh, path=path)}


def term_en(zh: str, *, path: Path | None = None) -> str:
    terms: dict[str, str] = load_glossary(path)["terms"]
    if zh not in terms:
        raise MissingTranslationError(zh)
    return terms[zh]
