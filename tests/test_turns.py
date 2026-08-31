"""Turn segmentation tests (design v3 §3.3)."""

from __future__ import annotations

import numpy as np

from core.sports.turns import (
    MIN_AMPLITUDE_DEG,
    MIN_TURN_S,
    Turn,
    boxcar,
    landmark_arrays,
    lowpass_taps,
    segment_turns,
    steering_signal,
    turn_sides,
    window_mask,
)
from tests.ski_fixtures import (
    SkierParams,
    asymmetric_skier,
    low_confidence_clip,
    make_clip,
    no_pose_clip,
    parallel_skier,
    profile_view_skier,
    short_clip,
    stemmed_skier,
    stride_sample,
    traverse_clip,
    wedge_skier,
)

FPS = 15.0


def _alternating(turns: list[Turn]) -> bool:
    return all(a.side != b.side for a, b in zip(turns, turns[1:]))


# --- low-pass primitive -----------------------------------------------------


def test_boxcar_is_zero_phase() -> None:
    # A symmetric bump must stay centred: no group delay after filtering.
    series = np.zeros(41)
    series[20] = 1.0
    out = boxcar(series, 5, passes=2)
    assert out.size == series.size
    assert int(np.argmax(out)) == 20
    assert abs(float(np.sum(out)) - 1.0) < 1e-9


def test_boxcar_taps_follow_the_cutoff_rule() -> None:
    assert lowpass_taps(15.0) % 2 == 1
    assert lowpass_taps(30.0) >= lowpass_taps(15.0)
    assert lowpass_taps(1.0) == 3


def test_boxcar_handles_degenerate_input() -> None:
    assert boxcar(np.array([]), 5).size == 0
    assert boxcar(np.array([2.0]), 9).tolist() == [2.0]


# --- the synthetic sinusoid -------------------------------------------------


def test_sinusoid_turn_count_and_sides() -> None:
    """0.5 Hz swing over 12 s is 12 one-second turns; the two partial arcs at
    the clip ends are dropped, so 10-12 complete turns must be reported."""
    turns = segment_turns(parallel_skier().frames, FPS)
    assert 10 <= len(turns) <= 12
    assert _alternating(turns)
    left, right = turn_sides(turns)
    assert abs(left - right) <= 1
    # First arc runs from the first crossing (t=1 s) into negative theta.
    assert turns[0].side == "R"
    for turn in turns:
        assert turn.duration_s >= MIN_TURN_S
        assert abs(turn.duration_s - 1.0) < 0.15
        assert turn.amplitude_deg >= MIN_AMPLITUDE_DEG


def test_turn_boundaries_land_on_whole_seconds() -> None:
    turns = segment_turns(parallel_skier().frames, FPS)
    for turn in turns:
        nearest = round(turn.t_start_ms / 1000.0)
        assert abs(turn.t_start_ms / 1000.0 - nearest) < 0.12


def test_indices_are_dense_and_ordered() -> None:
    turns = segment_turns(parallel_skier().frames, FPS)
    assert [turn.index for turn in turns] == list(range(len(turns)))
    for a, b in zip(turns, turns[1:]):
        assert a.t_end_ms <= b.t_start_ms + 1e-6


# --- phases -----------------------------------------------------------------


def test_phase_windows_partition_the_arc() -> None:
    turns = segment_turns(parallel_skier().frames, FPS)
    turn = turns[1]
    span = turn.t_end_ms - turn.t_start_ms
    third = span / 3.0
    for name, expected in (
        ("initiation", (turn.t_start_ms, turn.t_start_ms + third)),
        ("shaping", (turn.t_start_ms + third, turn.t_start_ms + 2 * third)),
        ("finish", (turn.t_start_ms + 2 * third, turn.t_end_ms)),
    ):
        lo, hi = turn.window(name)
        assert abs(lo - expected[0]) < 1e-6
        assert abs(hi - expected[1]) < 1e-6
    trans_lo, trans_hi = turn.transition
    assert trans_lo < turn.t_start_ms < trans_hi
    assert abs((trans_hi - trans_lo) - 0.30 * span) < 1e-6
    assert turn.window("all") == (turn.t_start_ms, turn.t_end_ms)


def test_transition_window_is_clamped_to_the_clip() -> None:
    params = SkierParams(turn_hz=1.0, duration_s=6.0)
    turns = segment_turns(make_clip(params).frames, FPS)
    assert turns
    t_ms = np.array([frame.t_ms for frame in make_clip(params).frames])
    for turn in turns:
        lo, hi = turn.transition
        assert lo >= float(t_ms[0]) - 1e-6
        assert hi <= float(t_ms[-1]) + 1e-6
        assert np.any(window_mask(t_ms, turn.transition))


# --- amplitude and duration rejection ---------------------------------------


def test_traverse_yields_no_turns() -> None:
    assert segment_turns(traverse_clip().frames, FPS) == []


def test_small_amplitude_wobble_is_rejected() -> None:
    # 6 px of swing on a 190 px leg is well under the 8 degree amplitude floor.
    turns = segment_turns(make_clip(SkierParams(swing_px=6.0)).frames, FPS)
    assert turns == []


def test_a_3hz_wobble_is_attenuated_away_entirely() -> None:
    """3 Hz is far above the 2 Hz low-pass, so the amplitude floor rejects it.

    This case never reaches the duration debounce — the previous version of
    this test looped over an empty list and passed without exercising anything.
    """
    turns = segment_turns(make_clip(SkierParams(turn_hz=3.0)).frames, FPS)
    assert turns == []


def test_fast_wobble_is_debounced_below_the_minimum_duration() -> None:
    """1.6 Hz survives the filter but its half-cycle is under ``MIN_TURN_S``.

    A 1.6 Hz swing is a 0.31 s half-cycle, i.e. shorter than the 0.35 s floor,
    yet enough of it survives the 2 Hz low-pass to reach the segmenter. So the
    debounce is what has to hold: turns are still returned (the loop must not be
    empty, or this asserts nothing) and every one of them spans ``MIN_TURN_S``
    because the sub-threshold swings were merged rather than emitted.
    """
    turns = segment_turns(make_clip(SkierParams(turn_hz=1.6)).frames, FPS)
    assert turns, "1.6 Hz must survive the amplitude filter for this to test anything"
    for turn in turns:
        assert turn.duration_s >= MIN_TURN_S
    assert _alternating(turns)


def test_faster_rhythm_gives_more_turns() -> None:
    slow = segment_turns(make_clip(SkierParams(turn_hz=0.4)).frames, FPS)
    fast = segment_turns(make_clip(SkierParams(turn_hz=0.8)).frames, FPS)
    assert len(fast) > len(slow)


# --- defensive paths --------------------------------------------------------


def test_short_clip_returns_no_turns() -> None:
    assert segment_turns(short_clip().frames, FPS) == []


def test_empty_frame_list_returns_no_turns() -> None:
    assert segment_turns([], FPS) == []


def test_low_confidence_clip_returns_no_turns() -> None:
    assert segment_turns(low_confidence_clip().frames, FPS) == []


def test_missing_blaze_returns_no_turns() -> None:
    assert segment_turns(no_pose_clip().frames, FPS) == []


def test_missing_hips_returns_no_turns() -> None:
    clip = parallel_skier(drop_landmarks=(23, 24))
    assert segment_turns(clip.frames, FPS) == []


def test_missing_ankles_returns_no_turns() -> None:
    clip = parallel_skier(drop_landmarks=(27, 28))
    assert segment_turns(clip.frames, FPS) == []


def test_nonsense_fps_does_not_raise() -> None:
    for fps in (0.0, -5.0, float("nan")):
        assert isinstance(segment_turns(parallel_skier().frames, fps), list)


def test_one_sided_hip_does_not_fake_a_midpoint() -> None:
    """Dropping a single hip must invalidate the pelvis midpoint, not shift it."""
    arrays = landmark_arrays(parallel_skier(drop_landmarks=(23,)).frames)
    mid = arrays.mid(23, 24)
    assert np.all(~np.isfinite(mid[:, 0]))


# --- steering signal --------------------------------------------------------


def test_steering_signal_is_finite_and_centred() -> None:
    clip = parallel_skier()
    signal = steering_signal(clip.frames, FPS)
    assert signal.ok
    assert np.all(np.isfinite(signal.theta_deg))
    assert abs(float(np.median(signal.theta_deg))) < 1e-9
    assert signal.tangent_source == "path"
    assert signal.usable_fraction > 0.99
    assert signal.hysteresis_deg >= 2.0


def test_steering_signal_reports_unusable_input() -> None:
    signal = steering_signal(low_confidence_clip().frames, FPS)
    assert not signal.ok or signal.tangent_source == "none"
    assert signal.usable_fraction == 0.0


def test_signal_amplitude_tracks_the_swing() -> None:
    small = steering_signal(make_clip(SkierParams(swing_px=40.0)).frames, FPS)
    large = steering_signal(make_clip(SkierParams(swing_px=110.0)).frames, FPS)
    assert np.max(np.abs(large.theta_deg)) > np.max(np.abs(small.theta_deg))


# --- stride invariance ------------------------------------------------------


def test_segmentation_is_stride_invariant_with_effective_fps() -> None:
    full = make_clip(SkierParams(fps=30.0))
    strided = stride_sample(full, 2)
    a = segment_turns(full.frames, 30.0)
    b = segment_turns(strided.frames, 15.0)
    assert abs(len(a) - len(b)) <= 1
    assert [turn.side for turn in a][: len(b)] == [turn.side for turn in b][: len(a)]


# --- other fixtures still segment ------------------------------------------


def test_other_fixtures_segment_cleanly() -> None:
    fixtures = (
        wedge_skier(),
        stemmed_skier(),
        asymmetric_skier(),
        profile_view_skier(),
    )
    for clip in fixtures:
        turns = segment_turns(clip.frames, FPS)
        assert turns, clip.clip_id
        assert _alternating(turns), clip.clip_id
        for turn in turns:
            assert np.isfinite(turn.amplitude_deg)
            assert turn.t_end_ms > turn.t_start_ms


def test_stem_does_not_move_the_boundaries() -> None:
    """A stem changes the feet, not the pelvis or ankles, so segmentation of the
    stemmed fixture must match the clean one turn for turn."""
    clean = segment_turns(parallel_skier().frames, FPS)
    stemmed = segment_turns(stemmed_skier().frames, FPS)
    assert len(clean) == len(stemmed)
    for a, b in zip(clean, stemmed):
        assert abs(a.t_start_ms - b.t_start_ms) < 1e-6
        assert a.side == b.side
