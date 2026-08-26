"""Play window and multi-frame seed lookup for analysis."""

from __future__ import annotations

from clients.windows.store.library import ClipMeta, SeedMark


def play_window_ms(meta: ClipMeta) -> tuple[float, float]:
    start = float(meta.play_start_ms or 0)
    if meta.play_end_ms is not None:
        end = float(meta.play_end_ms)
    else:
        end = float(meta.duration_ms) if meta.duration_ms > 0 else 1e12
    if end <= start:
        end = start + 1.0
    return start, end


def in_play_range(t_ms: float, start_ms: float, end_ms: float) -> bool:
    return start_ms <= t_ms <= end_ms


def collect_seeds(meta: ClipMeta) -> list[SeedMark]:
    if meta.seeds:
        return sorted(meta.seeds, key=lambda item: item.t_ms)
    if meta.seed_box is not None:
        return [SeedMark(t_ms=0.0, box=meta.seed_box)]
    return []


def seed_at(
    t_ms: float, seeds: list[SeedMark], half_ms: float
) -> SeedMark | None:
    hit: SeedMark | None = None
    best = half_ms
    for item in seeds:
        delta = abs(item.t_ms - t_ms)
        if delta <= best:
            best = delta
            hit = item
    return hit
