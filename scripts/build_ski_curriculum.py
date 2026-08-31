"""Write content/ski/curriculum.v3.json. Run from repo root.

``curriculum.v2.json`` is deliberately left alone: it is still the bundle
`core.sports.curriculum.CURRICULUM_PATH` loads, so the migration can land
without breaking the shipped classifier.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.sports.catalog import assemble
from core.sports.curriculum import CURRICULUM_V3_PATH, Curriculum
from core.sports.ski_expert import accept_curriculum

OUT = CURRICULUM_V3_PATH


def main() -> None:
    data = assemble()
    bundle = Curriculum.model_validate(data)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    issues = accept_curriculum(bundle)
    if issues:
        raise SystemExit("ski expert rejected:\n" + "\n".join(issues))
    print(f"wrote {OUT}")
    print("ski expert: accepted")


if __name__ == "__main__":
    main()
