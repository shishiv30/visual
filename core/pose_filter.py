"""Person-gate, geometric veto, and temporal smoothing for COCO-17 poses."""

from __future__ import annotations

from schemas.core_inference import (
    CoreInferenceResult,
    Detection,
    ErrorCode,
    InferenceError,
    Keypoint,
    Pose,
)

MAX_BBOX_ASPECT = 3.2
MAX_HEIGHT_OVER_SHOULDER = 4.5
MAX_FULL_HEIGHT_FRAC = 0.90
MIN_FULL_WIDTH_FRAC = 0.35
MIN_SHOULDER_VIS = 0.30
MIN_HEAD_VIS = 0.20
EMA_ALPHA = 0.45
CROP_PAD = 0.28
TALL_CROP_KEEP_BOTTOM = 0.55


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def pick_primary(
    result: CoreInferenceResult,
    prev_bbox: tuple[float, float, float, float] | None,
) -> CoreInferenceResult:
    if len(result.poses) <= 1:
        return result
    best_i = 0
    best = -1.0
    for i, pose in enumerate(result.poses):
        det_i = pose.detection_index
        score = pose.score
        if 0 <= det_i < len(result.detections) and prev_bbox is not None:
            score = score + bbox_iou(result.detections[det_i].bbox_xyxy, prev_bbox)
        if score > best:
            best = score
            best_i = i
    pose = result.poses[best_i]
    det_i = pose.detection_index
    det = result.detections[det_i] if 0 <= det_i < len(result.detections) else None
    pose.detection_index = 0
    result.poses = [pose]
    result.detections = [det] if det is not None else []
    return result


def _kp(pose: Pose, name: str) -> Keypoint | None:
    for kp in pose.keypoints:
        if kp.name == name:
            return kp
    return None


def is_plausible(result: CoreInferenceResult) -> bool:
    if result.error is not None or not result.poses or not result.detections:
        return False
    pose = result.poses[0]
    x1, y1, x2, y2 = result.detections[0].bbox_xyxy
    width = max(1.0, x2 - x1)
    height = max(0.0, y2 - y1)
    frame_w = float(result.frame.width)
    frame_h = float(result.frame.height)
    if height / width > MAX_BBOX_ASPECT:
        return False
    if height > MAX_FULL_HEIGHT_FRAC * frame_h and width < MIN_FULL_WIDTH_FRAC * frame_w:
        return False
    left_s = _kp(pose, "left_shoulder")
    right_s = _kp(pose, "right_shoulder")
    if (
        left_s is not None
        and right_s is not None
        and left_s.confidence >= MIN_SHOULDER_VIS
        and right_s.confidence >= MIN_SHOULDER_VIS
    ):
        shoulder = abs(left_s.x - right_s.x)
        if shoulder > 1.0 and height / shoulder > MAX_HEIGHT_OVER_SHOULDER:
            return False
    head_vis = 0.0
    n_head = 0
    for name in ("nose", "left_eye", "right_eye", "left_ear", "right_ear"):
        kp = _kp(pose, name)
        if kp is None:
            continue
        head_vis += kp.confidence
        n_head += 1
    if n_head and (head_vis / n_head) < MIN_HEAD_VIS:
        return False
    return True


def _named(result: CoreInferenceResult, name: str) -> Keypoint | None:
    if not result.poses:
        return None
    return _kp(result.poses[0], name)


def _pair_mid(
    result: CoreInferenceResult, left: str, right: str
) -> tuple[float, float] | None:
    a = _named(result, left)
    b = _named(result, right)
    if a is None or b is None:
        return None
    if a.confidence < MIN_SHOULDER_VIS or b.confidence < MIN_SHOULDER_VIS:
        return None
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def torso_length(result: CoreInferenceResult) -> float:
    if not result.poses:
        return 0.0
    sh = _pair_mid(result, "left_shoulder", "right_shoulder")
    hp = _pair_mid(result, "left_hip", "right_hip")
    if sh is None or hp is None:
        return 0.0
    return ((sh[0] - hp[0]) ** 2 + (sh[1] - hp[1]) ** 2) ** 0.5


def pose_center_jump(a: CoreInferenceResult, b: CoreInferenceResult) -> float:
    am = _pair_mid(a, "left_hip", "right_hip") or _pair_mid(
        a, "left_shoulder", "right_shoulder"
    )
    bm = _pair_mid(b, "left_hip", "right_hip") or _pair_mid(
        b, "left_shoulder", "right_shoulder"
    )
    if am is None or bm is None:
        return 0.0
    return ((am[0] - bm[0]) ** 2 + (am[1] - bm[1]) ** 2) ** 0.5


def relative_jump(a: CoreInferenceResult, b: CoreInferenceResult) -> float:
    scale = max(torso_length(a), torso_length(b), 1.0)
    return pose_center_jump(a, b) / scale


def crop_disagrees_with_prev(
    prev: CoreInferenceResult | None, curr: CoreInferenceResult
) -> bool:
    if prev is None or not prev.poses or not curr.poses:
        return False
    t_prev = torso_length(prev)
    t_curr = torso_length(curr)
    if t_prev > 1.0 and t_curr / t_prev < 0.75:
        return True
    if relative_jump(prev, curr) > 0.35:
        return True
    return False


def reject_implausible(result: CoreInferenceResult) -> CoreInferenceResult:
    if result.error is not None:
        return result
    if is_plausible(result):
        return result
    result.detections = []
    result.poses = []
    result.error = InferenceError(
        code=ErrorCode.LOW_CONFIDENCE,
        message="pose rejected: extreme aspect or low head/shoulder visibility",
    )
    return result


def crop_box_for_retry(
    bbox: tuple[float, float, float, float],
    frame_w: int,
    frame_h: int,
    *,
    keep_bottom: float = TALL_CROP_KEEP_BOTTOM,
    pad: float = CROP_PAD,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    y1 = y1 + bh * (1.0 - keep_bottom)
    pad_x = bw * pad
    pad_y = bh * pad * keep_bottom
    nx1 = int(max(0.0, x1 - pad_x))
    ny1 = int(max(0.0, y1 - pad_y))
    nx2 = int(min(float(frame_w), x2 + pad_x))
    ny2 = int(min(float(frame_h), y2 + pad_y))
    if nx2 <= nx1 or ny2 <= ny1:
        return 0, 0, frame_w, frame_h
    return nx1, ny1, nx2, ny2


def remap_to_full(
    result: CoreInferenceResult,
    ox: int,
    oy: int,
    full_w: int,
    full_h: int,
) -> CoreInferenceResult:
    result.frame.width = full_w
    result.frame.height = full_h
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox_xyxy
        det.bbox_xyxy = (x1 + ox, y1 + oy, x2 + ox, y2 + oy)
    for pose in result.poses:
        for kp in pose.keypoints:
            kp.x += ox
            kp.y += oy
    return result


def ema_smooth(
    prev: CoreInferenceResult | None,
    curr: CoreInferenceResult,
    *,
    alpha: float = EMA_ALPHA,
) -> CoreInferenceResult:
    if (
        prev is None
        or prev.error is not None
        or not prev.poses
        or curr.error is not None
        or not curr.poses
    ):
        return curr
    prev_kps = prev.poses[0].keypoints
    curr_kps = curr.poses[0].keypoints
    if len(prev_kps) != len(curr_kps):
        return curr
    for a, b in zip(prev_kps, curr_kps):
        if b.confidence < 0.2:
            b.x, b.y, b.z = a.x, a.y, a.z
            continue
        b.x = alpha * b.x + (1.0 - alpha) * a.x
        b.y = alpha * b.y + (1.0 - alpha) * a.y
        b.z = alpha * b.z + (1.0 - alpha) * a.z
    if prev.detections and curr.detections:
        px = prev.detections[0].bbox_xyxy
        cx = curr.detections[0].bbox_xyxy
        curr.detections[0].bbox_xyxy = (
            alpha * cx[0] + (1.0 - alpha) * px[0],
            alpha * cx[1] + (1.0 - alpha) * px[1],
            alpha * cx[2] + (1.0 - alpha) * px[2],
            alpha * cx[3] + (1.0 - alpha) * px[3],
        )
    return curr
