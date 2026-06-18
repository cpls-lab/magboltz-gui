"""Tests for structured export formats."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from magboltz_gui.util.export_controller import available_export_types
from magboltz_gui.util.export_controller import export_to_file
from magboltz_gui.util.export_types import CsvOptions, ExportFormat, ExportType, JsonOptions, XmlOptions
from magboltz_gui.util.run_result import RunResult


def test_summary_csv(reference_run: RunResult, tmp_path: Path) -> None:
    path = tmp_path / "summary.csv"
    export_to_file(reference_run, ExportType.SUMMARY, ExportFormat.CSV, path, csv_options=CsvOptions())

    text = path.read_text(encoding="utf-8")

    assert "gas_temperature_C" in text
    assert "mean_electron_energy_eV" in text


def test_energy_distribution_csv_rows(reference_run: RunResult, tmp_path: Path) -> None:
    path = tmp_path / "energy.csv"
    export_to_file(reference_run, ExportType.ENERGY_DISTRIBUTION, ExportFormat.CSV, path, csv_options=CsvOptions())

    lines = path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) > 2


def test_full_run_json(reference_run: RunResult, tmp_path: Path) -> None:
    path = tmp_path / "full.json"
    export_to_file(reference_run, ExportType.FULL_RUN_ARCHIVE, ExportFormat.JSON, path, json_options=JsonOptions())

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert payload["export_type"] == ExportType.FULL_RUN_ARCHIVE.value
    assert payload["data"]["conditions"]["gas_temperature_C"] == 20.0


def test_xml_export(reference_run: RunResult, tmp_path: Path) -> None:
    path = tmp_path / "summary.xml"
    export_to_file(reference_run, ExportType.SUMMARY, ExportFormat.XML, path, xml_options=XmlOptions())

    text = path.read_text(encoding="utf-8")

    assert "<magboltz_export" in text


def test_reference_run_exposes_all_export_types(reference_run: RunResult) -> None:
    assert available_export_types(reference_run) == [
        ExportType.SUMMARY,
        ExportType.CONVERGENCE_TABLE,
        ExportType.ENERGY_DISTRIBUTION,
        ExportType.COLLISION_FREQUENCIES,
        ExportType.FULL_RUN_ARCHIVE,
    ]


@pytest.mark.parametrize(
    ("export_type", "expected_text"),
    [
        (ExportType.SUMMARY, "mean_electron_energy_eV"),
        (ExportType.CONVERGENCE_TABLE, "difzz"),
        (ExportType.ENERGY_DISTRIBUTION, "spec"),
        (ExportType.COLLISION_FREQUENCIES, "gas_name"),
    ],
)
def test_tabular_export_types_write_csv(
    reference_run: RunResult,
    tmp_path: Path,
    export_type: ExportType,
    expected_text: str,
) -> None:
    path = tmp_path / f"{export_type.value}.csv"

    export_to_file(reference_run, export_type, ExportFormat.CSV, path, csv_options=CsvOptions())

    text = path.read_text(encoding="utf-8")
    assert expected_text in text
    assert len(text.strip().splitlines()) >= 2


@pytest.mark.parametrize(
    ("export_type", "expected_payload_type"),
    [
        (ExportType.SUMMARY, dict),
        (ExportType.CONVERGENCE_TABLE, list),
        (ExportType.ENERGY_DISTRIBUTION, list),
        (ExportType.COLLISION_FREQUENCIES, list),
        (ExportType.FULL_RUN_ARCHIVE, dict),
    ],
)
def test_all_export_types_write_json(
    reference_run: RunResult,
    tmp_path: Path,
    export_type: ExportType,
    expected_payload_type: type,
) -> None:
    path = tmp_path / f"{export_type.value}.json"

    export_to_file(reference_run, export_type, ExportFormat.JSON, path, json_options=JsonOptions())

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["export_type"] == export_type.value
    assert isinstance(payload["data"], expected_payload_type)
    assert payload["data"]


@pytest.mark.parametrize(
    "export_type",
    [
        ExportType.SUMMARY,
        ExportType.CONVERGENCE_TABLE,
        ExportType.ENERGY_DISTRIBUTION,
        ExportType.COLLISION_FREQUENCIES,
        ExportType.FULL_RUN_ARCHIVE,
    ],
)
def test_all_export_types_write_xml(reference_run: RunResult, tmp_path: Path, export_type: ExportType) -> None:
    path = tmp_path / f"{export_type.value}.xml"

    export_to_file(reference_run, export_type, ExportFormat.XML, path, xml_options=XmlOptions())

    text = path.read_text(encoding="utf-8")
    assert "<magboltz_export" in text
    assert f'export_type="{export_type.value}"' in text


def test_full_run_archive_rejects_csv(reference_run: RunResult, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Full run archive is not supported for CSV"):
        export_to_file(reference_run, ExportType.FULL_RUN_ARCHIVE, ExportFormat.CSV, tmp_path / "full.csv")
