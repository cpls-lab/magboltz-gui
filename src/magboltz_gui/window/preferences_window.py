"""Application preferences dialog."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


MAGBOLTZ_EXECUTABLE_SETTING = "paths/magboltz_executable"
USE_QT_STANDARD_ICONS_SETTING = "ui/use_qt_standard_icons"


class PreferencesDialog(QDialog):
    """Edit user-level application preferences."""

    def __init__(
        self,
        magboltz_path: Optional[Path],
        use_qt_standard_icons: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self._settings = QSettings()
        self._init_ui()
        self.set_magboltz_path(magboltz_path)
        self.set_use_qt_standard_icons(use_qt_standard_icons)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        path_layout = QHBoxLayout()
        self.txtMagboltzPath = QLineEdit()
        self.txtMagboltzPath.setPlaceholderText("Autodetect from PATH")
        self.txtMagboltzPath.textChanged.connect(self._update_detected_label)
        self.btnBrowseMagboltz = QPushButton("Browse...")
        self.btnAutodetectMagboltz = QPushButton("Use autodetect")
        self.btnBrowseMagboltz.clicked.connect(self._browse_magboltz)
        self.btnAutodetectMagboltz.clicked.connect(self.txtMagboltzPath.clear)
        path_layout.addWidget(self.txtMagboltzPath, 1)
        path_layout.addWidget(self.btnBrowseMagboltz)
        path_layout.addWidget(self.btnAutodetectMagboltz)
        form.addRow("Magboltz executable", path_layout)

        self.lblDetectedMagboltz = QLabel()
        self.lblDetectedMagboltz.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Resolved executable", self.lblDetectedMagboltz)

        self.chkUseQtStandardIcons = QCheckBox("Use Qt default toolbar icons")
        self.chkUseQtStandardIcons.setToolTip(
            "On macOS this replaces the bundled toolbar icons with the default icons supplied by Qt/Cocoa."
        )
        form.addRow("Icons", self.chkUseQtStandardIcons)

        layout.addLayout(form)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)
        self._update_detected_label()

    def set_magboltz_path(self, path: Optional[Path]) -> None:
        self.txtMagboltzPath.setText("" if path is None else str(path))

    def magboltz_path(self) -> Optional[Path]:
        text = self.txtMagboltzPath.text().strip()
        return Path(text) if text else None

    def set_use_qt_standard_icons(self, enabled: bool) -> None:
        self.chkUseQtStandardIcons.setChecked(enabled)

    def use_qt_standard_icons(self) -> bool:
        return self.chkUseQtStandardIcons.isChecked()

    def save(self) -> None:
        path = self.magboltz_path()
        self._settings.setValue(MAGBOLTZ_EXECUTABLE_SETTING, "" if path is None else str(path))
        self._settings.setValue(USE_QT_STANDARD_ICONS_SETTING, self.use_qt_standard_icons())

    def _browse_magboltz(self) -> None:
        current = self.txtMagboltzPath.text().strip()
        start_dir = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(self, "Select Magboltz executable", start_dir, "All files (*)")
        if path:
            self.txtMagboltzPath.setText(path)

    def _update_detected_label(self) -> None:
        path = self.magboltz_path()
        if path is not None:
            self.lblDetectedMagboltz.setText(str(path))
            return
        detected = shutil.which("magboltz")
        self.lblDetectedMagboltz.setText(detected or "Not found in PATH")


def load_magboltz_executable_setting() -> Optional[Path]:
    """Return the configured Magboltz executable, or None for PATH autodetect."""
    value = QSettings().value(MAGBOLTZ_EXECUTABLE_SETTING, "", type=str)
    value = value.strip() if isinstance(value, str) else ""
    return Path(value) if value else None


def load_use_qt_standard_icons_setting() -> bool:
    """Return whether toolbar icons should use Qt's platform defaults."""
    return QSettings().value(USE_QT_STANDARD_ICONS_SETTING, False, type=bool)
