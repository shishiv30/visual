"""Score frames 0–100 and fill low-score gaps from high-score neighbors."""

from __future__ import annotations

from core.pose_filter import relative_jump, torso_length
from schemas.clip_analysis import AnalyzedFrame, BlazeJoint
from schemas.core_inference import (
    CoreInferenceResult,
    ErrorCode,
    Keypoint,
    Pose,
)

HIGH_SCORE = 55.0
LOW_SCORE = 40.0
MAX_GAP_MS = 400.0
HOLD_MS = 200.0
INTERP_CONF_SCALE = 0.85
SPIKE_JUMP = 0.22
NEIGHBOR_JUMP = 0.15
SCALE_LO = 0.75
SCALE_HI = 1.35
MAX_SPIKE_RUN = 2
TORSO_NAMES = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
)
BLAZE_N = 33
#: Below this, one landmark (not necessarily the whole pose) is weak enough
#: that ``stabilize_weak_joints`` will try to bridge it from neighbors before
#: any per-metric consumer has to gate it out. Above it, the joint is left
#: alone even though a metric's own, usually stricter, confidence gate may
#: still discount or drop it later.
JOINT_CONF_MIN = 0.35


def frame_score(result: CoreInferenceResult) -> float:
    if not result.poses:
        return 0.0
    if result.error is not None and result.error.code in {
        ErrorCode.NO_PERSON,
        ErrorCode.LOW_CONFIDENCE,
    }:
        return 0.0
    pose = result.poses[0]
    base = max(0.0, min(100.0, pose.score * 100.0))
    named = {kp.name: kp for kp in pose.keypoints}
    vis = [named[name].confidence for name in TORSO_NAMES if name in named]
    if vis:
        torso = (sum(vis) / len(vis)) * 100.0
        base = 0.85 * base + 0.15 * torso
    return max(0.0, min(100.0, base))


def _kp_map(pose: Pose) -> dict[str, Keypoint]:
    return {kp.name: kp for kp in pose.keypoints}


def _lerp(a: float, b: float, w: float) -> float:
    return (1.0 - w) * a + w * b


def _hold_pose(anchor: CoreInferenceResult, curr: CoreInferenceResult) -> CoreInferenceResult:
    out = anchor.model_copy(deep=True)
    out.frame = curr.frame.model_copy(deep=True)
    out.model_meta = curr.model_meta.model_copy(deep=True)
    out.error = None
    if not out.poses:
        return curr
    out.poses[0].score = min(1.0, out.poses[0].score * INTERP_CONF_SCALE)
    for kp in out.poses[0].keypoints:
        kp.confidence = min(1.0, kp.confidence * INTERP_CONF_SCALE)
    if out.detections:
        out.detections[0].confidence = min(
            1.0, out.detections[0].confidence * INTERP_CONF_SCALE
        )
    return out


def _lerp_pose(
    left: CoreInferenceResult,
    right: CoreInferenceResult,
    curr: CoreInferenceResult,
    weight: float,
) -> CoreInferenceResult:
    out = left.model_copy(deep=True)
    out.frame = curr.frame.model_copy(deep=True)
    out.model_meta = curr.model_meta.model_copy(deep=True)
    out.error = None
    if not out.poses or not right.poses:
        return curr
    lp = out.poses[0]
    rp = right.poses[0]
    lmap = _kp_map(lp)
    rmap = _kp_map(rp)
    blended: list[Keypoint] = []
    for name, a in lmap.items():
        b = rmap.get(name)
        if b is None:
            copied = a.model_copy()
            copied.confidence = min(1.0, copied.confidence * INTERP_CONF_SCALE)
            blended.append(copied)
            continue
        z = None
        if a.z is not None and b.z is not None:
            z = _lerp(a.z, b.z, weight)
        blended.append(
            Keypoint(
                name=name,
                x=_lerp(a.x, b.x, weight),
                y=_lerp(a.y, b.y, weight),
                z=z,
                confidence=min(1.0, min(a.confidence, b.confidence) * INTERP_CONF_SCALE),
            )
        )
    lp.keypoints = blended
    lp.score = min(1.0, min(lp.score, rp.score) * INTERP_CONF_SCALE)
    lp.detection_index = 0
    if out.detections and right.detections:
        lb = out.detections[0].bbox_xyxy
        rb = right.detections[0].bbox_xyxy
        out.detections[0].bbox_xyxy = (
            _lerp(lb[0], rb[0], weight),
            _lerp(lb[1], rb[1], weight),
            _lerp(lb[2], rb[2], weight),
            _lerp(lb[3], rb[3], weight),
        )
        out.detections[0].confidence = min(
            1.0,
            min(out.detections[0].confidence, right.detections[0].confidence)
            * INTERP_CONF_SCALE,
        )
    return out


def _nearest_high(scores: list[float], start: int, step: int) -> int | None:
    i = start
    n = len(scores)
    while 0 <= i < n:
        if scores[i] >= HIGH_SCORE:
            return i
        i += step
    return None


def fill_low_score_poses(frames: list[AnalyzedFrame]) -> list[AnalyzedFrame]:
    if len(frames) <= 1:
        return frames
    scores = [frame_score(item.result) for item in frames]
    n = len(frames)
    i = 0
    while i < n:
        if scores[i] >= LOW_SCORE:
            i += 1
            continue
        j = i
        while j < n and scores[j] < LOW_SCORE:
            j += 1
        left_i = _nearest_high(scores, i - 1, -1)
        right_i = _nearest_high(scores, j, 1)
        if left_i is not None and right_i is not None:
            t_left = frames[left_i].t_ms
            t_right = frames[right_i].t_ms
            if 0.0 < (t_right - t_left) <= MAX_GAP_MS:
                span = t_right - t_left
                left = frames[left_i].result
                right = frames[right_i].result
                for k in range(i, j):
                    w = (frames[k].t_ms - t_left) / span
                    frames[k].result = _lerp_pose(left, right, frames[k].result, w)
        elif left_i is not None:
            t_left = frames[left_i].t_ms
            left = frames[left_i].result
            for k in range(i, j):
                if frames[k].t_ms - t_left <= HOLD_MS:
                    frames[k].result = _hold_pose(left, frames[k].result)
        elif right_i is not None:
            t_right = frames[right_i].t_ms
            right = frames[right_i].result
            for k in range(i, j):
                if t_right - frames[k].t_ms <= HOLD_MS:
                    frames[k].result = _hold_pose(right, frames[k].result)
        i = j
    return frames


def _has_pose(result: CoreInferenceResult) -> bool:
    return bool(result.poses) and result.error is None


def is_spike_frame(
    prev: CoreInferenceResult,
    curr: CoreInferenceResult,
    nxt: CoreInferenceResult,
) -> bool:
    if not (_has_pose(prev) and _has_pose(curr) and _has_pose(nxt)):
        return False
    if relative_jump(prev, nxt) > NEIGHBOR_JUMP:
        return False
    mean_torso = (torso_length(prev) + torso_length(nxt)) / 2.0
    curr_torso = torso_length(curr)
    if mean_torso > 1.0:
        scale = curr_torso / mean_torso
        if scale < SCALE_LO or scale > SCALE_HI:
            return True
    jumped = (
        relative_jump(prev, curr) > SPIKE_JUMP
        and relative_jump(nxt, curr) > SPIKE_JUMP
    )
    return jumped


def _lerp_blaze(
    left: list[BlazeJoint] | None,
    right: list[BlazeJoint] | None,
    weight: float,
) -> list[BlazeJoint] | None:
    if left is None and right is None:
        return None
    if left is None:
        return [j.model_copy() for j in right or []]
    if right is None or len(left) != len(right):
        return [j.model_copy() for j in left]
    out: list[BlazeJoint] = []
    for a, b in zip(left, right):
        out.append(
            BlazeJoint(
                x=_lerp(a.x, b.x, weight),
                y=_lerp(a.y, b.y, weight),
                z=_lerp(a.z, b.z, weight),
                confidence=min(1.0, min(a.confidence, b.confidence) * INTERP_CONF_SCALE),
            )
        )
    return out


def _blend_analyzed(
    frames: list[AnalyzedFrame],
    index: int,
    left_i: int,
    right_i: int,
) -> None:
    span = frames[right_i].t_ms - frames[left_i].t_ms
    if span <= 0.0:
        return
    w = (frames[index].t_ms - frames[left_i].t_ms) / span
    frames[index].result = _lerp_pose(
        frames[left_i].result,
        frames[right_i].result,
        frames[index].result,
        w,
    )
    frames[index].blaze33 = _lerp_blaze(
        frames[left_i].blaze33,
        frames[right_i].blaze33,
        w,
    )


def stabilize_pose_sequence(frames: list[AnalyzedFrame]) -> list[AnalyzedFrame]:
    n = len(frames)
    if n < 3:
        return frames
    replaced = [False] * n
    for i in range(1, n - 1):
        if replaced[i]:
            continue
        left_i, right_i = i - 1, i + 1
        if frames[right_i].t_ms - frames[left_i].t_ms > MAX_GAP_MS:
            continue
        if not is_spike_frame(
            frames[left_i].result, frames[i].result, frames[right_i].result
        ):
            continue
        _blend_analyzed(frames, i, left_i, right_i)
        replaced[i] = True
    for i in range(1, n - 2):
        if replaced[i] or replaced[i + 1]:
            continue
        left_i, right_i = i - 1, i + 2
        if frames[right_i].t_ms - frames[left_i].t_ms > MAX_GAP_MS:
            continue
        if (right_i - left_i - 1) > MAX_SPIKE_RUN:
            continue
        left = frames[left_i].result
        right = frames[right_i].result
        a = frames[i].result
        b = frames[i + 1].result
        if not is_spike_frame(left, a, right) or not is_spike_frame(left, b, right):
            continue
        _blend_analyzed(frames, i, left_i, right_i)
        _blend_analyzed(frames, i + 1, left_i, right_i)
        replaced[i] = True
        replaced[i + 1] = True
    return frames


def _lerp_joint(left: BlazeJoint, right: BlazeJoint, weight: float) -> BlazeJoint:
    return BlazeJoint(
        x=_lerp(left.x, right.x, weight),
        y=_lerp(left.y, right.y, weight),
        z=_lerp(left.z, right.z, weight),
        confidence=min(1.0, min(left.confidence, right.confidence) * INTERP_CONF_SCALE),
    )


def _hold_joint(anchor: BlazeJoint) -> BlazeJoint:
    return BlazeJoint(
        x=anchor.x,
        y=anchor.y,
        z=anchor.z,
        confidence=min(1.0, anchor.confidence * INTERP_CONF_SCALE),
    )


def stabilize_weak_joints(
    frames: list[AnalyzedFrame], conf_min: float = JOINT_CONF_MIN
) -> list[AnalyzedFrame]:
    """Bridge one landmark's short confidence dip from its own neighbors.

    ``fill_low_score_poses`` already does this at the whole-pose level, keyed
    off the frame's overall score. That leaves the common ski case
    unaddressed: the torso tracks perfectly all the way through a turn but one
    ankle or foot drops out for a few frames — occluded by snow spray, motion
    blur, or a self-occlusion at full flex — while the rest of the skeleton
    stays confident. A frame like that never triggers the whole-frame path
    (its overall score is fine), so the weak joint used to sit at its raw,
    noisy coordinates until a metric's own confidence gate dropped it or (the
    bug this fixes) it became the "most extreme" sample and got shown to the
    coach as evidence.

    This runs per landmark index, independently of every other joint, with
    the exact same ``MAX_GAP_MS``/``HOLD_MS`` policy as the whole-frame
    version: a short gap flanked by two well-tracked samples is linearly
    interpolated between them; a gap open on only one side is held from
    that side, decaying via ``INTERP_CONF_SCALE`` so it is never mistaken for
    a fresh measurement; a gap with no well-tracked anchor on either side
    (or longer than ``MAX_GAP_MS``) is left alone, since there is nothing
    real to interpolate from. Every per-metric confidence gate downstream
    (``turns.landmark_arrays``' CONF_MIN, the evidence-frame bar) still
    applies on top of this — it only gives those gates a better-populated
    series to gate over, it does not replace them.
    """
    n = len(frames)
    if n < 2:
        return frames
    for j in range(BLAZE_N):
        conf = [
            frame.blaze33[j].confidence
            if frame.blaze33 is not None and len(frame.blaze33) > j
            else 0.0
            for frame in frames
        ]
        i = 0
        while i < n:
            if conf[i] >= conf_min:
                i += 1
                continue
            k = i
            while k < n and conf[k] < conf_min:
                k += 1
            left_i = i - 1 if i > 0 and conf[i - 1] >= conf_min else None
            right_i = k if k < n and conf[k] >= conf_min else None
            if left_i is not None and right_i is not None:
                t_left = frames[left_i].t_ms
                t_right = frames[right_i].t_ms
                if 0.0 < (t_right - t_left) <= MAX_GAP_MS:
                    left_joint = frames[left_i].blaze33[j]
                    right_joint = frames[right_i].blaze33[j]
                    span = t_right - t_left
                    for m in range(i, k):
                        joints = frames[m].blaze33
                        if joints is None or len(joints) <= j:
                            continue
                        w = (frames[m].t_ms - t_left) / span
                        joints[j] = _lerp_joint(left_joint, right_joint, w)
            elif left_i is not None:
                t_left = frames[left_i].t_ms
                left_joint = frames[left_i].blaze33[j]
                for m in range(i, k):
                    if frames[m].t_ms - t_left <= HOLD_MS:
                        joints = frames[m].blaze33
                        if joints is not None and len(joints) > j:
                            joints[j] = _hold_joint(left_joint)
            elif right_i is not None:
                t_right = frames[right_i].t_ms
                right_joint = frames[right_i].blaze33[j]
                for m in range(i, k):
                    if t_right - frames[m].t_ms <= HOLD_MS:
                        joints = frames[m].blaze33
                        if joints is not None and len(joints) > j:
                            joints[j] = _hold_joint(right_joint)
            i = k
    return frames
