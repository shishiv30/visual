"""ffmpeg / OpenCV media normalization (max 120s, H.264, 30fps, height 720)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

MAX_SECONDS = 120.0
MAX_HEIGHT = 720


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def probe_duration_ms(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 0.0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    n = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
    cap.release()
    if fps > 1e-3 and n > 0:
        return 1000.0 * n / fps
    return 0.0


def probe_size(path: Path) -> tuple[int, int, float]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        img = cv2.imread(str(path))
        if img is None:
            return 1, 1, 0.0
        h, w = img.shape[:2]
        return int(w), int(h), 0.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    cap.release()
    return max(w, 1), max(h, 1), fps if fps > 1 else 30.0


def _even(n: int) -> int:
    return max(2, n - (n % 2))


def _scale_bgr(bgr: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h > MAX_HEIGHT:
        scale = MAX_HEIGHT / float(h)
        w = max(1, int(round(w * scale)))
        h = MAX_HEIGHT
    w, h = _even(w), _even(h)
    if (h, w) == bgr.shape[:2]:
        return bgr
    return cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA)


def normalize_image(src: Path, dest: Path, thumb: Path) -> tuple[int, int]:
    bgr = cv2.imread(str(src))
    if bgr is None:
        raise ValueError(f"cannot read image {src}")
    out = _scale_bgr(bgr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), out, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    cv2.imwrite(str(thumb), out, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    h, w = out.shape[:2]
    return int(w), int(h)


def write_thumb_from_video(src: Path, thumb: Path, t_ms: float = 0.0) -> None:
    cap = cv2.VideoCapture(str(src))
    if t_ms > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, t_ms)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise ValueError(f"cannot grab thumbnail from {src}")
    thumb.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(thumb), _scale_bgr(frame), [int(cv2.IMWRITE_JPEG_QUALITY), 80])


def normalize_video(
    src: Path,
    dest: Path,
    thumb: Path,
    *,
    start_s: float = 0.0,
    duration_s: float | None = None,
) -> tuple[int, int, float, int]:
    ffmpeg = find_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dur = duration_s if duration_s is not None else MAX_SECONDS
    dur = min(max(dur, 0.1), MAX_SECONDS)
    if ffmpeg:
        vf = (
            "scale=-2:'min(720,ih)',"
            "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30"
        )
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            f"{start_s:.3f}",
            "-i",
            str(src),
            "-t",
            f"{dur:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        err = proc.stderr or ""
        if proc.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)
            raise RuntimeError(err[-2000:] if err else "ffmpeg failed")
    else:
        _normalize_video_cv2(src, dest, start_s=start_s, duration_s=dur)
    write_thumb_from_video(dest, thumb, 0.0)
    w, h, fps = probe_size(dest)
    duration_ms = int(probe_duration_ms(dest))
    return w, h, fps, duration_ms


def _normalize_video_cv2(
    src: Path, dest: Path, *, start_s: float, duration_s: float
) -> None:
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise ValueError(f"cannot open video {src}")
    cap.set(cv2.CAP_PROP_POS_MSEC, start_s * 1000.0)
    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        raise ValueError("empty video")
    frame = _scale_bgr(frame)
    h, w = frame.shape[:2]
    writer = cv2.VideoWriter(
        str(dest), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (w, h)
    )
    end_ms = (start_s + duration_s) * 1000.0
    while ok and frame is not None:
        t = float(cap.get(cv2.CAP_PROP_POS_MSEC))
        if t > end_ms + 40:
            break
        writer.write(_scale_bgr(frame))
        ok, frame = cap.read()
    writer.release()
    cap.release()
