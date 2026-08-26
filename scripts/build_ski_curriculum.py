"""Write content/ski/curriculum.v2.json. Run from repo root."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.sports.catalog import assemble
from core.sports.curriculum import Curriculum, load_curriculum
from core.sports.ski_expert import accept_curriculum

OUT = ROOT / "content" / "ski" / "curriculum.v2.json"


def main() -> None:
    data = assemble()
    Curriculum.model_validate(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_curriculum.cache_clear()
    issues = accept_curriculum()
    if issues:
        raise SystemExit("ski expert rejected:\n" + "\n".join(issues))
    print(f"wrote {OUT}")
    print("ski expert: accepted")


if __name__ == "__main__":
    main()
