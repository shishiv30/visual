# -*- coding: utf-8 -*-
"""Generate remaining locale fills from a compact TSV of translations.

TSV columns: en \\t fr \\t de \\t es \\t it \\t ja \\t ko \\t pt
Source file: locales/_ski_locale_fills/_bulk.tsv (written by companion data files).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILL = ROOT / "locales" / "_ski_locale_fills"
KEYS = [r["en"] for r in json.loads((ROOT / "tmp_i18n_keys.json").read_text(encoding="utf-8"))]


def load_existing() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in FILL.glob("part*.json"):
        out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def parse_tsv(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        line = line.strip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 8:
            raise SystemExit(f"bad TSV row ({len(parts)} cols): {line[:80]!r}")
        en, fr, de, es, it, ja, ko, pt = parts
        out[en] = {"fr": fr, "de": de, "es": es, "it": it, "ja": ja, "ko": ko, "pt": pt}
    return out


def main() -> None:
    existing = load_existing()
    bulk_paths = sorted(FILL.glob("_bulk*.tsv"))
    if not bulk_paths:
        raise SystemExit("no _bulk*.tsv files")
    added: dict[str, dict[str, str]] = {}
    for path in bulk_paths:
        added.update(parse_tsv(path.read_text(encoding="utf-8")))
    merged = {**existing, **added}
    missing = [k for k in KEYS if k not in merged]
    extra = [k for k in merged if k not in KEYS]
    if extra:
        raise SystemExit(f"unknown keys in fills: {extra[:5]}")
    out = FILL / "part_merged.json"
    # write only the newly added for incremental merge; also write full status
    (FILL / "part_bulk.json").write_text(
        json.dumps(added, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"bulk keys={len(added)} total={len(merged)} missing={len(missing)}")
    if missing:
        print("still missing sample:")
        for k in missing[:15]:
            print(" -", k[:100])
        (ROOT / "tmp_i18n_missing.json").write_text(
            json.dumps(missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
