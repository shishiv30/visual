"""Capture / import page with optional 120s trim."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from clients.windows.pipeline.ingest import IngestWorker
from clients.windows.pipeline.normalize import MAX_SECONDS, probe_duration_ms
from clients.windows.ui.loading_overlay import LoadingOverlay
from clients.windows.ui.qtutil import (
    bgr_to_pixmap,
    make_floating_back,
    place_floating_back,
    set_button_icon,
    style_floating_back,
)
from clients.windows.ui.theme import BLUE, PAGE_INSET, SPACE_PANEL
from clients.windows.ui.trim_dialog import TrimDialog
from core.i18n import t

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


class CapturePage(QWidget):
    back_requested = Signal()
    clip_ready = Signal(str)
    import_busy = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("capturePage")
        self._cam: cv2.VideoCapture | None = None
        self._writer: cv2.VideoWriter | None = None
        self._record_path: Path | None = None
        self._recording = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._ingest_thread: QThread | None = None
        self._ingest_worker: IngestWorker | None = None

        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(640, 360)
        self._preview.setStyleSheet("background:#111;color:#ddd;")

        self._record_btn = QPushButton()
        self._record_btn.clicked.connect(self._toggle_record)
        self._pick_btn = QPushButton()
        set_button_icon(self._pick_btn, "import", BLUE)
        self._pick_btn.clicked.connect(self._pick_file)

        bar = QHBoxLayout()
        bar.addWidget(self._record_btn)
        bar.addWidget(self._pick_btn)
        bar.addStretch()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(PAGE_INSET, PAGE_INSET, PAGE_INSET, PAGE_INSET)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(self._preview)
        layout.addLayout(bar)
        self._overlay = LoadingOverlay(self)
        self._back_btn = make_floating_back(self)
        self._back_btn.clicked.connect(self._on_back)
        self.retranslate()

    def retranslate(self) -> None:
        if not self._recording:
            self._preview.setText(t("Camera preview"))
        self._sync_record_button()
        style_floating_back(self._back_btn, tooltip=t("Back"))
        self._pick_btn.setText(t("Import…"))
        set_button_icon(self._pick_btn, "import", BLUE)
        self._overlay.retranslate()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        place_floating_back(self._back_btn, self)
        self._back_btn.raise_()

    def prepare_import(self) -> None:
        self.stop_camera()
        self._preview.clear()
        self._preview.hide()
        self._record_btn.hide()
        self._pick_btn.hide()
        self._back_btn.hide()

    def restore_chrome(self) -> None:
        self._overlay.dismiss()
        self._set_chrome_visible(True)
        if not self._recording:
            self._preview.setText(t("Camera preview"))

    def _set_chrome_visible(self, visible: bool) -> None:
        self._preview.setVisible(visible)
        self._record_btn.setVisible(visible)
        self._pick_btn.setVisible(visible)
        self._back_btn.setVisible(visible)

    def _sync_record_button(self) -> None:
        if self._recording:
            set_button_icon(self._record_btn, "stop")
            self._record_btn.setText(t("Stop"))
        else:
            set_button_icon(self._record_btn, "record")
            self._record_btn.setText(t("Record"))

    def start_camera(self) -> None:
        if sys.platform == "darwin":
            QMessageBox.information(
                self,
                t("Camera not available"),
                t("Camera capture is not supported on macOS. Use Import to load a video file."),
            )
            self.back_requested.emit()
            return
        self._overlay.dismiss()
        self._set_chrome_visible(True)
        self._cam = cv2.VideoCapture(0)
        self._timer.start(33)

    def stop_camera(self) -> None:
        self._timer.stop()
        self._stop_writer()
        if self._cam is not None:
            self._cam.release()
            self._cam = None

    def _on_back(self) -> None:
        if self._recording:
            self._toggle_record()
        self.stop_camera()
        self.back_requested.emit()

    def _tick(self) -> None:
        if self._cam is None:
            return
        ok, frame = self._cam.read()
        if not ok or frame is None:
            return
        self._preview.setPixmap(bgr_to_pixmap(frame, max_width=960))
        if self._recording and self._writer is not None:
            self._writer.write(frame)

    def _toggle_record(self) -> None:
        if not self._recording:
            if self._cam is None:
                self.start_camera()
            ok, frame = self._cam.read() if self._cam is not None else (False, None)
            if not ok or frame is None:
                QMessageBox.warning(self, t("Camera device"), t("Could not open the camera."))
                return
            h, w = frame.shape[:2]
            fd, name = tempfile.mkstemp(suffix=".avi")
            os.close(fd)
            tmp = Path(name)
            self._record_path = tmp
            self._writer = cv2.VideoWriter(
                str(tmp), cv2.VideoWriter_fourcc(*"XVID"), 20.0, (w, h)
            )
            self._recording = True
            self._sync_record_button()
            return
        self._recording = False
        self._sync_record_button()
        path = self._record_path
        self._stop_writer()
        self.stop_camera()
        if path is not None and path.is_file():
            self._ingest_video(path, delete_src=True)

    def _stop_writer(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def pick_file(self) -> bool:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            t("Choose video or image"),
            "",
            t("Media (*.mp4 *.mov *.avi *.mkv *.webm *.jpg *.jpeg *.png *.webp *.bmp)"),
        )
        if not path_str:
            return False
        path = Path(path_str)
        if path.suffix.lower() in IMAGE_EXT:
            self._begin_ingest("image", path, 0.0, 0.0, False)
            return True
        if path.suffix.lower() in VIDEO_EXT:
            return self._ingest_video(path, delete_src=False)
        QMessageBox.warning(self, t("Format"), t("Unsupported file type."))
        return False

    def _pick_file(self) -> None:
        self.pick_file()

    def _ingest_video(self, src: Path, *, delete_src: bool) -> bool:
        duration_ms = probe_duration_ms(src)
        start_s = 0.0
        duration_s = min(duration_ms / 1000.0 if duration_ms else MAX_SECONDS, MAX_SECONDS)
        if duration_ms > MAX_SECONDS * 1000.0 + 50:
            dialog = TrimDialog(src, self)
            if dialog.exec() != TrimDialog.DialogCode.Accepted:
                if delete_src:
                    src.unlink(missing_ok=True)
                return False
            start_s = dialog.start_s()
            duration_s = dialog.duration_s()
        self._begin_ingest("video", src, start_s, duration_s, delete_src)
        return True

    def _begin_ingest(
        self,
        kind: str,
        src: Path,
        start_s: float,
        duration_s: float,
        delete_src: bool,
    ) -> None:
        self._set_chrome_visible(False)
        self._overlay.setGeometry(self.rect())
        self._overlay.show_kind("import")
        self.import_busy.emit(True)
        thread = QThread()
        worker = IngestWorker(
            kind=kind,
            src=str(src),
            start_s=start_s,
            duration_s=duration_s,
            delete_src=delete_src,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ingest_ok)
        worker.failed.connect(self._on_ingest_fail)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_ingest)
        self._ingest_thread = thread
        self._ingest_worker = worker
        thread.start()

    def _clear_ingest(self) -> None:
        self._ingest_thread = None
        self._ingest_worker = None

    def _on_ingest_ok(self, clip_id: str) -> None:
        self._overlay.dismiss()
        self.import_busy.emit(False)
        self.clip_ready.emit(clip_id)

    def _on_ingest_fail(self, message: str) -> None:
        self._overlay.dismiss()
        self.import_busy.emit(False)
        self._set_chrome_visible(True)
        QMessageBox.critical(self, t("Import failed"), message)
