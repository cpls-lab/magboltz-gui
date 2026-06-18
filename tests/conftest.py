"""Shared pytest fixtures for Magboltz-GUI core tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from magboltz_gui.util.output_parser import parse_magboltz_output
from magboltz_gui.util.run_result import RunResult


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the immutable test-fixture directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def reference_input_path(fixtures_dir: Path) -> Path:
    """Reference Ar/CO2 Magboltz input card used for regression tests."""
    return fixtures_dir / "ar_co2_70_30_1000vcm.in"


@pytest.fixture(scope="session")
def reference_output_text(fixtures_dir: Path) -> str:
    """Captured Magboltz stdout for the Ar/CO2 reference case."""
    return (fixtures_dir / "magboltz_output.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def reference_input_text(reference_input_path: Path) -> str:
    """Raw text of the Ar/CO2 reference input card."""
    return reference_input_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def reference_run(
    reference_output_text: str,
    reference_input_text: str,
    reference_input_path: Path,
) -> RunResult:
    """Parsed reference run with input-card provenance attached."""
    return parse_magboltz_output(
        reference_output_text,
        input_text=reference_input_text,
        input_path=str(reference_input_path),
    )
