from __future__ import annotations

from dataclasses import dataclass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

_PLOT_EXCLUDED_COLUMNS = {
    "run_id",
    "status",
    "returncode",
    "executed_at",
    "stdout",
    "stderr",
}


@dataclass(frozen=True)
class CampaignPlotDataset:
    """Tabular campaign data prepared for interactive X/Y plotting."""

    all_rows: list[dict[str, str]]
    selected_rows: list[dict[str, str]]


class CampaignPlotWindow(QDialog):
    """Generic campaign plot dialog for numeric result-table columns."""

    def __init__(self, dataset: CampaignPlotDataset, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Campaign plot")
        self.resize(900, 700)
        self._dataset = dataset
        self._numeric_columns = _numeric_columns(dataset.all_rows)
        self._init_ui()
        self._render()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        controls_group = QGroupBox("Plot controls")
        controls_layout = QVBoxLayout(controls_group)

        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel("Scope"))
        self.scopeGroup = QButtonGroup(self)
        self.radioAllRuns = QRadioButton(f"All runs ({len(self._dataset.all_rows)})")
        self.radioSelectedRuns = QRadioButton(f"Selected runs ({len(self._dataset.selected_rows)})")
        self.radioSelectedRuns.setEnabled(bool(self._dataset.selected_rows))
        self.scopeGroup.addButton(self.radioAllRuns)
        self.scopeGroup.addButton(self.radioSelectedRuns)
        scope_layout.addWidget(self.radioAllRuns)
        scope_layout.addWidget(self.radioSelectedRuns)
        scope_layout.addStretch(1)
        controls_layout.addLayout(scope_layout)
        if self._dataset.selected_rows:
            self.radioSelectedRuns.setChecked(True)
        else:
            self.radioAllRuns.setChecked(True)

        form_layout = QFormLayout()
        self.comboX = QComboBox()
        self.comboY = QComboBox()
        for column in self._numeric_columns:
            self.comboX.addItem(column)
            self.comboY.addItem(column)
        if self.comboY.count() > 1:
            self.comboY.setCurrentIndex(1)
        self.comboStyle = QComboBox()
        self.comboStyle.addItems(["Scatter", "Line", "Line + markers"])
        form_layout.addRow("X", self.comboX)
        form_layout.addRow("Y", self.comboY)
        form_layout.addRow("Style", self.comboStyle)
        controls_layout.addLayout(form_layout)

        self.statusLabel = QLabel()
        controls_layout.addWidget(self.statusLabel)
        layout.addWidget(controls_group)

        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.comboX.currentIndexChanged.connect(self._render)
        self.comboY.currentIndexChanged.connect(self._render)
        self.comboStyle.currentIndexChanged.connect(self._render)
        self.radioAllRuns.toggled.connect(self._render)
        self.radioSelectedRuns.toggled.connect(self._render)

    def _active_rows(self) -> list[dict[str, str]]:
        if self.radioSelectedRuns.isChecked():
            return self._dataset.selected_rows
        return self._dataset.all_rows

    def _render(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if not self._numeric_columns:
            self.statusLabel.setText("No numeric campaign columns are available for plotting.")
            self.canvas.draw()
            return

        x_column = self.comboX.currentText()
        y_column = self.comboY.currentText()
        rows = [
            row
            for row in self._active_rows()
            if _to_float(row.get(x_column, "")) is not None and _to_float(row.get(y_column, "")) is not None
        ]
        x_values = [_to_float(row[x_column]) for row in rows]
        y_values = [_to_float(row[y_column]) for row in rows]
        x = [value for value in x_values if value is not None]
        y = [value for value in y_values if value is not None]

        style = self.comboStyle.currentText()
        if style == "Scatter":
            ax.scatter(x, y)
        elif style == "Line":
            ax.plot(x, y)
        else:
            ax.plot(x, y, marker="o")
        ax.set_xlabel(x_column)
        ax.set_ylabel(y_column)
        ax.set_title(f"{y_column} vs {x_column}")
        ax.grid(True, alpha=0.25)
        self.statusLabel.setText(f"Plotting {len(rows)} run(s).")
        self.canvas.draw()


def _numeric_columns(rows: list[dict[str, str]]) -> list[str]:
    columns: list[str] = []
    if not rows:
        return columns
    for column in rows[0]:
        if column in _PLOT_EXCLUDED_COLUMNS:
            continue
        values = [row.get(column, "") for row in rows]
        if any(_to_float(value) is not None for value in values):
            columns.append(column)
    return columns


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
