import json
import sys
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
    library_root,
    list_clips,
    list_reports_for_athlete,
    load_analysis,
    load_frame_feedback,
    load_meta,
    load_stage_report,
    meta_path,
    prepare_reanalyze,
    save_analysis,
    save_meta,
    stage_report_path,
    toggle_frame_skeleton_ok,
    toggle_frame_stage_vote,
)
from clients.windows.store.prefs import (
    LANG_KEY,
    LEGACY_LANG_KEY,
    load_language,
    prefs_path,
    save_language,
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
    assert report.schema_version == "3.0.0"
    # The v3 blocks are absent from a stored 2.1.0 report and must migrate to
    # empty, never to a fabricated stage, metric or tree (design §10).
    assert report.classification is None
    assert report.turns is None
    assert report.scene is None
    assert report.profile_summary is None
    assert report.knowledge_ref is None
    assert report.knowledge_focus is None
    assert report.metrics == []
    assert report.tree == []
    assert report.filming == []
    assert report.kb_stage == ""
    assert report.tier == "full"


def _stored_report(clip_id: str, stage_id: str, ready: bool) -> str:
    return json.dumps(
        {
            "schema_version": "2.1.0",
            "clip_id": clip_id,
            "category_id": "alpine_piste",
            "stage_id": stage_id,
            "category_name": "Piste",
            "stage_name": stage_id,
            "confidence": 0.8,
            "ready_for_next_stage": ready,
            "disclaimer": "d",
            "keypoints": [],
        }
    )


def test_list_reports_for_athlete_filters_and_excludes(library_env: Path) -> None:
    for clip_id, key, stage, ready in (
        ("h1", "amy", "pizza_glide", True),
        ("h2", "amy", "parallel", False),
        ("h3", "bob", "carve_long", True),
        ("h4", None, "pizza", True),
    ):
        meta = _meta(clip_id)
        meta.athlete_key = key
        save_meta(meta)
        stage_report_path(clip_id).write_text(
            _stored_report(clip_id, stage, ready), encoding="utf-8"
        )
    amy = list_reports_for_athlete("amy")
    assert {r.stage_id for r in amy} == {"pizza_glide", "parallel"}
    assert [r.stage_id for r in list_reports_for_athlete("amy", "h2")] == [
        "pizza_glide"
    ]
    # An unidentified clip has no history; it must not inherit everyone else's.
    assert list_reports_for_athlete(None) == []
    assert list_reports_for_athlete("") == []


def test_load_stage_report_skips_corrupt_file(library_env: Path) -> None:
    meta = _meta("bad-report")
    save_meta(meta)
    stage_report_path(meta.clip_id).write_text("{not json", encoding="utf-8")
    assert load_stage_report(meta.clip_id) is None


def test_clip_meta_scene_is_optional_and_round_trips(library_env: Path) -> None:
    plain = _meta("no-scene")
    assert plain.scene is None
    save_meta(plain)
    # A meta.json written before the scene block existed must still load.
    stored = json.loads(meta_path(plain.clip_id).read_text(encoding="utf-8"))
    del stored["scene"]
    meta_path(plain.clip_id).write_text(json.dumps(stored), encoding="utf-8")
    assert load_meta(plain.clip_id).scene is None

    scened = _meta("with-scene")
    scened.scene = {"snow_surface": "ice", "slope_band": None}
    save_meta(scened)
    assert load_meta(scened.clip_id).scene == {
        "snow_surface": "ice",
        "slope_band": None,
    }


def test_clip_analysis_scene_and_athlete_blocks_persist(library_env: Path) -> None:
    save_meta(_meta("ctx-clip"))
    analysis = _empty_analysis("ctx-clip")
    assert analysis.scene is None
    assert analysis.athlete is None
    assert analysis.fps_effective is None
    analysis.scene = {"snow_surface": "hardpack", "fps_effective": 15.0}
    analysis.athlete = {"age_band": "age-7-12", "height_m": 1.32}
    save_analysis(analysis)
    loaded = load_analysis("ctx-clip")
    assert loaded.scene == {"snow_surface": "hardpack", "fps_effective": 15.0}
    assert loaded.athlete == {"age_band": "age-7-12", "height_m": 1.32}
    assert loaded.fps_effective == 15.0


def test_prefs_language_key_case_and_legacy_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "ui.json"
    monkeypatch.setenv("VISUAL_PREFS", str(path))
    # An install written by the old build stored the capitalized key.
    path.write_text(json.dumps({LEGACY_LANG_KEY: "zh"}), encoding="utf-8")
    assert load_language() == "zh"
    # What we write is what we read back.
    save_language("en")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {LANG_KEY: "en"}
    assert load_language() == "en"
    # Both keys present: the current one wins.
    path.write_text(
        json.dumps({LANG_KEY: "en", LEGACY_LANG_KEY: "zh"}), encoding="utf-8"
    )
    assert load_language() == "en"


def _no_store_env(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    for name in ("VISUAL_LIBRARY", "VISUAL_PREFS", "LOCALAPPDATA", "XDG_DATA_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))


def test_store_paths_per_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"

    # Windows, unchanged: LOCALAPPDATA when set, ~/AppData/Local otherwise.
    _no_store_env(monkeypatch, home)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppDataLocal"))
    assert library_root() == tmp_path / "AppDataLocal" / "visual" / "library"
    assert prefs_path() == tmp_path / "AppDataLocal" / "visual" / "ui.json"
    monkeypatch.delenv("LOCALAPPDATA")
    assert library_root() == home / "AppData" / "Local" / "visual" / "library"
    assert prefs_path() == home / "AppData" / "Local" / "visual" / "ui.json"

    # macOS: Application Support, and LOCALAPPDATA must not leak in.
    _no_store_env(monkeypatch, home)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppDataLocal"))
    mac_root = home / "Library" / "Application Support" / "visual"
    assert library_root() == mac_root / "library"
    assert prefs_path() == mac_root / "ui.json"

    # Linux: XDG_DATA_HOME when set, ~/.local/share otherwise.
    _no_store_env(monkeypatch, home)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert library_root() == tmp_path / "xdg" / "visual" / "library"
    assert prefs_path() == tmp_path / "xdg" / "visual" / "ui.json"
    monkeypatch.delenv("XDG_DATA_HOME")
    assert library_root() == home / ".local" / "share" / "visual" / "library"
    assert prefs_path() == home / ".local" / "share" / "visual" / "ui.json"


def test_store_path_overrides_win_on_every_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for platform in ("win32", "darwin", "linux"):
        _no_store_env(monkeypatch, tmp_path / "home")
        monkeypatch.setattr(sys, "platform", platform)
        monkeypatch.setenv("VISUAL_LIBRARY", str(tmp_path / "lib"))
        monkeypatch.setenv("VISUAL_PREFS", str(tmp_path / "ui.json"))
        assert library_root() == tmp_path / "lib"
        assert prefs_path() == tmp_path / "ui.json"


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

