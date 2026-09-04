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


class SkiBoardOverlay(BaseModel):
    """One ski axis stored at analyze time (image pixels)."""

    tip: list[float]
    tail: list[float]
    confidence: float = 0.0


class SkiFrameOverlay(BaseModel):
    """Precomputed ski overlay for one analyzed frame."""

    left: SkiBoardOverlay | None = None
    right: SkiBoardOverlay | None = None
    wedge_deg: float | None = None
    detect_ok: bool = False
    source: Literal["segment", "pose"] | None = None


class AnalyzedFrame(BaseModel):
    t_ms: float
    result: CoreInferenceResult
    blaze33: list[BlazeJoint] | None = None
    ski: SkiFrameOverlay | None = None


class ClipAnalysis(BaseModel):
    """Sampled pose frames for one clip, plus the scene and athlete context.

    `scene` and `athlete` are plain JSON blocks rather than typed models on
    purpose: `schemas` is a leaf package, and importing `core.sports.scene` /
    `core.sports.profile` here would close an import cycle through
    `core.sports.__init__` → `assess` → this module. Build the typed views with
    `SceneContext.from_dict(analysis.scene)` and
    `AthleteContext.from_dict(analysis.athlete)`.

    Both default to None so analysis.json files written before v3 still load.
    """

    schema_version: Literal["0.1.0"] = "0.1.0"
    clip_id: str
    fps: float
    frame_count: int
    frames: list[AnalyzedFrame]
    scene: dict | None = None
    athlete: dict | None = None

    @property
    def fps_effective(self) -> float | None:
        """True sample rate of `frames`, or None when it was never recorded.

        `fps` is the source rate; `frames` is sampled with a stride, so every
        frequency derived from `fps` is inflated by that stride (the ~2x bug at
        `core/sports/signals.py:266`). None means unknown — callers must decide,
        not silently fall back to `fps`.
        """
        if not isinstance(self.scene, dict):
            return None
        raw = self.scene.get("fps_effective")
        if isinstance(raw, bool) or raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0.0 else None
