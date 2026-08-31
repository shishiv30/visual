from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from clients.windows.store.athletes import AthleteProfile
from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    ClipStatus,
    SeedMark,
    media_path,
    save_meta,
)
from clients.windows.ui.prepare_page import PreparePage
from core.i18n import set_language


@pytest.fixture
def library_and_athletes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VISUAL_LIBRARY", str(tmp_path / "library"))
    monkeypatch.setenv("VISUAL_ATHLETES", str(tmp_path / "athletes.json"))
    return tmp_path


def test_prepare_start_requires_athlete_and_emits_profile(
    library_and_athletes: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    meta = ClipMeta(
        clip_id="c-ath",
        created_at="2026-08-25T21:45:00-05:00",
        display_name="clip",
        kind=ClipKind.IMAGE,
        status=ClipStatus.PENDING,
        duration_ms=0,
        seeds=[SeedMark(t_ms=0.0, box=(0.1, 0.1, 0.5, 0.8))],
    )
    save_meta(meta)
    import numpy as np
    import cv2

    path = media_path(meta)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((64, 64, 3), dtype=np.uint8))

    page = PreparePage()
    seen: list[object] = []
    page.analysis_requested.connect(lambda *args: seen.append(args))
    page.open_clip(meta.clip_id)
    page._name.clear()
    boxes: list[str] = []

    def fake_info(parent, title, text):
        boxes.append(f"{title}|{text}")
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", fake_info)
    page._start()
    assert not seen
    assert boxes

    page._name.setText("Ada")
    page._height.setValue(175)
    page._weight.setValue(70)
    page._ski.setValue(165)
    page._start()
    assert len(seen) == 1
    athlete = seen[0][4]
    assert isinstance(athlete, AthleteProfile)
    assert athlete.key == "Ada-70-175-165"
    del app


def _image_clip(clip_id: str) -> ClipMeta:
    meta = ClipMeta(
        clip_id=clip_id,
        created_at="2026-08-25T21:45:00-05:00",
        display_name="clip",
        kind=ClipKind.IMAGE,
        status=ClipStatus.PENDING,
        duration_ms=0,
        seeds=[SeedMark(t_ms=0.0, box=(0.1, 0.1, 0.5, 0.8))],
    )
    save_meta(meta)
    import cv2
    import numpy as np

    path = media_path(meta)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((64, 64, 3), dtype=np.uint8))
    return meta


def test_prepare_scene_picker_is_optional_and_emitted(
    library_and_athletes: Path,
) -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    meta = _image_clip("c-scene")
    page = PreparePage()
    seen: list[tuple] = []
    page.analysis_requested.connect(lambda *args: seen.append(args))
    page.open_clip(meta.clip_id)
    page._name.setText("Ada")

    # Default is "not sure": the report must still run.
    page._start()
    assert seen[-1][5] == {
        "snow_surface": None,
        "slope_band": None,
        "terrain_type": None,
        "view": None,
        "camera_motion": None,
        "fps_effective": None,
    }

    page._snow.setCurrentIndex(page._snow.findData("ice"))
    page._slope.setCurrentIndex(page._slope.findData("double-black"))
    page._start()
    assert seen[-1][5]["snow_surface"] == "ice"
    assert seen[-1][5]["slope_band"] == "double-black"

    # A stored scene pre-fills the picker; an unknown one falls back to not sure.
    meta.scene = {"snow_surface": "powder", "slope_band": "sandpaper"}
    save_meta(meta)
    page.open_clip(meta.clip_id)
    assert page._snow.currentData() == "powder"
    assert page._slope.currentData() == ""
    del app
