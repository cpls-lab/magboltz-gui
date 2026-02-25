from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QCheckBox,
    QDialogButtonBox,
    QWidget,
)

from importlib.resources import files
from PyQt6.QtGui import QIcon
from magboltz_gui.util.export_types import ExportType, ExportFormat, CsvOptions, JsonOptions, XmlOptions
from magboltz_gui.util.export_controller import default_filename, available_export_types
from magboltz_gui.util.run_result import RunResult


class ExportDialog(QDialog):
    def __init__(self, run: RunResult, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Results")
        icon_path = files("magboltz_gui.icons").joinpath("icon.svg")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._run = run
        self._settings = QSettings()
        self._init_ui()
        self._load_settings()
        self._update_state()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.cmbExportType = QComboBox()
        for t in available_export_types(self._run):
            self.cmbExportType.addItem(self._label_for_export_type(t), t.value)
        self.cmbFormat = QComboBox()
        self.cmbFormat.addItem("CSV", ExportFormat.CSV.value)
        self.cmbFormat.addItem("JSON", ExportFormat.JSON.value)
        self.cmbFormat.addItem("XML", ExportFormat.XML.value)

        form.addRow("Export type", self.cmbExportType)
        form.addRow("Format", self.cmbFormat)

        path_layout = QHBoxLayout()
        self.txtPath = QLineEdit()
        self.btnBrowse = QPushButton("Browse")
        path_layout.addWidget(self.txtPath)
        path_layout.addWidget(self.btnBrowse)
        form.addRow("Destination", path_layout)
        layout.addLayout(form)

        self.grpOptions = QGroupBox("Options")
        self.optionsLayout = QVBoxLayout(self.grpOptions)

        # CSV options
        self.csvWidget = QWidget()
        csvForm = QFormLayout(self.csvWidget)
        self.cmbDelimiter = QComboBox()
        self.cmbDelimiter.addItem("Comma (,)", ",")
        self.cmbDelimiter.addItem("Semicolon (;)", ";")
        self.cmbDelimiter.addItem("Tab (\\t)", "\t")
        self.chkCsvUnits = QCheckBox("Include units in header")
        self.chkCsvMeta = QCheckBox("Include metadata columns")
        self.chkCsvFlatten = QCheckBox("Flatten mixture into gas columns")
        self.chkCsvUnits.setChecked(True)
        self.chkCsvMeta.setChecked(True)
        self.chkCsvFlatten.setChecked(True)
        csvForm.addRow("Delimiter", self.cmbDelimiter)
        csvForm.addRow(self.chkCsvUnits)
        csvForm.addRow(self.chkCsvMeta)
        csvForm.addRow(self.chkCsvFlatten)

        # JSON/XML options
        self.jsonXmlWidget = QWidget()
        jsonForm = QFormLayout(self.jsonXmlWidget)
        self.chkIncludeInput = QCheckBox("Include input_text")
        self.chkIncludeRaw = QCheckBox("Include raw stdout_text")
        self.chkIncludeWarnings = QCheckBox("Include parser warnings")
        self.chkPretty = QCheckBox("Pretty print (JSON)")
        self.chkIncludeInput.setChecked(True)
        self.chkIncludeWarnings.setChecked(True)
        self.chkPretty.setChecked(True)
        jsonForm.addRow(self.chkIncludeInput)
        jsonForm.addRow(self.chkIncludeRaw)
        jsonForm.addRow(self.chkIncludeWarnings)
        jsonForm.addRow(self.chkPretty)

        self.optionsLayout.addWidget(self.csvWidget)
        self.optionsLayout.addWidget(self.jsonXmlWidget)
        layout.addWidget(self.grpOptions)

        self.lblError = QLabel("")
        self.lblError.setStyleSheet("color: red;")
        layout.addWidget(self.lblError)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttons)

        self.btnBrowse.clicked.connect(self._browse)
        self.cmbFormat.currentIndexChanged.connect(self._update_state)
        self.cmbExportType.currentIndexChanged.connect(self._update_state)
        self.txtPath.textChanged.connect(self._update_state)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def _label_for_export_type(self, t: ExportType) -> str:
        return {
            ExportType.SUMMARY: "Summary",
            ExportType.CONVERGENCE_TABLE: "Convergence table (VEL/POS/TIME/ENERGY/COUNT/DIFXX/DIFYY/DIFZZ)",
            ExportType.ENERGY_DISTRIBUTION: "Energy distribution (E,SPEC)",
            ExportType.COLLISION_FREQUENCIES: "Collision frequencies (by gas/process)",
            ExportType.FULL_RUN_ARCHIVE: "Full run (archive)",
        }[t]

    def _current_export_type(self) -> ExportType:
        return ExportType(self.cmbExportType.currentData())

    def _current_format(self) -> ExportFormat:
        return ExportFormat(self.cmbFormat.currentData())

    def _update_state(self) -> None:
        export_type = self._current_export_type()
        fmt = self._current_format()

        self._suggest_filename()

        # CSV / JSON / XML option panes
        self.csvWidget.setVisible(fmt == ExportFormat.CSV)
        self.jsonXmlWidget.setVisible(fmt in (ExportFormat.JSON, ExportFormat.XML))
        self.chkPretty.setVisible(fmt == ExportFormat.JSON)

        # CSV cannot do full run
        error = ""
        if fmt == ExportFormat.CSV and export_type == ExportType.FULL_RUN_ARCHIVE:
            error = "Full run archive is not supported for CSV."
        if not self.txtPath.text().strip():
            error = "Select a destination path."
        self.lblError.setText(error)
        ok_btn = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setEnabled(error == "")

        # raw stdout only meaningful for full run
        self.chkIncludeRaw.setEnabled(export_type == ExportType.FULL_RUN_ARCHIVE)
        if export_type != ExportType.FULL_RUN_ARCHIVE:
            self.chkIncludeRaw.setChecked(False)

    def _suggest_filename(self) -> None:
        fmt = self._current_format()
        export_type = self._current_export_type()
        ext = fmt.value
        if fmt == ExportFormat.CSV and export_type == ExportType.FULL_RUN_ARCHIVE:
            return
        name = default_filename(self._run, export_type, ext)
        if not self.txtPath.text().strip():
            self.txtPath.setText(name)

    def _browse(self) -> None:
        fmt = self._current_format()
        export_type = self._current_export_type()
        ext = fmt.value
        suggested = default_filename(self._run, export_type, ext)
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", suggested, f"*.{ext}")
        if path:
            self.txtPath.setText(path)

    def _load_settings(self) -> None:
        self.cmbExportType.setCurrentIndex(self._settings.value("export/last_type", 0, int))
        self.cmbFormat.setCurrentIndex(self._settings.value("export/last_format", 0, int))
        self.cmbDelimiter.setCurrentIndex(self._settings.value("export/last_delim", 0, int))
        self.chkCsvUnits.setChecked(self._settings.value("export/csv_units", True, bool))
        self.chkCsvMeta.setChecked(self._settings.value("export/csv_meta", True, bool))
        self.chkCsvFlatten.setChecked(self._settings.value("export/csv_flatten", True, bool))
        self.chkIncludeInput.setChecked(self._settings.value("export/include_input", True, bool))
        self.chkIncludeWarnings.setChecked(self._settings.value("export/include_warnings", True, bool))
        self.chkPretty.setChecked(self._settings.value("export/pretty", True, bool))

    def _save_settings(self) -> None:
        self._settings.setValue("export/last_type", self.cmbExportType.currentIndex())
        self._settings.setValue("export/last_format", self.cmbFormat.currentIndex())
        self._settings.setValue("export/last_delim", self.cmbDelimiter.currentIndex())
        self._settings.setValue("export/csv_units", self.chkCsvUnits.isChecked())
        self._settings.setValue("export/csv_meta", self.chkCsvMeta.isChecked())
        self._settings.setValue("export/csv_flatten", self.chkCsvFlatten.isChecked())
        self._settings.setValue("export/include_input", self.chkIncludeInput.isChecked())
        self._settings.setValue("export/include_warnings", self.chkIncludeWarnings.isChecked())
        self._settings.setValue("export/pretty", self.chkPretty.isChecked())

    def accept(self) -> None:
        self._save_settings()
        super().accept()

    def export_settings(self) -> tuple[ExportType, ExportFormat, Path, CsvOptions, JsonOptions, XmlOptions]:
        export_type = self._current_export_type()
        fmt = self._current_format()
        path = Path(self.txtPath.text())
        csv_opts = CsvOptions(
            delimiter=self.cmbDelimiter.currentData(),
            include_units=self.chkCsvUnits.isChecked(),
            include_metadata=self.chkCsvMeta.isChecked(),
            flatten_mixture=self.chkCsvFlatten.isChecked(),
        )
        json_opts = JsonOptions(
            include_input_text=self.chkIncludeInput.isChecked(),
            include_raw_stdout=self.chkIncludeRaw.isChecked(),
            include_parser_warnings=self.chkIncludeWarnings.isChecked(),
            pretty_print=self.chkPretty.isChecked(),
        )
        xml_opts = XmlOptions(
            include_input_text=self.chkIncludeInput.isChecked(),
            include_raw_stdout=self.chkIncludeRaw.isChecked(),
            include_parser_warnings=self.chkIncludeWarnings.isChecked(),
        )
        return export_type, fmt, path, csv_opts, json_opts, xml_opts
