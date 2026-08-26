"""HSV appearance ROI: histogram + CamShift search + pose crop remap."""

from __future__ import annotations

import cv2
import numpy as np

from schemas.core_inference import CoreInferenceResult

HIST_H_BINS = 30
HIST_S_BINS = 32
MIN_SAT = 40
MAX_VAL = 250
SEARCH_EXPAND = 1.8
POSE_PAD = 0.35
MIN_CROP_SIDE = 256
TERM = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 12, 1)


def _clip_box(
    box: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    nx1 = int(max(0.0, min(x1, x2)))
    ny1 = int(max(0.0, min(y1, y2)))
    nx2 = int(min(width, max(x1, x2)))
    ny2 = int(min(height, max(y1, y2)))
    if nx2 <= nx1 or ny2 <= ny1:
        return 0, 0, width, height
    return nx1, ny1, nx2, ny2


def denorm_box(
    seed: tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = seed
    return x1 * width, y1 * height, x2 * width, y2 * height


def _hsv_clahe(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    hue, sat, val = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    val = clahe.apply(val)
    return cv2.merge((hue, sat, val))


def build_hist(bgr: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    h, w = bgr.shape[:2]
    x1, y1, x2, y2 = _clip_box(box, w, h)
    roi = bgr[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, MIN_SAT, 32), (180, 255, MAX_VAL))
    hist = cv2.calcHist([hsv], [0, 1], mask, [HIST_H_BINS, HIST_S_BINS], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 255, cv2.NORM_MINMAX)
    return hist


def _expand_window(
    box: tuple[float, float, float, float], width: int, height: int, scale: float
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    cx = 0.5 * (x1 + x2)
    cy = 0.5 * (y1 + y2)
    bw = max(8.0, (x2 - x1) * scale)
    bh = max(8.0, (y2 - y1) * scale)
    nx1 = int(max(0.0, cx - bw / 2.0))
    ny1 = int(max(0.0, cy - bh / 2.0))
    nw = int(min(width - nx1, bw))
    nh = int(min(height - ny1, bh))
    return nx1, ny1, max(1, nw), max(1, nh)


def search(
    bgr: np.ndarray,
    hist: np.ndarray,
    prev_box: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    height, width = bgr.shape[:2]
    hsv = _hsv_clahe(bgr)
    back = cv2.calcBackProject([hsv], [0, 1], hist, [0, 180, 0, 256], 1)
    x, y, w, h = _expand_window(prev_box, width, height, SEARCH_EXPAND)
    window = (x, y, w, h)
    try:
        _rot, window = cv2.CamShift(back, window, TERM)
        tx, ty, tw, th = window
        if tw >= 8 and th >= 8:
            return float(tx), float(ty), float(tx + tw), float(ty + th)
    except cv2.error:
        pass
    small = cv2.resize(back, (max(1, width // 4), max(1, height // 4)))
    _, _, _, max_loc = cv2.minMaxLoc(small)
    px = max_loc[0] * 4
    py = max_loc[1] * 4
    bw = max(16.0, prev_box[2] - prev_box[0])
    bh = max(16.0, prev_box[3] - prev_box[1])
    return (
        float(max(0, px - bw / 2)),
        float(max(0, py - bh / 2)),
        float(min(width, px + bw / 2)),
        float(min(height, py + bh / 2)),
    )


def crop_for_pose(
    bgr: np.ndarray,
    box: tuple[float, float, float, float],
    *,
    pad: float = POSE_PAD,
    min_side: int = MIN_CROP_SIDE,
) -> tuple[np.ndarray, int, int, float]:
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = box
    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    padded = (x1 - bw * pad, y1 - bh * pad, x2 + bw * pad, y2 + bh * pad)
    ox, oy, x2c, y2c = _clip_box(padded, width, height)
    crop = bgr[oy:y2c, ox:x2c]
    if crop.size == 0:
        return bgr, 0, 0, 1.0
    ch, cw = crop.shape[:2]
    scale = 1.0
    shortest = min(ch, cw)
    if shortest < min_side:
        scale = min_side / float(shortest)
        crop = cv2.resize(
            crop,
            (int(cw * scale), int(ch * scale)),
            interpolation=cv2.INTER_LINEAR,
        )
    return crop, ox, oy, scale


def remap_from_crop(
    result: CoreInferenceResult,
    ox: int,
    oy: int,
    scale: float,
    full_w: int,
    full_h: int,
) -> CoreInferenceResult:
    inv = 1.0 / scale if scale else 1.0
    result.frame.width = full_w
    result.frame.height = full_h
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox_xyxy
        det.bbox_xyxy = (
            x1 * inv + ox,
            y1 * inv + oy,
            x2 * inv + ox,
            y2 * inv + oy,
        )
    for pose in result.poses:
        for kp in pose.keypoints:
            kp.x = kp.x * inv + ox
            kp.y = kp.y * inv + oy
    return result


def blend_hist(prev: np.ndarray, new: np.ndarray, alpha: float = 0.15) -> np.ndarray:
    mixed = (1.0 - alpha) * prev.astype(np.float32) + alpha * new.astype(np.float32)
    cv2.normalize(mixed, mixed, 0, 255, cv2.NORM_MINMAX)
    return mixed


def first_frame_bgr(path: str) -> np.ndarray | None:
    image = cv2.imread(path)
    if image is not None:
        return image
    cap = cv2.VideoCapture(path)
    ok, frame = cap.read()
    cap.release()
    if ok and frame is not None:
        return frame
    return None
