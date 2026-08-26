from clients.windows.pipeline.clip_range import (
    collect_seeds,
    in_play_range,
    play_window_ms,
    seed_at,
)
from clients.windows.store.library import ClipKind, ClipMeta, SeedMark


def _meta(**kwargs) -> ClipMeta:
    data = {
        "clip_id": "c",
        "created_at": "2026-08-25T21:45:00-05:00",
        "display_name": "08/25/2026-21:45",
        "kind": ClipKind.VIDEO,
        "duration_ms": 10000,
    }
    data.update(kwargs)
    return ClipMeta(**data)


def test_seed_at_hits_nearby_mark() -> None:
    seeds = [
        SeedMark(t_ms=0.0, box=(0.1, 0.1, 0.4, 0.8)),
        SeedMark(t_ms=2000.0, box=(0.2, 0.2, 0.5, 0.9)),
    ]
    hit = seed_at(2010.0, seeds, half_ms=33.0)
    assert hit is not None
    assert hit.box[0] == 0.2
    assert seed_at(1000.0, seeds, 33.0) is None


def test_play_window_and_range() -> None:
    meta = _meta(play_start_ms=1000, play_end_ms=4000)
    start, end = play_window_ms(meta)
    assert start == 1000.0
    assert end == 4000.0
    assert in_play_range(2500.0, start, end)
    assert not in_play_range(50.0, start, end)
    assert not in_play_range(5000.0, start, end)


def test_collect_seeds_falls_back_to_seed_box() -> None:
    meta = _meta(seed_box=(0.1, 0.1, 0.3, 0.7))
    seeds = collect_seeds(meta)
    assert len(seeds) == 1
    assert seeds[0].t_ms == 0.0
