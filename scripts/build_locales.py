"""Build locales/zh.json and locales/en.json from the zh–en UI dictionary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DICT_PATH = ROOT / "locales" / "zh_en.json"
OUT_DIR = ROOT / "locales"


def main() -> None:
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    entries = data["ui"]
    if not isinstance(entries, dict) or not entries:
        raise SystemExit("locales/zh_en.json must have a non-empty ui object")
    zh: dict[str, str] = {}
    en: dict[str, str] = {}
    for key, pair in entries.items():
        if not isinstance(pair, dict) or "zh" not in pair or "en" not in pair:
            raise SystemExit(f"ui.{key} must have zh and en")
        zh[key] = str(pair["zh"])
        en[key] = str(pair["en"])
        if not en[key].strip():
            raise SystemExit(f"missing English for ui.{key}")
    (OUT_DIR / "zh.json").write_text(
        json.dumps(zh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "en.json").write_text(
        json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote zh.json and en.json ({len(zh)} keys)")


if __name__ == "__main__":
    main()
