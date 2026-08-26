from datetime import datetime
from pathlib import Path

import pytest

from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    ClipStatus,
    SeedMark,
    analysis_path,
    clip_dir,
    delete_clip,
    display_name_now,
    frame_feedback_path,
    list_clips,
    load_frame_feedback,
    load_meta,
    load_stage_report,
    prepare_reanalyze,
    save_analysis,
    save_meta,
    stage_report_path,
    toggle_frame_skeleton_ok,
    toggle_frame_stage_vote,
)
from schemas.clip_analysis import AnalyzedFrame, ClipAnalysis
from schemas.core_inference import (
    BackendId,
    CoreInferenceResult,
    FrameMeta,
    ModelMeta,
    SourceKind,
)


@pytest.fixture
def library_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("VISUAL_LIBRARY", str(tmp_path))
    return tmp_path


def _meta(clip_id: str, status: ClipStatus = ClipStatus.DONE) -> ClipMeta:
    return ClipMeta(
        clip_id=clip_id,
        created_at="2026-08-25T21:45:00-05:00",
        display_name="08/25/2026-21:45",
        kind=ClipKind.VIDEO,
        status=status,
    )


def _empty_analysis(clip_id: str) -> ClipAnalysis:
    result = CoreInferenceResult(
        frame=FrameMeta(
            source_kind=SourceKind.VIDEO_FRAME,
            timestamp_ms=0.0,
            width=64,
            height=64,
        ),
        detections=[],
        poses=[],
        tracks=[],
        classifications=[],
        segments=[],
        model_meta=ModelMeta(
            backend_id=BackendId.MEDIAPIPE_POSE.value,
            model_name="pose_landmarker_full.task",
            latency_ms=1.0,
            device="cpu",
        ),
        error=None,
    )
    return ClipAnalysis(
        clip_id=clip_id,
        fps=30.0,
        frame_count=1,
        frames=[AnalyzedFrame(t_ms=0.0, result=result)],
    )


def test_display_name_format() -> None:
    stamp = datetime(2026, 8, 25, 21, 45)
    assert display_name_now(stamp) == "08/25/2026-21:45"


def test_clip_meta_roundtrip() -> None:
    meta = ClipMeta(
        clip_id="abc",
        created_at="2026-08-25T21:45:00-05:00",
        display_name="08/25/2026-21:45",
        kind=ClipKind.VIDEO,
    )
    parsed = ClipMeta.model_validate_json(meta.model_dump_json())
    assert parsed.status.value == "pending"
    assert parsed.kind == ClipKind.VIDEO
    assert parsed.seed_box is None


def test_delete_clip_removes_folder(library_env: Path) -> None:
    meta = _meta("to-delete")
    save_meta(meta)
    (clip_dir(meta.clip_id) / "clip.mp4").write_bytes(b"x")
    save_analysis(_empty_analysis(meta.clip_id))
    delete_clip(meta.clip_id)
    assert not clip_dir(meta.clip_id).exists()
    assert list_clips() == []


def test_prepare_reanalyze_resets_status_and_drops_json(library_env: Path) -> None:
    meta = _meta("to-refresh")
    meta.seed_box = (0.1, 0.1, 0.4, 0.8)
    meta.seeds = [SeedMark(t_ms=100.0, box=(0.1, 0.1, 0.4, 0.8))]
    meta.play_start_ms = 500
    meta.play_end_ms = 4000
    save_meta(meta)
    save_analysis(_empty_analysis(meta.clip_id))
    assert analysis_path(meta.clip_id).is_file()
    updated = prepare_reanalyze(meta.clip_id)
    assert updated.status == ClipStatus.PENDING
    assert updated.error is None
    assert updated.seed_box is None
    assert updated.seeds == []
    assert updated.play_start_ms == 0
    assert updated.play_end_ms is None
    assert not analysis_path(meta.clip_id).is_file()
    assert load_meta(meta.clip_id).status == ClipStatus.PENDING


def test_load_stage_report_accepts_legacy_schema(library_env: Path) -> None:
    meta = _meta("legacy-report")
    save_meta(meta)
    stage_report_path(meta.clip_id).write_text(
        """{
          "schema_version": "1.0.0",
          "clip_id": "legacy-report",
          "category_id": "alpine_piste",
          "stage_id": "pizza_glide",
          "category_name": "Piste",
          "stage_name": "Wedge glide",
          "confidence": 0.5,
          "ready_for_next_stage": false,
          "disclaimer": "old",
          "keypoints": []
        }""",
        encoding="utf-8",
    )
    report = load_stage_report(meta.clip_id)
    assert report is not None
    assert report.stage_id == "pizza_glide"
    assert report.schema_version == "2.1.0"


def test_load_stage_report_skips_corrupt_file(library_env: Path) -> None:
    meta = _meta("bad-report")
    save_meta(meta)
    stage_report_path(meta.clip_id).write_text("{not json", encoding="utf-8")
    assert load_stage_report(meta.clip_id) is None


def test_frame_feedback_votes_and_skeleton(library_env: Path) -> None:
    meta = _meta("vote-clip")
    save_meta(meta)
    like = toggle_frame_stage_vote(
        meta.clip_id,
        86,
        "like",
        t_ms=1234.0,
        pose_index=43,
        stage_id="carve_short",
    )
    assert like.frames["86"].stage_vote == "like"
    assert like.frames["86"].skeleton_ok is True
    unlike = toggle_frame_stage_vote(
        meta.clip_id,
        86,
        "unlike",
        t_ms=1234.0,
        pose_index=43,
        stage_id="carve_short",
    )
    assert unlike.frames["86"].stage_vote == "unlike"
    bad = toggle_frame_skeleton_ok(
        meta.clip_id,
        86,
        t_ms=1234.0,
        pose_index=43,
        stage_id="carve_short",
    )
    assert bad.frames["86"].skeleton_ok is False
    assert bad.frames["86"].stage_vote == "unlike"
    again = toggle_frame_stage_vote(
        meta.clip_id,
        86,
        "unlike",
        t_ms=1234.0,
        pose_index=43,
        stage_id="carve_short",
    )
    assert again.frames["86"].stage_vote is None
    assert again.frames["86"].skeleton_ok is False
    reloaded = load_frame_feedback(meta.clip_id)
    assert reloaded.stage_id_at_vote == "carve_short"
    assert reloaded.frames["86"].stage_vote is None
    assert reloaded.frames["86"].skeleton_ok is False
    frame_feedback_path(meta.clip_id).write_text("{not json", encoding="utf-8")
    assert load_frame_feedback(meta.clip_id).frames == {}

