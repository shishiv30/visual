from __future__ import annotations

from datetime import date

from core.sports.profile import (
    AGE_3_6,
    AGE_7_12,
    AGE_13_17,
    AGE_18_39,
    AGE_40_59,
    AGE_60PLUS,
    LEG_LEN_FRACTION,
    AthleteContext,
    age_band_for,
)


def test_age_band_boundaries() -> None:
    cases = [
        (2.5, AGE_3_6),
        (3.0, AGE_3_6),
        (6.99, AGE_3_6),
        (7.0, AGE_7_12),
        (12.99, AGE_7_12),
        (13.0, AGE_13_17),
        (17.99, AGE_13_17),
        (18.0, AGE_18_39),
        (39.99, AGE_18_39),
        (40.0, AGE_40_59),
        (59.99, AGE_40_59),
        (60.0, AGE_60PLUS),
        (95.0, AGE_60PLUS),
    ]
    for age, band in cases:
        assert age_band_for(age) == band, age


def test_age_band_unknown_inputs_return_none() -> None:
    for bad in (None, -1.0, "not a number", float("nan")):
        assert age_band_for(bad) is None


def test_from_profile_snapshot_real_shape() -> None:
    snapshot = {
        "key": "Ada-28-132-110",
        "name": "Ada",
        "birthday": "2016-03-01",
        "height_cm": 132.0,
        "gender": "female",
        "weight_kg": 28.0,
        "ski_cm": 110.0,
        "updated_at": "2026-08-30T09:00:00-05:00",
    }
    ctx = AthleteContext.from_profile_snapshot(snapshot, clip_date=date(2026, 8, 30))
    assert ctx.age_band == AGE_7_12
    assert 10.4 < (ctx.age_years or 0.0) < 10.6
    assert ctx.height_m == 1.32
    assert ctx.mass_kg == 28.0
    assert ctx.sex == "female"
    assert ctx.ski_cm == 110.0
    assert ctx.leg_len_m == LEG_LEN_FRACTION * 1.32
    assert round(ctx.bmi or 0.0, 2) == 16.07
    assert round(ctx.ski_len_ratio or 0.0, 3) == 0.833
    assert ctx.is_complete


def test_clip_date_accepts_iso_timestamp_from_meta() -> None:
    snapshot = {"birthday": "2000-01-01", "height_cm": 180, "weight_kg": 75}
    ctx = AthleteContext.from_profile_snapshot(
        snapshot, clip_date="2026-08-30T21:45:00-05:00"
    )
    assert ctx.age_band == AGE_18_39
    assert 26.6 < (ctx.age_years or 0.0) < 26.7


def test_missing_birthday_gives_none_band_not_an_error() -> None:
    for snapshot in (
        {"height_cm": 175, "weight_kg": 70, "ski_cm": 165},
        {"birthday": "", "height_cm": 175, "weight_kg": 70},
        {"birthday": "garbage", "height_cm": 175, "weight_kg": 70},
        {"birthday": "2030-01-01", "height_cm": 175, "weight_kg": 70},
    ):
        ctx = AthleteContext.from_profile_snapshot(snapshot, clip_date="2026-08-30")
        assert ctx.age_years is None
        assert ctx.age_band is None
        assert not ctx.is_complete


def test_partial_and_empty_profiles() -> None:
    empty = AthleteContext.from_profile_snapshot(None)
    assert empty == AthleteContext()
    assert not empty.is_complete
    assert empty.leg_len_m is None
    assert empty.bmi is None
    assert empty.ski_len_ratio is None
    assert empty.age_band is None

    for junk in ("nonsense", 7, [], {"height_cm": 0, "weight_kg": -3, "ski_cm": None}):
        ctx = AthleteContext.from_profile_snapshot(junk)
        assert ctx.height_m is None
        assert ctx.mass_kg is None
        assert ctx.ski_cm is None

    height_only = AthleteContext.from_profile_snapshot(
        {"birthday": "1990-01-01", "height_cm": 180}, clip_date="2026-08-30"
    )
    assert height_only.height_m == 1.8
    assert height_only.leg_len_m is not None
    assert height_only.bmi is None
    assert not height_only.is_complete


def test_gender_unspecified_and_unknown_become_none() -> None:
    for value in ("unspecified", "", None, "alien", "AthleteGender.UNSPECIFIED"):
        ctx = AthleteContext.from_profile_snapshot({"gender": value})
        assert ctx.sex is None
    assert AthleteContext.from_profile_snapshot({"gender": "MALE"}).sex == "male"
    assert (
        AthleteContext.from_profile_snapshot({"gender": "AthleteGender.OTHER"}).sex
        == "other"
    )


def test_to_dict_round_trips_through_from_dict() -> None:
    ctx = AthleteContext.from_profile_snapshot(
        {
            "birthday": "1990-05-05",
            "height_cm": 175,
            "weight_kg": 70,
            "ski_cm": 165,
            "gender": "male",
        },
        clip_date="2026-08-30",
    )
    block = ctx.to_dict()
    assert block["age_band"] == AGE_18_39
    assert AthleteContext.from_dict(block) == ctx
    assert AthleteContext.from_dict(None) == AthleteContext()
    assert AthleteContext.from_dict("junk") == AthleteContext()
