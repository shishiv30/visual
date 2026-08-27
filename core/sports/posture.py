"""Heuristic posture composites from FeaturePack (not SI lab metrics)."""

from __future__ import annotations

from core.sports.signals import FeaturePack
from schemas.stage_report import KeypointResult, PostureScores


def _clamp(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def _score_quiet(upper_quiet: float) -> float:
    # Low torso sway is better; map typical 0.2–3.0 onto 100–0.
    return _clamp(100.0 - upper_quiet * 35.0)


def _score_stance_lock(stance_std: float) -> float:
    # Moderate variability OK; extreme jitter hurts stability.
    return _clamp(100.0 - stance_std * 40.0)


def _score_rhythm_couple(knee_freq: float, turn_freq: float) -> float:
    if knee_freq <= 0.05 and turn_freq <= 0.05:
        return 45.0
    ratio = min(knee_freq, turn_freq) / max(knee_freq, turn_freq, 1e-3)
    return _clamp(40.0 + ratio * 60.0)


def _score_hands(hands_low: float) -> float:
    return _clamp(hands_low * 100.0)


def _score_control_from_keypoints(results: list[KeypointResult]) -> float | None:
    known = [item.score for item in results if item.score is not None]
    if not known:
        return None
    return _clamp(sum(known) / len(known))


def _score_lean_control(inward_lean: float) -> float:
    # Some angulation is good; extreme lean is unstable control.
    if inward_lean <= 0.05:
        return 55.0
    if inward_lean <= 0.35:
        return _clamp(55.0 + inward_lean * 100.0)
    return _clamp(100.0 - (inward_lean - 0.35) * 80.0)


def _score_balance(backseat: float, knee_valgus: float) -> float:
    # Lower backseat and mid valgus are better balance proxies.
    seat = _clamp(100.0 - abs(backseat) * 80.0)
    valgus = _clamp(100.0 - abs(knee_valgus - 0.15) * 120.0)
    return _clamp(0.55 * seat + 0.45 * valgus)


def posture_scores(
    pack: FeaturePack,
    results: list[KeypointResult] | None = None,
) -> PostureScores:
    """Coach-heuristic 0–100 composites from existing kinematics."""
    stability = _clamp(
        0.55 * _score_quiet(pack.upper_quiet)
        + 0.45 * _score_stance_lock(pack.stance_width_std)
    )
    coordination = _clamp(
        0.6 * _score_rhythm_couple(pack.knee_flex_freq, pack.turn_freq)
        + 0.4 * _score_hands(pack.hands_low)
    )
    from_kp = _score_control_from_keypoints(results or [])
    lean = _score_lean_control(pack.inward_lean)
    if from_kp is None:
        control = lean
    else:
        control = _clamp(0.65 * from_kp + 0.35 * lean)
    balance = _score_balance(pack.backseat, pack.knee_valgus)
    return PostureScores(
        stability=round(stability, 1),
        coordination=round(coordination, 1),
        control=round(control, 1),
        balance=round(balance, 1),
    )
