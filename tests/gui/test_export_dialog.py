"""GUI smoke tests for the export dialog."""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QDialogButtonBox

from magboltz_gui.util.export_controller import export_to_file
from magboltz_gui.util.export_types import ExportFormat, ExportType
from magboltz_gui.util.run_result import RunResult
from magboltz_gui.window.export_window import ExportDialog


pytestmark = pytest.mark.gui


def test_export_dialog_defaults_to_valid_summary_export(qtbot, reference_run: RunResult) -> None:
    dialog = ExportDialog(reference_run)
    qtbot.addWidget(dialog)
    dialog.show()

    ok_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)

    assert dialog.cmbExportType.currentData() == ExportType.SUMMARY.value
    assert dialog.cmbFormat.currentData() == ExportFormat.CSV.value
    assert dialog.txtPath.text().endswith(".csv")
    assert dialog.csvWidget.isVisible()
    assert not dialog.jsonXmlWidget.isVisible()
    assert dialog.lblError.text() == ""
    assert ok_button is not None
    assert ok_button.isEnabled()


def test_export_dialog_rejects_full_run_csv_but_allows_json(qtbot, reference_run: RunResult) -> None:
    dialog = ExportDialog(reference_run)
    qtbot.addWidget(dialog)
    dialog.show()

    full_run_index = dialog.cmbExportType.findData(ExportType.FULL_RUN_ARCHIVE.value)
    json_index = dialog.cmbFormat.findData(ExportFormat.JSON.value)
    assert full_run_index >= 0
    assert json_index >= 0

    dialog.cmbExportType.setCurrentIndex(full_run_index)
    dialog.cmbFormat.setCurrentIndex(dialog.cmbFormat.findData(ExportFormat.CSV.value))
    ok_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)

    assert ok_button is not None
    assert not ok_button.isEnabled()
    assert "not supported for CSV" in dialog.lblError.text()

    dialog.cmbFormat.setCurrentIndex(json_index)

    assert dialog.txtPath.text().endswith(".json")
    assert dialog.jsonXmlWidget.isVisible()
    assert not dialog.csvWidget.isVisible()
    assert dialog.lblError.text() == ""
    assert ok_button.isEnabled()


def test_export_dialog_keeps_user_selected_path_when_format_changes(qtbot, reference_run: RunResult, tmp_path) -> None:
    dialog = ExportDialog(reference_run)
    qtbot.addWidget(dialog)
    dialog.show()

    custom_path = tmp_path / "custom-output.dat"
    dialog.txtPath.setText(str(custom_path))

    json_index = dialog.cmbFormat.findData(ExportFormat.JSON.value)
    assert json_index >= 0
    dialog.cmbFormat.setCurrentIndex(json_index)

    assert dialog.txtPath.text() == str(custom_path)


@pytest.mark.parametrize(
    ("fmt", "suffix", "expected_text"),
    [
        (ExportFormat.CSV, ".csv", "vz_um_ns"),
        (ExportFormat.JSON, ".json", '"schema_version"'),
        (ExportFormat.XML, ".xml", "<magboltz_export"),
    ],
)
def test_export_dialog_settings_can_write_selected_format(
    qtbot,
    reference_run: RunResult,
    tmp_path,
    fmt: ExportFormat,
    suffix: str,
    expected_text: str,
) -> None:
    dialog = ExportDialog(reference_run)
    qtbot.addWidget(dialog)
    dialog.show()

    format_index = dialog.cmbFormat.findData(fmt.value)
    assert format_index >= 0
    output_path = tmp_path / f"summary{suffix}"

    dialog.cmbExportType.setCurrentIndex(dialog.cmbExportType.findData(ExportType.SUMMARY.value))
    dialog.cmbFormat.setCurrentIndex(format_index)
    dialog.txtPath.setText(str(output_path))

    export_type, export_format, path, csv_options, json_options, xml_options = dialog.export_settings()
    export_to_file(
        reference_run,
        export_type,
        export_format,
        path,
        csv_options=csv_options,
        json_options=json_options,
        xml_options=xml_options,
    )

    assert output_path.is_file()
    assert expected_text in output_path.read_text(encoding="utf-8")
