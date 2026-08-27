from __future__ import annotations

from pathlib import Path

import pytest

from clients.windows.store.athletes import (
    AthleteGender,
    athlete_key,
    get_by_key,
    list_athletes,
    upsert_athlete,
)


@pytest.fixture
def athletes_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "athletes.json"
    monkeypatch.setenv("VISUAL_ATHLETES", str(path))
    return path


def test_athlete_key_changes_when_any_of_four_differs(athletes_env: Path) -> None:
    assert athlete_key("Ada", 70, 175, 165) == "Ada-70-175-165"
    assert athlete_key("Ada", 71, 175, 165) != athlete_key("Ada", 70, 175, 165)
    assert athlete_key("Ada", 70, 176, 165) != athlete_key("Ada", 70, 175, 165)
    assert athlete_key("Ada", 70, 175, 166) != athlete_key("Ada", 70, 175, 165)
    assert athlete_key("Bob", 70, 175, 165) != athlete_key("Ada", 70, 175, 165)
    assert athletes_env.exists() is False


def test_upsert_updates_same_key_and_creates_new_on_weight_change(
    athletes_env: Path,
) -> None:
    first = upsert_athlete(
        name=" Ada ",
        weight_kg=70,
        height_cm=175,
        ski_cm=165,
        birthday="1998-05-01",
        gender=AthleteGender.FEMALE,
    )
    assert first.key == "Ada-70-175-165"
    second = upsert_athlete(
        name="Ada",
        weight_kg=70,
        height_cm=175,
        ski_cm=165,
        birthday="1999-01-02",
        gender=AthleteGender.FEMALE,
    )
    assert second.key == first.key
    assert get_by_key(first.key) is not None
    assert get_by_key(first.key).birthday == "1999-01-02"
    assert len(list_athletes()) == 1

    third = upsert_athlete(
        name="Ada",
        weight_kg=72,
        height_cm=175,
        ski_cm=165,
        birthday="1999-01-02",
        gender=AthleteGender.FEMALE,
    )
    assert third.key == "Ada-72-175-165"
    keys = {item.key for item in list_athletes()}
    assert keys == {"Ada-70-175-165", "Ada-72-175-165"}
    assert athletes_env.is_file()
