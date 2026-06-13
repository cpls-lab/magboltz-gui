"""Non-blocking campaign setup tab for parameter-sweep input generation."""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from magboltz_gui.campaign import CampaignPlan, ExplicitSweep, LinearSweep, LogSweep, SerialCampaignRunner, SweepMode
from magboltz_gui.campaign.sweep import SweepParameter
from magboltz_gui.data.input_cards import InputCards


PARAMETER_CHOICES: tuple[tuple[str, str], ...] = (
    ("Electric field", "electric_field"),
    ("Magnetic field", "magnetic_field"),
    ("Field angle", "angle"),
    ("Gas pressure", "gas_pressure"),
    ("Gas temperature", "gas_temperature"),
    ("Real collisions", "number_of_real_collisions"),
    ("Final energy", "final_energy"),
    ("Gas 1 fraction", "gases[0].gas_frac"),
    ("Gas 2 fraction", "gases[1].gas_frac"),
    ("Gas 3 fraction", "gases[2].gas_frac"),
    ("Gas 4 fraction", "gases[3].gas_frac"),
    ("Gas 5 fraction", "gases[4].gas_frac"),
    ("Gas 6 fraction", "gases[5].gas_frac"),
)

SWEEP_TYPES = ("values", "linear", "logspace")


class CampaignWidget(QWidget):
    """First campaign GUI slice: preview and generate sweep input cards."""

    def __init__(
        self,
        get_current_cards: Callable[[], InputCards],
        show_info: Callable[[str, str], None],
        show_error: Callable[[str, str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_current_cards = get_current_cards
        self._show_info = show_info
        self._show_error = show_error
        self._base_cards: InputCards | None = None

        self._build_ui()
        self.use_current_input()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)

        sweep_group = QGroupBox("Sweep parameters")
        sweep_layout = QVBoxLayout(sweep_group)
        self.sweepTable = QTableWidget(0, 8)
        self.sweepTable.setHorizontalHeaderLabels(
            ["Enabled", "Parameter", "Mode", "Sweep", "Values / start", "Stop", "Points", "Label"]
        )
        self.sweepTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sweepTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.sweepTable.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        sweep_buttons = QHBoxLayout()
        self.btnAddSweep = QToolButton()
        self.btnAddSweep.setIcon(_sweep_icon("add"))
        self.btnAddSweep.setIconSize(QSize(20, 20))
        self.btnAddSweep.setToolTip("Add sweep")
        self.btnAddSweep.setText("Add sweep")
        self.btnRemoveSweep = QToolButton()
        self.btnRemoveSweep.setIcon(_sweep_icon("remove"))
        self.btnRemoveSweep.setIconSize(QSize(20, 20))
        self.btnRemoveSweep.setToolTip("Remove selected sweep")
        self.btnRemoveSweep.setText("Remove selected")
        self.btnAddSweep.clicked.connect(self.add_default_sweep_row)
        self.btnRemoveSweep.clicked.connect(self.remove_selected_sweep)
        sweep_buttons.addWidget(self.btnAddSweep)
        sweep_buttons.addWidget(self.btnRemoveSweep)
        sweep_buttons.addStretch(1)
        sweep_layout.addWidget(self.sweepTable)
        sweep_layout.addLayout(sweep_buttons)

        preview_group = QGroupBox("Campaign preview")
        preview_layout = QVBoxLayout(preview_group)
        self.previewSummary = QLabel("Runs: 0")
        self.previewTable = QTableWidget(0, 0)
        preview_header = self.previewTable.horizontalHeader()
        assert preview_header is not None
        preview_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.btnPreview = QPushButton("Preview runs")
        self.btnGenerate = QPushButton("Generate input cards...")
        self.btnPreview.clicked.connect(self.preview_runs)
        self.btnGenerate.clicked.connect(self.generate_input_cards)
        preview_layout.addWidget(self.previewSummary)
        preview_layout.addWidget(self.previewTable)
        preview_layout.addWidget(self.btnPreview)
        preview_layout.addWidget(self.btnGenerate)

        layout.addWidget(sweep_group, 0, 0)
        layout.addWidget(preview_group, 1, 0)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 2)

        self.add_default_sweep_row()

    def use_current_input(self) -> None:
        """Snapshot the current GUI input card as campaign base."""
        self._base_cards = deepcopy(self._get_current_cards())

    def add_default_sweep_row(self) -> None:
        """Append an editable sweep row with a useful electric-field default."""
        self.add_sweep_row(parameter_path="electric_field", sweep_type="logspace", values="100", stop="10000", points="5")

    def add_sweep_row(
        self,
        parameter_path: str,
        sweep_type: str,
        values: str = "",
        stop: str = "",
        points: str = "",
        label: str = "",
        mode: SweepMode = SweepMode.PRODUCT,
        enabled: bool = True,
    ) -> None:
        """Append a sweep row. Public to keep GUI tests simple."""
        row = self.sweepTable.rowCount()
        self.sweepTable.insertRow(row)

        enabled_widget = QCheckBox()
        enabled_widget.setChecked(enabled)
        enabled_widget.setStyleSheet("margin-left: 12px;")
        self.sweepTable.setCellWidget(row, 0, enabled_widget)

        parameter_combo = QComboBox()
        for text, path in PARAMETER_CHOICES:
            parameter_combo.addItem(text, path)
        index = parameter_combo.findData(parameter_path)
        parameter_combo.setCurrentIndex(max(index, 0))
        self.sweepTable.setCellWidget(row, 1, parameter_combo)

        mode_combo = QComboBox()
        mode_combo.setToolTip(
            "Independent rows are combined with all other independent rows. "
            "Coupled rows form one group and advance point-by-point together."
        )
        mode_combo.addItem("Independent", SweepMode.PRODUCT.value)
        mode_combo.addItem("Coupled", SweepMode.COUPLED.value)
        mode_combo.setCurrentIndex(mode_combo.findData(mode.value))
        self.sweepTable.setCellWidget(row, 2, mode_combo)
        self._apply_mode_constraints(parameter_combo, mode_combo)
        parameter_combo.currentIndexChanged.connect(
            lambda _index, parameter=parameter_combo, mode_selector=mode_combo: self._apply_mode_constraints(
                parameter, mode_selector
            )
        )

        sweep_combo = QComboBox()
        sweep_combo.addItems(SWEEP_TYPES)
        sweep_combo.setCurrentText(sweep_type)
        self.sweepTable.setCellWidget(row, 3, sweep_combo)

        for column, text in ((4, values), (5, stop), (6, points), (7, label)):
            self.sweepTable.setItem(row, column, QTableWidgetItem(text))

    def remove_selected_sweep(self) -> None:
        """Remove the selected sweep row."""
        row = self.sweepTable.currentRow()
        if row >= 0:
            self.sweepTable.removeRow(row)

    def _apply_mode_constraints(self, parameter_combo: QComboBox, mode_combo: QComboBox) -> None:
        path = str(parameter_combo.currentData())
        if _is_gas_fraction_path(path):
            mode_combo.setCurrentIndex(mode_combo.findData(SweepMode.COUPLED.value))
            mode_combo.setEnabled(False)
            mode_combo.setToolTip("Gas fractions are always coupled to prevent invalid Cartesian mixtures.")
        else:
            mode_combo.setEnabled(True)
            mode_combo.setToolTip(
                "Independent rows are combined with all other independent rows. "
                "Coupled rows form one group and advance point-by-point together."
            )

    def preview_runs(self) -> None:
        """Render the generated run matrix without writing files."""
        try:
            runs = self._build_runs()
        except Exception as exc:
            self._show_error("Invalid campaign", str(exc))
            return
        self._populate_preview(runs)

    def generate_input_cards(self) -> None:
        """Write campaign input cards to a user-selected directory."""
        try:
            plan = self._build_plan()
        except Exception as exc:
            self._show_error("Invalid campaign", str(exc))
            return

        directory = QFileDialog.getExistingDirectory(self, "Select campaign output directory")
        if not directory:
            return

        runs = SerialCampaignRunner().prepare(plan, Path(directory))
        self._populate_preview(runs)
        self._show_info("Campaign generated", f"Generated {len(runs)} input cards in:\n{directory}")

    def _build_runs(self):
        from magboltz_gui.campaign import generate_runs

        return generate_runs(self._build_plan())

    def _build_plan(self) -> CampaignPlan:
        self.use_current_input()
        if self._base_cards is None:
            raise ValueError("No input card selected")
        parameters = self._read_parameters()
        return CampaignPlan(base_cards=self._base_cards, parameters=parameters)

    def _read_parameters(self) -> list[SweepParameter]:
        parameters: list[SweepParameter] = []
        for row in range(self.sweepTable.rowCount()):
            enabled = self.sweepTable.cellWidget(row, 0)
            if isinstance(enabled, QCheckBox) and not enabled.isChecked():
                continue

            parameter_combo = self.sweepTable.cellWidget(row, 1)
            mode_combo = self.sweepTable.cellWidget(row, 2)
            sweep_combo = self.sweepTable.cellWidget(row, 3)
            if (
                not isinstance(parameter_combo, QComboBox)
                or not isinstance(mode_combo, QComboBox)
                or not isinstance(sweep_combo, QComboBox)
            ):
                continue

            path = str(parameter_combo.currentData())
            mode = SweepMode(str(mode_combo.currentData()))
            sweep_type = sweep_combo.currentText()
            first = self._cell_text(row, 4)
            stop = self._cell_text(row, 5)
            points = self._cell_text(row, 6)
            label = self._cell_text(row, 7) or None

            if sweep_type == "values":
                sweep = ExplicitSweep(_parse_values(first))
            elif sweep_type == "linear":
                sweep = LinearSweep(float(first), float(stop), int(points))
            elif sweep_type == "logspace":
                sweep = LogSweep(float(first), float(stop), int(points))
            else:
                raise ValueError(f"Unsupported sweep type: {sweep_type}")
            parameters.append(SweepParameter(path=path, sweep=sweep, label=label, mode=mode))

        if not parameters:
            raise ValueError("Add at least one enabled sweep parameter")
        return parameters

    def _cell_text(self, row: int, column: int) -> str:
        item = self.sweepTable.item(row, column)
        return item.text().strip() if item is not None else ""

    def _populate_preview(self, runs) -> None:
        labels = list(runs[0].parameter_values) if runs else []
        self.previewTable.setColumnCount(1 + len(labels))
        self.previewTable.setHorizontalHeaderLabels(["run_id", *labels])
        self.previewTable.setRowCount(len(runs))
        for row, run in enumerate(runs):
            self.previewTable.setItem(row, 0, QTableWidgetItem(run.run_id))
            for column, label in enumerate(labels, start=1):
                self.previewTable.setItem(row, column, QTableWidgetItem(str(run.parameter_values[label])))
        self.previewSummary.setText(f"Runs: {len(runs)}")


def _parse_values(text: str) -> list[float | int | bool | str]:
    if not text:
        raise ValueError("Explicit sweep values cannot be empty")
    values: list[float | int | bool | str] = []
    for raw in text.split(","):
        token = raw.strip()
        if token.lower() in {"true", "false"}:
            values.append(token.lower() == "true")
            continue
        try:
            number = float(token)
        except ValueError:
            values.append(token)
        else:
            values.append(int(number) if number.is_integer() else number)
    return values


def _is_gas_fraction_path(path: str) -> bool:
    return path.startswith("gases[") and path.endswith("].gas_frac")


def _sweep_icon(kind: str) -> QIcon:
    icon_names = {
        "add": ("addition-color-icon.svg", "list-add"),
        "remove": ("subtract-color-icon.svg", "list-remove"),
    }
    bundled_name, theme_name = icon_names[kind]
    icon_path = files("magboltz_gui.icons").joinpath("linux_icons", bundled_name)
    if icon_path.is_file():
        return QIcon(str(icon_path))
    return QIcon.fromTheme(theme_name)
