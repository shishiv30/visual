"""Local clip library under %LOCALAPPDATA%/visual/library."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from schemas.clip_analysis import ClipAnalysis
from schemas.stage_report import StageReport


class ClipKind(str, Enum):
    VIDEO = "video"
    IMAGE = "image"


class ClipStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"


class SeedMark(BaseModel):
    t_ms: float
    box: tuple[float, float, float, float]


class ClipMeta(BaseModel):
    clip_id: str
    created_at: str
    display_name: str
    duration_ms: int = 0
    width: int = 1
    height: int = 1
    fps: float = 30.0
    kind: ClipKind = ClipKind.VIDEO
    status: ClipStatus = ClipStatus.PENDING
    error: str | None = None
    seed_box: tuple[float, float, float, float] | None = None
    seeds: list[SeedMark] = Field(default_factory=list)
    play_start_ms: int = 0
    play_end_ms: int | None = None


class FrameFeedbackEntry(BaseModel):
    t_ms: float = 0.0
    pose_index: int | None = None
    stage_vote: Literal["like", "unlike"] | None = None
    skeleton_ok: bool = True
    updated_at: str = ""


class FrameFeedbackFile(BaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    clip_id: str
    stage_id_at_vote: str = ""
    frames: dict[str, FrameFeedbackEntry] = Field(default_factory=dict)


def library_root() -> Path:
    override = os.environ.get("VISUAL_LIBRARY")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "visual" / "library"
    return Path.home() / "AppData" / "Local" / "visual" / "library"


def display_name_now(now: datetime | None = None) -> str:
    stamp = now or datetime.now().astimezone()
    return stamp.strftime("%m/%d/%Y-%H:%M")


def clip_dir(clip_id: str) -> Path:
    return library_root() / clip_id


def media_path(meta: ClipMeta) -> Path:
    folder = clip_dir(meta.clip_id)
    if meta.kind == ClipKind.IMAGE:
        return folder / "clip.jpg"
    return folder / "clip.mp4"


def thumb_path(clip_id: str) -> Path:
    return clip_dir(clip_id) / "thumb.jpg"


def meta_path(clip_id: str) -> Path:
    return clip_dir(clip_id) / "meta.json"


def analysis_path(clip_id: str) -> Path:
    return clip_dir(clip_id) / "analysis.json"


def stage_report_path(clip_id: str) -> Path:
    return clip_dir(clip_id) / "stage_report.json"


def frame_feedback_path(clip_id: str) -> Path:
    return clip_dir(clip_id) / "frame_feedback.json"


def save_meta(meta: ClipMeta) -> None:
    path = meta_path(meta.clip_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")


def load_meta(clip_id: str) -> ClipMeta:
    return ClipMeta.model_validate_json(meta_path(clip_id).read_text(encoding="utf-8"))


def load_analysis(clip_id: str) -> ClipAnalysis:
    return ClipAnalysis.model_validate_json(
        analysis_path(clip_id).read_text(encoding="utf-8")
    )


def save_analysis(analysis: ClipAnalysis) -> None:
    analysis_path(analysis.clip_id).write_text(
        analysis.model_dump_json(indent=2), encoding="utf-8"
    )


def save_stage_report(report: StageReport) -> None:
    stage_report_path(report.clip_id).write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )


def load_stage_report(clip_id: str) -> StageReport | None:
    path = stage_report_path(clip_id)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    version = str(data.get("schema_version") or "")
    if version != "2.1.0":
        data = {**data, "schema_version": "2.1.0"}
    data.setdefault("keypoints", [])
    try:
        return StageReport.model_validate(data)
    except ValidationError:
        return None


def empty_frame_feedback(clip_id: str) -> FrameFeedbackFile:
    return FrameFeedbackFile(clip_id=clip_id)


def load_frame_feedback(clip_id: str) -> FrameFeedbackFile:
    path = frame_feedback_path(clip_id)
    empty = empty_frame_feedback(clip_id)
    if not path.is_file():
        return empty
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(data, dict):
        return empty
    try:
        return FrameFeedbackFile.model_validate(data)
    except ValidationError:
        return empty


def save_frame_feedback(doc: FrameFeedbackFile) -> None:
    path = frame_feedback_path(doc.clip_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")


def _touch_frame_entry(
    doc: FrameFeedbackFile,
    video_frame: int,
    *,
    t_ms: float,
    pose_index: int | None,
    stage_id: str,
) -> FrameFeedbackEntry:
    key = str(int(video_frame))
    entry = doc.frames.get(key)
    if entry is None:
        entry = FrameFeedbackEntry()
        doc.frames[key] = entry
    entry.t_ms = t_ms
    entry.pose_index = pose_index
    entry.updated_at = created_at_iso()
    if stage_id:
        doc.stage_id_at_vote = stage_id
    return entry


def toggle_frame_stage_vote(
    clip_id: str,
    video_frame: int,
    vote: Literal["like", "unlike"],
    *,
    t_ms: float,
    pose_index: int | None,
    stage_id: str,
) -> FrameFeedbackFile:
    doc = load_frame_feedback(clip_id)
    doc.clip_id = clip_id
    entry = _touch_frame_entry(
        doc, video_frame, t_ms=t_ms, pose_index=pose_index, stage_id=stage_id
    )
    if entry.stage_vote == vote:
        entry.stage_vote = None
    else:
        entry.stage_vote = vote
    save_frame_feedback(doc)
    return doc


def toggle_frame_skeleton_ok(
    clip_id: str,
    video_frame: int,
    *,
    t_ms: float,
    pose_index: int | None,
    stage_id: str,
) -> FrameFeedbackFile:
    doc = load_frame_feedback(clip_id)
    doc.clip_id = clip_id
    entry = _touch_frame_entry(
        doc, video_frame, t_ms=t_ms, pose_index=pose_index, stage_id=stage_id
    )
    entry.skeleton_ok = not entry.skeleton_ok
    save_frame_feedback(doc)
    return doc


def new_clip_id() -> str:
    return str(uuid.uuid4())


def list_clips() -> list[ClipMeta]:
    root = library_root()
    if not root.is_dir():
        return []
    items: list[ClipMeta] = []
    for folder in root.iterdir():
        path = folder / "meta.json"
        if not path.is_file():
            continue
        try:
            items.append(ClipMeta.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    items.sort(key=lambda m: m.created_at, reverse=True)
    return items


def created_at_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def delete_clip(clip_id: str) -> None:
    folder = clip_dir(clip_id)
    if folder.is_dir():
        shutil.rmtree(folder)


def prepare_reanalyze(clip_id: str) -> ClipMeta:
    meta = load_meta(clip_id)
    meta.status = ClipStatus.PENDING
    meta.error = None
    meta.seed_box = None
    meta.seeds = []
    meta.play_start_ms = 0
    meta.play_end_ms = None
    save_meta(meta)
    path = analysis_path(clip_id)
    if path.is_file():
        path.unlink()
    report = stage_report_path(clip_id)
    if report.is_file():
        report.unlink()
    return meta
