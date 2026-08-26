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
