"""Pure layout math for the prepare-page filmstrip timeline."""

from __future__ import annotations

MIN_ZOOM = 1.0
MAX_ZOOM = 5.0
MIN_RANGE_MS = 200
RULER_TICK_PX = 100.0
KEYFRAME_HIT_PX = 10.0


def clamp_zoom(zoom: float) -> float:
    return max(MIN_ZOOM, min(MAX_ZOOM, zoom))


def content_width_px(viewport_width: int, zoom: float) -> float:
    return max(1.0, float(viewport_width)) * clamp_zoom(zoom)


def max_scroll_x(viewport_width: int, zoom: float) -> float:
    content = content_width_px(viewport_width, zoom)
    return max(0.0, content - float(viewport_width))


def clamp_scroll_x(scroll_x: float, viewport_width: int, zoom: float) -> float:
    return max(0.0, min(max_scroll_x(viewport_width, zoom), scroll_x))


def ms_to_x(
    t_ms: float,
    duration_ms: float,
    viewport_width: int,
    zoom: float,
    scroll_x: float,
) -> float:
    duration = max(1.0, duration_ms)
    content = content_width_px(viewport_width, zoom)
    return (t_ms / duration) * content - scroll_x


def x_to_ms(
    x: float,
    duration_ms: float,
    viewport_width: int,
    zoom: float,
    scroll_x: float,
) -> float:
    duration = max(1.0, duration_ms)
    content = content_width_px(viewport_width, zoom)
    t_ms = ((x + scroll_x) / content) * duration
    return max(0.0, min(duration, t_ms))


def clamp_range(
    in_ms: int,
    out_ms: int | None,
    duration_ms: int,
    min_range_ms: int = MIN_RANGE_MS,
) -> tuple[int, int]:
    duration = max(min_range_ms, duration_ms)
    start = max(0, min(in_ms, duration))
    end = duration if out_ms is None else max(0, min(out_ms, duration))
    if end - start < min_range_ms:
        end = min(duration, start + min_range_ms)
        if end - start < min_range_ms:
            start = max(0, end - min_range_ms)
    return start, end


def zoom_keeping_ms(
    zoom: float,
    anchor_x: float,
    duration_ms: float,
    viewport_width: int,
    old_zoom: float,
    old_scroll_x: float,
) -> tuple[float, float]:
    """Return (new_zoom, new_scroll) so the time under anchor_x stays put."""
    new_zoom = clamp_zoom(zoom)
    t_ms = x_to_ms(anchor_x, duration_ms, viewport_width, old_zoom, old_scroll_x)
    content = content_width_px(viewport_width, new_zoom)
    duration = max(1.0, duration_ms)
    new_scroll = (t_ms / duration) * content - anchor_x
    return new_zoom, clamp_scroll_x(new_scroll, viewport_width, new_zoom)


def ruler_tick_ms(
    duration_ms: float, viewport_width: int, zoom: float, tick_px: float = RULER_TICK_PX
) -> float:
    content = content_width_px(viewport_width, zoom)
    duration = max(1.0, duration_ms)
    return (tick_px / content) * duration


def nearest_keyframe_ms(
    x: float,
    keyframe_ms: list[int],
    duration_ms: float,
    viewport_width: int,
    zoom: float,
    scroll_x: float,
    hit_px: float = KEYFRAME_HIT_PX,
) -> int | None:
    best: int | None = None
    best_d = hit_px
    for t_ms in keyframe_ms:
        kx = ms_to_x(float(t_ms), duration_ms, viewport_width, zoom, scroll_x)
        dist = abs(kx - x)
        if dist <= best_d:
            best_d = dist
            best = t_ms
    return best


def format_ruler_time(t_ms: float, *, fine: bool) -> str:
    total_s = max(0.0, t_ms / 1000.0)
    minutes = int(total_s // 60)
    seconds = total_s - minutes * 60
    if fine:
        return f"{minutes}:{seconds:04.1f}"
    return f"{minutes}:{int(seconds):02d}"
