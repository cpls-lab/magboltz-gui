from pathlib import Path
from typing import Optional, List

from PyQt6 import uic
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView

from magboltz_gui.database import GasDatabase
from magboltz_gui.input_cards import InputCards, InputGas
from magboltz_gui import parser
from magboltz_gui.delegates import PercentDelegate, GasNameDelegate


class MagboltzGUI(QMainWindow):

    def __init__(self: 'MagboltzGUI') -> None:
        super().__init__()
        uic.loadUi("magboltz_gui/ui/main.ui", self)

        self.centralWidget().setVisible(False)

        self._currentCards: Optional[InputCards] = None
        self._currentFile: Optional[Path] = None
        self._currentModified : bool = False

        self.actionNew.triggered.connect(self.new)
        self.actionOpen.triggered.connect(self.open)
        self.actionSave.triggered.connect(self.save)
        self.actionSaveAs.triggered.connect(self.saveAs)
        self.actionClose.triggered.connect(self.close)

        self.btnGasAdd.setDefaultAction(self.actionGasAdd)
        self.btnGasRemove.setDefaultAction(self.actionGasRemove)

        # Make "Gas name" stretch to fill available space
        header = self.gasListTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Gas ID shrinks to content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Gas name fills extra space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Gas fraction shrinks to content

        header.setMinimumSectionSize(50)

        self.database = GasDatabase()
        self.database.load("magboltz_gui/database.csv")


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


    def save(self) -> None:
        if self._currentCards is None:
            self.show_error("File was not open")
            return

        if self._currentFile is None:
            self.saveAs()
        else:
            parser.save(self._currentCards, self._currentFile)
            self._currentModified = False

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

            self.disconnect()

    def show_error(self, message: str) -> None:
        msg_box = QMessageBox.critical(self, "Error", message, QMessageBox.StandardButton.Ok)
        msg_box.setMinimumSize(400, 200)

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
        self.spinFinalEnergy.setValue(self._currentCards.final_energy)
        self.checkFinalEnergyAuto.setChecked(self._currentCards.final_energy == 0.)
        self.spinGasTemperature.setValue(self._currentCards.gas_temperature)
        self.spinGasPressure.setValue(self._currentCards.gas_pressure)
        self.spinElectricField.setValue(self._currentCards.electric_field)
        self.spinMagneticField.setValue(self._currentCards.magnetic_field)
        self.spinAngle.setValue(self._currentCards.angle)

        self.spinRealInteractions.valueChanged.connect(self.onRealInteractionsChanged)
        self.spinFinalEnergy.valueChanged.connect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.connect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.connect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.connect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.connect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.connect(self.onAngleChanged)

        gas_name_delegate = GasNameDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(1, gas_name_delegate)

        delegate = PercentDelegate(self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(2, delegate)

        self.refresh()

        self.btnGasAdd.triggered.connect(self.onBtnGasAdd)
        self.btnGasRemove.triggered.connect(self.onBtnGasRemove)
        self.btnGasNormalize.triggered.connect(self.onBtnGasNormalize)


    def refresh(self):
        self.gasListTable.clear()

        self.gasListTable.setHorizontalHeaderLabels(["Gas ID", "Gas name", "Gas fraction"])

        self.gasListTable.verticalHeader().setVisible(False)
        self.gasListTable.setShowGrid(False)

        i = 0
        for gas in self._currentCards.gases:
            gas_id_widget = QTableWidgetItem(str(gas.gas_id))
            gas_id_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            try:
                gas_name = self.database.get(gas.gas_id).pretty_name
            except KeyError:
                gas_name = '(select gas)'
            gas_name_widget = QTableWidgetItem(gas_name)

            gas_frac_widget = QTableWidgetItem(f"{gas.gas_frac} %")
            gas_frac_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

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
            self._currentCards.gases.remove(row)
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

    def onFinalEnergyChanged(self, value: float) -> None:
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
        self.spinFinalEnergy.valueChanged.disconnect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.disconnect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.disconnect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.disconnect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.disconnect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.disconnect(self.onAngleChanged)

        self.btnGasAdd.triggered.disconnect(self.onBtnGasAdd)

        self.gasListTableView.setModel(None)