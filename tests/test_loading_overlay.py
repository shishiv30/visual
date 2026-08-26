from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from clients.windows.ui.loading_overlay import LoadingOverlay
from core.i18n import set_language


def test_loading_overlay_caption() -> None:
    set_language("en")
    app = QApplication.instance() or QApplication([])
    overlay = LoadingOverlay()
    overlay.show_kind("import")
    assert "Upload" in overlay._caption.text() or "load" in overlay._caption.text().lower()
    overlay.show_kind("analyze")
    assert "Analyz" in overlay._caption.text()
    overlay.dismiss()
    overlay.show_kind("import")
    overlay.show_kind("import")
    assert overlay._spinner._timer.isActive()
    overlay.dismiss()
    assert not overlay.isVisible()
    del app
