"""Playback with COCO-17 overlay and floating chrome."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal, Never
from urllib.parse import quote

import cv2
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from clients.windows.overlay.skeleton import draw_poses
from clients.windows.pipeline.clip_range import play_window_ms
from clients.windows.pipeline.export_overlay import (
    export_overlay,
    format_frame_hud,
    nearest_frame,
)
from clients.windows.pipeline.frame_locator import (
    build_locator_payload,
    draw_locator_label,
    locator_payload_json,
    short_clip_id,
)
from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    empty_frame_feedback,
    list_reports_for_athlete,
    load_analysis,
    load_frame_feedback,
    load_meta,
    load_stage_report,
    media_path,
    save_stage_report,
    toggle_frame_skeleton_ok,
    toggle_frame_stage_vote,
)
from core.sports.history import StageHistory
from clients.windows.ui.qtutil import (
    bgr_to_pixmap,
    make_floating_back,
    place_floating_back,
    set_button_icon,
    style_floating_back,
)
from clients.windows.ui.report_panel import StageReportPanel
from clients.windows.ui.theme import LIGHT_PURPLE, PAGE_INSET, SPACE_CHAPTER, UNKNOWN_GRAY, WATERMELON
from clients.windows.ui.timeline_strip import TimelineStrip
from core.i18n import t
from core.sports.assess import assess_clip
from schemas.clip_analysis import ClipAnalysis

CHROME_ICON = QColor("#F5F5F5")

SPEEDS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
#: ``(target_id, display key, url template)``. The display key is the English
#: brand name registered in the locale catalog — the ids are internal only and
#: must never reach ``t()`` (snake_case locale keys are forbidden).
SHARE_TARGETS = (
    ("share_youtube", "YouTube", "https://www.youtube.com/upload"),
    ("share_tiktok", "TikTok", "https://www.tiktok.com/upload"),
    ("share_x", "X", "https://twitter.com/intent/tweet?text={text}"),
    ("share_facebook", "Facebook", "https://www.facebook.com/sharer/sharer.php"),
    ("share_weibo", "Weibo", "https://service.weibo.com/share/share.php?title={text}"),
    (
        "share_bilibili",
        "Bilibili",
        "https://member.bilibili.com/platform/upload/video/frame",
    ),
)


class VideoView(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source: QPixmap | None = None
        self.setMinimumSize(240, 135)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setStyleSheet("background:#000;")

    def set_frame(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self._source is None or self._source.isNull():
            return
        target_h = self.height()
        if target_h <= 0:
            return
        scaled = self._source.scaledToHeight(
            target_h,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        painter.setClipRect(self.rect())
        painter.drawPixmap(x, 0, scaled)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class PlayerPage(QWidget):
    back_requested = Signal()
    nodeClicked = Signal(str, str)  # (level_id, clip_id_best)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playerPage")
        self._meta: ClipMeta | None = None
        self._analysis: ClipAnalysis | None = None
        self._report_model = None
        self._cap: cv2.VideoCapture | None = None
        self._playing = False
        self._ended = False
        self._speed = 1.0
        self._fps = 30.0
        self._lo_frame = 0
        self._hi_frame = 0
        self._export_path: Path | None = None
        self._feedback = empty_frame_feedback("")
        self._hud_t_ms = 0.0
        self._hud_video_frame = 0
        self._hud_pose_i: int | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_chrome)

        self._view = VideoView()
        self._view.clicked.connect(self._on_view_click)

        self._play_btn = QPushButton()
        self._play_btn.setFlat(True)
        self._play_btn.clicked.connect(self._toggle)
        self._speed_box = QComboBox()
        for speed in SPEEDS:
            self._speed_box.addItem(f"{speed:g}x", speed)
        self._speed_box.setCurrentIndex(SPEEDS.index(1.0))
        self._speed_box.currentIndexChanged.connect(self._on_speed)
        self._download_btn = QPushButton()
        self._download_btn.setFlat(True)
        set_button_icon(self._download_btn, "download", CHROME_ICON, restyle=False)
        self._download_btn.clicked.connect(self._on_download)
        self._share_btn = QPushButton()
        self._share_btn.setFlat(True)
        set_button_icon(self._share_btn, "share", CHROME_ICON, restyle=False)
        self._share_btn.clicked.connect(self._on_share)
        self._locator_btn = QPushButton()
        self._locator_btn.setObjectName("frameLocator")
        self._locator_btn.setFlat(True)
        self._locator_btn.clicked.connect(self._copy_locator)
        self._like_btn = QPushButton()
        self._like_btn.setObjectName("likeVote")
        self._like_btn.setFlat(True)
        self._like_btn.setCheckable(True)
        self._like_btn.setFixedHeight(32)
        self._like_btn.clicked.connect(self._on_like)
        self._unlike_btn = QPushButton()
        self._unlike_btn.setObjectName("unlikeVote")
        self._unlike_btn.setFlat(True)
        self._unlike_btn.setCheckable(True)
        self._unlike_btn.setFixedHeight(32)
        self._unlike_btn.clicked.connect(self._on_unlike)
        self._skeleton_btn = QPushButton()
        self._skeleton_btn.setObjectName("skeletonVote")
        self._skeleton_btn.setFlat(True)
        self._skeleton_btn.setCheckable(True)
        self._skeleton_btn.setFixedHeight(32)
        self._skeleton_btn.clicked.connect(self._on_skeleton_bad)

        self._chrome = QWidget()
        self._chrome.setObjectName("playerChrome")
        self._chrome.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._chrome.setAutoFillBackground(False)
        self._chrome.installEventFilter(self)
        bar = QHBoxLayout(self._chrome)
        bar.setContentsMargins(8, 8, 8, 8)
        bar.addWidget(self._play_btn)
        bar.addWidget(self._locator_btn)
        bar.addStretch(1)
        bar.addWidget(self._speed_box)
        bar.addWidget(self._like_btn)
        bar.addWidget(self._unlike_btn)
        bar.addWidget(self._skeleton_btn)
        bar.addWidget(self._download_btn)
        bar.addWidget(self._share_btn)

        stage = QWidget()
        stage.setStyleSheet("background:#000;")
        grid = QGridLayout(stage)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self._view, 0, 0)
        grid.addWidget(self._chrome, 0, 0, alignment=Qt.AlignmentFlag.AlignBottom)

        self._timeline = TimelineStrip()
        self._timeline.set_trim_enabled(False)
        self._timeline.playheadChanged.connect(self._on_timeline_playhead)

        player_block = QWidget()
        player_layout = QVBoxLayout(player_block)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(0)
        player_layout.addWidget(stage, stretch=1)
        player_layout.addWidget(self._timeline)

        self._report = StageReportPanel()
        self._report.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._report.seekRequested.connect(self._on_report_seek)
        self._report.seekAndPlayRequested.connect(self._on_report_seek_and_play)
        self._report.nodeClicked.connect(self.nodeClicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(PAGE_INSET, PAGE_INSET, PAGE_INSET, PAGE_INSET)
        layout.setSpacing(SPACE_CHAPTER)
        layout.addWidget(player_block, stretch=1)
        layout.addWidget(self._report, stretch=2)
        self._back_btn = make_floating_back(self)
        self._back_btn.clicked.connect(self._on_back)
        self.retranslate()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        place_floating_back(self._back_btn, self)

    def eventFilter(self, watched, event) -> bool:
        if watched is self._chrome and event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
        ):
            self._on_chrome_activity()
        return super().eventFilter(watched, event)

    def retranslate(self) -> None:
        self._sync_play_button()
        style_floating_back(self._back_btn, tooltip=t("Back"))
        self._download_btn.setText("")
        self._download_btn.setToolTip(t("Download"))
        set_button_icon(self._download_btn, "download", CHROME_ICON, restyle=False)
        self._share_btn.setText("")
        self._share_btn.setToolTip(t("Share"))
        set_button_icon(self._share_btn, "share", CHROME_ICON, restyle=False)
        self._locator_btn.setToolTip(t("Copy frame locator"))
        set_button_icon(self._locator_btn, "tag", CHROME_ICON, restyle=False)
        self._like_btn.setText("")
        self._like_btn.setToolTip(t("Like"))
        set_button_icon(self._like_btn, "thumb_up", LIGHT_PURPLE, restyle=False)
        self._unlike_btn.setText("")
        self._unlike_btn.setToolTip(t("Unlike"))
        set_button_icon(self._unlike_btn, "thumb_down", WATERMELON, restyle=False)
        self._skeleton_btn.setText("")
        self._skeleton_btn.setToolTip(t("Bad skeleton"))
        set_button_icon(self._skeleton_btn, "reanalyze", UNKNOWN_GRAY, restyle=False)
        self._speed_box.setToolTip(t("Speed"))
        self._report.retranslate()

    def _set_playback_controls_visible(self, visible: bool) -> None:
        self._play_btn.setVisible(visible)
        self._speed_box.setVisible(visible)
        self._timeline.setVisible(visible)

    def _sync_play_button(self) -> None:
        self._play_btn.setText("")
        if self._playing:
            set_button_icon(self._play_btn, "pause", CHROME_ICON, restyle=False)
            self._play_btn.setToolTip(t("Pause"))
        else:
            set_button_icon(self._play_btn, "play", CHROME_ICON, restyle=False)
            self._play_btn.setToolTip(t("Play"))

    def open_clip(self, clip_id: str) -> None:
        self._release()
        self._export_path = None
        self._meta = load_meta(clip_id)
        try:
            self._analysis = load_analysis(clip_id)
        except (OSError, ValueError):
            self._analysis = None
        self._feedback = load_frame_feedback(clip_id)
        self.reproject_report()
        path = media_path(self._meta)
        if self._meta.kind == ClipKind.IMAGE:
            self._timeline.clear()
            bgr = cv2.imread(str(path))
            if bgr is not None:
                self._show(bgr, 0.0, video_frame=0)
            self._lo_frame = 0
            self._hi_frame = 0
            self._set_playback_controls_visible(False)
            self._show_chrome(auto_hide=False)
            return
        self._set_playback_controls_visible(True)
        self._cap = cv2.VideoCapture(str(path))
        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 30.0) or 30.0
        total = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
        start_ms, end_ms = play_window_ms(self._meta)
        self._lo_frame = int(start_ms / 1000.0 * self._fps)
        self._hi_frame = int(end_ms / 1000.0 * self._fps)
        if end_ms >= 1e11:
            self._hi_frame = total - 1
        self._lo_frame = max(0, min(self._lo_frame, max(total - 1, 0)))
        self._hi_frame = max(self._lo_frame, min(self._hi_frame, max(total - 1, 0)))
        duration = int(self._meta.duration_ms) or int(1000.0 * total / self._fps)
        self._timeline.bind_video(path, duration)
        self._timeline.set_range(start_ms, None if end_ms >= 1e11 else int(end_ms))
        if self._analysis is not None:
            self._timeline.set_keyframes([int(frame.t_ms) for frame in self._analysis.frames])
        self._playing = True
        self._ended = False
        self._seek(self._lo_frame)
        self._timer.start(self._interval_ms())
        self._sync_play_button()
        self._show_chrome(auto_hide=True)

    def reproject_report(self) -> None:
        """Rebuild stage report strings for the active UI language."""
        if self._meta is None:
            return
        athlete_key = self._meta.athlete_key
        self._report.set_athlete_key(athlete_key)
        if self._analysis is not None:
            prior_reports = list_reports_for_athlete(
                athlete_key, exclude_clip_id=self._meta.clip_id
            )
            history = StageHistory.from_reports(prior_reports)
            report = assess_clip(self._analysis, history=history)
            save_stage_report(report)
            self._report_model = report
        else:
            self._report_model = load_stage_report(self._meta.clip_id)
        self._refresh_report()

    def _interval_ms(self) -> int:
        return max(8, int(1000.0 / self._fps / self._speed))

    def _on_back(self) -> None:
        self._release()
        self.back_requested.emit()

    def _on_view_click(self) -> None:
        self._show_chrome(auto_hide=self._playing)

    def _on_chrome_activity(self) -> None:
        if self._playing:
            self._hide_timer.start(3000)

    def _show_chrome(self, *, auto_hide: bool) -> None:
        self._chrome.show()
        if auto_hide and self._playing:
            self._hide_timer.start(3000)
        else:
            self._hide_timer.stop()

    def _hide_chrome(self) -> None:
        if self._playing and not self._ended:
            self._chrome.hide()

    def _toggle(self) -> None:
        if self._meta is None or self._meta.kind == ClipKind.IMAGE:
            return
        if self._ended and self._cap is not None:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._lo_frame)
            self._ended = False
        self._playing = not self._playing
        if self._playing:
            self._timer.start(self._interval_ms())
            self._show_chrome(auto_hide=True)
        else:
            self._timer.stop()
            self._show_chrome(auto_hide=False)
        self._sync_play_button()

    def _on_speed(self, _index: int) -> None:
        self._speed = float(self._speed_box.currentData() or 1.0)
        self._on_chrome_activity()
        if self._playing:
            self._timer.start(self._interval_ms())

    def _on_report_seek(self, t_ms: int) -> None:
        if self._playing:
            self._playing = False
            self._timer.stop()
            self._sync_play_button()
        frame_index = int(round(t_ms / 1000.0 * self._fps))
        self._seek(frame_index)

    def _on_report_seek_and_play(self, t_ms: int) -> None:
        frame_index = int(round(t_ms / 1000.0 * self._fps))
        self._seek(frame_index)
        if not self._playing:
            self._toggle()

    def _on_timeline_playhead(self, t_ms: int) -> None:
        frame_index = int(round(t_ms / 1000.0 * self._fps))
        self._seek(frame_index)

    def _seek(self, frame_index: int) -> None:
        if self._cap is None:
            return
        frame_index = max(self._lo_frame, min(frame_index, self._hi_frame))
        self._ended = False
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, bgr = self._cap.read()
        if ok and bgr is not None:
            t_ms = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
            self._show(bgr, t_ms, video_frame=frame_index)
        self._on_chrome_activity()

    def _tick(self) -> None:
        if self._cap is None or not self._playing:
            return
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            self._playing = False
            self._ended = True
            self._timer.stop()
            self._sync_play_button()
            self._show_chrome(auto_hide=False)
            return
        t_ms = float(self._cap.get(cv2.CAP_PROP_POS_MSEC))
        displayed = max(0, int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
        if displayed > self._hi_frame:
            self._playing = False
            self._ended = True
            self._timer.stop()
            self._sync_play_button()
            self._show_chrome(auto_hide=False)
            return
        self._show(bgr, t_ms, video_frame=displayed)

    def _stage_id(self) -> str:
        if self._report_model is None:
            return ""
        return str(self._report_model.stage_id)

    def _hud_text(self, t_ms: float, video_frame: int, pose_i: int | None) -> str:
        pose_n = len(self._analysis.frames) if self._analysis is not None else 0
        total = 0
        if self._meta is not None:
            total = self._meta.duration_ms
        short_id = short_clip_id(self._meta.clip_id) if self._meta is not None else ""
        return format_frame_hud(
            t_ms, total, video_frame, pose_i, pose_n, short_id=short_id
        )

    def _sync_feedback_buttons(self) -> None:
        key = str(int(self._hud_video_frame))
        entry = self._feedback.frames.get(key)
        vote = entry.stage_vote if entry is not None else None
        skeleton_ok = True if entry is None else entry.skeleton_ok
        self._like_btn.blockSignals(True)
        self._unlike_btn.blockSignals(True)
        self._skeleton_btn.blockSignals(True)
        self._like_btn.setChecked(vote == "like")
        self._unlike_btn.setChecked(vote == "unlike")
        self._skeleton_btn.setChecked(not skeleton_ok)
        self._like_btn.blockSignals(False)
        self._unlike_btn.blockSignals(False)
        self._skeleton_btn.blockSignals(False)

    def _copy_locator(self) -> None:
        if self._meta is None:
            return
        frame, _pose_i = nearest_frame(self._analysis, self._hud_t_ms)
        key = str(int(self._hud_video_frame))
        entry = self._feedback.frames.get(key)
        payload = build_locator_payload(
            clip_id=self._meta.clip_id,
            display_name=self._meta.display_name,
            video_frame=self._hud_video_frame,
            t_ms=self._hud_t_ms,
            fps=self._fps,
            analysis=self._analysis,
            analyzed=frame,
            pose_index=self._hud_pose_i,
            stage_id=self._stage_id(),
            feedback=None if entry is None else entry.model_dump(),
        )
        QGuiApplication.clipboard().setText(locator_payload_json(payload))
        QToolTip.showText(
            self._locator_btn.mapToGlobal(self._locator_btn.rect().center()),
            t("Frame locator JSON copied"),
            self._locator_btn,
            self._locator_btn.rect(),
            1500,
        )

    def _on_like(self) -> None:
        self._vote_stage("like")

    def _on_unlike(self) -> None:
        self._vote_stage("unlike")

    def _vote_stage(self, vote: Literal["like", "unlike"]) -> None:
        if self._meta is None:
            return
        match vote:
            case "like" | "unlike":
                self._feedback = toggle_frame_stage_vote(
                    self._meta.clip_id,
                    self._hud_video_frame,
                    vote,
                    t_ms=self._hud_t_ms,
                    pose_index=self._hud_pose_i,
                    stage_id=self._stage_id(),
                )
            case _:
                unreachable: Never = vote
                raise ValueError(unreachable)
        self._sync_feedback_buttons()

    def _on_skeleton_bad(self) -> None:
        if self._meta is None:
            return
        self._feedback = toggle_frame_skeleton_ok(
            self._meta.clip_id,
            self._hud_video_frame,
            t_ms=self._hud_t_ms,
            pose_index=self._hud_pose_i,
            stage_id=self._stage_id(),
        )
        self._sync_feedback_buttons()

    def _show(self, bgr, t_ms: float, *, video_frame: int = 0) -> None:
        frame, pose_i = nearest_frame(self._analysis, t_ms)
        if frame is not None:
            bgr = draw_poses(bgr, frame.result)
        hud = self._hud_text(t_ms, video_frame, pose_i)
        bgr = draw_locator_label(bgr, hud)
        self._view.set_frame(bgr_to_pixmap(bgr))
        self._hud_t_ms = t_ms
        self._hud_video_frame = video_frame
        self._hud_pose_i = pose_i
        short_id = short_clip_id(self._meta.clip_id) if self._meta is not None else ""
        self._locator_btn.setText(short_id)
        self._timeline.set_playhead_ms(int(t_ms))
        self._sync_feedback_buttons()

    def _on_download(self) -> None:
        path = self._export_overlay(ask_path=True)
        if path is not None:
            self._export_path = path

    def _on_share(self) -> None:
        menu = QMenu(self)
        for key, label_key, _url in SHARE_TARGETS:
            menu.addAction(t(label_key), lambda k=key: self._share_to(k))
        menu.exec(self._share_btn.mapToGlobal(self._share_btn.rect().bottomLeft()))

    def _share_to(self, key: str) -> None:
        path = self._export_path or self._export_overlay(ask_path=False)
        if path is None:
            return
        self._export_path = path
        QGuiApplication.clipboard().setText(str(path))
        text = quote(t("Visual Pose — Windows"))
        url = ""
        for item_key, _label_key, template in SHARE_TARGETS:
            if item_key == key:
                url = template.format(text=text)
                break
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _export_overlay(self, *, ask_path: bool) -> Path | None:
        if self._meta is None:
            return None
        image = self._meta.kind == ClipKind.IMAGE
        if ask_path:
            filt = t("JPEG (*.jpg)") if image else t("MP4 (*.mp4)")
            chosen, _ = QFileDialog.getSaveFileName(self, t("Download"), "", filt)
            if not chosen:
                return None
            dest = Path(chosen)
        else:
            suffix = ".jpg" if image else ".mp4"
            dest = Path(tempfile.mkstemp(suffix=suffix)[1])
        try:
            self._download_btn.setEnabled(False)
            self._share_btn.setEnabled(False)
            export_overlay(
                media_path(self._meta),
                dest,
                self._analysis,
                image=image,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, t("Download"), f"{t('Export failed')}\n{exc}")
            return None
        finally:
            self._download_btn.setEnabled(True)
            self._share_btn.setEnabled(True)
        return dest

    def _release(self) -> None:
        self._timer.stop()
        self._hide_timer.stop()
        self._playing = False
        self._ended = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._timeline.clear()
        self._sync_play_button()
        self._chrome.show()

    def _refresh_report(self) -> None:
        self._report.set_report(self._report_model)
