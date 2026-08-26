"""Versioned Core inference contract (Pydantic)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SourceKind(str, Enum):
    IMAGE = "image"
    VIDEO_FRAME = "video_frame"


class ErrorCode(str, Enum):
    NO_PERSON = "NO_PERSON"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    GPU_OOM = "GPU_OOM"
    INVALID_INPUT = "INVALID_INPUT"


class SkeletonKind(str, Enum):
    COCO_17 = "coco_17"


class CameraIntrinsics(BaseModel):
    fx: float
    fy: float
    cx: float
    cy: float


class FrameMeta(BaseModel):
    source_kind: SourceKind
    timestamp_ms: float
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    camera_intrinsics: CameraIntrinsics | None = None


class Detection(BaseModel):
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox_xyxy: tuple[float, float, float, float]
    track_id: int | None = None


class Keypoint(BaseModel):
    name: str
    x: float
    y: float
    z: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class Pose(BaseModel):
    skeleton: SkeletonKind
    keypoints: list[Keypoint]
    score: float
    detection_index: int | None = None


class Track(BaseModel):
    track_id: int
    detection_index: int


class Classification(BaseModel):
    class_name: str
    confidence: float


class Segment(BaseModel):
    class_name: str
    confidence: float
    rle: str


class BackendId(str, Enum):
    YOLO11N_POSE = "yolo11n-pose"
    YOLO11N = "yolo11n"
    MEDIAPIPE_POSE = "mediapipe_pose"


class ModelMeta(BaseModel):
    backend_id: str
    model_name: str
    latency_ms: float
    device: str


class InferenceError(BaseModel):
    code: ErrorCode
    message: str


class CoreInferenceResult(BaseModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    frame: FrameMeta
    detections: list[Detection]
    poses: list[Pose]
    tracks: list[Track]
    classifications: list[Classification]
    segments: list[Segment]
    model_meta: ModelMeta
    error: InferenceError | None = None


COCO17_NAMES: tuple[str, ...] = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)
