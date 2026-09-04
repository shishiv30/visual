"""Tests for scene inference (P2)."""

from __future__ import annotations

from core.sports.metrics import MetricPack, MetricValue
from core.sports.scene_infer import infer_scene_hints


def _metric(metric_id: str, value: float) -> MetricValue:
    return MetricValue(
        metric_id=metric_id,
        value=value,
        unit="",
        form="A",
        reliability=1.0,
        state="ok",
    )


def test_infer_scene_hints_stable_piste() -> None:
    pack = MetricPack(
        metrics={
            "com_vertical_travel": _metric("com_vertical_travel", 0.05),
            "edge_angle_proxy": _metric("edge_angle_proxy", 10.0),
            "turn_amplitude": _metric("turn_amplitude", 18.0),
            "turn_duration_var": _metric("turn_duration_var", 0.12),
        }
    )
    hints = infer_scene_hints(pack)
    assert hints.confidence >= 0.5
    assert hints.terrain_type == "piste"
    assert hints.snow_surface in {"packed", "soft", "hardpack"}


def test_infer_scene_hints_mogul_signal() -> None:
    pack = MetricPack(
        metrics={
            "com_vertical_travel": _metric("com_vertical_travel", 0.20),
            "edge_angle_proxy": _metric("edge_angle_proxy", 12.0),
            "turn_amplitude": _metric("turn_amplitude", 22.0),
            "turn_duration_var": _metric("turn_duration_var", 0.10),
        }
    )
    hints = infer_scene_hints(pack)
    assert hints.terrain_type == "mogul"
