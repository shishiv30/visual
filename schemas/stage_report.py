"""Clip coaching report filled from curriculum JSON."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class KeypointStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class KeypointResult(BaseModel):
    id: str
    name: str = ""
    status: KeypointStatus
    score: float | None = None
    value: float | None = None
    evidence_ms: float | None = None
    good: str
    bad: str
    drills: list[dict]


class TreeNode(BaseModel):
    id: str
    name: str
    current: bool = False


class FrameScorePoint(BaseModel):
    t_ms: float
    score: float


class PostureScores(BaseModel):
    """Heuristic coach composites 0–100 (not lab SI metrics)."""

    stability: float = 0.0
    coordination: float = 0.0
    control: float = 0.0
    balance: float = 0.0


class StageReport(BaseModel):
    schema_version: Literal["2.1.0"] = "2.1.0"
    clip_id: str
    category_id: str
    stage_id: str
    category_name: str
    stage_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    ready_for_next_stage: bool
    disclaimer: str
    stage_focus: str = ""
    training_focus: str = ""
    how_to_advance: str = ""
    score_0_100: float = 0.0
    terrain_id: str = ""
    terrain_name: str = ""
    terrain_desc: str = ""
    weakest_checkpoint_id: str = ""
    next_level_ids: list[str] = Field(default_factory=list)
    next_level_names: list[str] = Field(default_factory=list)
    next_plans: list[dict] = Field(default_factory=list)
    session_plan: list[dict] = Field(default_factory=list)
    tree_path: list[TreeNode] = Field(default_factory=list)
    film_steps: list[str] = Field(default_factory=list)
    keypoints: list[KeypointResult]
    score_series: list[FrameScorePoint] = Field(default_factory=list)
    heuristic_not_fis_carve: bool = False
    posture: PostureScores | None = None
