from __future__ import annotations

from core.sports.scene import (
    REQUIRES_FIRM_SNOW,
    REQUIRES_POWDER,
    REQUIRES_STEEPS,
    CameraMotion,
    SceneContext,
    SlopeBand,
    SnowSurface,
    ViewClass,
)

ALL_REQUIRES = (REQUIRES_FIRM_SNOW, REQUIRES_STEEPS, REQUIRES_POWDER)


def test_empty_scene_satisfies_nothing_and_raises_nothing() -> None:
    scene = SceneContext()
    assert scene.is_empty
    for requires in ALL_REQUIRES:
        assert scene.requires_satisfied(requires) is False
    # A level with no scene requirement (tier `full`) is always a candidate.
    assert scene.requires_satisfied([]) is True
    assert scene.requires_satisfied(None) is True
    assert scene.requires_satisfied(["snow_surface"]) is False
    assert scene.requires_satisfied(["bogus_field"]) is False
    assert scene.requires_satisfied([""]) is False


def test_firm_snow_requires_hardpack_or_ice() -> None:
    for surface in (SnowSurface.HARDPACK, SnowSurface.ICE):
        assert SceneContext(snow_surface=surface).requires_satisfied(REQUIRES_FIRM_SNOW)
    for surface in (
        SnowSurface.CORDUROY,
        SnowSurface.PACKED,
        SnowSurface.SOFT,
        SnowSurface.POWDER,
        SnowSurface.CRUD,
        SnowSurface.SLUSH,
    ):
        assert not SceneContext(snow_surface=surface).requires_satisfied(
            REQUIRES_FIRM_SNOW
        )


def test_powder_requires_soft_or_powder() -> None:
    for surface in (SnowSurface.SOFT, SnowSurface.POWDER):
        assert SceneContext(snow_surface=surface).requires_satisfied(REQUIRES_POWDER)
    assert not SceneContext(snow_surface=SnowSurface.ICE).requires_satisfied(
        REQUIRES_POWDER
    )
    # Slope alone never stands in for the snow fact.
    assert not SceneContext(slope_band=SlopeBand.BLACK).requires_satisfied(
        REQUIRES_POWDER
    )


def test_steeps_requires_black_or_double_black() -> None:
    for band in (SlopeBand.BLACK, SlopeBand.DOUBLE_BLACK):
        assert SceneContext(slope_band=band).requires_satisfied(REQUIRES_STEEPS)
    for band in (SlopeBand.GREEN, SlopeBand.BLUE):
        assert not SceneContext(slope_band=band).requires_satisfied(REQUIRES_STEEPS)


def test_from_dict_is_tolerant_and_never_raises() -> None:
    assert SceneContext.from_dict(None) == SceneContext()
    assert SceneContext.from_dict("junk") == SceneContext()
    assert SceneContext.from_dict({"snow_surface": "not sure"}).snow_surface is None
    assert SceneContext.from_dict({"snow_surface": None}).snow_surface is None
    assert SceneContext.from_dict({"snow_surface": "sandpaper"}).snow_surface is None
    assert (
        SceneContext.from_dict({"snow_surface": " ICE "}).snow_surface
        is SnowSurface.ICE
    )
    assert (
        SceneContext.from_dict({"slope_band": "double_black"}).slope_band
        is SlopeBand.DOUBLE_BLACK
    )
    assert SceneContext.from_dict({"view": "quarter"}).view is ViewClass.QUARTER
    assert (
        SceneContext.from_dict({"camera_motion": "follow"}).camera_motion
        is CameraMotion.FOLLOW
    )


def test_fps_effective_explicit_argument_wins_and_rejects_nonsense() -> None:
    stored = {"fps_effective": 30.0}
    assert SceneContext.from_dict(stored).fps_effective == 30.0
    assert SceneContext.from_dict(stored, fps_effective=15.0).fps_effective == 15.0
    for bad in (0.0, -1.0, "x", None):
        assert SceneContext.from_dict({"fps_effective": bad}).fps_effective is None
    assert SceneContext().with_fps_effective(14.985).fps_effective == 14.985


def test_to_dict_json_ready_and_round_trips() -> None:
    scene = SceneContext(
        snow_surface=SnowSurface.POWDER,
        slope_band=SlopeBand.DOUBLE_BLACK,
        view=ViewClass.FRONTAL,
        camera_motion=CameraMotion.STATIC,
        fps_effective=15.0,
    )
    block = scene.to_dict()
    assert block == {
        "snow_surface": "powder",
        "slope_band": "double-black",
        "terrain_type": None,
        "view": "frontal",
        "camera_motion": "static",
        "fps_effective": 15.0,
    }
    assert SceneContext.from_dict(block) == scene
    assert not scene.is_empty
