"""Tests for parsing native Magboltz stdout."""

from __future__ import annotations

import pytest

from magboltz_gui.util.run_result import RunResult


def test_parse_basic_fields(reference_run: RunResult) -> None:
    assert reference_run.meta.tool_name == "magboltz"
    assert "MAGBOLTZ 2 VERSION 11.19" in (reference_run.meta.tool_version or "")
    assert len(reference_run.mixture) == 2
    assert reference_run.mixture[0].name == "ARGON"
    assert reference_run.mixture[0].fraction_percent == pytest.approx(70.0)
    assert reference_run.conditions.gas_temperature_C == pytest.approx(20.0)
    assert reference_run.conditions.gas_pressure_torr == pytest.approx(760.0)
    assert reference_run.conditions.integration.n_steps == 4000
    assert reference_run.conditions.integration.E_max_eV == pytest.approx(4.0)
    assert reference_run.counts.total_real_collisions == 200000000
    assert reference_run.counts.num_null_collisions == 540776987
    assert reference_run.tables.convergence_table
    assert reference_run.tables.energy_distribution


def test_parse_transport(reference_run: RunResult) -> None:
    assert reference_run.transport.vz_um_ns is not None
    assert reference_run.transport.vz_um_ns.v_um_ns == pytest.approx(29.43)
    assert reference_run.transport.mean_electron_energy_eV == pytest.approx(0.1455)


def test_parse_mixture_after_blank_line(reference_output_text: str) -> None:
    text = reference_output_text.replace(
        " GASES  USED                  PERCENTAGE USED\n\n",
        " GASES  USED                  PERCENTAGE USED\n\n\n",
        1,
    )

    from magboltz_gui.util.output_parser import parse_magboltz_output

    run = parse_magboltz_output(text)

    assert [gas.name for gas in run.mixture] == ["ARGON", "CO2"]
