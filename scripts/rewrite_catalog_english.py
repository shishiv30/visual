"""Rewrite catalog/*.py Chinese string literals to English keys via glossary."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = json.loads(
    (ROOT / "content" / "ski" / "glossary.zh-en.json").read_text(encoding="utf-8")
)
PHRASES: dict[str, str] = dict(GLOSSARY["phrases"])
# longest first so nested replacements don't break
ORDERED = sorted(PHRASES.items(), key=lambda item: len(item[0]), reverse=True)


def _rewrite(text: str) -> str:
    for zh, en in ORDERED:
        # double and single quoted
        for quote in ('"', "'"):
            text = text.replace(f"{quote}{zh}{quote}", f"{quote}{en}{quote}")
    return text


def main() -> None:
    catalog = ROOT / "core" / "sports" / "catalog"
    changed = []
    for path in catalog.glob("*.py"):
        orig = path.read_text(encoding="utf-8")
        updated = _rewrite(orig)
        if updated != orig:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.name)
    # helpers docstring
    helpers = catalog / "helpers.py"
    h = helpers.read_text(encoding="utf-8")
    h2 = h.replace(
        "Curriculum factory helpers (Chinese copy only; English from glossary).",
        "Curriculum factory helpers (English keys; zh from locales/strings.json).",
    )
    if h2 != h:
        helpers.write_text(h2, encoding="utf-8")
        if helpers.name not in changed:
            changed.append(helpers.name)
    print("rewrote", changed)


if __name__ == "__main__":
    main()
