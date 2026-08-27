"""Library list page."""

from __future__ import annotations

from typing import Never

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPixmap, QRegion, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyleOption,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from clients.windows.store.library import (
    ClipKind,
    ClipMeta,
    ClipStatus,
    list_clips,
    load_stage_report,
    thumb_path,
)
from clients.windows.ui.loading_overlay import LoadingSpinner
from clients.windows.ui.qtutil import format_duration_ms, set_button_icon
from clients.windows.ui.theme import (
    BLUE,
    CARD_RADIUS,
    PURPLE,
    SPACE_PANEL,
    SPACE_TEXT,
    WATERMELON,
)
from core.i18n import LANG_LABELS, SUPPORTED, language, t


def report_button_enabled(status: ClipStatus, has_report: bool) -> bool:
    return status == ClipStatus.DONE and has_report


LIST_INSET = 8
CARD_PAD = 8


def _rounded_rect_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def _left_rounded_rect_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(rect.left() + radius, rect.top())
    path.lineTo(rect.right() + 1.0, rect.top())
    path.lineTo(rect.right() + 1.0, rect.bottom())
    path.lineTo(rect.left() + radius, rect.bottom())
    path.arcTo(
        QRectF(rect.left(), rect.bottom() - 2.0 * radius, 2.0 * radius, 2.0 * radius),
        270.0,
        -90.0,
    )
    path.lineTo(rect.left(), rect.top() + radius)
    path.arcTo(
        QRectF(rect.left(), rect.top(), 2.0 * radius, 2.0 * radius),
        180.0,
        -90.0,
    )
    path.closeSubpath()
    return path


class ClipRow(QWidget):
    """Card that clips children to rounded corners (QSS cannot clip pixmaps)."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("clipRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        path = _rounded_rect_path(QRectF(self.rect()), float(CARD_RADIUS))
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paintEvent(self, event: QPaintEvent) -> None:
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            target = self.childAt(event.position().toPoint())
            while target is not None and target is not self:
                if isinstance(target, QPushButton):
                    super().mousePressEvent(event)
                    return
                target = target.parentWidget()
            self.clicked.emit()
        super().mousePressEvent(event)


class ThumbLabel(QLabel):
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(_left_rounded_rect_path(QRectF(self.rect()), float(CARD_RADIUS)))
        pix = self.pixmap()
        if pix is not None and not pix.isNull():
            painter.drawPixmap(self.rect(), pix)
            return
        painter.fillRect(self.rect(), QColor("#000000"))
        painter.setPen(QColor("#bdbdbd"))
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), self.text())


def _status_key(status: ClipStatus) -> str:
    match status:
        case ClipStatus.PENDING:
            return "Pending"
        case ClipStatus.PROCESSING:
            return "Processing"
        case ClipStatus.DONE:
            return "Done"
        case _:
            unreachable: Never = status
            raise ValueError(unreachable)


class ListPage(QWidget):
    capture_requested = Signal()
    import_requested = Signal()
    play_requested = Signal(str)
    seed_requested = Signal(str)
    delete_requested = Signal(str)
    reanalyze_requested = Signal(str)
    language_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("listPage")
        self._ignore_item_click = False
        self._capture_btn = QPushButton()
        set_button_icon(self._capture_btn, "camera", BLUE)
        self._upload_btn = QPushButton()
        set_button_icon(self._upload_btn, "import", BLUE)
        self._lang_label = QLabel()
        self._lang = QComboBox()
        for code in SUPPORTED:
            self._lang.addItem(LANG_LABELS[code], code)
        self._lang.currentIndexChanged.connect(self._on_lang)
        self._capture_btn.clicked.connect(self.capture_requested.emit)
        self._upload_btn.clicked.connect(self.import_requested.emit)

        toolbar = QWidget()
        toolbar.setObjectName("listToolbar")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(10)
        bar.addWidget(self._capture_btn)
        bar.addWidget(self._upload_btn)
        bar.addStretch()
        bar.addWidget(self._lang_label)
        bar.addWidget(self._lang)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("clipListScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_body = QWidget()
        self._list_layout = QVBoxLayout(self._list_body)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(SPACE_PANEL)
        self._scroll.setWidget(self._list_body)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(LIST_INSET, LIST_INSET, LIST_INSET, LIST_INSET)
        layout.setSpacing(SPACE_PANEL)
        layout.addWidget(toolbar)
        layout.addWidget(self._scroll, stretch=1)
        self.retranslate()
        self.reload()

    def retranslate(self) -> None:
        self._capture_btn.setText(t("Camera"))
        set_button_icon(self._capture_btn, "camera", BLUE)
        self._upload_btn.setText(t("Import"))
        set_button_icon(self._upload_btn, "import", BLUE)
        self._lang_label.setText(t("Language"))
        self._lang.blockSignals(True)
        idx = max(0, self._lang.findData(language()))
        self._lang.setCurrentIndex(idx)
        self._lang.blockSignals(False)
        self.reload()

    def reload(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for meta in list_clips():
            row = self._row(meta)
            row.clicked.connect(lambda _=False, cid=meta.clip_id: self._on_row_click(cid))
            self._list_layout.addWidget(row)
        self._list_layout.addStretch()

    def _on_lang(self, _index: int) -> None:
        code = str(self._lang.currentData() or "en")
        self.language_changed.emit(code)

    def _row(self, meta: ClipMeta) -> QWidget:
        row = ClipRow()
        thumb = ThumbLabel()
        thumb.setObjectName("thumb")
        thumb.setFixedSize(128, 72)
        thumb.setScaledContents(True)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path = thumb_path(meta.clip_id)
        if path.is_file():
            thumb.setPixmap(QPixmap(str(path)))
        else:
            thumb.setText(t("No preview"))
        name = QLabel(meta.display_name)
        duration = QLabel(
            format_duration_ms(meta.duration_ms, image=meta.kind == ClipKind.IMAGE)
        )
        status = t(_status_key(meta.status))
        if meta.error:
            status = t("{status} (failed, retry)", status=status)
        st = QLabel(status)
        st.setObjectName("statusChip")
        kind = {
            ClipStatus.PENDING: "pending",
            ClipStatus.PROCESSING: "processing",
            ClipStatus.DONE: "done",
        }[meta.status]
        st.setProperty("kind", kind)
        st.style().unpolish(st)
        st.style().polish(st)
        spinner = LoadingSpinner(22)
        spinner.setVisible(meta.status == ClipStatus.PROCESSING)
        delete_btn = QPushButton(t("Delete"))
        set_button_icon(delete_btn, "delete", WATERMELON)
        refresh_btn = QPushButton(t("Reanalyze"))
        set_button_icon(refresh_btn, "reanalyze", PURPLE)
        refresh_btn.setVisible(meta.status != ClipStatus.PROCESSING)
        report_btn = QPushButton(t("Report"))
        set_button_icon(report_btn, "report", BLUE)
        report = (
            load_stage_report(meta.clip_id)
            if meta.status == ClipStatus.DONE
            else None
        )
        has_report = report is not None
        report_btn.setVisible(report_button_enabled(meta.status, has_report))
        delete_btn.clicked.connect(
            lambda _checked=False, cid=meta.clip_id: self._confirm_delete(cid)
        )
        refresh_btn.clicked.connect(
            lambda _checked=False, cid=meta.clip_id: self._emit_reanalyze(cid)
        )
        report_btn.clicked.connect(
            lambda _checked=False, cid=meta.clip_id: self._open_report(cid)
        )
        col = QVBoxLayout()
        col.setContentsMargins(0, 4, 0, 4)
        col.setSpacing(SPACE_TEXT)
        col.addWidget(name)
        col.addWidget(duration)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.addWidget(spinner)
        status_row.addWidget(st)
        status_row.addStretch()
        col.addLayout(status_row)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, CARD_PAD, 0)
        header.setSpacing(10)
        header.addWidget(thumb)
        header.addLayout(col)
        header.addStretch()
        header.addWidget(report_btn)
        header.addWidget(refresh_btn)
        header.addWidget(delete_btn)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        return row

    def _on_row_click(self, clip_id: str) -> None:
        if self._ignore_item_click:
            self._ignore_item_click = False
            return
        clips = {m.clip_id: m for m in list_clips()}
        meta = clips.get(clip_id)
        if meta is None:
            return
        if meta.status == ClipStatus.PENDING:
            self.seed_requested.emit(clip_id)
            return
        if meta.status == ClipStatus.PROCESSING:
            QMessageBox.information(
                self, t("Processing"), t("This clip is still processing. Play it when it is done.")
            )
            return
        self.play_requested.emit(clip_id)

    def _confirm_delete(self, clip_id: str) -> None:
        self._ignore_item_click = True
        answer = QMessageBox.question(
            self,
            t("Delete"),
            t("Delete this clip and its local files? This cannot be undone."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(clip_id)

    def _emit_reanalyze(self, clip_id: str) -> None:
        self._ignore_item_click = True
        self.reanalyze_requested.emit(clip_id)

    def _open_report(self, clip_id: str) -> None:
        self._ignore_item_click = True
        self.play_requested.emit(clip_id)
