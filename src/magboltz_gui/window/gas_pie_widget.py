# gas_pie_widget.py
from __future__ import annotations
from typing import Dict
from PyQt6 import QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT

from matplotlib.figure import Figure


class GasPieWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._figure = Figure(figsize=(4, 4))
        self._canvas = FigureCanvas(self._figure)  # type:ignore
        self._ax = self._figure.add_subplot(111)
        self._ax.set_aspect("equal")  # keep it round

        toolbar = NavigationToolbar2QT(self._canvas, self)  # type:ignore

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self._canvas)

    def set_composition(
        self, composition: Dict[str, float], title: str = "Gas composition", normalize: bool = False
    ) -> None:
        if not composition:
            raise ValueError("composition dict is empty")
        labels = list(composition.keys())
        values = [float(v) for v in composition.values()]
        if any(v < 0 for v in values):
            raise ValueError("values must be non-negative")
        total = sum(values)
        if total <= 0:
            raise ValueError("sum must be > 0")
        if normalize:
            values = [v / total for v in values]

        self._ax.clear()
        self._ax.set_title(title)
        # autopct shows percentages; pctdistance/labeldistance tweak spacing for tiny slices
        self._ax.pie(
            values, labels=labels, autopct=lambda p: f"{p:.1f}%", startangle=90, pctdistance=0.75, labeldistance=1.05
        )
        self._ax.set_aspect("equal")
        self._canvas.draw_idle()  # type:ignore
