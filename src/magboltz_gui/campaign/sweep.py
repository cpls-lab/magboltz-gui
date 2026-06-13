"""Parameter value generators for reproducible Magboltz campaigns."""

from __future__ import annotations

from dataclasses import dataclass
from math import log10
from typing import Protocol


class Sweep(Protocol):
    """Protocol implemented by campaign value generators."""

    def values(self) -> list[float | int | bool | str]:
        """Return concrete values for this sweep."""


@dataclass(frozen=True)
class ExplicitSweep:
    """A sweep over explicitly provided values."""

    items: tuple[float | int | bool | str, ...]

    def __init__(self, items: list[float | int | bool | str] | tuple[float | int | bool | str, ...]) -> None:
        if not items:
            raise ValueError("ExplicitSweep requires at least one value")
        object.__setattr__(self, "items", tuple(items))

    def values(self) -> list[float | int | bool | str]:
        """Return the configured values."""
        return list(self.items)


@dataclass(frozen=True)
class LinearSweep:
    """A linearly spaced numeric sweep, including both endpoints."""

    start: float
    stop: float
    points: int

    def __post_init__(self) -> None:
        if self.points < 1:
            raise ValueError("LinearSweep requires at least one point")

    def values(self) -> list[float]:
        """Return linearly spaced values."""
        if self.points == 1:
            return [self.start]
        step = (self.stop - self.start) / (self.points - 1)
        return [self.start + i * step for i in range(self.points)]


@dataclass(frozen=True)
class LogSweep:
    """A base-10 logarithmically spaced numeric sweep, including both endpoints."""

    start: float
    stop: float
    points: int

    def __post_init__(self) -> None:
        if self.points < 1:
            raise ValueError("LogSweep requires at least one point")
        if self.start <= 0 or self.stop <= 0:
            raise ValueError("LogSweep endpoints must be positive")

    def values(self) -> list[float]:
        """Return logarithmically spaced values."""
        if self.points == 1:
            return [self.start]
        start_log = log10(self.start)
        step = (log10(self.stop) - start_log) / (self.points - 1)
        return [10 ** (start_log + i * step) for i in range(self.points)]


@dataclass(frozen=True)
class SweepParameter:
    """
    One input-card field varied during a campaign.

    ``path`` supports top-level fields such as ``electric_field`` and indexed
    list fields such as ``gases[0].gas_frac``.
    """

    path: str
    sweep: Sweep
    label: str | None = None

    @property
    def display_label(self) -> str:
        """Return a stable label for tables and manifests."""
        return self.label or self.path
