"""Opt-in tests that execute a real Magboltz binary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from magboltz_gui.util import parser
from magboltz_gui.util.output_parser import parse_magboltz_output
from magboltz_gui.util.run_result import RunResult


pytestmark = pytest.mark.magboltz


def _magboltz_binary() -> Path:
    binary = os.environ.get("MAGBOLTZ_TEST_BIN")
    if not binary:
        pytest.skip("Set MAGBOLTZ_TEST_BIN to run Magboltz executable tests")
    path = Path(binary)
    if not path.is_file():
        pytest.fail(f"MAGBOLTZ_TEST_BIN does not point to a file: {path}")
    return path


def _run_magboltz(binary: Path, input_path: Path, timeout: float) -> str:
    completed = subprocess.run(
        [str(binary)],
        input=input_path.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        pytest.fail(
            "Magboltz execution failed\n"
            f"binary: {binary}\n"
            f"input: {input_path}\n"
            f"returncode: {completed.returncode}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )
    return completed.stdout


def _assert_selected_transport_equal(actual: RunResult, expected: RunResult) -> None:
    assert [gas.name for gas in actual.mixture] == [gas.name for gas in expected.mixture]
    assert [gas.fraction_percent for gas in actual.mixture] == pytest.approx(
        [gas.fraction_percent for gas in expected.mixture]
    )
    assert actual.conditions.electric_field_V_cm == pytest.approx(expected.conditions.electric_field_V_cm)
    assert actual.conditions.gas_temperature_C == pytest.approx(expected.conditions.gas_temperature_C)
    assert actual.conditions.gas_pressure_torr == pytest.approx(expected.conditions.gas_pressure_torr)
    assert actual.transport.vz_um_ns is not None
    assert expected.transport.vz_um_ns is not None
    assert actual.transport.vz_um_ns.v_um_ns == pytest.approx(expected.transport.vz_um_ns.v_um_ns)
    assert actual.transport.mean_electron_energy_eV == pytest.approx(expected.transport.mean_electron_energy_eV)

    actual_dt = actual.transport.diffusion.transverse.get("DT_cm2_s")
    expected_dt = expected.transport.diffusion.transverse.get("DT_cm2_s")
    actual_dl = actual.transport.diffusion.longitudinal.get("DL_cm2_s")
    expected_dl = expected.transport.diffusion.longitudinal.get("DL_cm2_s")
    assert actual_dt is not None
    assert expected_dt is not None
    assert actual_dl is not None
    assert expected_dl is not None
    assert actual_dt.value == pytest.approx(expected_dt.value)
    assert actual_dl.value == pytest.approx(expected_dl.value)


def test_generated_input_card_matches_handwritten_card_with_real_magboltz(
    reference_input_path: Path,
    tmp_path: Path,
) -> None:
    """Run native Magboltz on handwritten and GUI-serialized equivalent cards."""
    binary = _magboltz_binary()
    timeout = float(os.environ.get("MAGBOLTZ_TEST_TIMEOUT", "900"))

    cards = parser.load(reference_input_path)
    generated_input_path = tmp_path / "generated.in"
    parser.save(cards, generated_input_path)

    handwritten_stdout = _run_magboltz(binary, reference_input_path, timeout)
    generated_stdout = _run_magboltz(binary, generated_input_path, timeout)

    handwritten_run = parse_magboltz_output(
        handwritten_stdout,
        input_text=reference_input_path.read_text(encoding="utf-8"),
        input_path=str(reference_input_path),
    )
    generated_run = parse_magboltz_output(
        generated_stdout,
        input_text=generated_input_path.read_text(encoding="utf-8"),
        input_path=str(generated_input_path),
    )

    _assert_selected_transport_equal(generated_run, handwritten_run)
