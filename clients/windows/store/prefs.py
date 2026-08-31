"""Persisted UI prefs under the per-platform store root (see paths.py)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from clients.windows.store.paths import app_data_root
from core.i18n import detect_system_language, normalize_lang

#: Key written and read today.
LANG_KEY = "language"
#: Key written by builds up to 2026-08; still read so a saved setting survives.
LEGACY_LANG_KEY = "Language"


def prefs_path() -> Path:
    override = os.environ.get("VISUAL_PREFS")
    if override:
        return Path(override)
    return app_data_root() / "ui.json"


def load_language() -> str:
    path = prefs_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw = data.get(LANG_KEY) or data.get(LEGACY_LANG_KEY)
                if raw:
                    return normalize_lang(str(raw))
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return detect_system_language()


def save_language(code: str) -> None:
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {LANG_KEY: normalize_lang(code)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
