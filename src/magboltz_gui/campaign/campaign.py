"""Campaign expansion and input-card mutation utilities."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from itertools import product
import re
from typing import Any

from magboltz_gui.data.input_cards import InputCards

from magboltz_gui.campaign.sweep import SweepParameter


class CampaignMode(StrEnum):
    """How multiple sweep parameters are combined."""

    PRODUCT = "product"
    COUPLED = "coupled"


@dataclass(frozen=True)
class CampaignPlan:
    """A reproducible parameter-sweep campaign definition."""

    base_cards: InputCards
    parameters: tuple[SweepParameter, ...]
    mode: CampaignMode = CampaignMode.PRODUCT

    def __init__(
        self,
        base_cards: InputCards,
        parameters: list[SweepParameter] | tuple[SweepParameter, ...],
        mode: CampaignMode = CampaignMode.PRODUCT,
    ) -> None:
        if not parameters:
            raise ValueError("CampaignPlan requires at least one sweep parameter")
        object.__setattr__(self, "base_cards", base_cards)
        object.__setattr__(self, "parameters", tuple(parameters))
        object.__setattr__(self, "mode", mode)


@dataclass(frozen=True)
class CampaignRun:
    """One concrete run generated from a campaign plan."""

    index: int
    run_id: str
    input_cards: InputCards
    parameter_values: dict[str, float | int | bool | str]


def generate_runs(plan: CampaignPlan) -> list[CampaignRun]:
    """Expand a campaign plan into concrete input-card runs."""
    parameter_values = {parameter.display_label: parameter.sweep.values() for parameter in plan.parameters}

    if plan.mode == CampaignMode.PRODUCT:
        labels = list(parameter_values)
        value_rows = [dict(zip(labels, values)) for values in product(*(parameter_values[label] for label in labels))]
    elif plan.mode == CampaignMode.COUPLED:
        lengths = {len(values) for values in parameter_values.values()}
        if len(lengths) != 1:
            raise ValueError("Coupled campaign parameters must have the same number of values")
        labels = list(parameter_values)
        value_rows = [
            {label: parameter_values[label][row_index] for label in labels} for row_index in range(next(iter(lengths)))
        ]
    else:
        raise ValueError(f"Unsupported campaign mode: {plan.mode}")

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


def apply_input_card_value(cards: InputCards, path: str, value: float | int | bool | str) -> None:
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
