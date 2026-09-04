# -*- coding: utf-8 -*-
"""Merge all part*.json fills into locales/strings.json and rebuild flats."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT = ROOT / "locales" / "strings.json"
FILL = ROOT / "locales" / "_ski_locale_fills"
LANGS = ("fr", "de", "es", "it", "ja", "ko", "pt")


def main() -> None:
    catalog = json.loads(DICT.read_text(encoding="utf-8"))
    strings: dict = catalog["strings"]
    fills: dict[str, dict[str, str]] = {}
    for path in sorted(FILL.glob("part*.json")):
        if path.name.startswith("part_complete"):
            continue
        fills.update(json.loads(path.read_text(encoding="utf-8")))

    updated = 0
    for key, langs in fills.items():
        if key not in strings:
            raise SystemExit(f"unknown key: {key!r}")
        entry = strings[key]
        for lang in LANGS:
            text = str(langs.get(lang) or "").strip()
            if not text:
                continue
            entry[lang] = text
            updated += 1

    DICT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    covered = sum(
        1
        for v in strings.values()
        if all(str(v.get(lang) or "").strip() for lang in LANGS)
    )
    print(f"merged fills={len(fills)} cells_touched={updated} fully_covered={covered}/{len(strings)}")


if __name__ == "__main__":
    main()
