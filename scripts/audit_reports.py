"""Print layout + bilingual review for synthetic report parameter sets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.sports.report_audit import review_all_cases, review_issues
from core.sports.report_cases import CASES


def main() -> int:
    print("case_id\tstage\tready\tscore\tstatus")
    failed = 0
    for case, result in zip(CASES, review_all_cases(), strict=True):
        mark = "ok" if result.ok else "FAIL"
        if not result.ok:
            failed += 1
        print(
            f"{result.case_id}\t{result.stage_id}\t{result.ready}\t"
            f"{result.score:.1f}\t{mark}"
        )
        print(f"  {case.note}")
        for issue in result.issues:
            print(f"  - {issue}")
    extra = [item for item in review_issues() if item.startswith("curriculum:")]
    for item in extra:
        print(item)
        failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
