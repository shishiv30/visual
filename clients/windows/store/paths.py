"""Where the desktop client keeps its store, per platform.

The store used to resolve to Windows `AppData` on every OS, so a macOS or Linux
run needed `VISUAL_LIBRARY` / `VISUAL_PREFS` set by hand (design §10). The
overrides and the Windows behaviour are unchanged; the other platforms now get
their own conventional locations.

| Platform      | Root                                          |
|---------------|-----------------------------------------------|
| win32         | `%LOCALAPPDATA%\\visual`, else `~/AppData/Local/visual` |
| darwin        | `~/Library/Application Support/visual`        |
| other (Linux) | `$XDG_DATA_HOME/visual`, else `~/.local/share/visual`   |

`sys.platform` is read on every call so tests can monkeypatch it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "visual"


def _env_dir(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw or not raw.strip():
        return None
    return Path(raw)


def app_data_root() -> Path:
    """Per-user directory holding the library, prefs and athlete profiles."""
    if sys.platform.startswith("win"):
        local = _env_dir("LOCALAPPDATA")
        if local is not None:
            return local / APP_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    xdg = _env_dir("XDG_DATA_HOME")
    if xdg is not None:
        return xdg / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME
