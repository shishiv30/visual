import json
from pathlib import Path

from schemas.clip_analysis import ClipAnalysis
from schemas.core_inference import CoreInferenceResult

EXAMPLE = Path(__file__).resolve().parents[1] / "schemas" / "examples" / "result.v0.json"


def test_clip_analysis_wraps_core_result() -> None:
    frame = CoreInferenceResult.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    clip = ClipAnalysis(
        clip_id="00000000-0000-0000-0000-000000000001",
        fps=30.0,
        frame_count=1,
        frames=[{"t_ms": 0, "result": frame}],
    )
    dumped = clip.model_dump()
    assert dumped["schema_version"] == "0.1.0"
    assert dumped["frames"][0]["result"]["schema_version"] == "0.1.0"
    roundtrip = ClipAnalysis.model_validate_json(clip.model_dump_json())
    assert roundtrip.clip_id == clip.clip_id


def _clip() -> ClipAnalysis:
    frame = CoreInferenceResult.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    return ClipAnalysis(
        clip_id="00000000-0000-0000-0000-000000000001",
        fps=30.0,
        frame_count=1,
        frames=[{"t_ms": 0, "result": frame}],
    )


def test_old_analysis_json_without_scene_or_athlete_still_loads() -> None:
    stored = json.loads(_clip().model_dump_json())
    del stored["scene"]
    del stored["athlete"]
    loaded = ClipAnalysis.model_validate_json(json.dumps(stored))
    assert loaded.scene is None
    assert loaded.athlete is None
    assert loaded.fps_effective is None
    assert loaded.fps == 30.0


def test_scene_and_athlete_blocks_are_additive() -> None:
    clip = _clip()
    clip.scene = {"snow_surface": "ice", "slope_band": None, "fps_effective": 15.0}
    clip.athlete = {"age_band": "age-18-39", "height_m": 1.75, "sex": "female"}
    loaded = ClipAnalysis.model_validate_json(clip.model_dump_json())
    assert loaded.scene == clip.scene
    assert loaded.athlete == clip.athlete
    assert loaded.fps_effective == 15.0
    # A scene without the computed rate reports unknown, not the source fps.
    loaded.scene = {"snow_surface": "ice"}
    assert loaded.fps_effective is None
