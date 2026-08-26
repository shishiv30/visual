"""Clip-level pose analysis wrapping per-frame CoreInferenceResult."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from schemas.core_inference import CoreInferenceResult


class BlazeJoint(BaseModel):
    x: float
    y: float
    z: float
    confidence: float


class AnalyzedFrame(BaseModel):
    t_ms: float
    result: CoreInferenceResult
    blaze33: list[BlazeJoint] | None = None


class ClipAnalysis(BaseModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    clip_id: str
    fps: float
    frame_count: int
    frames: list[AnalyzedFrame]
