"""GUI smoke tests for the main window."""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QMessageBox, QStyleOptionViewItem

pytest.importorskip("matplotlib", reason="Main window embeds matplotlib canvases")

from magboltz_gui.window.delegates import AmountDelegate
from magboltz_gui.window.main_window import MagboltzGUI
import magboltz_gui.window.campaign_widget as campaign_widget
from magboltz_gui.campaign import SweepMode
from magboltz_gui.data.input_cards import InputGas


pytestmark = pytest.mark.gui


def test_main_window_initializes_default_input_card(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    assert window.centralWidget() is not None
    assert window.centralWidget().isVisible()
    assert window.mainTab.currentWidget() == window.tabConfiguration
    assert window.gasListTable.rowCount() == 0
    assert window.spinRealInteractions.value() == window._currentCards.number_of_real_collisions
    assert window.spinElectricField.value() == pytest.approx(window._currentCards.electric_field)
    assert not window.btnResultExport.isEnabled()
    assert not window.btnResultPlots.isEnabled()
    assert window.mainTab.indexOf(window.campaignTab) >= 0
    assert window.actionCampaignOpen.text() == "Open Campaign..."
    assert window.actionCampaignSave.text() == "Save Campaign..."
    assert window.campaignTab.executableLabel.text() == "Magboltz executable: magboltz"
    run_menu_actions = [action.text() for action in window.menuRun.actions()]
    assert "Open Result" in run_menu_actions
    assert "Open Campaign..." in run_menu_actions
    assert "Save Campaign..." in run_menu_actions


def test_main_window_gas_buttons_update_model_and_table(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    qtbot.mouseClick(window.btnGasAdd, Qt.MouseButton.LeftButton)

    assert len(window._currentCards.gases) == 1
    assert window.gasListTable.rowCount() == 1
    assert window._currentCards.gases[0].gas_id == 80

    window.gasListTable.setCurrentCell(0, 0)
    qtbot.mouseClick(window.btnGasRemove, Qt.MouseButton.LeftButton)

    assert window._currentCards.gases == []
    assert window.gasListTable.rowCount() == 0


def test_main_window_parameter_widgets_update_input_model(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    window.spinRealInteractions.setValue(12)
    window.spinGasTemperature.setValue(21.5)
    window.spinGasPressure.setValue(750.0)
    window.spinElectricField.setValue(1235.0)
    window.checkPenning.setChecked(True)
    window.checkThermal.setChecked(False)

    assert window._currentCards.number_of_real_collisions == 12
    assert window._currentCards.gas_temperature == pytest.approx(21.5)
    assert window._currentCards.gas_pressure == pytest.approx(750.0)
    assert window._currentCards.electric_field == pytest.approx(1235.0)
    assert window._currentCards.enable_penning is True
    assert window._currentCards.enable_thermal is False


def test_main_window_command_line_tracks_input_path(qtbot, tmp_path: Path) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    input_path = tmp_path / "input.in"
    window._currentInputFile = input_path
    window.updateCmdLine()

    assert window.commandLine.text() == f"magboltz < {input_path}"


def test_main_window_final_energy_auto_checkbox_updates_spinbox(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    window.checkFinalEnergyAuto.setChecked(False)
    assert window.spinFinalEnergy.value() == pytest.approx(50.0)
    assert window._currentCards.final_energy == pytest.approx(50.0)

    window.checkFinalEnergyAuto.setChecked(True)
    assert window.spinFinalEnergy.value() == pytest.approx(0.0)
    assert window._currentCards.final_energy == pytest.approx(0.0)


def test_main_window_copies_command_line_to_clipboard(qtbot, tmp_path: Path) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    input_path = tmp_path / "input.in"
    window._currentInputFile = input_path
    window.updateCmdLine()

    qtbot.mouseClick(window.btnCmdCopyToClipbord, Qt.MouseButton.LeftButton)

    clipboard = QApplication.clipboard()
    assert clipboard is not None
    assert clipboard.text() == f"magboltz < {input_path}"


def test_main_window_open_result_file_populates_parsed_result(qtbot, monkeypatch, reference_output_text: str, tmp_path: Path) -> None:
    output_path = tmp_path / "magboltz-output.txt"
    output_path.write_text(reference_output_text, encoding="utf-8")
    messages: list[tuple[str, str]] = []

    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(output_path), ""))
    monkeypatch.setattr(window, "show_info", lambda title, message, *args, **kwargs: messages.append((title, message)))

    window.openResultFile()

    assert window._last_run_result is not None
    assert window._last_run_result.transport.vz_um_ns is not None
    assert window._last_run_result.transport.vz_um_ns.v_um_ns == pytest.approx(29.43)
    assert window.btnResultExport.isEnabled()
    assert window.btnResultPlots.isEnabled()
    assert messages and messages[0][0] == "Result loaded"


def test_main_window_run_without_saved_input_reports_error(qtbot, monkeypatch) -> None:
    errors: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(window, "show_error", lambda title, message, *args, **kwargs: errors.append((title, message)))

    window.run()

    assert errors == [("Error", "To run the magboltz process, you must to save the file")]


def test_main_window_amount_delegate_updates_gas_ratio_model(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    window.gasAdd()

    index = window.gasListTable.model().index(0, 2)
    delegate = window.gasListTable.itemDelegateForColumn(2)
    assert isinstance(delegate, AmountDelegate)
    editor = delegate.createEditor(window.gasListTable, QStyleOptionViewItem(), index)
    qtbot.addWidget(editor)
    assert isinstance(editor, QDoubleSpinBox)

    editor.setValue(42.5)
    delegate.setModelData(editor, window.gasListTable.model(), index)

    assert window._currentCards.gases[0].gas_frac == pytest.approx(42.5)
    assert window.gasListTable.item(0, 2).text() == "42.500"


def test_campaign_tab_previews_product_sweep(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()

    campaign = window.campaignTab
    campaign.preview_runs()

    assert campaign.previewSummary.text() == "Runs: 5"
    assert campaign.previewTable.rowCount() == 5
    assert campaign.previewTable.item(0, 0).text() == "run_0001"
    assert campaign.previewTable.item(0, 1).text() == "100.0"


def test_campaign_tab_generates_input_cards(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(window.campaignTab, "_show_info", lambda title, message: messages.append((title, message)))

    window.campaignTab.generate_input_cards()

    assert (tmp_path / "run_0001" / "input.in").is_file()
    assert (tmp_path / "base_input.in").is_file()
    assert (tmp_path / "run_0001" / "parameters.json").is_file()
    assert (tmp_path / "summary.csv").is_file()
    assert messages and messages[0][0] == "Campaign generated"
    assert window.campaignTab.resultsSummary.text() == "Results: input cards generated, not run"


def test_campaign_tab_opens_saved_campaign_and_restores_base_input(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    window._currentCards.electric_field = 1234.0
    window._currentCards.gases = [InputGas(gas_id=2, gas_frac=70.0), InputGas(gas_id=12, gas_frac=30.0)]
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="linear",
        values="100",
        stop="200",
        points="2",
    )
    campaign.add_sweep_row(
        parameter_path="gases[0].gas_frac",
        sweep_type="values",
        values="70, 80",
        label="Ar",
    )
    campaign.add_sweep_row(
        parameter_path="gases[1].gas_frac",
        sweep_type="values",
        values="30, 20",
        label="CO2",
    )
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(campaign, "_show_info", lambda title, message: messages.append((title, message)))
    campaign.generate_input_cards()

    window._currentCards.electric_field = 42.0
    campaign.sweepTable.setRowCount(0)
    messages.clear()

    campaign.open_campaign()

    assert window._currentCards.electric_field == pytest.approx(1234.0)
    assert campaign.sweepTable.rowCount() == 3
    assert campaign.sweepTable.item(0, 5).text() == "100.0"
    assert campaign.sweepTable.item(0, 6).text() == "200.0"
    assert campaign.sweepTable.item(0, 7).text() == "2"
    assert campaign.sweepTable.item(1, 4).text() == "70, 80"
    assert campaign.previewSummary.text() == "Runs: 4"
    assert campaign.resultsSummary.text() == "Results: 4 runs; done: 0; failed: 0; pending: 4"
    assert messages and messages[0][0] == "Campaign opened"


def test_campaign_tab_previews_mixed_product_and_coupled_sweep(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    window._currentCards.gases = [InputGas(gas_id=2, gas_frac=70.0), InputGas(gas_id=12, gas_frac=30.0)]
    campaign = window.campaignTab
    campaign.use_current_input()
    campaign.sweepTable.setRowCount(0)
    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100, 200",
    )
    campaign.add_sweep_row(
        parameter_path="gases[0].gas_frac",
        sweep_type="values",
        values="70, 80",
        label="Ar",
        mode=SweepMode.COUPLED,
    )
    campaign.add_sweep_row(
        parameter_path="gases[1].gas_frac",
        sweep_type="values",
        values="30, 20",
        label="CO2",
        mode=SweepMode.COUPLED,
    )

    campaign.preview_runs()

    assert campaign.previewSummary.text() == "Runs: 4"
    assert campaign.matrixSummary.text() == (
        "Independent rows: 1; product size: 2; coupled rows: 2; coupled size: 2; total: 4"
    )
    assert campaign.previewTable.columnCount() == 4
    assert campaign.previewTable.item(0, 1).text() == "100"
    assert campaign.previewTable.item(0, 2).text() == "70"
    assert campaign.previewTable.item(0, 3).text() == "30"
    assert campaign.previewTable.item(3, 1).text() == "200"
    assert campaign.previewTable.item(3, 2).text() == "80"
    assert campaign.previewTable.item(3, 3).text() == "20"


def test_campaign_tab_forces_gas_fraction_sweeps_to_coupled(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)

    campaign.add_sweep_row(
        parameter_path="gases[0].gas_frac",
        sweep_type="values",
        values="70, 80",
        mode=SweepMode.PRODUCT,
    )
    mode_combo = campaign.sweepTable.cellWidget(0, 2)
    assert isinstance(mode_combo, QComboBox)
    assert mode_combo.currentData() == SweepMode.COUPLED.value
    assert not mode_combo.isEnabled()

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100, 200",
    )
    parameter_combo = campaign.sweepTable.cellWidget(1, 1)
    mode_combo = campaign.sweepTable.cellWidget(1, 2)
    assert isinstance(parameter_combo, QComboBox)
    assert isinstance(mode_combo, QComboBox)
    assert mode_combo.isEnabled()

    parameter_combo.setCurrentIndex(parameter_combo.findData("gases[1].gas_frac"))

    assert mode_combo.currentData() == SweepMode.COUPLED.value
    assert not mode_combo.isEnabled()


def test_campaign_tab_updates_editable_sweep_cells_by_type(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100, 200, 300",
    )
    values_item = campaign.sweepTable.item(0, 4)
    start_item = campaign.sweepTable.item(0, 5)
    stop_item = campaign.sweepTable.item(0, 6)
    points_item = campaign.sweepTable.item(0, 7)
    sweep_combo = campaign.sweepTable.cellWidget(0, 3)
    assert isinstance(sweep_combo, QComboBox)

    assert values_item.flags() & Qt.ItemFlag.ItemIsEditable
    assert not start_item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert not stop_item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert points_item.text() == "3"
    assert points_item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert not points_item.flags() & Qt.ItemFlag.ItemIsEditable

    values_item.setText("100, 200, 300, 400")

    assert points_item.text() == "4"

    sweep_combo.setCurrentText("linear")

    assert not values_item.flags() & Qt.ItemFlag.ItemIsEnabled
    assert start_item.flags() & Qt.ItemFlag.ItemIsEditable
    assert stop_item.flags() & Qt.ItemFlag.ItemIsEditable
    assert points_item.flags() & Qt.ItemFlag.ItemIsEditable


def test_campaign_tab_reports_contextual_validation_errors(qtbot, monkeypatch) -> None:
    errors: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(campaign, "_show_error", lambda title, message: errors.append((title, message)))

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="linear",
        values="",
        stop="100",
        points="1",
    )
    campaign.add_sweep_row(
        parameter_path="gases[0].gas_frac",
        sweep_type="values",
        values="70, 80",
    )

    campaign.preview_runs()

    assert errors
    assert errors[0][0] == "Invalid campaign"
    assert "Fix campaign sweep rows:" in errors[0][1]
    assert "Row 1 (Electric field): Start is required" in errors[0][1]
    assert "Row 2 (Gas 1 fraction): Coupled mode requires at least two enabled coupled rows" in errors[0][1]


def test_campaign_tab_reports_coupled_point_mismatch_before_core(qtbot, monkeypatch) -> None:
    errors: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(campaign, "_show_error", lambda title, message: errors.append((title, message)))

    campaign.add_sweep_row(
        parameter_path="gases[0].gas_frac",
        sweep_type="values",
        values="70, 80",
    )
    campaign.add_sweep_row(
        parameter_path="gases[1].gas_frac",
        sweep_type="values",
        values="30",
    )

    campaign.preview_runs()

    assert errors
    assert "Coupled rows must have the same number of points" in errors[0][1]
    assert "row 1 Gas 1 fraction=2" in errors[0][1]
    assert "row 2 Gas 2 fraction=1" in errors[0][1]


def test_campaign_tab_limits_large_preview_and_warns(qtbot) -> None:
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="linear",
        values="1",
        stop="1000",
        points="1000",
    )

    campaign.preview_runs()

    assert campaign.previewSummary.text() == "Runs: 1000 (showing first 100) - large campaign"
    assert campaign.matrixSummary.text() == (
        "Independent rows: 1; product size: 1000; coupled rows: 0; coupled size: 1; "
        "total: 1000; warning: review before generating"
    )
    assert campaign.previewTable.rowCount() == 100


def test_campaign_tab_requires_confirmation_before_generating_large_campaign(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.No)
    monkeypatch.setattr(campaign, "_show_info", lambda title, message: messages.append((title, message)))

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="linear",
        values="1",
        stop="1000",
        points="1000",
    )

    campaign.generate_input_cards()

    assert not messages
    assert not (tmp_path / "summary.csv").exists()


def test_campaign_tab_generates_large_campaign_after_confirmation(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(campaign, "_show_info", lambda title, message: messages.append((title, message)))

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="linear",
        values="1",
        stop="1000",
        points="1000",
    )

    campaign.generate_input_cards()

    assert (tmp_path / "summary.csv").is_file()
    assert (tmp_path / "campaign.json").is_file()
    assert messages and "Generated 1000 input cards" in messages[0][1]


def test_campaign_tab_runs_campaign_and_reports_status(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []

    class FakeResult:
        def __init__(self, ok: bool) -> None:
            self.ok = ok

    class FakeRunner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self, plan, output_dir: Path):
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "summary.csv").write_text("run_id,electric_field\nrun_0001,100\n", encoding="utf-8")
            (output_dir / "run_0001").mkdir()
            (output_dir / "run_0001" / "stdout.txt").write_text("ok\n", encoding="utf-8")
            (output_dir / "run_0001" / "stderr.txt").write_text("", encoding="utf-8")
            return [FakeResult(True), FakeResult(False)]

    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(campaign, "_show_info", lambda title, message: messages.append((title, message)))
    monkeypatch.setattr(campaign_widget, "SerialCampaignRunner", FakeRunner)

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100",
    )

    campaign.run_campaign()

    assert (tmp_path / "run_0001" / "stdout.txt").is_file()
    assert messages
    assert messages[0][0] == "Campaign run finished"
    assert "Executed 2 runs" in messages[0][1]
    assert "OK: 1" in messages[0][1]
    assert "Failed: 1" in messages[0][1]
    assert campaign.resultsSummary.text() == "Results: 1 runs; done: 1; failed: 0; pending: 0"
    assert campaign.resultsTable.item(0, 0).text() == "run_0001"
    assert campaign.resultsTable.item(0, 1).text() == "done"
    assert campaign.resultsTable.item(0, 3).text() == "100"


def test_campaign_tab_opens_saved_campaign_results(qtbot, monkeypatch, tmp_path: Path) -> None:
    messages: list[tuple[str, str]] = []
    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(campaign, "_show_info", lambda title, message: messages.append((title, message)))

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100",
    )
    campaign.generate_input_cards()
    (tmp_path / "run_status.csv").write_text(
        "run_id,status,returncode,input,stdout,stderr\n"
        f"run_0001,failed,1,{tmp_path / 'run_0001' / 'input.in'},{tmp_path / 'run_0001' / 'stdout.txt'},{tmp_path / 'run_0001' / 'stderr.txt'}\n",
        encoding="utf-8",
    )
    (tmp_path / "run_0001" / "stdout.txt").write_text("", encoding="utf-8")
    (tmp_path / "run_0001" / "stderr.txt").write_text("failed\n", encoding="utf-8")

    messages.clear()
    campaign.open_campaign()

    assert campaign.resultsSummary.text() == "Results: 1 runs; done: 0; failed: 1; pending: 0"
    assert campaign.resultsTable.item(0, 0).text() == "run_0001"
    assert campaign.resultsTable.item(0, 1).text() == "failed"
    assert campaign.resultsTable.item(0, 2).text() == "1"


def test_campaign_tab_reports_missing_magboltz_executable(qtbot, monkeypatch, tmp_path: Path) -> None:
    errors: list[tuple[str, str]] = []

    class MissingMagboltzRunner:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self, plan, output_dir: Path):
            output_dir.mkdir(parents=True, exist_ok=True)
            raise FileNotFoundError(2, "No such file or directory", "magboltz")

    window = MagboltzGUI()
    qtbot.addWidget(window)
    window.show()
    campaign = window.campaignTab
    campaign.sweepTable.setRowCount(0)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    monkeypatch.setattr(campaign, "_show_error", lambda title, message: errors.append((title, message)))
    monkeypatch.setattr(campaign_widget, "SerialCampaignRunner", MissingMagboltzRunner)

    campaign.add_sweep_row(
        parameter_path="electric_field",
        sweep_type="values",
        values="100",
    )

    campaign.run_campaign()

    assert errors
    assert errors[0][0] == "Campaign run failed"
    assert "Could not start `magboltz`" in errors[0][1]
    assert "available in PATH" in errors[0][1]
