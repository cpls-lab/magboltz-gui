import unittest
from pathlib import Path

from magboltz_gui.util.output_parser import parse_magboltz_output


class TestOutputParser(unittest.TestCase):
    def setUp(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "magboltz_output.txt"
        self.text = fixture.read_text(encoding="utf-8")

    def test_parse_basic_fields(self) -> None:
        run = parse_magboltz_output(self.text)
        self.assertEqual(run.meta.tool_name, "magboltz")
        self.assertIn("MAGBOLTZ 2 VERSION 11.19", run.meta.tool_version or "")
        self.assertEqual(len(run.mixture), 2)
        self.assertEqual(run.mixture[0].name, "ARGON")
        self.assertAlmostEqual(run.mixture[0].fraction_percent or 0.0, 70.0, places=3)
        self.assertAlmostEqual(run.conditions.gas_temperature_C or 0.0, 20.0, places=2)
        self.assertAlmostEqual(run.conditions.gas_pressure_torr or 0.0, 760.0, places=2)
        self.assertEqual(run.conditions.integration.n_steps, 4000)
        self.assertAlmostEqual(run.conditions.integration.E_max_eV or 0.0, 4.0, places=2)
        self.assertEqual(run.counts.total_real_collisions, 200000000)
        self.assertEqual(run.counts.num_null_collisions, 540776987)
        self.assertTrue(run.tables.convergence_table)
        self.assertTrue(run.tables.energy_distribution)

    def test_parse_transport(self) -> None:
        run = parse_magboltz_output(self.text)
        self.assertAlmostEqual(run.transport.vz_um_ns.v_um_ns or 0.0, 29.43, places=2)
        self.assertAlmostEqual(run.transport.mean_electron_energy_eV or 0.0, 0.1455, places=4)

