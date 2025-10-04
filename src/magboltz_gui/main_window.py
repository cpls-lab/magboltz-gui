import platform
from importlib.resources import files
from os import POSIX_SPAWN_CLOSE
from pathlib import Path
from typing import Optional, List

from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt, QProcess
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView, QTableWidget, \
    QApplication

from magboltz_gui.database import GasDatabase
from magboltz_gui.input_cards import InputCards, InputGas
from magboltz_gui import parser
from magboltz_gui.delegates import PercentDelegate, GasNameDelegate
from magboltz_gui.process import ProcessManager


class MagboltzGUI(QMainWindow):

    def __init__(self: 'MagboltzGUI') -> None:
        super().__init__()
        uic.loadUi(files("magboltz_gui.ui").joinpath("main.ui"), self)

        system = platform.system()
        if system == "Darwin":
            self.initDarwinActionIcons()

        self.centralWidget().setVisible(False)

        self._currentCards: Optional[InputCards] = None
        self._currentFile: Optional[Path] = None
        self._currentModified : bool = False

        self.actionNew.triggered.connect(self.new)
        self.actionOpen.triggered.connect(self.open)
        self.actionSave.triggered.connect(self.save)
        self.actionSaveAs.triggered.connect(self.saveAs)
        self.actionClose.triggered.connect(self.close)
        self.actionRun.triggered.connect(self.run)


        self.btnGasAdd.setDefaultAction(self.actionGasAdd)
        self.btnGasRemove.setDefaultAction(self.actionGasRemove)

        self.btnCopyToClipbord.clicked.connect(self.copyToClipboard)

        self.mainTab.setCurrentWidget(self.tabConfiguration)


        # Make "Gas name" stretch to fill available space
        header = self.gasListTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Gas ID shrinks to content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Gas name fills extra space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Gas fraction shrinks to content

        header.setMinimumSectionSize(50)

        self.database = GasDatabase()
        self.database.load(files("magboltz_gui.data").joinpath("database.csv"))

        self.magboltzPath : Optional[Path] = None
        self.processes: List[ProcessManager] = []


    def initDarwinActionIcons(self):
        # This method set the icons for MacOS

        action_list : List[QAction] = [
            self.actionNew	,
            self.actionOpen	          ,
            self.actionSave           ,
            self.actionSaveAs         ,
            self.actionRevert         ,
            self.actionClose          ,
            self.actionQuit	          ,
            self.actionRun	          ,
            self.actionGasAdd	      ,
            self.actionGasRemove	  ,
            self.actionactionNormalize,
        ]

        icns_map = {
            "document-new": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/NewDocumentIcon.icns",
            "document-open": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/GenericDocumentIcon.icns",
            "document-save": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/SaveDocumentIcon.icns",
            "document-save-as": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/SaveAsTemplateIcon.icns",
            "document-revert": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/UndoIcon.icns",
            "edit-delete": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/TrashIcon.icns",
            "application-exit": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AlertStopIcon.icns",
            "system-run": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ExecutableBinaryIcon.icns",
            "list-add": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/AddIcon.icns",
            "list-remove": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/RemoveIcon.icns",
            "accessories-calculator": "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/CalculatorIcon.icns",
        }

        for action in action_list:

            name = action.icon().name()
            icon = icns_map.get(name, None)

            if icon is not None:
                if Path(icon).is_file():
                    QIcon(icon)



    def new(self):
        self._currentCards = InputCards()
        self._currentCards = InputCards()
        self._currentFile = None
        self._currentModified = False
        self.connect()


    def open(self) -> None:

        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")

        if file_name:  # If user picked a file (not Cancel)
            self._currentCards = parser.load(Path(file_name))
            self._currentFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()
            self.connect()

    def saveAs(self) -> None:

        if self._currentCards is None:
            self.show_error("File was not open")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", str(self._currentFile) if self._currentFile else "input.txt", "All Files (*);;Text Files (*.txt)")

        if file_name:
            parser.save(self._currentCards, Path(file_name))
            self._currentFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()


    def save(self) -> None:
        if self._currentCards is None:
            self.show_error("File was not open")
            return

        if self._currentFile is None:
            self.saveAs()
        else:
            parser.save(self._currentCards, self._currentFile)
            self._currentModified = False
            self.updateCmdLine()


    def close(self):
        if self._currentCards is not None:

            response = self.show_save_question()

            if response is None:
                return

            if response == True:
                self.save()

            self._currentCards = None
            self._currentFile = None
            self._currentModified = False

            self.updateCmdLine()
            self.disconnect()

    def copyToClipboard(self) -> None:
        QApplication.clipboard().setText(self.commandLine.text())

    def run(self):

        if self._currentCards is None:
            self.show_error("To run the magboltz process, you must to open the input file")
            return

        if self._currentFile is None:
            self.show_error("To run the magboltz process, you must to save the file")
            return

        if self._currentModified is False:
            self.save()

        self.mainTab.setCurrentWidget(self.tabExecution)

        process = ProcessManager(self)
        self.processes.append(process)
        process.run()


    def updateCmdLine(self):

        if self._currentFile is not None:
            self.commandLine.setText(f"{self.magboltzPath or 'magboltz'} < {self._currentFile}")
        else:
            self.commandLine.setText("")

    def onFinalEnergyAutoChanged(self, state: int) -> None:
        print("aaa")
        if state == Qt.CheckState.Checked.value:
            self.spinFinalEnergy.setValue(0.)
        else:
            self.spinFinalEnergy.setValue(50.)


    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message, QMessageBox.StandardButton.Ok)


    def show_save_question(self) -> Optional[bool]:
        reply = QMessageBox.question(
            self,
            "Save Changes?",
            "Do you want to save changes before closing?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            return True
        elif reply == QMessageBox.StandardButton.No:
            return False
        else:
            return None

    def connect(self):

        assert self._currentCards is not None

        self.centralWidget().setVisible(True)

        self.spinRealInteractions.setValue(self._currentCards.number_of_real_collisions)
        self.checkPenning.setChecked(self._currentCards.enable_penning)
        self.checkThermal.setChecked(self._currentCards.enable_thermal)
        self.spinFinalEnergy.setValue(self._currentCards.final_energy)
        self.checkFinalEnergyAuto.setChecked(self._currentCards.final_energy == 0.)
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

        gas_name_delegate = GasNameDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(1, gas_name_delegate)

        delegate = PercentDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(2, delegate)

        self.refresh()

        self.btnGasAdd.triggered.connect(self.onBtnGasAdd)
        self.btnGasRemove.triggered.connect(self.onBtnGasRemove)
        self.btnGasNormalize.triggered.connect(self.onBtnGasNormalize)


    def refresh(self):
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
                gas_name = '(select gas)'
            gas_name_widget = QTableWidgetItem(gas_name)

            gas_frac_widget = QTableWidgetItem(f"{gas.gas_frac} %")
            gas_frac_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.gasListTable.insertRow(i)
            self.gasListTable.setItem(i, 0, gas_id_widget)
            self.gasListTable.setItem(i, 1, gas_name_widget)
            self.gasListTable.setItem(i, 2, gas_frac_widget)
            i += 1




    def onBtnGasAdd(self):
        row_index = self.gasListTable.rowCount()
        self.gasListTable.insertRow(row_index)
        self._currentCards.gases.append(InputGas(80, 0.))
        self.refresh()

    def onBtnGasRemove(self):
        row = self.gasListTable.currentRow()

        if row >= 0:
            self._currentCards.gases.pop(row)
            self.refresh()
        else:
            self.show_error('Select a row to remove')

    def onBtnGasNormalize(self):
        fraction_sum = 0.
        for gas in self._currentCards.gases:
            fraction_sum += gas.gas_frac

        if fraction_sum > 0.:

            for gas in self._currentCards.gases:
                gas.gas_frac *= 100. / fraction_sum

            self.refresh()
        else:

            QMessageBox.warning(
                self,  # Parent
                "Warning",  # Title
                "Please set the gas fractions."  # Message
            )



    def onRealInteractionsChanged(self, value: int) -> None:
        self._currentCards.number_of_real_collisions = value

    def onPenningChanged(self, value: bool) -> None:
        self._currentCards.enable_penning = value

    def onThermalChanged(self, value: bool) -> None:
        self._currentCards.enable_thermal = value
        
    def onFinalEnergyChanged(self, value: float) -> None:
        self.checkFinalEnergyAuto.setChecked(value == 0.)
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

    def disconnect(self):

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

        self.btnGasAdd.triggered.disconnect(self.onBtnGasAdd)
        self.btnGasRemove.triggered.disconnect(self.onBtnGasRemove)
        self.btnGasNormalize.triggered.disconnect(self.onBtnGasNormalize)
        


        self.gasListTable.clear()