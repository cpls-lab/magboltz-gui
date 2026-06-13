"""GUI smoke tests for the main window."""

from __future__ import annotations

from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDoubleSpinBox, QFileDialog, QStyleOptionViewItem

pytest.importorskip("matplotlib", reason="Main window embeds matplotlib canvases")

from magboltz_gui.window.delegates import AmountDelegate
from magboltz_gui.window.main_window import MagboltzGUI
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
    assert (tmp_path / "run_0001" / "parameters.json").is_file()
    assert (tmp_path / "summary.csv").is_file()
    assert messages and messages[0][0] == "Campaign generated"


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
    assert campaign.previewTable.columnCount() == 4
    assert campaign.previewTable.item(0, 1).text() == "100"
    assert campaign.previewTable.item(0, 2).text() == "70"
    assert campaign.previewTable.item(0, 3).text() == "30"
    assert campaign.previewTable.item(3, 1).text() == "200"
    assert campaign.previewTable.item(3, 2).text() == "80"
    assert campaign.previewTable.item(3, 3).text() == "20"
