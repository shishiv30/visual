"""Fill locales/strings.json with authentic ski-school terminology for 7 langs.

Idiom sources: ESF (FR), DSV/ÖSSV (DE), ISIA/RFEDI (ES/IT), SAJ (JA), KSIA (KO),
plus common alpine-coach PT. English keys stay as catalog keys (no ``en`` field).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "locales" / "strings.json"

# Generated translations live in locales/_ski_locale_fills/*.json (one object per
# English key → {fr,de,es,it,ja,ko,pt}). This script merges them.
FILL_DIR = ROOT / "locales" / "_ski_locale_fills"
LANGS = ("fr", "de", "es", "it", "ja", "ko", "pt")


def main() -> None:
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    strings: dict = data["strings"]
    fills: dict[str, dict[str, str]] = {}
    if not FILL_DIR.is_dir():
        raise SystemExit(f"missing fill dir: {FILL_DIR}")
    for path in sorted(FILL_DIR.glob("*.json")):
        chunk = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(chunk, dict):
            raise SystemExit(f"bad fill file: {path}")
        fills.update(chunk)

    missing_keys = [k for k in strings if k not in fills]
    if missing_keys:
        raise SystemExit(
            f"{len(missing_keys)} keys lack fills (first: {missing_keys[:5]!r})"
        )

    for key, langs in fills.items():
        if key not in strings:
            raise SystemExit(f"unknown English key in fills: {key!r}")
        entry = strings[key]
        if "en" in entry:
            raise SystemExit(f"key must not carry en: {key!r}")
        for lang in LANGS:
            text = str(langs.get(lang) or "").strip()
            if not text:
                raise SystemExit(f"empty {lang} for {key!r}")
            entry[lang] = text

    DICT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"merged {len(fills)} keys × {len(LANGS)} langs into {DICT_PATH}")


if __name__ == "__main__":
    main()
