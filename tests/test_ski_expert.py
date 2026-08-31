from __future__ import annotations

from core.sports.curriculum import CURRICULUM_V3_PATH, Curriculum
from core.sports.knowledge import expert_view, load_expert, load_signals, signal_ids
from core.sports.signals import CLIP_SIGNALS
from core.sports.ski_expert import accept_curriculum


def test_ski_expert_accepts_repo_curriculum() -> None:
    assert accept_curriculum() == []


def test_ski_expert_accepts_v3_curriculum() -> None:
    bundle = Curriculum.model_validate_json(
        CURRICULUM_V3_PATH.read_text(encoding="utf-8")
    )
    assert accept_curriculum(bundle) == []


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


def test_v3_expert_view_rewires_the_tree() -> None:
    v2 = expert_view("2.1.0")
    v3 = expert_view("3.0.0")
    assert v2["tree_next"]["pizza"] == ["wedge_christie"]
    assert v3["tree_next"]["pizza"] == ["sideslip", "mogul_wedge"]
    assert v3["tree_next"]["parallel"] == ["dynamic_parallel"]
    assert v3["tree_next"]["dynamic_parallel"] == [
        "skid_short",
        "carve_long",
        "firm_snow",
    ]
    assert v3["scene_levels"]["steeps"] == ["slope_band:black|double-black"]
    # shared constants survive the overlay
    assert v3["pass_score"] == v2["pass_score"]
    assert v3["proxy_checkpoints"] == v2["proxy_checkpoints"]
