"""Rule-based scene hints for Prepare page prefill (P2)."""

from __future__ import annotations

from dataclasses import dataclass

from core.sports.metrics import MetricPack


@dataclass(frozen=True)
class SceneHints:
    snow_surface: str | None
    terrain_type: str | None
    confidence: float
    reasons: tuple[str, ...] = ()


def infer_scene_hints(pack: MetricPack) -> SceneHints:
    """Suggest snow_surface / terrain_type from whole-clip metrics.

    Confidence below 0.5 means callers should not prefill UI chips.
    """
    reasons: list[str] = []
    com = pack.get("com_vertical_travel")
    edge = pack.get("edge_angle_proxy")
    turn_amp = pack.get("turn_amplitude")
    turn_var = pack.get("turn_duration_var")

    snow: str | None = None
    terrain: str | None = None
    score = 0.0

    com_val = float(com.value) if com and com.value is not None else None
    edge_val = float(edge.value) if edge and edge.value is not None else None
    amp_val = float(turn_amp.value) if turn_amp and turn_amp.value is not None else None
    var_val = float(turn_var.value) if turn_var and turn_var.value is not None else None

    if com_val is not None and com_val >= 0.12:
        terrain = "mogul"
        score += 0.35
        reasons.append("high_com_vertical_travel")
    elif amp_val is not None and var_val is not None and var_val >= 0.35:
        terrain = "offpiste"
        score += 0.25
        reasons.append("irregular_turn_timing")
    else:
        terrain = "piste"
        score += 0.30
        reasons.append("stable_turn_metrics")

    if edge_val is not None and edge_val >= 14.0:
        snow = "hardpack"
        score += 0.35
        reasons.append("high_edge_proxy")
    elif edge_val is not None and edge_val <= 8.0:
        snow = "soft"
        score += 0.25
        reasons.append("low_edge_proxy")
    else:
        snow = "packed"
        score += 0.20
        reasons.append("mid_edge_proxy")

    confidence = min(1.0, score)
    if confidence < 0.5:
        return SceneHints(None, None, confidence, tuple(reasons))
    return SceneHints(snow, terrain, confidence, tuple(reasons))
