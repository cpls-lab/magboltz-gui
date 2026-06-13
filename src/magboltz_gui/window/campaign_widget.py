"""Non-blocking campaign setup tab for parameter-sweep input generation."""

from __future__ import annotations

import csv
from copy import deepcopy
from importlib.resources import files
import json
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, QThread, QSize, Qt, pyqtSignal, pyqtSlot
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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from magboltz_gui.campaign import CampaignCancelled, CampaignPlan, ExplicitSweep, LinearSweep, LogSweep, SerialCampaignRunner, SweepMode
from magboltz_gui.campaign.sweep import SweepParameter
from magboltz_gui.data.input_cards import InputCards
from magboltz_gui.util import parser
from magboltz_gui.util.output_parser import parse_magboltz_output


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
PREVIEW_ROW_LIMIT = 100
LARGE_CAMPAIGN_RUNS = 1000


class CampaignRunWorker(QObject):
    """Run a serial campaign off the GUI thread."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object, object, object)
    cancelled = pyqtSignal(object, object, object)
    failed = pyqtSignal(str, str)

    def __init__(self, plan: CampaignPlan, directory: Path, executable: str) -> None:
        super().__init__()
        self._plan = plan
        self._directory = directory
        self._executable = executable
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    @pyqtSlot()
    def run(self) -> None:
        try:
            results = SerialCampaignRunner(executable=self._executable).run(
                self._plan,
                self._directory,
                progress_callback=lambda completed, total, run_id: self.progress.emit(completed, total, run_id),
                cancel_callback=lambda: self._cancel_requested,
            )
        except CampaignCancelled as exc:
            self.cancelled.emit(self._plan, self._directory, exc.results)
        except FileNotFoundError as exc:
            executable = exc.filename or self._executable
            self.failed.emit(
                "Campaign run failed",
                (
                    f"Could not start `{executable}`.\n\n"
                    "Install Magboltz or make sure the executable is available in PATH before running a campaign.\n"
                    f"Input cards may already have been generated in:\n{self._directory}"
                ),
            )
        except Exception as exc:
            self.failed.emit("Campaign run failed", str(exc))
        else:
            self.finished.emit(self._plan, self._directory, results)


class CampaignWidget(QWidget):
    """First campaign GUI slice: preview and generate sweep input cards."""

    def __init__(
        self,
        get_current_cards: Callable[[], InputCards],
        get_magboltz_executable: Callable[[], str],
        set_current_cards: Callable[[InputCards], None] | None,
        show_info: Callable[[str, str], None],
        show_error: Callable[[str, str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_current_cards = get_current_cards
        self._get_magboltz_executable = get_magboltz_executable
        self._set_current_cards = set_current_cards
        self._show_info = show_info
        self._show_error = show_error
        self._base_cards: InputCards | None = None
        self._updating_sweep_table = False
        self._campaign_thread: QThread | None = None
        self._campaign_worker: CampaignRunWorker | None = None

        self._build_ui()
        self.use_current_input()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)

        sweep_group = QGroupBox("Sweep parameters")
        sweep_layout = QVBoxLayout(sweep_group)
        self.sweepTable = QTableWidget(0, 9)
        self.sweepTable.setHorizontalHeaderLabels(
            ["Enabled", "Parameter", "Mode", "Sweep", "Values", "Start", "Stop", "Points", "Label"]
        )
        self.sweepTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sweepTable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sweepTable.itemChanged.connect(self._on_sweep_item_changed)
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
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

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
        self.matrixSummary = QLabel("Independent rows: 0, coupled rows: 0")
        self.previewTable = QTableWidget(0, 0)
        preview_header = self.previewTable.horizontalHeader()
        assert preview_header is not None
        preview_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.executableLabel = QLabel()
        self.executableLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._refresh_executable_label()
        self.btnPreview = QPushButton("Preview runs")
        self.btnOpen = QPushButton("Open campaign...")
        self.btnGenerate = QPushButton("Generate input cards...")
        self.btnRun = QPushButton("Run campaign...")
        self.btnCancel = QPushButton("Stop campaign")
        self.btnCancel.setEnabled(False)
        self.btnPreview.clicked.connect(self.preview_runs)
        self.btnOpen.clicked.connect(self.open_campaign)
        self.btnGenerate.clicked.connect(self.generate_input_cards)
        self.btnRun.clicked.connect(self.run_campaign)
        self.btnCancel.clicked.connect(self.cancel_campaign)
        action_buttons = QHBoxLayout()
        action_buttons.addWidget(self.btnPreview)
        action_buttons.addWidget(self.btnOpen)
        action_buttons.addWidget(self.btnGenerate)
        action_buttons.addWidget(self.btnRun)
        action_buttons.addWidget(self.btnCancel)
        action_buttons.addStretch(1)
        preview_layout.addWidget(self.previewSummary)
        preview_layout.addWidget(self.matrixSummary)
        preview_layout.addWidget(self.executableLabel)
        preview_layout.addWidget(self.previewTable)
        preview_layout.addLayout(action_buttons)

        results_group = QGroupBox("Campaign results")
        results_layout = QVBoxLayout(results_group)
        self.resultsSummary = QLabel("Results: not run")
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Campaign idle")
        self.resultsTable = QTableWidget(0, 0)
        results_header = self.resultsTable.horizontalHeader()
        assert results_header is not None
        results_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.resultsTable.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.resultsTable.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.resultsSummary)
        results_layout.addWidget(self.progressBar)
        results_layout.addWidget(self.resultsTable)

        layout.addWidget(sweep_group, 0, 0)
        layout.addWidget(preview_group, 1, 0)
        layout.addWidget(results_group, 2, 0)
        layout.setColumnStretch(0, 1)
        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 2)
        layout.setRowStretch(2, 2)

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
        sweep_combo.currentTextChanged.connect(lambda _text, sweep_row=row: self._apply_sweep_type_constraints(sweep_row))

        start = values if sweep_type != "values" else ""
        explicit_values = values if sweep_type == "values" else ""
        for column, text in ((4, explicit_values), (5, start), (6, stop), (7, points), (8, label)):
            self.sweepTable.setItem(row, column, QTableWidgetItem(text))
        self._apply_sweep_type_constraints(row)

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

    def _apply_sweep_type_constraints(self, row: int) -> None:
        sweep_combo = self.sweepTable.cellWidget(row, 3)
        if not isinstance(sweep_combo, QComboBox):
            return
        sweep_type = sweep_combo.currentText()
        is_explicit = sweep_type == "values"
        self._set_cell_enabled(row, 4, is_explicit, "Used by explicit value sweeps.")
        self._set_cell_enabled(row, 5, not is_explicit, "Used by linear and logspace sweeps.")
        self._set_cell_enabled(row, 6, not is_explicit, "Used by linear and logspace sweeps.")
        if is_explicit:
            self._set_cell_read_only(row, 7, "Automatically counted from comma-separated values.")
            self._update_explicit_points(row)
        else:
            self._set_cell_enabled(row, 7, True, "Used by linear and logspace sweeps.")

    def _set_cell_enabled(self, row: int, column: int, enabled: bool, enabled_tooltip: str) -> None:
        item = self.sweepTable.item(row, column)
        if item is None:
            item = QTableWidgetItem("")
            self.sweepTable.setItem(row, column, item)
        flags = item.flags()
        if enabled:
            item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip(enabled_tooltip)
        else:
            item.setFlags(flags & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsEditable & ~Qt.ItemFlag.ItemIsSelectable)
            item.setToolTip("Disabled for the selected sweep type.")

    def _set_cell_read_only(self, row: int, column: int, tooltip: str) -> None:
        item = self.sweepTable.item(row, column)
        if item is None:
            item = QTableWidgetItem("")
            self.sweepTable.setItem(row, column, item)
        item.setFlags((item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable) & ~Qt.ItemFlag.ItemIsEditable)
        item.setToolTip(tooltip)

    def _on_sweep_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating_sweep_table or item.column() != 4:
            return
        sweep_combo = self.sweepTable.cellWidget(item.row(), 3)
        if isinstance(sweep_combo, QComboBox) and sweep_combo.currentText() == "values":
            self._update_explicit_points(item.row())

    def _update_explicit_points(self, row: int) -> None:
        values_text = self._cell_text(row, 4)
        count = len(_value_tokens(values_text))
        points_item = self.sweepTable.item(row, 7)
        if points_item is None:
            points_item = QTableWidgetItem("")
            self.sweepTable.setItem(row, 7, points_item)
        self._updating_sweep_table = True
        try:
            points_item.setText(str(count))
        finally:
            self._updating_sweep_table = False

    def preview_runs(self) -> None:
        """Render the generated run matrix without writing files."""
        self._refresh_executable_label()
        try:
            plan = self._build_plan()
            runs = self._generate_runs(plan)
        except Exception as exc:
            self._show_error("Invalid campaign", str(exc))
            return
        self._populate_preview(runs, plan)

    def generate_input_cards(self) -> None:
        """Write campaign input cards to a user-selected directory."""
        self._refresh_executable_label()
        selection = self._select_output_directory("Select campaign output directory")
        if selection is None:
            return
        plan, directory = selection

        runs = SerialCampaignRunner().prepare(plan, directory)
        self._populate_preview(runs, plan)
        self._clear_results("Results: input cards generated, not run")
        self._show_info("Campaign generated", f"Generated {len(runs)} input cards in:\n{directory}")

    def open_campaign(self) -> None:
        """Load a previously generated campaign directory."""
        self._refresh_executable_label()
        directory = QFileDialog.getExistingDirectory(self, "Select campaign directory")
        if not directory:
            return
        try:
            plan = self._load_campaign(Path(directory))
            runs = self._generate_runs(plan)
        except Exception as exc:
            self._show_error("Open campaign failed", str(exc))
            return
        self._populate_preview(runs, plan)
        self._populate_results_from_directory(Path(directory))
        self._show_info("Campaign opened", f"Loaded {len(runs)} runs from:\n{directory}")

    def run_campaign(self) -> None:
        """Write and execute campaign input cards serially."""
        if self._campaign_thread is not None:
            self._show_error("Campaign already running", "Wait for the current campaign run to finish.")
            return
        self._refresh_executable_label()
        selection = self._select_output_directory("Select campaign run directory")
        if selection is None:
            return
        plan, directory = selection

        self._set_campaign_running(True)
        self.resultsSummary.setText(f"Results: running campaign in {directory}")
        thread = QThread(self)
        worker = CampaignRunWorker(plan, directory, self._get_magboltz_executable())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_campaign_run_progress)
        worker.finished.connect(self._on_campaign_run_finished)
        worker.cancelled.connect(self._on_campaign_run_cancelled)
        worker.failed.connect(self._on_campaign_run_failed)
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_campaign_worker)
        self._campaign_thread = thread
        self._campaign_worker = worker
        thread.start()

    def cancel_campaign(self) -> None:
        if self._campaign_worker is None:
            return
        self._campaign_worker.cancel()
        self.btnCancel.setEnabled(False)
        self.progressBar.setFormat("Stopping campaign...")
        self.resultsSummary.setText("Results: stopping campaign")

    def _on_campaign_run_progress(self, completed: int, total: int, run_id: str) -> None:
        self.progressBar.setMaximum(max(total, 1))
        self.progressBar.setValue(completed)
        self.progressBar.setFormat(f"Completed {completed}/{total}: {run_id}")
        self.resultsSummary.setText(f"Results: running campaign ({completed}/{total})")

    def _on_campaign_run_finished(self, plan: CampaignPlan, directory: Path, results) -> None:
        runs = self._generate_runs(plan)
        self._populate_preview(runs, plan)
        self._populate_results_from_execution(results, directory)
        ok_count = sum(result.ok for result in results)
        failed_count = len(results) - ok_count
        self._show_info(
            "Campaign run finished",
            f"Executed {len(results)} runs in:\n{directory}\n\nOK: {ok_count}\nFailed: {failed_count}",
        )

    def _on_campaign_run_cancelled(self, _plan: CampaignPlan, directory: Path, results) -> None:
        self._populate_results_from_execution(results, directory)
        self.progressBar.setFormat(f"Campaign stopped after {len(results)} runs")
        self._show_info("Campaign stopped", f"Stopped campaign in:\n{directory}\n\nCompleted runs: {len(results)}")

    def _on_campaign_run_failed(self, title: str, message: str) -> None:
        self._show_error(title, message)

    def _clear_campaign_worker(self) -> None:
        self._campaign_thread = None
        self._campaign_worker = None
        self._set_campaign_running(False)

    def _set_campaign_running(self, running: bool) -> None:
        if running:
            self.progressBar.setMaximum(0)
            self.progressBar.setValue(0)
            self.progressBar.setFormat("Starting campaign...")
        else:
            self.progressBar.setMaximum(max(self.progressBar.maximum(), 1))
            self.progressBar.setValue(self.progressBar.maximum())
            self.progressBar.setFormat("Campaign idle")
        self.btnRun.setEnabled(not running)
        self.btnGenerate.setEnabled(not running)
        self.btnOpen.setEnabled(not running)
        self.btnPreview.setEnabled(not running)
        self.btnCancel.setEnabled(running)
        self.sweepTable.setEnabled(not running)

    def _select_output_directory(self, title: str) -> tuple[CampaignPlan, Path] | None:
        try:
            plan = self._build_plan()
        except Exception as exc:
            self._show_error("Invalid campaign", str(exc))
            return None
        total_runs = _campaign_size(plan)
        if total_runs >= LARGE_CAMPAIGN_RUNS and not self._confirm_large_generate(plan, total_runs):
            return None

        directory = QFileDialog.getExistingDirectory(self, title)
        if not directory:
            return None
        return plan, Path(directory)

    def _load_campaign(self, directory: Path) -> CampaignPlan:
        manifest_path = directory / "campaign.json"
        if not manifest_path.is_file():
            raise ValueError(f"Missing campaign manifest:\n{manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        base_input = manifest.get("base_input")
        if not isinstance(base_input, str) or not base_input:
            raise ValueError("Campaign manifest does not declare base_input")
        base_path = directory / base_input
        if not base_path.is_file():
            raise ValueError(f"Missing base input card:\n{base_path}")

        base_cards = parser.load(base_path)
        self._base_cards = deepcopy(base_cards)
        if self._set_current_cards is not None:
            self._set_current_cards(deepcopy(base_cards))
        self._load_sweep_rows(manifest)
        return CampaignPlan(base_cards=base_cards, parameters=self._read_parameters())

    def _refresh_executable_label(self) -> None:
        executable = self._get_magboltz_executable()
        self.executableLabel.setText(f"Magboltz executable: {executable}")
        self.executableLabel.setToolTip(
            "Executable used by Run campaign. It matches the main Magboltz command path."
        )

    def refresh_executable(self) -> None:
        """Refresh the displayed executable after preferences change."""
        self._refresh_executable_label()

    def _load_sweep_rows(self, manifest: dict) -> None:
        sweeps = manifest.get("sweeps")
        if not isinstance(sweeps, list) or not sweeps:
            raise ValueError("Campaign manifest does not contain sweep rows")
        self.sweepTable.setRowCount(0)
        for sweep in sweeps:
            if not isinstance(sweep, dict):
                raise ValueError("Campaign manifest contains an invalid sweep row")
            parameter_path = _required_manifest_string(sweep, "path")
            sweep_type = _required_manifest_string(sweep, "sweep_type")
            mode = SweepMode(_required_manifest_string(sweep, "mode"))
            label = sweep.get("label") or ""
            if sweep_type == "values":
                values = _format_manifest_values(sweep.get("values"))
                stop = ""
                points = str(sweep.get("points", ""))
            elif sweep_type in {"linear", "logspace"}:
                values = str(sweep.get("start", ""))
                stop = str(sweep.get("stop", ""))
                points = str(sweep.get("points", ""))
            else:
                raise ValueError(f"Unsupported sweep type in manifest: {sweep_type}")
            self.add_sweep_row(
                parameter_path=parameter_path,
                sweep_type=sweep_type,
                values=values,
                stop=stop,
                points=points,
                label=str(label),
                mode=mode,
            )

    def _generate_runs(self, plan: CampaignPlan):
        from magboltz_gui.campaign import generate_runs

        return generate_runs(plan)

    def _confirm_large_generate(self, plan: CampaignPlan, total_runs: int) -> bool:
        response = QMessageBox.question(
            self,
            "Generate large campaign?",
            (
                f"This campaign will generate {total_runs} input-card directories.\n\n"
                f"{_matrix_summary_text(plan)}\n\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

    def _build_plan(self) -> CampaignPlan:
        self.use_current_input()
        if self._base_cards is None:
            raise ValueError("No input card selected")
        parameters = self._read_parameters()
        return CampaignPlan(base_cards=self._base_cards, parameters=parameters)

    def _read_parameters(self) -> list[SweepParameter]:
        parameters: list[SweepParameter] = []
        errors: list[str] = []
        coupled_rows: list[tuple[int, str, int]] = []
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
                errors.append(f"Row {row + 1}: internal sweep controls are incomplete")
                continue

            path = str(parameter_combo.currentData())
            mode = SweepMode(str(mode_combo.currentData()))
            sweep_type = sweep_combo.currentText()
            values = self._cell_text(row, 4)
            start = self._cell_text(row, 5)
            stop = self._cell_text(row, 6)
            points = self._cell_text(row, 7)
            label = self._cell_text(row, 8) or None
            row_context = f"Row {row + 1} ({parameter_combo.currentText()})"

            try:
                if sweep_type == "values":
                    sweep = ExplicitSweep(_parse_values(values))
                elif sweep_type == "linear":
                    sweep = LinearSweep(
                        _required_float(start, "Start"),
                        _required_float(stop, "Stop"),
                        _required_points(points),
                    )
                elif sweep_type == "logspace":
                    start_value = _required_float(start, "Start")
                    stop_value = _required_float(stop, "Stop")
                    if start_value <= 0 or stop_value <= 0:
                        raise ValueError("Start and Stop must be positive for logspace sweeps")
                    sweep = LogSweep(start_value, stop_value, _required_points(points))
                else:
                    raise ValueError(f"Unsupported sweep type: {sweep_type}")
            except ValueError as exc:
                errors.append(f"{row_context}: {exc}")
                continue

            parameters.append(SweepParameter(path=path, sweep=sweep, label=label, mode=mode))
            if mode == SweepMode.COUPLED:
                display_label = label or parameter_combo.currentText()
                coupled_rows.append((row + 1, display_label, len(sweep.values())))

        if not parameters:
            errors.append("Add at least one enabled sweep parameter")
        if len(coupled_rows) == 1:
            row_number, label, _points = coupled_rows[0]
            errors.append(f"Row {row_number} ({label}): Coupled mode requires at least two enabled coupled rows")
        coupled_point_counts = {points for _row, _label, points in coupled_rows}
        if len(coupled_point_counts) > 1:
            details = ", ".join(f"row {row} {label}={points}" for row, label, points in coupled_rows)
            errors.append(f"Coupled rows must have the same number of points ({details})")
        if errors:
            raise ValueError("Fix campaign sweep rows:\n- " + "\n- ".join(errors))
        return parameters

    def _cell_text(self, row: int, column: int) -> str:
        item = self.sweepTable.item(row, column)
        return item.text().strip() if item is not None else ""

    def _populate_preview(self, runs, plan: CampaignPlan) -> None:
        labels = list(runs[0].parameter_values) if runs else []
        visible_runs = runs[:PREVIEW_ROW_LIMIT]
        self.previewTable.setColumnCount(1 + len(labels))
        self.previewTable.setHorizontalHeaderLabels(["run_id", *labels])
        self.previewTable.setRowCount(len(visible_runs))
        for row, run in enumerate(visible_runs):
            self.previewTable.setItem(row, 0, QTableWidgetItem(run.run_id))
            for column, label in enumerate(labels, start=1):
                self.previewTable.setItem(row, column, QTableWidgetItem(str(run.parameter_values[label])))
        self.previewSummary.setText(_preview_summary_text(len(runs), len(visible_runs)))
        self.matrixSummary.setText(_matrix_summary_text(plan))

    def _clear_results(self, summary: str = "Results: not run") -> None:
        self.resultsSummary.setText(summary)
        self.resultsTable.setColumnCount(0)
        self.resultsTable.setRowCount(0)

    def _populate_results_from_execution(self, results, directory: Path) -> None:
        summary_rows = _read_csv_dicts(directory / "summary.csv")
        status_by_run = {}
        for index, result in enumerate(results):
            run_id = getattr(result, "run_id", "")
            if not run_id and index < len(summary_rows):
                run_id = summary_rows[index].get("run_id", "")
            if not run_id:
                continue
            status_by_run[run_id] = {
                "status": "done" if result.ok else "failed",
                "returncode": str(getattr(result, "returncode", "")),
                "stdout": getattr(result, "stdout_path", directory / run_id / "stdout.txt").as_posix(),
                "stderr": getattr(result, "stderr_path", directory / run_id / "stderr.txt").as_posix(),
            }
        self._populate_results_table(summary_rows, status_by_run, directory)

    def _populate_results_from_directory(self, directory: Path) -> None:
        summary_rows = _read_csv_dicts(directory / "summary.csv")
        if not summary_rows:
            self._clear_results("Results: no summary.csv found")
            return
        status_rows = _read_csv_dicts(directory / "run_status.csv")
        status_by_run = {row.get("run_id", ""): row for row in status_rows if row.get("run_id")}
        self._populate_results_table(summary_rows, status_by_run, directory)

    def _populate_results_table(
        self,
        summary_rows: list[dict[str, str]],
        status_by_run: dict[str, dict[str, str]],
        directory: Path,
    ) -> None:
        if not summary_rows:
            self._clear_results("Results: no runs")
            return
        parameter_columns = [column for column in summary_rows[0] if column != "run_id"]
        columns = [
            "run_id",
            "status",
            "returncode",
            *parameter_columns,
            "vz_um_ns",
            "mean_energy_eV",
            "stdout",
            "stderr",
        ]
        self.resultsTable.setColumnCount(len(columns))
        self.resultsTable.setHorizontalHeaderLabels(columns)
        self.resultsTable.setRowCount(len(summary_rows))

        ok_count = 0
        failed_count = 0
        pending_count = 0
        for row_index, summary in enumerate(summary_rows):
            run_id = summary.get("run_id", "")
            status_row = status_by_run.get(run_id, {})
            status = status_row.get("status") or _infer_run_status(directory, run_id)
            if status == "done":
                ok_count += 1
            elif status == "failed":
                failed_count += 1
            else:
                pending_count += 1

            stdout_path = _result_path(directory, status_row.get("stdout"), run_id, "stdout.txt")
            stderr_path = _result_path(directory, status_row.get("stderr"), run_id, "stderr.txt")
            parsed = _parse_result_values(stdout_path, _result_path(directory, None, run_id, "input.in"))
            values = {
                "run_id": run_id,
                "status": status,
                "returncode": status_row.get("returncode", ""),
                **{column: summary.get(column, "") for column in parameter_columns},
                "vz_um_ns": parsed.get("vz_um_ns", ""),
                "mean_energy_eV": parsed.get("mean_energy_eV", ""),
                "stdout": stdout_path.as_posix() if stdout_path.is_file() else "",
                "stderr": stderr_path.as_posix() if stderr_path.is_file() else "",
            }
            for column_index, column in enumerate(columns):
                self.resultsTable.setItem(row_index, column_index, QTableWidgetItem(str(values[column])))

        self.resultsSummary.setText(
            f"Results: {len(summary_rows)} runs; done: {ok_count}; failed: {failed_count}; pending: {pending_count}"
        )


def _parse_values(text: str) -> list[float | int | bool | str]:
    tokens = _value_tokens(text)
    if not tokens:
        raise ValueError("Explicit sweep values cannot be empty")
    values: list[float | int | bool | str] = []
    for token in tokens:
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


def _value_tokens(text: str) -> list[str]:
    return [value.strip() for value in text.replace("\n", ",").split(",") if value.strip()]


def _required_float(text: str, field_name: str) -> float:
    if not text:
        raise ValueError(f"{field_name} is required")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


def _required_points(text: str) -> int:
    if not text:
        raise ValueError("Points is required")
    try:
        points = int(text)
    except ValueError as exc:
        raise ValueError("Points must be an integer") from exc
    if points < 2:
        raise ValueError("Points must be at least 2")
    return points


def _required_manifest_string(mapping: dict, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Campaign manifest sweep row is missing `{key}`")
    return value


def _format_manifest_values(values: object) -> str:
    if not isinstance(values, list):
        raise ValueError("Campaign manifest values sweep is missing `values`")
    return ", ".join(str(value) for value in values)


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _result_path(directory: Path, raw_path: str | None, run_id: str, filename: str) -> Path:
    if raw_path:
        path = Path(raw_path)
        return path if path.is_absolute() else directory / path
    return directory / run_id / filename


def _infer_run_status(directory: Path, run_id: str) -> str:
    run_dir = directory / run_id
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    if stdout_path.is_file() or stderr_path.is_file():
        return "done"
    if run_dir.is_dir():
        return "pending"
    return "missing"


def _parse_result_values(stdout_path: Path, input_path: Path) -> dict[str, str]:
    if not stdout_path.is_file():
        return {}
    try:
        stdout_text = stdout_path.read_text(encoding="utf-8")
        input_text = input_path.read_text(encoding="utf-8") if input_path.is_file() else None
        result = parse_magboltz_output(stdout_text, input_text=input_text, input_path=input_path.as_posix())
    except Exception:
        return {}

    values: dict[str, str] = {}
    if result.transport.vz_um_ns is not None and result.transport.vz_um_ns.v_um_ns is not None:
        values["vz_um_ns"] = str(result.transport.vz_um_ns.v_um_ns)
    if result.transport.mean_electron_energy_eV is not None:
        values["mean_energy_eV"] = str(result.transport.mean_electron_energy_eV)
    return values


def _is_gas_fraction_path(path: str) -> bool:
    return path.startswith("gases[") and path.endswith("].gas_frac")


def _preview_summary_text(total_runs: int, visible_runs: int) -> str:
    text = f"Runs: {total_runs}"
    if visible_runs < total_runs:
        text += f" (showing first {visible_runs})"
    if total_runs >= LARGE_CAMPAIGN_RUNS:
        text += " - large campaign"
    return text


def _matrix_summary_text(plan: CampaignPlan) -> str:
    independent = [parameter for parameter in plan.parameters if parameter.mode == SweepMode.PRODUCT]
    coupled = [parameter for parameter in plan.parameters if parameter.mode == SweepMode.COUPLED]
    product_size = _product_size([len(parameter.sweep.values()) for parameter in independent])
    coupled_size = len(coupled[0].sweep.values()) if coupled else 1
    total_size = product_size * coupled_size
    parts = [
        f"Independent rows: {len(independent)}",
        f"product size: {product_size}",
        f"coupled rows: {len(coupled)}",
        f"coupled size: {coupled_size}",
        f"total: {total_size}",
    ]
    if total_size >= LARGE_CAMPAIGN_RUNS:
        parts.append("warning: review before generating")
    return "; ".join(parts)


def _campaign_size(plan: CampaignPlan) -> int:
    return _product_size([len(parameter.sweep.values()) for parameter in plan.parameters if parameter.mode == SweepMode.PRODUCT]) * _coupled_size(plan)


def _coupled_size(plan: CampaignPlan) -> int:
    coupled = [parameter for parameter in plan.parameters if parameter.mode == SweepMode.COUPLED]
    return len(coupled[0].sweep.values()) if coupled else 1


def _product_size(sizes: list[int]) -> int:
    total = 1
    for size in sizes:
        total *= size
    return total


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
