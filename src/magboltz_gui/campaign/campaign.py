"""Campaign expansion and input-card mutation utilities."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import product
import re
from typing import Any

from magboltz_gui.data.input_cards import InputCards

from magboltz_gui.campaign.sweep import SweepMode, SweepParameter

Value = float | int | bool | str
ValueRow = dict[str, Value]


@dataclass(frozen=True)
class CampaignPlan:
    """A reproducible parameter-sweep campaign definition."""

    base_cards: InputCards
    parameters: tuple[SweepParameter, ...]

    def __init__(
        self,
        base_cards: InputCards,
        parameters: list[SweepParameter] | tuple[SweepParameter, ...],
    ) -> None:
        if not parameters:
            raise ValueError("CampaignPlan requires at least one sweep parameter")
        object.__setattr__(self, "base_cards", base_cards)
        object.__setattr__(self, "parameters", tuple(parameters))


@dataclass(frozen=True)
class CampaignRun:
    """One concrete run generated from a campaign plan."""

    index: int
    run_id: str
    input_cards: InputCards
    parameter_values: ValueRow


def generate_runs(plan: CampaignPlan) -> list[CampaignRun]:
    """Expand a campaign plan into concrete input-card runs."""
    product_rows, coupled_rows = _parameter_rows(plan.parameters)
    value_rows = [
        _merge_value_rows(rows)
        for rows in product(*product_rows, coupled_rows)
    ]

    runs: list[CampaignRun] = []
    path_by_label = {parameter.display_label: parameter.path for parameter in plan.parameters}
    for index, values in enumerate(value_rows, start=1):
        cards = deepcopy(plan.base_cards)
        for label, value in values.items():
            apply_input_card_value(cards, path_by_label[label], value)
        runs.append(
            CampaignRun(
                index=index,
                run_id=f"run_{index:04d}",
                input_cards=cards,
                parameter_values=values,
            )
        )
    return runs


def _parameter_rows(parameters: tuple[SweepParameter, ...]) -> tuple[list[list[ValueRow]], list[ValueRow]]:
    product_rows: list[list[ValueRow]] = []
    coupled_parameters: list[SweepParameter] = []

    for parameter in parameters:
        values = parameter.sweep.values()
        if parameter.mode == SweepMode.PRODUCT:
            product_rows.append([{parameter.display_label: value} for value in values])
        elif parameter.mode == SweepMode.COUPLED:
            coupled_parameters.append(parameter)
        else:
            raise ValueError(f"Unsupported sweep mode: {parameter.mode}")

    if not product_rows:
        product_rows.append([{}])

    coupled_rows = _coupled_rows(coupled_parameters)
    return product_rows, coupled_rows


def _coupled_rows(parameters: list[SweepParameter]) -> list[ValueRow]:
    if not parameters:
        return [{}]
    if len(parameters) == 1:
        raise ValueError("Coupled mode requires at least two sweep parameters")

    parameter_values = {parameter.display_label: parameter.sweep.values() for parameter in parameters}
    lengths = {len(values) for values in parameter_values.values()}
    if len(lengths) != 1:
        raise ValueError("Coupled sweep parameters must have the same number of values")

    labels = list(parameter_values)
    return [{label: parameter_values[label][row_index] for label in labels} for row_index in range(next(iter(lengths)))]


def _merge_value_rows(rows: tuple[ValueRow, ...]) -> ValueRow:
    merged: ValueRow = {}
    for row in rows:
        merged.update(row)
    return merged


def apply_input_card_value(cards: InputCards, path: str, value: Value) -> None:
    """Assign a value to an ``InputCards`` field using a small path syntax."""
    target, attr = _resolve_parent(cards, path)
    if not hasattr(target, attr):
        raise AttributeError(f"Input card path does not exist: {path}")
    setattr(target, attr, value)


_PART_RE = re.compile(r"^(?P<attr>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<index>[0-9]+)\])?$")


def _resolve_parent(cards: InputCards, path: str) -> tuple[Any, str]:
    parts = path.split(".")
    if not parts or any(not part for part in parts):
        raise ValueError(f"Invalid input-card path: {path!r}")

    target: Any = cards
    for part in parts[:-1]:
        target = _resolve_part(target, part, path)

    leaf_match = _PART_RE.match(parts[-1])
    if leaf_match is None or leaf_match.group("index") is not None:
        raise ValueError(f"Invalid assignable input-card path: {path!r}")
    return target, leaf_match.group("attr")


def _resolve_part(target: Any, part: str, full_path: str) -> Any:
    match = _PART_RE.match(part)
    if match is None:
        raise ValueError(f"Invalid input-card path: {full_path!r}")
    attr = match.group("attr")
    if not hasattr(target, attr):
        raise AttributeError(f"Input card path does not exist: {full_path}")
    value = getattr(target, attr)
    index = match.group("index")
    if index is None:
        return value
    return value[int(index)]
