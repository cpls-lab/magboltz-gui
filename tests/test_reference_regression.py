"""Reference regression tests for the SoftwareX validation path."""

from __future__ import annotations

import json
from pathlib import Path

from magboltz_gui.util.export_controller import export_to_file
from magboltz_gui.util.export_types import CsvOptions, ExportFormat, ExportType, JsonOptions, XmlOptions
from magboltz_gui.util.run_result import RunResult


FIXTURES = Path(__file__).parent / "fixtures"


def test_reference_transport_values_are_parsed(reference_run: RunResult) -> None:
    assert [gas.name for gas in reference_run.mixture] == ["ARGON", "CO2"]
    assert reference_run.mixture[0].fraction_percent == 70.0
    assert reference_run.mixture[1].fraction_percent == 30.0
    assert reference_run.conditions.electric_field_V_cm == 1000.0
    assert reference_run.transport.vz_um_ns is not None
    assert reference_run.transport.vz_um_ns.v_um_ns == 29.43
    assert reference_run.transport.mean_electron_energy_eV == 0.1455


def test_structured_exports_preserve_reference_values(reference_run: RunResult, tmp_path: Path) -> None:
    csv_path = tmp_path / "summary.csv"
    export_to_file(
        reference_run,
        ExportType.SUMMARY,
        ExportFormat.CSV,
        csv_path,
        csv_options=CsvOptions(include_metadata=True, include_units=False),
    )
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "vz_um_ns" in csv_text
    assert "29.43" in csv_text
    assert "0.1455" in csv_text

    json_path = tmp_path / "full.json"
    export_to_file(
        reference_run,
        ExportType.FULL_RUN_ARCHIVE,
        ExportFormat.JSON,
        json_path,
        json_options=JsonOptions(include_input_text=True, include_raw_stdout=False),
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    data = payload["data"]
    assert data["mixture"][0]["name"] == "ARGON"
    assert data["transport"]["vz_um_ns"]["v_um_ns"] == 29.43

    xml_path = tmp_path / "summary.xml"
    export_to_file(
        reference_run,
        ExportType.SUMMARY,
        ExportFormat.XML,
        xml_path,
        xml_options=XmlOptions(),
    )
    xml_text = xml_path.read_text(encoding="utf-8")
    assert "<vz_um_ns>29.43</vz_um_ns>" in xml_text
    assert "<mean_electron_energy_eV>0.1455</mean_electron_energy_eV>" in xml_text
