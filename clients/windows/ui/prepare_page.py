"""Seek, person box, and logical in/out before analysis."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from clients.windows.pipeline.clip_range import play_window_ms
from clients.windows.store.athletes import (
    AthleteGender,
    AthleteProfile,
    get_by_key,
    list_athletes,
    upsert_athlete,
)
from clients.windows.store.library import ClipKind, ClipMeta, SeedMark, load_meta, media_path
from clients.windows.ui.qtutil import (
    bgr_to_pixmap,
    format_duration_ms,
    make_floating_back,
    place_floating_back,
    set_button_icon,
    style_floating_back,
)
from clients.windows.ui.seed_dialog import SeedCanvas
from clients.windows.ui.theme import BLUE, PAGE_INSET, SPACE_PANEL, SPACE_TEXT
from clients.windows.ui.timeline_strip import TimelineStrip
from core.i18n import t

CONTROL_HEIGHT = 44
DEFAULT_BIRTHDAY = QDate(1990, 1, 1)


def _labeled_field(label: QLabel, control: QWidget) -> QWidget:
    wrap = QWidget()
    col = QVBoxLayout(wrap)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(6)
    col.addWidget(label)
    col.addWidget(control)
    return wrap


def _style_control(widget: QWidget) -> None:
    widget.setFixedHeight(CONTROL_HEIGHT)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class PreparePage(QWidget):
    back_requested = Signal()
    analysis_requested = Signal(str, list, int, object, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preparePage")
        self._meta: ClipMeta | None = None
        self._cap: cv2.VideoCapture | None = None
        self._fps = 30.0
        self._t_ms = 0.0
        self._frame_index = 0
        self._seeds: dict[int, SeedMark] = {}
        self._in_ms = 0
        self._out_ms: int | None = None
        self._loading_profile = False

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        blank = np.zeros((180, 320, 3), dtype=np.uint8)
        self._canvas = SeedCanvas(bgr_to_pixmap(blank, max_width=720))
        self._canvas.boxCommitted.connect(self._on_box_committed)

        self._time = QLabel()
        self._timeline = TimelineStrip()
        self._timeline.playheadChanged.connect(self._on_playhead)
        self._timeline.rangeChanged.connect(self._on_range)

        self._start_btn = QPushButton()
        set_button_icon(self._start_btn, "ok", BLUE)
        self._start_btn.clicked.connect(self._start)
        _style_control(self._start_btn)

        self._range = QLabel()
        self._range.setWordWrap(True)

        self._profile_label = QLabel()
        self._profile = QComboBox()
        _style_control(self._profile)
        self._profile.currentIndexChanged.connect(self._on_profile_picked)

        self._name_label = QLabel()
        self._name = QLineEdit()
        _style_control(self._name)
        self._birthday_label = QLabel()
        self._birthday = QDateEdit()
        self._birthday.setCalendarPopup(True)
        self._birthday.setDate(DEFAULT_BIRTHDAY)
        _style_control(self._birthday)
        self._height_label = QLabel()
        self._height = QDoubleSpinBox()
        self._height.setRange(50.0, 250.0)
        self._height.setDecimals(1)
        self._height.setValue(170.0)
        _style_control(self._height)
        self._gender_label = QLabel()
        self._gender = QComboBox()
        _style_control(self._gender)
        self._weight_label = QLabel()
        self._weight = QDoubleSpinBox()
        self._weight.setRange(20.0, 200.0)
        self._weight.setDecimals(1)
        self._weight.setValue(65.0)
        _style_control(self._weight)
        self._ski_label = QLabel()
        self._ski = QDoubleSpinBox()
        self._ski.setRange(80.0, 220.0)
        self._ski.setDecimals(1)
        self._ski.setValue(160.0)
        _style_control(self._ski)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(SPACE_PANEL)
        form.setVerticalSpacing(SPACE_TEXT)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        profile_field = _labeled_field(self._profile_label, self._profile)
        form.addWidget(profile_field, 0, 0, 1, 2)
        form.addWidget(_labeled_field(self._name_label, self._name), 1, 0)
        form.addWidget(_labeled_field(self._birthday_label, self._birthday), 1, 1)
        form.addWidget(_labeled_field(self._height_label, self._height), 2, 0)
        form.addWidget(_labeled_field(self._gender_label, self._gender), 2, 1)
        form.addWidget(_labeled_field(self._weight_label, self._weight), 3, 0)
        form.addWidget(_labeled_field(self._ski_label, self._ski), 3, 1)
        self._form_box = QWidget()
        self._form_box.setObjectName("athleteForm")
        self._form_box.setLayout(form)

        bar = QHBoxLayout()
        bar.setSpacing(SPACE_TEXT)
        bar.addWidget(self._start_btn)
        bar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(PAGE_INSET, PAGE_INSET, PAGE_INSET, PAGE_INSET)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(self._hint)
        layout.addWidget(self._canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._time)
        layout.addWidget(self._timeline)
        layout.addWidget(self._form_box)
        layout.addLayout(bar)
        layout.addWidget(self._range)
        self._back_btn = make_floating_back(self)
        self._back_btn.clicked.connect(self._on_back)
        self.retranslate()
        self._reload_profiles()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        place_floating_back(self._back_btn, self)

    def retranslate(self) -> None:
        self._hint.setText(t("Click the filmstrip to seek; green diamonds are saved boxes (click to jump). Drag the blue start/end edges to trim. Shift+wheel zooms. Draw a person box — it saves for this frame; draw again on the same frame to replace."))
        self._start_btn.setText(t("Start analysis"))
        set_button_icon(self._start_btn, "ok", BLUE)
        style_floating_back(self._back_btn, tooltip=t("Back"))
        self._profile_label.setText(t("Saved profile"))
        self._name_label.setText(t("Name"))
        self._birthday_label.setText(t("Birthday"))
        self._height_label.setText(t("Height"))
        self._gender_label.setText(t("Gender"))
        self._weight_label.setText(t("Weight"))
        self._ski_label.setText(t("Ski length"))
        self._birthday.setDisplayFormat(t("MM/dd/yyyy"))
        self._height.setSuffix(t(" cm"))
        self._weight.setSuffix(t(" kg"))
        self._ski.setSuffix(t(" cm"))
        current_gender = self._gender.currentData()
        self._gender.blockSignals(True)
        self._gender.clear()
        for value, key in (
            (AthleteGender.UNSPECIFIED, "Unspecified"),
            (AthleteGender.FEMALE, "Female"),
            (AthleteGender.MALE, "Male"),
            (AthleteGender.OTHER, "Other"),
        ):
            self._gender.addItem(t(key), value.value)
        if current_gender is not None:
            idx = self._gender.findData(current_gender)
            if idx >= 0:
                self._gender.setCurrentIndex(idx)
        self._gender.blockSignals(False)
        self._reload_profiles(preserve_key=self._profile.currentData())
        self._refresh_labels()

    def open_clip(self, clip_id: str) -> None:
        self._release()
        self._meta = load_meta(clip_id)
        loaded = list(self._meta.seeds)
        if not loaded and self._meta.seed_box is not None:
            loaded = [SeedMark(t_ms=0.0, box=self._meta.seed_box)]
        start, end = play_window_ms(self._meta)
        self._in_ms = int(self._meta.play_start_ms or 0)
        self._out_ms = self._meta.play_end_ms
        path = media_path(self._meta)
        self._reload_profiles(preserve_key=self._meta.athlete_key)
        if self._meta.athlete_key:
            self._apply_profile_key(self._meta.athlete_key)
        elif self._meta.athlete:
            self._fill_from_dict(self._meta.athlete)
        if self._meta.kind == ClipKind.IMAGE:
            self._seeds = {0: loaded[0]} if loaded else {}
            bgr = cv2.imread(str(path))
            self._timeline.hide()
            if bgr is not None:
                self._show_bgr(bgr, 0.0, 0)
            self._refresh_labels()
            return
        self._timeline.show()
        self._cap = cv2.VideoCapture(str(path))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 30.0) or 30.0
        self._seeds = self._seeds_by_frame(loaded, self._fps)
        duration = int(self._meta.duration_ms) or 1
        self._timeline.bind_video(path, duration)
        if self._meta.play_end_ms is not None:
            self._out_ms = int(end)
        self._in_ms = int(start) if self._meta.play_start_ms else self._in_ms
        self._timeline.set_range(self._in_ms, self._out_ms)
        self._sync_keyframes()
        self._seek_ms(self._in_ms)
        self._refresh_labels()

    def _on_back(self) -> None:
        self._release()
        self.back_requested.emit()

    def _release(self) -> None:
        self._timeline.clear()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _on_playhead(self, t_ms: int) -> None:
        self._seek_ms(t_ms)

    def _on_range(self, in_ms: int, out_ms: int) -> None:
        self._in_ms = in_ms
        self._out_ms = out_ms
        self._refresh_labels()

    def _seek_ms(self, t_ms: int) -> None:
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_MSEC, float(max(0, t_ms)))
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            return
        shown = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        frame_index = max(0, int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        if shown <= 0.0:
            shown = float(t_ms)
        self._show_bgr(bgr, shown, frame_index)

    def _show_bgr(self, bgr, t_ms: float, frame_index: int) -> None:
        self._t_ms = t_ms
        self._frame_index = frame_index
        pix = bgr_to_pixmap(bgr, max_width=720)
        self._canvas.set_frame(pix)
        mark = self._seeds.get(frame_index) or self._seed_near(t_ms)
        self._canvas.set_box_norm(None if mark is None else mark.box)
        self._timeline.set_playhead_ms(int(t_ms))
        self._refresh_labels()

    def _seeds_by_frame(self, seeds: list[SeedMark], fps: float) -> dict[int, SeedMark]:
        frame_ms = 1000.0 / max(fps, 1.0)
        keyed: dict[int, SeedMark] = {}
        for item in seeds:
            keyed[int(round(item.t_ms / frame_ms))] = item
        return keyed

    def _seed_near(self, t_ms: float) -> SeedMark | None:
        hit: SeedMark | None = None
        best = 40.0
        for item in self._seeds.values():
            delta = abs(item.t_ms - t_ms)
            if delta <= best:
                best = delta
                hit = item
        return hit

    def _sync_keyframes(self) -> None:
        self._timeline.set_keyframes([int(item.t_ms) for item in self._seeds.values()])

    def _on_box_committed(self) -> None:
        box = self._canvas.box_norm()
        if box is None:
            return
        key = self._frame_index
        self._seeds[key] = SeedMark(t_ms=self._t_ms, box=box)
        self._sync_keyframes()
        self._refresh_labels()

    def _reload_profiles(self, preserve_key: str | None = None) -> None:
        self._loading_profile = True
        want = preserve_key
        self._profile.blockSignals(True)
        self._profile.clear()
        self._profile.addItem(t("New profile"), "")
        for item in list_athletes():
            self._profile.addItem(item.key, item.key)
        if want:
            idx = self._profile.findData(want)
            if idx >= 0:
                self._profile.setCurrentIndex(idx)
        self._profile.blockSignals(False)
        self._loading_profile = False

    def _on_profile_picked(self, _index: int) -> None:
        if self._loading_profile:
            return
        key = str(self._profile.currentData() or "")
        if not key:
            return
        self._apply_profile_key(key)

    def _apply_profile_key(self, key: str) -> None:
        profile = get_by_key(key)
        if profile is None:
            return
        self._fill_from_profile(profile)
        self._loading_profile = True
        idx = self._profile.findData(profile.key)
        if idx >= 0:
            self._profile.setCurrentIndex(idx)
        self._loading_profile = False

    def _fill_from_profile(self, profile: AthleteProfile) -> None:
        self._name.setText(profile.name)
        self._height.setValue(profile.height_cm)
        self._weight.setValue(profile.weight_kg)
        self._ski.setValue(profile.ski_cm)
        gender_idx = self._gender.findData(profile.gender.value)
        if gender_idx >= 0:
            self._gender.setCurrentIndex(gender_idx)
        if profile.birthday:
            parsed = QDate.fromString(profile.birthday, Qt.DateFormat.ISODate)
            if parsed.isValid():
                self._birthday.setDate(parsed)
            else:
                self._birthday.setDate(DEFAULT_BIRTHDAY)
        else:
            self._birthday.setDate(DEFAULT_BIRTHDAY)

    def _fill_from_dict(self, data: dict) -> None:
        try:
            profile = AthleteProfile.model_validate(data)
        except Exception:
            return
        self._fill_from_profile(profile)

    def _birthday_iso(self) -> str:
        return self._birthday.date().toString(Qt.DateFormat.ISODate)

    def _read_athlete(self) -> AthleteProfile | None:
        name = self._name.text().strip()
        if not name:
            return None
        try:
            return upsert_athlete(
                name=name,
                weight_kg=float(self._weight.value()),
                height_cm=float(self._height.value()),
                ski_cm=float(self._ski.value()),
                birthday=self._birthday_iso(),
                gender=str(self._gender.currentData() or AthleteGender.UNSPECIFIED.value),
            )
        except ValueError:
            return None

    def _start(self) -> None:
        if self._meta is None:
            return
        if not self._seeds:
            QMessageBox.information(self, t("No box"), t("Record at least one person box."))
            return
        athlete = self._read_athlete()
        if athlete is None:
            QMessageBox.information(
                self, t("Athlete info required"), t("Enter name, height, weight, and ski length, or pick a saved profile.")
            )
            return
        self._reload_profiles(preserve_key=athlete.key)
        seeds = sorted(self._seeds.values(), key=lambda item: item.t_ms)
        self.analysis_requested.emit(
            self._meta.clip_id, seeds, self._in_ms, self._out_ms, athlete
        )

    def _refresh_labels(self) -> None:
        total = 0
        if self._meta is not None:
            total = self._meta.duration_ms
        self._time.setText(
            f"{format_duration_ms(int(self._t_ms))} / {format_duration_ms(total)}"
        )
        out = self._out_ms if self._out_ms is not None else total
        self._range.setText(
            t(
                "In {lo:.1f}s → out {hi:.1f}s (logical, original file unchanged)",
                lo=self._in_ms / 1000.0,
                hi=(out / 1000.0) if out else 0.0,
            )
        )
