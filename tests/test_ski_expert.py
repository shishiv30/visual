from __future__ import annotations

from core.sports.knowledge import load_expert, load_signals, signal_ids
from core.sports.signals import CLIP_SIGNALS
from core.sports.ski_expert import accept_curriculum


def test_ski_expert_accepts_repo_curriculum() -> None:
    assert accept_curriculum() == []


def test_runtime_signals_match_catalog() -> None:
    assert set(CLIP_SIGNALS) == set(signal_ids())
    assert set(load_signals()) == set(CLIP_SIGNALS)


def test_expert_tree_forks_after_parallel() -> None:
    tree = load_expert()["tree_next"]
    assert tree["parallel"] == ["skid_short", "carve_long"]
    assert tree["skid_short"] == ["mogul_absorb"]
    assert "carve_long" not in tree["skid_short"]
    assert tree["carve_short"] == []
    assert "park" in load_expert()["catalog_no_score"]
