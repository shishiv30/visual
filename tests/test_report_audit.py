from __future__ import annotations

import pytest

from core.sports.report_audit import (
    audit_curriculum_i18n,
    review_all_cases,
    review_case,
    review_issues,
)
from core.sports.report_cases import CASES


def test_curriculum_localized_leaves_complete() -> None:
    assert audit_curriculum_i18n() == []


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.case_id)
def test_report_case_layout_and_bilingual(case) -> None:
    result = review_case(case)
    assert result.ok, f"{case.case_id} {result.stage_id}: {result.issues}"
    assert result.stage_id in case.expect_stages


def test_review_suite_has_no_issues() -> None:
    assert review_issues() == []
    results = review_all_cases()
    assert len(results) == len(CASES)
    assert {item.case_id for item in results} == {c.case_id for c in CASES}
