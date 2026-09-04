"""Turn segmentation for ski clips (design v3 §3.3).

This module turns a ``ClipAnalysis`` frame sequence into a list of :class:`Turn`
records so that curriculum gates phrased as *"20 consecutive turns, at most 2
faulty"* become computable. It is additive: nothing here touches
``core/sports/signals.py`` (v2), which keeps working unchanged.

Algorithm, following design §3.3 step by step
---------------------------------------------

1. **Steering signal.** ``theta(t)`` is the signed angle, in degrees, of the
   body axis ``hip_mid -> ankle_mid`` measured against the smoothed path
   tangent of the hip trajectory. When the skier steers, the feet swing to one
   side of the direction of travel while the hips stay closer to the path, so
   the sign of ``theta`` is the sign of the arc and its magnitude grows with
   the steering effort. The tangent is taken from the hip path smoothed over
   ~1.0 s, i.e. the *path*, not the per-frame wiggle; if the hips barely move
   (follow camera) the tangent degrades to the mean displacement direction and
   finally to image-down ``(0, +1)``. ``tangent_source`` on
   :class:`SteeringSignal` records which was used.

2. **Low-pass at 2 Hz.** Implemented as a **zero-phase centred moving average
   (boxcar) applied twice**, with edge-value replication padding — no scipy, no
   phase shift, so turn boundaries are not displaced in time. The tap count
   comes from the standard boxcar rule ``N ~= 0.443 * fs / fc`` (the -3 dB
   point of an N-tap moving average), forced odd and at least 3. Two passes
   give a steeper roll-off than one while staying symmetric.

3. **Boundaries.** Zero crossings of the bias-removed signal, gated by a
   hysteresis band ``h = max(2 deg, 0.15 * p90(|theta|))``. A confirmed side
   change emits a boundary at the interpolated zero crossing. A flip that
   arrives sooner than ``MIN_TURN_S`` after the previous boundary is ignored
   (debounce), which both enforces the minimum turn duration and guarantees
   that sides strictly alternate.

4. **Amplitude reject.** An arc whose peak ``|theta|`` is below
   ``MIN_AMPLITUDE_DEG`` is a traverse, not a turn, and is dropped.

5. **Phases.** ``initiation`` / ``shaping`` / ``finish`` are the three thirds of
   the arc; ``transition`` is centred on the *start* boundary with a half-width
   of ``TRANSITION_FRAC`` of the arc duration (design: "±15 % of the boundary
   window"), clamped to the clip's time range.

Partial arcs at the two ends of the clip are discarded: a turn needs both of
its boundaries to be observed.

Sign / side convention
----------------------
``theta > 0`` means the ankles sit on the +x (screen-right) side of the path
tangent, which is what happens when the skier steers toward screen-left. Such
an arc is labelled ``"L"``. Sides are therefore **screen-relative**; a caller
that knows the camera faces the skier's back rather than the front can flip
them. The labels always alternate, so a mirror flip is a relabel, never a
resegmentation.

Everything is pure numpy + stdlib, and every public entry point is defensive:
missing hips, a constant signal, an all-low-confidence clip, or a five-frame
clip all return an empty turn list rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from schemas.clip_analysis import AnalyzedFrame

# BlazePose-33 indices (same numbering as core/sports/signals.py).
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT, R_FOOT = 31, 32
BLAZE_N = 33

#: Same visibility gate as v2 (``signals.py:18``), kept so the two layers agree
#: on which frames are usable.
CONF_MIN = 0.25

LOWPASS_HZ = 2.0
#: -3 dB point of an N-tap moving average is ~0.443 * fs / N.
BOXCAR_GAIN = 0.443
#: Number of zero-phase boxcar passes.
LOWPASS_PASSES = 2
#: Path tangent smoothing window, seconds.
TANGENT_WINDOW_S = 1.0

MIN_TURN_S = 0.35
MIN_AMPLITUDE_DEG = 8.0
#: Steering angle above this is almost always follow-cam / path-tangent noise,
#: not real edge steering. Clipping keeps turn_rate honest and stops wedge
#: stages from winning on saturated ``turn_amplitude`` membership.
MAX_STEERING_DEG = 50.0
#: Amplitude is p90(|theta|) inside the arc, not the spike max.
AMPLITUDE_PERCENTILE = 90.0
HYSTERESIS_FRAC = 0.15
HYSTERESIS_MIN_DEG = 2.0
TRANSITION_FRAC = 0.15

#: Below this the hip path carries no usable direction (pixels per second).
MIN_PATH_SPEED_PX_S = 1.0
#: A steering signal needs at least this fraction of frames with hips+ankles.
MIN_USABLE_FRACTION = 0.5
MIN_SIGNAL_SAMPLES = 6
FPS_FLOOR = 1.0

Window = tuple[float, float]


@dataclass
class LandmarkArrays:
    """Landmarks as ``nan``-holed arrays, shared with ``core.sports.metrics``.

    ``x``/``y`` are ``(n_frames, 33)`` pixel arrays holding ``nan`` wherever a
    landmark is absent or below ``conf_min``. Working in ``nan`` space means
    every downstream formula propagates missingness for free and the aggregate
    step can use nan-aware robust statistics, instead of v2's pattern of
    appending to per-signal lists that silently lose frame alignment.
    """

    t_ms: np.ndarray
    x: np.ndarray
    y: np.ndarray
    conf: np.ndarray

    @property
    def n(self) -> int:
        return int(self.t_ms.size)

    def point(self, index: int) -> np.ndarray:
        """``(n, 2)`` array for one landmark."""
        return np.stack([self.x[:, index], self.y[:, index]], axis=1)

    def mid(self, left: int, right: int) -> np.ndarray:
        """Midpoint of a landmark pair, ``nan`` unless **both** are present.

        A one-sided fallback is deliberately not used: it would displace the
        midpoint by half the segment width and show up as a fake lateral
        offset in every metric normalised on that midpoint.
        """
        a = self.point(left)
        b = self.point(right)
        return 0.5 * (a + b)


def landmark_arrays(
    frames: list[AnalyzedFrame], conf_min: float = CONF_MIN
) -> LandmarkArrays:
    """Build :class:`LandmarkArrays` from analysed frames.

    Frames without ``blaze33`` (or with a short list) contribute an all-``nan``
    row so the time axis stays intact — dropping them, as v2 does, breaks any
    metric that needs a rate or a per-turn window.
    """
    n = len(frames)
    x = np.full((n, BLAZE_N), np.nan, dtype=np.float64)
    y = np.full((n, BLAZE_N), np.nan, dtype=np.float64)
    conf = np.zeros((n, BLAZE_N), dtype=np.float64)
    t_ms = np.zeros(n, dtype=np.float64)
    for i, frame in enumerate(frames):
        t_ms[i] = float(frame.t_ms)
        joints = frame.blaze33
        if joints is None or len(joints) < BLAZE_N:
            continue
        for j in range(BLAZE_N):
            joint = joints[j]
            conf[i, j] = float(joint.confidence)
            if joint.confidence < conf_min:
                continue
            if not np.isfinite(joint.x) or not np.isfinite(joint.y):
                continue
            x[i, j] = float(joint.x)
            y[i, j] = float(joint.y)
    return LandmarkArrays(t_ms=t_ms, x=x, y=y, conf=conf)


@dataclass
class Turn:
    """One segmented arc.

    ``t_start_ms``/``t_end_ms`` are the interpolated boundary times. The four
    phase windows are ``(start_ms, end_ms)`` pairs; ``transition`` straddles
    ``t_start_ms`` and therefore overlaps the previous turn's finish, which is
    exactly what an edge change is.
    """

    index: int
    t_start_ms: float
    t_end_ms: float
    side: str
    amplitude_deg: float
    duration_s: float
    transition: Window
    initiation: Window
    shaping: Window
    finish: Window

    def window(self, phase: str) -> Window:
        """Window by name; ``"all"`` returns the whole arc."""
        if phase == "all":
            return (self.t_start_ms, self.t_end_ms)
        try:
            value = getattr(self, phase)
        except AttributeError as exc:  # pragma: no cover - programmer error
            raise KeyError(phase) from exc
        if not isinstance(value, tuple):  # pragma: no cover - programmer error
            raise KeyError(phase)
        return value


@dataclass
class SteeringSignal:
    """Filtered steering angle plus the provenance a caller needs to trust it."""

    t_ms: np.ndarray
    theta_deg: np.ndarray
    valid: np.ndarray
    tangent_source: str
    hysteresis_deg: float
    usable_fraction: float

    @property
    def ok(self) -> bool:
        return bool(
            self.t_ms.size >= MIN_SIGNAL_SAMPLES
            and np.all(np.isfinite(self.theta_deg))
        )


def safe_fps(fps_effective: float) -> float:
    """Sanitise a caller-supplied frame rate: non-finite or <= 0 becomes 1 Hz."""
    value = float(fps_effective) if fps_effective is not None else float("nan")
    if not np.isfinite(value) or value < FPS_FLOOR:
        return FPS_FLOOR
    return value


def _boxcar_odd(taps: float) -> int:
    if not np.isfinite(taps):
        return 3
    n = int(round(taps))
    if n < 3:
        return 3
    if n % 2 == 0:
        n += 1
    return n


def lowpass_taps(fps_effective: float, cutoff_hz: float = LOWPASS_HZ) -> int:
    """Tap count for the boxcar approximating ``cutoff_hz``."""
    fps = safe_fps(fps_effective)
    cutoff = max(float(cutoff_hz), 1e-3)
    return _boxcar_odd(BOXCAR_GAIN * fps / cutoff)


def boxcar(series: np.ndarray, taps: int, passes: int = 1) -> np.ndarray:
    """Zero-phase centred moving average with edge replication.

    Symmetric kernel, odd tap count, so the output is aligned in time with the
    input: no group delay to correct for and no boundary displacement.
    """
    out = np.asarray(series, dtype=np.float64).copy()
    if out.size == 0 or taps <= 1:
        return out
    taps = taps if taps % 2 == 1 else taps + 1
    if taps > out.size:
        taps = out.size if out.size % 2 == 1 else max(1, out.size - 1)
    if taps <= 1:
        return out
    pad = taps // 2
    kernel = np.ones(taps, dtype=np.float64) / float(taps)
    for _ in range(max(1, passes)):
        padded = np.concatenate(
            [np.full(pad, out[0]), out, np.full(pad, out[-1])]
        )
        out = np.convolve(padded, kernel, mode="valid")
    return out


def _interpolate_nans(series: np.ndarray) -> np.ndarray | None:
    """Linear fill of interior gaps, edge hold outside; ``None`` if all-``nan``."""
    values = np.asarray(series, dtype=np.float64).copy()
    good = np.isfinite(values)
    if not np.any(good):
        return None
    if np.all(good):
        return values
    idx = np.arange(values.size, dtype=np.float64)
    values[~good] = np.interp(idx[~good], idx[good], values[good])
    return values


def _mean_direction(delta: np.ndarray) -> np.ndarray | None:
    total = np.nansum(delta, axis=0)
    norm = float(np.hypot(total[0], total[1]))
    if not np.isfinite(norm) or norm <= 1e-9:
        return None
    return total / norm


def _path_tangent(
    hip_mid: np.ndarray, t_ms: np.ndarray, fps_effective: float
) -> tuple[np.ndarray, str]:
    """Unit tangent per frame from the smoothed hip path.

    Returns ``(tangent (n,2), source)`` where source is ``"path"`` (per-frame
    tangent of the smoothed path), ``"mean_path"`` (single direction, used when
    the instantaneous speed is under the floor) or ``"image_vertical"`` (the
    hips do not move at all: follow camera or a still).
    """
    n = t_ms.size
    fallback = np.tile(np.array([0.0, 1.0]), (n, 1))
    filled_x = _interpolate_nans(hip_mid[:, 0])
    filled_y = _interpolate_nans(hip_mid[:, 1])
    if filled_x is None or filled_y is None or n < 3:
        return fallback, "image_vertical"
    taps = _boxcar_odd(max(3.0, TANGENT_WINDOW_S * safe_fps(fps_effective)))
    sx = boxcar(filled_x, taps)
    sy = boxcar(filled_y, taps)
    dx = np.gradient(sx)
    dy = np.gradient(sy)
    dt = 1.0 / safe_fps(fps_effective)
    speed = np.hypot(dx, dy) / dt
    delta = np.stack([dx, dy], axis=1)
    mean_dir = _mean_direction(delta)
    finite_speed = speed[np.isfinite(speed)]
    median_speed = float(np.median(finite_speed)) if finite_speed.size else 0.0
    if mean_dir is None or median_speed < MIN_PATH_SPEED_PX_S:
        if mean_dir is None:
            return fallback, "image_vertical"
        return np.tile(mean_dir, (n, 1)), "mean_path"
    norm = np.hypot(dx, dy)
    tangent = np.empty((n, 2), dtype=np.float64)
    weak = norm <= 1e-9
    tangent[:, 0] = np.where(weak, mean_dir[0], dx / np.where(weak, 1.0, norm))
    tangent[:, 1] = np.where(weak, mean_dir[1], dy / np.where(weak, 1.0, norm))
    return tangent, "path"


def steering_signal(
    frames: list[AnalyzedFrame],
    fps_effective: float,
    arrays: LandmarkArrays | None = None,
    *,
    compensated_hip_mid: np.ndarray | None = None,
) -> SteeringSignal:
    """Signed, 2 Hz low-passed, bias-removed steering angle in degrees.

    The bias (median) is removed after filtering so that "zero" means *the mean
    steering direction of this clip*, not the image vertical: a camera that is
    off-axis, or a traverse superimposed on the turns, would otherwise push
    every crossing to one side.
    """
    fps = safe_fps(fps_effective)
    arrays = arrays if arrays is not None else landmark_arrays(frames)
    n = arrays.n
    empty = SteeringSignal(
        t_ms=arrays.t_ms,
        theta_deg=np.zeros(n, dtype=np.float64),
        valid=np.zeros(n, dtype=bool),
        tangent_source="none",
        hysteresis_deg=HYSTERESIS_MIN_DEG,
        usable_fraction=0.0,
    )
    if n < MIN_SIGNAL_SAMPLES:
        return empty
    hip_mid = arrays.mid(L_HIP, R_HIP)
    path_mid = compensated_hip_mid if compensated_hip_mid is not None else hip_mid
    ankle_mid = arrays.mid(L_ANKLE, R_ANKLE)
    axis = ankle_mid - hip_mid
    valid = np.isfinite(axis[:, 0]) & np.isfinite(axis[:, 1])
    usable = float(np.count_nonzero(valid)) / float(n)
    empty.usable_fraction = usable
    if usable < MIN_USABLE_FRACTION or np.count_nonzero(valid) < MIN_SIGNAL_SAMPLES:
        return empty
    tangent, source = _path_tangent(path_mid, arrays.t_ms, fps)
    if compensated_hip_mid is not None:
        source = "compensated"
    # Signed so that positive theta means the ankles sit on the +x side of the
    # tangent (see the module docstring); with a tangent of image-down (0, 1)
    # this reduces to atan2(dx, dy).
    cross = tangent[:, 1] * axis[:, 0] - tangent[:, 0] * axis[:, 1]
    dot = tangent[:, 0] * axis[:, 0] + tangent[:, 1] * axis[:, 1]
    raw = np.degrees(np.arctan2(cross, dot))
    raw[~valid] = np.nan
    filled = _interpolate_nans(raw)
    if filled is None:
        return empty
    taps = lowpass_taps(fps)
    smooth = boxcar(filled, taps, passes=LOWPASS_PASSES)
    smooth = smooth - float(np.median(smooth))
    smooth = np.clip(smooth, -MAX_STEERING_DEG, MAX_STEERING_DEG)
    if not np.all(np.isfinite(smooth)):
        return empty
    scale = float(np.percentile(np.abs(smooth), 90))
    hysteresis = max(HYSTERESIS_MIN_DEG, HYSTERESIS_FRAC * scale)
    return SteeringSignal(
        t_ms=arrays.t_ms,
        theta_deg=smooth,
        valid=valid,
        tangent_source=source,
        hysteresis_deg=hysteresis,
        usable_fraction=usable,
    )


def _crossing_time(t_ms: np.ndarray, theta: np.ndarray, lo: int, hi: int) -> float:
    """Interpolated zero crossing between indices ``lo`` and ``hi``."""
    for k in range(lo, min(hi, theta.size - 1)):
        a, b = theta[k], theta[k + 1]
        if a == 0.0:
            return float(t_ms[k])
        if (a > 0.0) != (b > 0.0):
            span = b - a
            if abs(span) < 1e-12:
                return float(t_ms[k])
            w = float(-a / span)
            w = min(max(w, 0.0), 1.0)
            return float(t_ms[k] + w * (t_ms[k + 1] - t_ms[k]))
    return float(t_ms[min(hi, t_ms.size - 1)])


def _boundaries(signal: SteeringSignal) -> list[float]:
    theta = signal.theta_deg
    t_ms = signal.t_ms
    h = signal.hysteresis_deg
    out: list[float] = []
    state = 0
    last_index = 0
    last_boundary: float | None = None
    for i in range(theta.size):
        value = theta[i]
        side = 1 if value > h else (-1 if value < -h else 0)
        if side == 0:
            continue
        if state == 0:
            state = side
            last_index = i
            continue
        if side == state:
            last_index = i
            continue
        crossing = _crossing_time(t_ms, theta, last_index, i)
        too_soon = (
            last_boundary is not None
            and (crossing - last_boundary) < MIN_TURN_S * 1000.0
        )
        if too_soon:
            # Debounce: too soon to be a real edge change. Ignoring the flip
            # (rather than accepting it) is what keeps sides alternating.
            continue
        if last_boundary is not None and crossing <= last_boundary:
            continue
        out.append(crossing)
        last_boundary = crossing
        state = side
        last_index = i
    return out


def _phase_windows(
    start_ms: float, end_ms: float, clip_lo: float, clip_hi: float
) -> tuple[Window, Window, Window, Window]:
    span = max(end_ms - start_ms, 1e-6)
    third = span / 3.0
    half = TRANSITION_FRAC * span
    trans_lo = max(clip_lo, start_ms - half)
    trans_hi = min(clip_hi, start_ms + half)
    if trans_hi <= trans_lo:
        trans_hi = min(clip_hi, trans_lo + 1e-3)
    return (
        (trans_lo, trans_hi),
        (start_ms, start_ms + third),
        (start_ms + third, start_ms + 2.0 * third),
        (start_ms + 2.0 * third, end_ms),
    )


def segment_turns_from_signal(signal: SteeringSignal) -> list[Turn]:
    """Segment turns from an already-computed :class:`SteeringSignal`."""
    if signal.t_ms.size < MIN_SIGNAL_SAMPLES or signal.tangent_source == "none":
        return []
    theta = signal.theta_deg
    t_ms = signal.t_ms
    bounds = _boundaries(signal)
    if len(bounds) < 2:
        return []
    clip_lo = float(t_ms[0])
    clip_hi = float(t_ms[-1])
    turns: list[Turn] = []
    for start_ms, end_ms in zip(bounds[:-1], bounds[1:]):
        duration_s = (end_ms - start_ms) / 1000.0
        if duration_s < MIN_TURN_S:
            continue
        inside = (t_ms >= start_ms) & (t_ms <= end_ms)
        if not np.any(inside):
            continue
        arc = theta[inside]
        amplitude = float(np.percentile(np.abs(arc), AMPLITUDE_PERCENTILE))
        if not np.isfinite(amplitude) or amplitude < MIN_AMPLITUDE_DEG:
            continue
        mean_theta = float(np.mean(arc))
        side = "L" if mean_theta > 0.0 else "R"
        windows = _phase_windows(start_ms, end_ms, clip_lo, clip_hi)
        turns.append(
            Turn(
                index=len(turns),
                t_start_ms=float(start_ms),
                t_end_ms=float(end_ms),
                side=side,
                amplitude_deg=amplitude,
                duration_s=duration_s,
                transition=windows[0],
                initiation=windows[1],
                shaping=windows[2],
                finish=windows[3],
            )
        )
    return turns


def segment_turns(
    frames: list[AnalyzedFrame],
    fps_effective: float,
    arrays: LandmarkArrays | None = None,
) -> list[Turn]:
    """Segment a frame sequence into turns (design §3.3).

    ``fps_effective`` must be the *sampled* frame rate (source fps ÷ frame
    stride), not ``ClipAnalysis.fps``: everything time-based downstream is
    derived from it, which is what fixes the v2 2× frequency error
    (``signals.py:266``).

    Returns ``[]`` — never raises — for a short clip, a clip with no usable
    hips or ankles, a constant signal, or a clip that is one long traverse.
    """
    if not frames:
        return []
    signal = steering_signal(frames, fps_effective, arrays=arrays)
    return segment_turns_from_signal(signal)


def turn_sides(turns: list[Turn]) -> tuple[int, int]:
    """``(n_left, n_right)`` convenience count."""
    left = sum(1 for turn in turns if turn.side == "L")
    return left, len(turns) - left


def window_mask(t_ms: np.ndarray, window: Window) -> np.ndarray:
    """Boolean mask of samples inside ``window`` (inclusive)."""
    lo, hi = window
    return (t_ms >= lo) & (t_ms <= hi)
