"""Persisted UI prefs under %LOCALAPPDATA%/visual/ui.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.i18n import detect_system_language, normalize_lang


def prefs_path() -> Path:
    override = os.environ.get("VISUAL_PREFS")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    root = Path(local) / "visual" if local else Path.home() / "AppData" / "Local" / "visual"
    return root / "ui.json"


def load_language() -> str:
    path = prefs_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("language")
            if raw:
                return normalize_lang(str(raw))
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return detect_system_language()


def save_language(code: str) -> None:
    path = prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"language": normalize_lang(code)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
