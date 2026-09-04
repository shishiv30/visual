from clients.windows.ui.qtutil import (
    canvas_point_to_image,
    fit_image_display,
    scaled_display_size,
    widget_point_to_image,
)


def test_canvas_point_to_image_scales_from_preview() -> None:
    display_w, display_h = scaled_display_size(1920, 1080, 720)
    assert display_w == 720
    x, y = canvas_point_to_image(
        360.0,
        200.0,
        image_width=1920,
        image_height=1080,
        display_width=display_w,
        display_height=display_h,
    )
    assert x == 960.0
    assert y == 533.3


def test_widget_point_to_image_uses_letterboxed_display() -> None:
    scale, x_off, y_off, display_w, display_h, image_w, image_h = fit_image_display(
        1920,
        1080,
        800,
        600,
    )
    assert image_w == 1920
    assert image_h == 1080
    center_x = x_off + display_w / 2.0
    center_y = y_off + display_h / 2.0
    hit = widget_point_to_image(
        center_x,
        center_y,
        scale=scale,
        x_offset=x_off,
        y_offset=y_off,
        display_width=display_w,
        display_height=display_h,
        image_width=image_w,
        image_height=image_h,
    )
    assert hit is not None
    assert hit[0] == 960.0
    assert hit[1] == 540.0
    assert widget_point_to_image(
        0.0,
        0.0,
        scale=scale,
        x_offset=x_off,
        y_offset=y_off,
        display_width=display_w,
        display_height=display_h,
        image_width=image_w,
        image_height=image_h,
    ) is None
