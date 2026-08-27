"""Build flat locales/{lang}.json from nested locales/strings.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "locales" / "strings.json"
OUT_DIR = ROOT / "locales"
SUPPORTED = ("en", "es", "zh", "ko", "ja", "fr", "de", "it", "pt")


def main() -> None:
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    entries = data.get("strings")
    if not isinstance(entries, dict) or not entries:
        raise SystemExit("locales/strings.json must have a non-empty strings object")
    for key, pair in entries.items():
        if not isinstance(pair, dict):
            raise SystemExit(f"strings[{key!r}] must be an object")
        if "en" in pair:
            raise SystemExit(f"strings[{key!r}] must not contain en (key is English)")
        zh = str(pair.get("zh") or "").strip()
        if not zh:
            raise SystemExit(f"missing zh for strings[{key!r}]")

    for lang in SUPPORTED:
        flat: dict[str, str] = {}
        for key, pair in entries.items():
            if lang == "en":
                flat[key] = key
            else:
                text = str(pair.get(lang) or "")
                flat[key] = text if text.strip() else key
        (OUT_DIR / f"{lang}.json").write_text(
            json.dumps(flat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"wrote flat locales for {len(SUPPORTED)} langs ({len(entries)} keys)")


if __name__ == "__main__":
    main()
