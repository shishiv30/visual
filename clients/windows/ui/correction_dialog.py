"""Dialog for correcting a misclassified stage report.

The user picks the stage they believe is correct; the choice is saved as a
:class:`~clients.windows.store.library.ReportCorrection` alongside the clip
so the data can later be fed back to the classifier.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from clients.windows.store.library import (
    ReportCorrection,
    created_at_iso,
    save_report_correction,
)
from core.i18n import t
from schemas.stage_report import StageReport, TreeNodeV3


class CorrectionDialog(QDialog):
    """Let the user pick the correct stage and save the correction locally."""

    def __init__(self, report: StageReport, parent=None) -> None:
        super().__init__(parent)
        self._report = report
        self.setWindowTitle(t("Correct result"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        detected = QLabel(
            t("Detected stage: {name}", name=report.stage_name or report.stage_id)
        )
        detected.setObjectName("reportMeta")
        layout.addWidget(detected)

        prompt = QLabel(t("Select the actual stage:"))
        prompt.setObjectName("reportMeta")
        layout.addWidget(prompt)

        self._combo = QComboBox()
        nodes: list[TreeNodeV3] = [n for n in report.tree if n.tier in ("full", "scene")]
        nodes.sort(key=lambda n: n.depth)
        for node in nodes:
            self._combo.addItem(node.name or node.id, userData=node.id)
            if node.id == report.stage_id:
                self._combo.setCurrentIndex(self._combo.count() - 1)
        layout.addWidget(self._combo)

        note_label = QLabel(t("Note (optional):"))
        note_label.setObjectName("reportMeta")
        layout.addWidget(note_label)

        self._note = QLineEdit()
        self._note.setPlaceholderText(
            t("e.g. This is a mogul skiing clip, not a basic glide")
        )
        layout.addWidget(self._note)

        hint = QLabel(
            t("Your correction is saved locally and helps improve the detection algorithm.")
        )
        hint.setObjectName("reportMeta")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        corrected_id = self._combo.currentData()
        corrected_name = self._combo.currentText()
        correction = ReportCorrection(
            clip_id=self._report.clip_id,
            original_stage_id=self._report.stage_id,
            corrected_stage_id=corrected_id or self._report.stage_id,
            corrected_stage_name=corrected_name,
            note=self._note.text().strip(),
            created_at=created_at_iso(),
        )
        save_report_correction(correction)
        self.accept()
