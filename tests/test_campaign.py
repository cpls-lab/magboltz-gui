"""Tests for campaign sweep expansion and serial execution."""

from __future__ import annotations

import json
from pathlib import Path
import os

import pytest

from magboltz_gui.campaign import (
    CampaignPlan,
    ExplicitSweep,
    LinearSweep,
    LogSweep,
    SerialCampaignRunner,
    SweepMode,
    SweepParameter,
    generate_runs,
)
from magboltz_gui.data.input_cards import InputCards, InputGas
from magboltz_gui.util import parser


def _base_cards() -> InputCards:
    return InputCards(
        gases=[InputGas(gas_id=2, gas_frac=70.0), InputGas(gas_id=12, gas_frac=30.0)],
        number_of_real_collisions=20,
        final_energy=4.0,
        electric_field=1000.0,
    )


def test_linear_sweep_includes_endpoints() -> None:
    assert LinearSweep(start=100.0, stop=1000.0, points=4).values() == pytest.approx(
        [100.0, 400.0, 700.0, 1000.0]
    )


def test_log_sweep_includes_endpoints() -> None:
    assert LogSweep(start=100.0, stop=10000.0, points=3).values() == pytest.approx([100.0, 1000.0, 10000.0])


def test_product_campaign_generates_all_combinations_without_mutating_base() -> None:
    base = _base_cards()
    plan = CampaignPlan(
        base_cards=base,
        parameters=[
            SweepParameter("electric_field", ExplicitSweep([100.0, 200.0])),
            SweepParameter("gas_pressure", ExplicitSweep([760.0, 380.0])),
        ],
    )

    runs = generate_runs(plan)

    assert [run.run_id for run in runs] == ["run_0001", "run_0002", "run_0003", "run_0004"]
    assert [(run.input_cards.electric_field, run.input_cards.gas_pressure) for run in runs] == [
        (100.0, 760.0),
        (100.0, 380.0),
        (200.0, 760.0),
        (200.0, 380.0),
    ]
    assert base.electric_field == 1000.0
    assert base.gas_pressure == 760.0


def test_coupled_parameters_vary_rows_together() -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[
            SweepParameter("gases[0].gas_frac", ExplicitSweep([70.0, 80.0]), label="Ar", mode=SweepMode.COUPLED),
            SweepParameter("gases[1].gas_frac", ExplicitSweep([30.0, 20.0]), label="CO2", mode=SweepMode.COUPLED),
        ],
    )

    runs = generate_runs(plan)

    assert [[gas.gas_frac for gas in run.input_cards.gases] for run in runs] == [[70.0, 30.0], [80.0, 20.0]]
    assert runs[1].parameter_values == {"Ar": 80.0, "CO2": 20.0}


def test_mixed_product_and_coupled_parameters_generate_product_of_coupled_block() -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[
            SweepParameter("electric_field", ExplicitSweep([100.0, 200.0])),
            SweepParameter("gases[0].gas_frac", ExplicitSweep([70.0, 80.0]), label="Ar", mode=SweepMode.COUPLED),
            SweepParameter("gases[1].gas_frac", ExplicitSweep([30.0, 20.0]), label="CO2", mode=SweepMode.COUPLED),
        ],
    )

    runs = generate_runs(plan)

    assert len(runs) == 4
    assert [(run.input_cards.electric_field, run.input_cards.gases[0].gas_frac, run.input_cards.gases[1].gas_frac) for run in runs] == [
        (100.0, 70.0, 30.0),
        (100.0, 80.0, 20.0),
        (200.0, 70.0, 30.0),
        (200.0, 80.0, 20.0),
    ]


def test_coupled_parameters_reject_single_row() -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[
            SweepParameter("gases[0].gas_frac", ExplicitSweep([70.0, 80.0]), label="Ar", mode=SweepMode.COUPLED),
        ],
    )

    with pytest.raises(ValueError, match="at least two"):
        generate_runs(plan)


def test_coupled_parameters_reject_mismatched_lengths() -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[
            SweepParameter("gases[0].gas_frac", ExplicitSweep([70.0, 80.0]), label="Ar", mode=SweepMode.COUPLED),
            SweepParameter("gases[1].gas_frac", ExplicitSweep([30.0]), label="CO2", mode=SweepMode.COUPLED),
        ],
    )

    with pytest.raises(ValueError, match="same number"):
        generate_runs(plan)


def test_prepare_writes_input_cards_and_summary(tmp_path: Path) -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[SweepParameter("electric_field", ExplicitSweep([100.0, 200.0]))],
    )

    runs = SerialCampaignRunner().prepare(plan, tmp_path)

    assert [run.run_id for run in runs] == ["run_0001", "run_0002"]
    assert parser.load(tmp_path / "base_input.in").electric_field == 1000.0
    assert parser.load(tmp_path / "run_0002" / "input.in").electric_field == 200.0
    summary = (tmp_path / "summary.csv").read_text(encoding="utf-8")
    assert "run_id,electric_field" in summary
    assert "run_0001,100.0" in summary


def test_prepare_writes_campaign_manifest(tmp_path: Path) -> None:
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[
            SweepParameter("electric_field", LinearSweep(100.0, 200.0, 2)),
            SweepParameter("gases[0].gas_frac", ExplicitSweep([70.0, 80.0]), label="Ar", mode=SweepMode.COUPLED),
            SweepParameter("gases[1].gas_frac", ExplicitSweep([30.0, 20.0]), label="CO2", mode=SweepMode.COUPLED),
        ],
    )

    SerialCampaignRunner().prepare(plan, tmp_path)

    manifest = json.loads((tmp_path / "campaign.json").read_text(encoding="utf-8"))
    assert manifest["total_runs"] == 4
    assert manifest["base_input"] == "base_input.in"
    assert manifest["matrix"] == {
        "independent_rows": 1,
        "product_size": 2,
        "coupled_rows": 2,
        "coupled_size": 2,
        "total": 4,
    }
    assert manifest["sweeps"][0] == {
        "path": "electric_field",
        "label": None,
        "mode": "product",
        "points": 2,
        "sweep_type": "linear",
        "start": 100.0,
        "stop": 200.0,
    }
    assert manifest["sweeps"][1]["mode"] == "coupled"
    assert manifest["sweeps"][1]["sweep_type"] == "values"
    assert manifest["sweeps"][1]["values"] == [70.0, 80.0]


def test_serial_runner_executes_each_input_card(tmp_path: Path) -> None:
    fake_magboltz = tmp_path / "fake_magboltz"
    fake_magboltz.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "payload = sys.stdin.read()\n"
        "print('received-lines', len(payload.splitlines()))\n",
        encoding="utf-8",
    )
    os.chmod(fake_magboltz, 0o755)
    plan = CampaignPlan(
        base_cards=_base_cards(),
        parameters=[SweepParameter("electric_field", ExplicitSweep([100.0]))],
    )

    results = SerialCampaignRunner(executable=str(fake_magboltz)).run(
        plan,
        tmp_path / "campaign",
    )

    assert results[0].ok
    assert "received-lines" in results[0].stdout_path.read_text(encoding="utf-8")
    status = (tmp_path / "campaign" / "run_status.csv").read_text(encoding="utf-8")
    assert "run_id,status,returncode,input,stdout,stderr" in status
    assert "run_0001,done,0" in status
