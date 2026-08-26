"""Core inference Pydantic models."""

from schemas.clip_analysis import AnalyzedFrame, BlazeJoint, ClipAnalysis
from schemas.core_inference import COCO17_NAMES, CoreInferenceResult
from schemas.stage_report import StageReport

__all__ = [
    "AnalyzedFrame",
    "BlazeJoint",
    "ClipAnalysis",
    "COCO17_NAMES",
    "CoreInferenceResult",
    "StageReport",
]
