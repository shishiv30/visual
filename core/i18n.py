"""Load shared locale JSON for Windows / iOS / Android clients."""

from __future__ import annotations

import json
import locale
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"
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

_en: dict[str, str] = {}
_catalog: dict[str, str] = {}
_lang = DEFAULT_LANG


def locales_dir() -> Path:
    return LOCALES_DIR


def _read_json(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}


def _ensure_en() -> dict[str, str]:
    global _en
    if not _en:
        _en = _read_json(LOCALES_DIR / "en.json")
    return _en


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
    global _catalog, _lang
    lang = normalize_lang(code)
    _ensure_en()
    path = LOCALES_DIR / f"{lang}.json"
    _catalog = _read_json(path) if path.is_file() else dict(_en)
    _lang = lang
    return _lang


def language() -> str:
    return _lang


def t(key: str, **kwargs: object) -> str:
    if not _catalog and not _en:
        set_language(DEFAULT_LANG)
    text = _catalog.get(key) or _en.get(key) or _ensure_en().get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


set_language(DEFAULT_LANG)
