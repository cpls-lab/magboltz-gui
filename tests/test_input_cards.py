"""Tests for Magboltz input-card parsing and serialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from magboltz_gui.data.input_cards import InputCards, InputGas
from magboltz_gui.util import parser


def assert_cards_semantically_equal(actual: InputCards, expected: InputCards) -> None:
    """Compare cards by physical settings, not by whitespace formatting."""
    assert actual.number_of_gases == expected.number_of_gases
    assert [gas.gas_id for gas in actual.gases] == [gas.gas_id for gas in expected.gases]
    assert actual.number_of_real_collisions == expected.number_of_real_collisions
    assert actual.enable_penning is expected.enable_penning
    assert actual.enable_thermal is expected.enable_thermal
    assert actual.final_energy == pytest.approx(expected.final_energy)
    assert actual.gas_temperature == pytest.approx(expected.gas_temperature)
    assert actual.gas_pressure == pytest.approx(expected.gas_pressure)
    assert actual.electric_field == pytest.approx(expected.electric_field)
    assert actual.magnetic_field == pytest.approx(expected.magnetic_field)
    assert actual.angle == pytest.approx(expected.angle)
    assert [gas.gas_frac for gas in actual.gases] == pytest.approx([gas.gas_frac for gas in expected.gases])


def test_load_reference_input_card(reference_input_path: Path) -> None:
    cards = parser.load(reference_input_path)

    assert cards.number_of_gases == 2
    assert cards.gases == [InputGas(gas_id=2, gas_frac=70.0), InputGas(gas_id=12, gas_frac=30.0)]
    assert cards.number_of_real_collisions == 20
    assert cards.enable_penning is False
    assert cards.enable_thermal is True
    assert cards.final_energy == pytest.approx(4.0)
    assert cards.gas_temperature == pytest.approx(20.0)
    assert cards.gas_pressure == pytest.approx(760.0)
    assert cards.electric_field == pytest.approx(1000.0)
    assert cards.magnetic_field == pytest.approx(0.0)
    assert cards.angle == pytest.approx(0.0)


def test_save_normalizes_fractions(tmp_path: Path) -> None:
    cards = InputCards(
        gases=[InputGas(gas_id=2, gas_frac=7.0), InputGas(gas_id=12, gas_frac=3.0)],
        number_of_real_collisions=20,
        enable_penning=False,
        enable_thermal=True,
        final_energy=4.0,
        gas_temperature=20.0,
        gas_pressure=760.0,
        electric_field=1000.0,
        magnetic_field=0.0,
        angle=0.0,
    )
    path = tmp_path / "normalized.in"

    parser.save(cards, path)
    loaded = parser.load(path)

    assert [gas.gas_frac for gas in loaded.gases] == pytest.approx([70.0, 30.0])


def test_reference_input_card_round_trips_semantically(reference_input_path: Path, tmp_path: Path) -> None:
    cards = parser.load(reference_input_path)
    path = tmp_path / "saved.in"

    parser.save(cards, path)

    assert_cards_semantically_equal(parser.load(path), cards)
