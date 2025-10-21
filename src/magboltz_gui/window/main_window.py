from __future__ import annotations
import platform
from importlib.resources import files
from pathlib import Path
from typing import Optional, List

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
    QApplication,
    QVBoxLayout,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from magboltz_gui.data.database import GasDatabase
from magboltz_gui.data.input_cards import InputCards, InputGas
from magboltz_gui.generated.ui_main import Ui_MainWindow
from magboltz_gui.util import parser
from magboltz_gui.window.delegates import PercentDelegate, GasNameDelegate
from magboltz_gui.util.process import ProcessManager


class MagboltzGUI(QMainWindow, Ui_MainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        # uic.loadUi(files("magboltz_gui.ui").joinpath("main.ui"), self) <- Not needed anymore because we use pyuic6

        system = platform.system()
        if system == "Darwin":
            self.initDarwinActionIcons()

        self.centralWidget().setVisible(False)

        self._currentInputFile: Optional[Path] = None
        self._currentResultFile: Optional[Path] = None

        self._currentCards: InputCards = InputCards()
        self._currentModified: bool = False

        self.actionNew.triggered.connect(self.fileNew)
        self.actionOpen.triggered.connect(self.fileOpen)
        self.actionSave.triggered.connect(self.fileSave)
        self.actionSaveAs.triggered.connect(self.fileSaveAs)
        self.actionClose.triggered.connect(self.fileClose)
        self.actionRun.triggered.connect(self.run)
        self.actionGasAdd.triggered.connect(self.gasAdd)
        self.actionGasRemove.triggered.connect(self.gasRemove)
        self.actionGasNormalize.triggered.connect(self.gasNormalize)
        self.actionCmdCopyToClipboard.triggered.connect(self.cmdCopyToClipboard)
        self.actionResultSave.triggered.connect(self.saveResult)
        self.actionResultExport.triggered.connect(self.openExportWindow)

        self.btnGasAdd.setDefaultAction(self.actionGasAdd)
        self.btnGasRemove.setDefaultAction(self.actionGasRemove)
        self.btnGasNormalize.setDefaultAction(self.actionGasNormalize)

        self.btnCmdCopyToClipbord.setDefaultAction(self.actionCmdCopyToClipboard)
        self.btnResultSave.setDefaultAction(self.actionResultSave)
        self.btnResultExport.setDefaultAction(self.actionResultExport)

        self.mainTab.setCurrentWidget(self.tabConfiguration)

        self.createPieChart()

        # Make "Gas name" stretch to fill available space
        header = self.gasListTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Gas ID shrinks to content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Gas name fills extra space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Gas fraction shrinks to content

        header.setMinimumSectionSize(50)

        self.database = GasDatabase()
        self.database.load(Path(str(files("magboltz_gui.database").joinpath("database.csv"))))

        self.magboltzPath: Optional[Path] = None
        self.processes: List[ProcessManager] = []

    def createPieChart(self) -> None:
        fig = Figure(figsize=(3, 3))
        canvas = FigureCanvasQTAgg(fig)  # type:ignore

        # 2. Create an Axes and draw something (pie chart)
        ax = fig.add_subplot(111)
        ax.pie([], labels=[], autopct="%1.1f%%")

        # 3. Add the canvas to the QWidget container
        layout = QVBoxLayout(self.pieContainer)
        layout.setContentsMargins(0, 0, 0, 0)  # remove spacing
        layout.addWidget(canvas)

        self._gas_fig = fig
        self._gas_ax = ax
        self._gas_canvas = canvas

        self.splitterGases.setSizes([600, 200])

    def initDarwinActionIcons(self) -> None:
        # This method set the icons for macOS

        actions: List[QAction] = [
            self.actionNew,
            self.actionOpen,
            self.actionSave,
            self.actionSaveAs,
            self.actionRevert,
            self.actionClose,
            self.actionQuit,
            self.actionRun,
            self.actionGasAdd,
            self.actionGasRemove,
            self.actionGasNormalize,
            self.actionCmdCopyToClipboard,
            self.actionResultExport,
        ]

        icns_map = {
            self.actionNew: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/NewDocumentIcon.icns",
            self.actionOpen: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericDocumentIcon.icns",
            self.actionSave: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/SaveDocumentIcon.icns",
            self.actionSaveAs: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/SaveAsTemplateIcon.icns",
            self.actionRevert: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/UndoIcon.icns",
            self.actionClose: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/TrashIcon.icns",
            self.actionQuit: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AlertStopIcon.icns",
            self.actionRun: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ExecutableBinaryIcon.icns",
            self.actionGasAdd: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AddIcon.icns",
            self.actionGasRemove: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/RemoveIcon.icns",
            self.actionGasNormalize: "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/CalculatorIcon.icns",
            self.actionCmdCopyToClipboard: "",
            self.actionResultExport: "",  # find an incon similary to Excel
        }

        for action in actions:
            icon = icns_map.get(action, None)
            if icon is not None:
                if Path(icon).is_file():
                    action.setIcon(QIcon(icon))

    def fileNew(self) -> None:
        self._currentCards = InputCards()
        self._currentCards = InputCards()
        self._currentInputFile = None
        self._currentModified = False
        self._currentResultFile = None
        self.connect()

    def fileOpen(self) -> None:

        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")

        if file_name:  # If user picked a file (not Cancel)
            self._currentCards = parser.load(Path(file_name))
            self._currentInputFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()
            self.connect()

    def fileSaveAs(self) -> None:

        if not self.checkInputOpen():
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            str(self._currentInputFile) if self._currentInputFile else "input.txt",
            "All Files (*);;Text Files (*.txt)",
        )

        if file_name:
            parser.save(self._currentCards, Path(file_name))
            self._currentInputFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()

    def fileSave(self) -> None:
        if not self.checkInputOpen():
            return

        if self._currentInputFile is None:
            self.fileSaveAs()
        else:
            parser.save(self._currentCards, self._currentInputFile)
            self._currentModified = False
            self.updateCmdLine()

    def fileClose(self) -> None:
        if self._currentCards is not None:

            response = self.show_save_question()

            if response is None:
                return

            if response == True:
                self.fileSave()

            self._currentInputFile = None
            self._currentResultFile = None

            self._currentCards = InputCards()
            self._currentModified = False

            self.updateCmdLine()
            self.disconnect()

    def cmdCopyToClipboard(self) -> None:
        QApplication.clipboard().setText(self.commandLine.text())

    def checkInputOpen(self) -> bool:
        if self._currentCards is None:
            self.show_error("Error", "File was not open")
            return False
        return True

    def saveResult(self) -> None:

        if not self.checkInputOpen():
            return

        if not self.consoleOutput.toPlainText().strip():
            self.show_info("File Saved", f"First run Magboltz to save the results")

            return

        currentResultFileName, _ = QFileDialog.getSaveFileName(
            self,
            "Save Result",
            str(self._currentResultFile) if self._currentResultFile else "output.txt",
            "All Files (*);;Text Files (*.txt)",
        )

        if currentResultFileName is not None:

            currentResultFile = Path(currentResultFileName)

            text = self.consoleOutput.toPlainText()

            try:
                with open(currentResultFile, "w", encoding="utf-8") as file:
                    file.write(text)
            except Exception as e:
                self.show_error("Error", f"Could not save result: {e}")

            else:
                self.show_info("Success", f"File saved successfully:\n{currentResultFile}")
                self._currentResultFile = currentResultFile

    def openExportWindow(self) -> None:
        print("Test Test")

    def run(self) -> None:

        if self._currentCards is None:
            self.show_error("To run the magboltz process, you must to open the input file")
            return

        if self._currentInputFile is None:
            self.show_error("Error", "To run the magboltz process, you must to save the file")
            return

        if self._currentModified is False:
            self.fileSave()

        self.mainTab.setCurrentWidget(self.tabExecution)

        process = ProcessManager(self)
        self.processes.append(process)
        process.run()

    def updateCmdLine(self) -> None:

        if self._currentInputFile is not None:
            self.commandLine.setText(f"{self.magboltzPath or 'magboltz'} < {self._currentInputFile}")
        else:
            self.commandLine.setText("")

    def onFinalEnergyAutoChanged(self, state: int) -> None:
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            self.spinFinalEnergy.setValue(0.0)
        else:
            self.spinFinalEnergy.setValue(50.0)

    def show_error(
        self,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:
        self.show_message(QMessageBox.Icon.Critical, title, message, buttons, default)

    def show_info(
        self,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:
        self.show_message(QMessageBox.Icon.Information, title, message, buttons, default)

    def show_message(
        self,
        icon: QMessageBox.Icon,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:

        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(message)

        # Buttons
        msg.setStandardButtons(buttons)
        if default is not None:
            msg.setDefaultButton(default)

        # Resize automatically based on content
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.adjustSize()

        # Center relative to parent window
        parent_geom = self.geometry()
        msg_geom = msg.frameGeometry()

        x = parent_geom.center().x() - msg_geom.width() // 2
        y = parent_geom.center().y() - msg_geom.height() // 2
        msg.move(x, y)

        msg.exec()

    def show_save_question(self) -> Optional[bool]:
        reply = QMessageBox.question(
            self,
            "Save Changes?",
            "Do you want to save changes before closing?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            return True
        elif reply == QMessageBox.StandardButton.No:
            return False
        else:
            return None

    def connect(self) -> None:

        self.centralWidget().setVisible(True)

        self.spinRealInteractions.setValue(self._currentCards.number_of_real_collisions)
        self.checkPenning.setChecked(self._currentCards.enable_penning)
        self.checkThermal.setChecked(self._currentCards.enable_thermal)
        self.spinFinalEnergy.setValue(self._currentCards.final_energy)
        self.checkFinalEnergyAuto.setChecked(self._currentCards.final_energy == 0.0)
        self.spinGasTemperature.setValue(self._currentCards.gas_temperature)
        self.spinGasPressure.setValue(self._currentCards.gas_pressure)
        self.spinElectricField.setValue(self._currentCards.electric_field)
        self.spinMagneticField.setValue(self._currentCards.magnetic_field)
        self.spinAngle.setValue(self._currentCards.angle)

        self.spinRealInteractions.valueChanged.connect(self.onRealInteractionsChanged)
        self.checkPenning.stateChanged.connect(self.onPenningChanged)
        self.checkThermal.stateChanged.connect(self.onThermalChanged)
        self.checkFinalEnergyAuto.stateChanged.connect(self.onFinalEnergyAutoChanged)
        self.spinFinalEnergy.valueChanged.connect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.connect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.connect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.connect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.connect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.connect(self.onAngleChanged)

        self.gasListTable.cellChanged.connect(self.refresh_pie)

        gas_name_delegate = GasNameDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(1, gas_name_delegate)

        delegate = PercentDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(2, delegate)

        self.refresh()

        # self.btnGasAdd.triggered.connect(self.onBtnGasAdd)
        # self.btnGasRemove.triggered.connect(self.onBtnGasRemove)
        # self.btnGasNormalize.triggered.connect(self.onBtnGasNormalize)
        # self.btnExport.triggered.connect(self.onBtnExport)

    def refresh_pie(self) -> None:

        self._gas_ax.clear()

        gas_fracs = []
        gas_labels = []

        for gas in self._currentCards.gases:
            try:
                gas_name = self.database.get(gas.gas_id).short_name
            except KeyError:
                gas_name = "?"

            gas_fracs.append(gas.gas_frac)
            gas_labels.append(gas_name)

        if sum(gas_fracs) > 0:
            self._gas_ax.pie(gas_fracs, labels=gas_labels, autopct="%1.1f%%")
        else:
            self._gas_ax.pie(
                [],
                labels=[],
                autopct="%1.1f%%",
                wedgeprops={"edgecolor": "black", "linewidth": 1},
            )
        self._gas_ax.set_aspect("equal")
        self._gas_canvas.draw()  # type:ignore

    def refresh(self) -> None:

        self.gasListTable.clear()
        self.gasListTable.setRowCount(0)

        self.gasListTable.setHorizontalHeaderLabels(["Gas ID", "Gas name", "Gas fraction"])

        self.gasListTable.verticalHeader().setVisible(False)
        self.gasListTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.gasListTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.gasListTable.setShowGrid(False)

        i = 0
        for gas in self._currentCards.gases:
            gas_id_widget = QTableWidgetItem(str(gas.gas_id))
            gas_id_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            gas_id_widget.setFlags(gas_id_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)

            try:
                gas_name = self.database.get(gas.gas_id).pretty_name
            except KeyError:
                gas_name = "(select gas)"

            gas_name_widget = QTableWidgetItem(gas_name)

            gas_frac_widget = QTableWidgetItem(f"{gas.gas_frac} %")
            gas_frac_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.gasListTable.insertRow(i)
            self.gasListTable.setItem(i, 0, gas_id_widget)
            self.gasListTable.setItem(i, 1, gas_name_widget)
            self.gasListTable.setItem(i, 2, gas_frac_widget)
            i += 1

        self.refresh_pie()

    def gasAdd(self) -> None:

        row_index = self.gasListTable.rowCount()
        self.gasListTable.insertRow(row_index)
        self._currentCards.gases.append(InputGas(80, 0.0))
        self.refresh()

    def gasRemove(self) -> None:
        row = self.gasListTable.currentRow()

        if row >= 0:
            self._currentCards.gases.pop(row)
            self.refresh()
        else:
            self.show_error("Error", "Select a row to remove")

    def gasNormalize(self) -> None:
        fraction_sum = 0.0
        for gas in self._currentCards.gases:
            fraction_sum += gas.gas_frac

        if fraction_sum > 0.0:

            for gas in self._currentCards.gases:
                gas.gas_frac *= round(100.0 / fraction_sum, 1)

            self.refresh()
        else:
            # Split evenly
            for gas in self._currentCards.gases:
                gas.gas_frac = round(100.0 / len(self._currentCards.gases), 1)

    def onRealInteractionsChanged(self, value: int) -> None:

        self._currentCards.number_of_real_collisions = value

    def onPenningChanged(self, value: bool) -> None:

        self._currentCards.enable_penning = value

    def onThermalChanged(self, value: bool) -> None:

        self._currentCards.enable_thermal = value

    def onFinalEnergyChanged(self, value: float) -> None:

        self.checkFinalEnergyAuto.setChecked(value == 0.0)
        self._currentCards.final_energy = value

    def onGasTemperatureChanged(self, value: float) -> None:

        self._currentCards.gas_temperature = value

    def onGasPressureChanged(self, value: float) -> None:

        self._currentCards.gas_pressure = value

    def onElectricFieldChanged(self, value: float) -> None:

        self._currentCards.electric_field = value

    def onMagneticFieldChanged(self, value: float) -> None:

        self._currentCards.magnetic_field = value

    def onAngleChanged(self, value: float) -> None:

        self._currentCards.angle = value

    def disconnect(self) -> None:

        self.centralWidget().setVisible(False)

        self.spinRealInteractions.valueChanged.disconnect(self.onRealInteractionsChanged)
        self.checkPenning.stateChanged.disconnect(self.onPenningChanged)
        self.checkThermal.stateChanged.disconnect(self.onThermalChanged)
        self.checkFinalEnergyAuto.stateChanged.disconnect(self.onFinalEnergyAutoChanged)
        self.spinFinalEnergy.valueChanged.disconnect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.disconnect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.disconnect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.disconnect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.disconnect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.disconnect(self.onAngleChanged)

        # self.btnGasAdd.triggered.disconnect(self.onBtnGasAdd)
        # self.btnGasRemove.triggered.disconnect(self.onBtnGasRemove)
        # self.btnGasNormalize.triggered.disconnect(self.onBtnGasNormalize)
        # self.btnExport.triggered.disconnect(self.onBtnExport)

        self.gasListTable.clear()
