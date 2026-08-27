"""Rewrite t(\"snake_case\") call sites to English keys using locales/_snake_to_en.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPPING = json.loads((ROOT / "locales" / "_snake_to_en.json").read_text(encoding="utf-8"))


def main() -> None:
    roots = [ROOT / "clients" / "windows", ROOT / "tests", ROOT / "core"]
    files: list[Path] = []
    for root in roots:
        files.extend(root.rglob("*.py"))
    changed: list[Path] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        orig = text
        for snake, en in MAPPING.items():
            for quote in ('"', "'"):
                old = f"t({quote}{snake}{quote}"
                new = f"t({quote}{en}{quote}"
                text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    print(f"updated {len(changed)} files")
    for path in changed:
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
