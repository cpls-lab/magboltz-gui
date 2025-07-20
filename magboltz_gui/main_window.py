from pathlib import Path
from typing import Optional, List

from PyQt6 import uic
from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox

from magboltz_gui.input_cards import InputCards, Gas, InputGas
from magboltz_gui import parser
from magboltz_gui.main_model import GasListModel, GasFracSpinBoxDelegate, GasNameDelegate

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


        self.allGases : List[Gas] = [
            Gas(1, 'CF4', year=2015, rating=5),
            Gas(2, 'ARGON', year=2014, rating=5),
            Gas(3, 'HELIUM 4', year=2014, rating=5),
        ]

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

        self.gasListModel = GasListModel(self._currentCards.gases, ['Gas name', 'Fraction'], self.allGases)
        self.gasListTableView.setModel(self.gasListModel)

        # Set delegates
        self.gasListTableView.setItemDelegateForColumn(0, GasNameDelegate())
        self.gasListTableView.setItemDelegateForColumn(1, GasFracSpinBoxDelegate())

        self.btnGasAdd.triggered.connect(self.onBtnGasAdd)
        self.btnGasRemove.triggered.connect(self.onBtnGasRemove)



    def onBtnGasAdd(self):
        row = len(self._currentCards.gases)
        self.gasListModel.beginInsertRows(QModelIndex(), row, row)
        self._currentCards.gases.append(InputGas(80, 0.))
        self.gasListModel.endInsertRows()

    def onBtnGasRemove(self):
        row = len(self._currentCards.gases) - 1
        #self._currentCards.gases.append(InputGas(80, 0.))
        self.gasListModel.endInsertRows()

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