"""Windows offline pose client."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget  # noqa: E402

from clients.windows.pipeline.analyze import AnalysisQueue  # noqa: E402
from clients.windows.store.library import (  # noqa: E402
    ClipStatus,
    delete_clip,
    load_meta,
    prepare_reanalyze,
    save_meta,
)
from clients.windows.store.prefs import load_language, save_language  # noqa: E402
from clients.windows.ui.capture_page import CapturePage  # noqa: E402
from clients.windows.ui.loading_overlay import LoadingOverlay  # noqa: E402
from clients.windows.ui.list_page import ListPage  # noqa: E402
from clients.windows.ui.player_page import PlayerPage  # noqa: E402
from clients.windows.ui.prepare_page import PreparePage  # noqa: E402
from clients.windows.ui.theme import (  # noqa: E402
    app_stylesheet,
    apply_dark_palette,
    install_pointer_buttons,
)
from core.i18n import set_language, t  # noqa: E402
from core.mediapipe_engine import DEFAULT_TASK  # noqa: E402


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        set_language(load_language())
        self.resize(960, 800)
        self._stack = QStackedWidget()
        self._list = ListPage()
        self._capture = CapturePage()
        self._player = PlayerPage()
        self._prepare = PreparePage()
        self._stack.addWidget(self._list)
        self._stack.addWidget(self._capture)
        self._stack.addWidget(self._player)
        self._stack.addWidget(self._prepare)
        self.setCentralWidget(self._stack)

        self._queue = AnalysisQueue(self)
        self._queue.clip_updated.connect(self._list.reload)
        self._queue.busyChanged.connect(self._sync_loading)
        self._loading = LoadingOverlay(self._stack)
        self._importing = False

        self._list.capture_requested.connect(self._open_capture)
        self._list.import_requested.connect(self._open_import)
        self._list.play_requested.connect(self._open_player)
        self._list.seed_requested.connect(self._on_seed)
        self._list.delete_requested.connect(self._on_delete)
        self._list.reanalyze_requested.connect(self._on_reanalyze)
        self._list.language_changed.connect(self._on_language)
        self._capture.back_requested.connect(self._open_list)
        self._capture.clip_ready.connect(self._on_clip_ready)
        self._capture.import_busy.connect(self._on_import_busy)
        self._player.back_requested.connect(self._open_list)
        self._player.nodeClicked.connect(lambda _lid, cid: self._open_player(cid) if cid else None)
        self._prepare.back_requested.connect(self._open_list)
        self._prepare.analysis_requested.connect(self._on_prepare_done)
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(t("Visual Pose — Windows"))
        if not DEFAULT_TASK.is_file():
            self.statusBar().showMessage(t("Missing model {path}. Run: python scripts/download_pose_landmarker.py", path=str(DEFAULT_TASK)))
        self._list.retranslate()
        self._capture.retranslate()
        self._player.retranslate()
        self._prepare.retranslate()
        self._loading.retranslate()

    def _on_import_busy(self, busy: bool) -> None:
        self._importing = busy
        self._sync_loading()

    def _sync_loading(self) -> None:
        if self._importing:
            self._loading.show_kind("import")
            self._place_loading()
            return
        if self._queue.is_busy():
            self._loading.show_kind("analyze")
            self._place_loading()
            return
        self._loading.dismiss()

    def _place_loading(self) -> None:
        self._loading.setGeometry(self._stack.rect())
        self._loading.raise_()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._loading.isVisible():
            self._place_loading()

    def _on_language(self, code: str) -> None:
        set_language(code)
        save_language(code)
        self.retranslate()
        self._player.reproject_report()

    def _open_list(self) -> None:
        self._list.reload()
        self._stack.setCurrentWidget(self._list)

    def _open_capture(self) -> None:
        self._capture.start_camera()
        self._stack.setCurrentWidget(self._capture)

    def _open_import(self) -> None:
        self._capture.prepare_import()
        self._stack.setCurrentWidget(self._capture)
        started = self._capture.pick_file()
        if not started:
            self._capture.restore_chrome()
            self._open_list()

    def _open_player(self, clip_id: str) -> None:
        self._player.open_clip(clip_id)
        self._stack.setCurrentWidget(self._player)

    def _on_clip_ready(self, clip_id: str) -> None:
        self._open_list()

    def _on_seed(self, clip_id: str) -> None:
        self._prepare.open_clip(clip_id)
        self._stack.setCurrentWidget(self._prepare)

    def _on_prepare_done(
        self,
        clip_id: str,
        seeds: list,
        in_ms: int,
        out_ms: object,
        athlete: object,
        scene: object = None,
    ) -> None:
        meta = load_meta(clip_id)
        meta.seeds = list(seeds)
        meta.seed_box = seeds[0].box if seeds else None
        meta.play_start_ms = int(in_ms)
        meta.play_end_ms = None if out_ms is None else int(out_ms)
        if athlete is not None and hasattr(athlete, "model_dump"):
            snapshot = athlete.model_dump()
            meta.athlete_key = str(snapshot.get("key") or "") or None
            meta.athlete = snapshot
        if isinstance(scene, dict):
            meta.scene = scene
        meta.status = ClipStatus.PROCESSING
        meta.error = None
        save_meta(meta)
        self._queue.enqueue(clip_id)
        self._open_list()

    def _on_delete(self, clip_id: str) -> None:
        self._queue.drop(clip_id)
        if self._stack.currentWidget() in (self._player, self._prepare):
            self._open_list()
        delete_clip(clip_id)
        self._list.reload()

    def _on_reanalyze(self, clip_id: str) -> None:
        prepare_reanalyze(clip_id)
        self._on_seed(clip_id)


def main() -> int:
    app = QApplication(sys.argv)
    apply_dark_palette(app)
    app.setStyleSheet(app_stylesheet())
    install_pointer_buttons(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
