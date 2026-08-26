from pathlib import Path

from schemas.core_inference import CoreInferenceResult

EXAMPLE = Path(__file__).resolve().parents[1] / "schemas" / "examples" / "result.v0.json"


def test_example_json_matches_contract() -> None:
    parsed = CoreInferenceResult.model_validate_json(EXAMPLE.read_text(encoding="utf-8"))
    assert parsed.schema_version == "0.1.0"
    assert parsed.frame.width >= 1
