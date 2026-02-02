import unittest
from pathlib import Path
import tempfile

from magboltz_gui.util.output_parser import parse_magboltz_output
from magboltz_gui.util.export_controller import export_to_file
from magboltz_gui.util.export_types import ExportType, ExportFormat, CsvOptions, JsonOptions, XmlOptions


class TestExport(unittest.TestCase):
    def setUp(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "magboltz_output.txt"
        self.run = parse_magboltz_output(fixture.read_text(encoding="utf-8"))

    def test_summary_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.csv"
            export_to_file(self.run, ExportType.SUMMARY, ExportFormat.CSV, path, csv_options=CsvOptions())
            text = path.read_text(encoding="utf-8")
            self.assertIn("gas_temperature_C", text)
            self.assertIn("mean_electron_energy_eV", text)

    def test_energy_distribution_csv_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "energy.csv"
            export_to_file(self.run, ExportType.ENERGY_DISTRIBUTION, ExportFormat.CSV, path, csv_options=CsvOptions())
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            # header + data rows
            self.assertGreater(len(lines), 2)

    def test_full_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "full.json"
            export_to_file(self.run, ExportType.FULL_RUN_ARCHIVE, ExportFormat.JSON, path, json_options=JsonOptions())
            text = path.read_text(encoding="utf-8")
            self.assertIn("\"schema_version\"", text)
            self.assertIn("\"export_type\"", text)
            self.assertIn("\"conditions\"", text)

    def test_xml_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.xml"
            export_to_file(self.run, ExportType.SUMMARY, ExportFormat.XML, path, xml_options=XmlOptions())
            text = path.read_text(encoding="utf-8")
            self.assertIn("<magboltz_export", text)

