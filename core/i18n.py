"""Load shared locale catalog for Windows / iOS / Android clients.

Dictionary keys are the English display text. There is no ``en`` field:
``t(key, lang=\"en\")`` returns ``key`` directly. Other languages look up
``strings[key][lang]`` and fall back to the key.
"""

from __future__ import annotations

import json
import locale
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"
STRINGS_PATH = LOCALES_DIR / "strings.json"
DEFAULT_LANG = "en"
SUPPORTED = ("en", "es", "zh", "ko", "ja", "fr", "de", "it", "pt")
LANG_LABELS = {
    "en": "English",
    "es": "Español",
    "zh": "中文",
    "ko": "한국어",
    "ja": "日本語",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
}

_strings: dict[str, dict[str, str]] = {}
_lang = DEFAULT_LANG


def locales_dir() -> Path:
    return LOCALES_DIR


def _load_strings() -> dict[str, dict[str, str]]:
    global _strings
    if _strings:
        return _strings
    data = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))
    raw = data.get("strings") or {}
    catalog: dict[str, dict[str, str]] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        cleaned = {
            str(code): str(text)
            for code, text in entry.items()
            if code != "en" and str(text).strip()
        }
        catalog[str(key)] = cleaned
    _strings = catalog
    return _strings


def normalize_lang(code: str | None) -> str:
    if not code:
        return DEFAULT_LANG
    raw = code.strip().replace("_", "-").lower()
    primary = raw.split("-", 1)[0]
    if primary in SUPPORTED:
        return primary
    return DEFAULT_LANG


def detect_system_language() -> str:
    try:
        sys_locale = locale.getdefaultlocale()[0] or ""
    except ValueError:
        sys_locale = ""
    return normalize_lang(sys_locale)


def set_language(code: str) -> str:
    global _lang
    _load_strings()
    _lang = normalize_lang(code)
    return _lang


def language() -> str:
    return _lang


def has_key(key: str) -> bool:
    return key in _load_strings()


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Resolve display text. English returns the key; other langs look up."""
    _load_strings()
    code = normalize_lang(lang) if lang is not None else _lang
    if code == "en":
        text = key
    else:
        entry = _strings.get(key) or {}
        text = (entry.get(code) or "").strip() or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


set_language(DEFAULT_LANG)
