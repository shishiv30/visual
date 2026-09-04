"""Export media with the same COCO-17 overlay used in playback."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2

from clients.windows.overlay.skeleton import draw_poses
from clients.windows.pipeline.normalize import find_ffmpeg
from clients.windows.ui.qtutil import format_duration_ms
from schemas.clip_analysis import AnalyzedFrame, ClipAnalysis
from schemas.core_inference import CoreInferenceResult


def nearest_frame(
    analysis: ClipAnalysis | None, t_ms: float
) -> tuple[AnalyzedFrame | None, int | None]:
    if analysis is None or not analysis.frames:
        return None, None
    best_i = min(
        range(len(analysis.frames)),
        key=lambda i: abs(analysis.frames[i].t_ms - t_ms),
    )
    return analysis.frames[best_i], best_i


def nearest_result(analysis: ClipAnalysis | None, t_ms: float) -> CoreInferenceResult | None:
    frame, _index = nearest_frame(analysis, t_ms)
    if frame is None:
        return None
    return frame.result


def format_frame_hud(
    t_ms: float,
    total_ms: int,
    video_frame: int,
    pose_index: int | None,
    pose_count: int,
    short_id: str = "",
) -> str:
    clock = f"{format_duration_ms(int(t_ms))} / {format_duration_ms(total_ms)}"
    hud = f"{clock}  f{video_frame}"
    if pose_index is not None and pose_count > 0:
        hud += f"  p{pose_index}/{pose_count}"
    if short_id:
        return f"{short_id}  {hud}"
    return hud


def overlay_frame(
    bgr,
    analysis: ClipAnalysis | None,
    t_ms: float,
):
    frame, _index = nearest_frame(analysis, t_ms)
    if frame is None:
        return bgr
    return draw_poses(bgr, frame.result)


def export_overlay(
    src: Path,
    dest: Path,
    analysis: ClipAnalysis | None,
    *,
    image: bool,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if image:
        bgr = cv2.imread(str(src))
        if bgr is None:
            raise RuntimeError("read failed")
        out = overlay_frame(bgr, analysis, 0.0)
        if not cv2.imwrite(str(dest), out):
            raise RuntimeError("write failed")
        return

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError("open failed")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if fps < 1e-3:
        fps = 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1)
    tmp = Path(tempfile.mkstemp(suffix=".avi")[1])
    writer = cv2.VideoWriter(
        str(tmp), cv2.VideoWriter_fourcc(*"XVID"), fps, (width, height)
    )
    if not writer.isOpened():
        cap.release()
        tmp.unlink(missing_ok=True)
        raise RuntimeError("writer failed")
    try:
        while True:
            ok, bgr = cap.read()
            if not ok or bgr is None:
                break
            t_ms = float(cap.get(cv2.CAP_PROP_POS_MSEC))
            writer.write(overlay_frame(bgr, analysis, t_ms))
    finally:
        writer.release()
        cap.release()

    ffmpeg = find_ffmpeg()
    if ffmpeg:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(tmp),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        tmp.unlink(missing_ok=True)
        return
    tmp.replace(dest.with_suffix(".avi") if dest.suffix.lower() != ".avi" else dest)
