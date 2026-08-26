from clients.windows.ui.timeline_math import (
    MAX_ZOOM,
    MIN_RANGE_MS,
    MIN_ZOOM,
    RULER_TICK_PX,
    clamp_range,
    clamp_scroll_x,
    clamp_zoom,
    content_width_px,
    format_ruler_time,
    max_scroll_x,
    ms_to_x,
    nearest_keyframe_ms,
    ruler_tick_ms,
    x_to_ms,
    zoom_keeping_ms,
)


def test_clamp_zoom() -> None:
    assert clamp_zoom(0.5) == MIN_ZOOM
    assert clamp_zoom(9.0) == MAX_ZOOM
    assert clamp_zoom(2.5) == 2.5


def test_ms_x_roundtrip() -> None:
    duration = 10_000.0
    viewport = 400
    zoom = 2.0
    scroll = 80.0
    for t_ms in (0.0, 2500.0, 10_000.0):
        x = ms_to_x(t_ms, duration, viewport, zoom, scroll)
        back = x_to_ms(x, duration, viewport, zoom, scroll)
        assert abs(back - t_ms) < 0.6


def test_scroll_range_at_100_percent() -> None:
    assert max_scroll_x(400, 1.0) == 0.0
    assert content_width_px(400, 2.0) == 800.0
    assert max_scroll_x(400, 2.0) == 400.0
    assert clamp_scroll_x(-10, 400, 2.0) == 0.0
    assert clamp_scroll_x(999, 400, 2.0) == 400.0


def test_clamp_range_min_duration() -> None:
    start, end = clamp_range(100, 150, 5000)
    assert end - start >= MIN_RANGE_MS
    start, end = clamp_range(0, None, 5000)
    assert start == 0
    assert end == 5000


def test_zoom_keeps_anchor_time() -> None:
    duration = 8000.0
    viewport = 200
    old_zoom = 1.0
    old_scroll = 0.0
    anchor = 50.0
    before = x_to_ms(anchor, duration, viewport, old_zoom, old_scroll)
    zoom, scroll = zoom_keeping_ms(2.0, anchor, duration, viewport, old_zoom, old_scroll)
    after = x_to_ms(anchor, duration, viewport, zoom, scroll)
    assert zoom == 2.0
    assert abs(after - before) < 1.0


def test_format_ruler_time() -> None:
    assert format_ruler_time(0, fine=False) == "0:00"
    assert format_ruler_time(65_000, fine=False) == "1:05"
    assert format_ruler_time(1500, fine=True) == "0:01.5"


def test_ruler_tick_is_one_per_100px() -> None:
    duration = 10_000.0
    viewport = 400
    zoom = 1.0
    step = ruler_tick_ms(duration, viewport, zoom)
    px = ms_to_x(step, duration, viewport, zoom, 0.0) - ms_to_x(
        0.0, duration, viewport, zoom, 0.0
    )
    assert abs(px - RULER_TICK_PX) < 0.5


def test_nearest_keyframe_ms() -> None:
    keys = [1000, 5000, 9000]
    hit = nearest_keyframe_ms(22.0, keys, 10_000.0, 200, 1.0, 0.0, hit_px=12.0)
    assert hit == 1000
    assert nearest_keyframe_ms(70.0, keys, 10_000.0, 200, 1.0, 0.0, hit_px=8.0) is None

