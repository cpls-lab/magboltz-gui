"""GUI tests for generic campaign plotting."""

from __future__ import annotations

import pytest

pytest.importorskip("matplotlib", reason="Campaign plot window embeds matplotlib canvases")

from magboltz_gui.window.campaign_plot_window import CampaignPlotDataset, CampaignPlotWindow


pytestmark = pytest.mark.gui


def test_campaign_plot_window_uses_numeric_columns_and_selected_scope(qtbot) -> None:
    dataset = CampaignPlotDataset(
        all_rows=[
            {"run_id": "run_0001", "electric_field": "100", "vz_um_ns": "29.43", "status": "done"},
            {"run_id": "run_0002", "electric_field": "200", "vz_um_ns": "40.5", "status": "done"},
        ],
        selected_rows=[
            {"run_id": "run_0002", "electric_field": "200", "vz_um_ns": "40.5", "status": "done"},
        ],
    )

    dialog = CampaignPlotWindow(dataset)
    qtbot.addWidget(dialog)
    dialog.show()

    assert [dialog.comboX.itemText(index) for index in range(dialog.comboX.count())] == [
        "electric_field",
        "vz_um_ns",
    ]
    assert dialog.radioSelectedRuns.isChecked()
    assert dialog.statusLabel.text() == "Plotting 1 run(s)."

    dialog.radioAllRuns.setChecked(True)

    assert dialog.statusLabel.text() == "Plotting 2 run(s)."


def test_campaign_plot_window_disables_selected_scope_without_selected_rows(qtbot) -> None:
    dataset = CampaignPlotDataset(
        all_rows=[{"run_id": "run_0001", "electric_field": "100", "vz_um_ns": "29.43"}],
        selected_rows=[],
    )

    dialog = CampaignPlotWindow(dataset)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.radioAllRuns.isChecked()
    assert not dialog.radioSelectedRuns.isEnabled()


def test_campaign_plot_window_reports_skipped_incomplete_rows(qtbot) -> None:
    dataset = CampaignPlotDataset(
        all_rows=[
            {"run_id": "run_0001", "electric_field": "100", "vz_um_ns": "29.43"},
            {"run_id": "run_0002", "electric_field": "200", "vz_um_ns": ""},
        ],
        selected_rows=[],
    )

    dialog = CampaignPlotWindow(dataset)
    qtbot.addWidget(dialog)
    dialog.show()

    assert dialog.statusLabel.text() == "Plotting 1 run(s); skipped 1 incomplete/non-numeric row(s)."
