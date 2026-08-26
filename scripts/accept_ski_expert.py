"""Ski expert acceptance of compiled curriculum knowledge points."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sports.ski_expert import accept_curriculum


def main() -> int:
    issues = accept_curriculum()
    if issues:
        print("ski expert: REJECTED")
        for item in issues:
            print(f"- {item}")
        return 1
    print("ski expert: ACCEPTED")
    print("tree, terrains, required hockey/one-ski, signals, body tokens, drills OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
