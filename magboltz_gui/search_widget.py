from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QDialog, QTableWidgetItem, QHeaderView, QTableWidget, QMessageBox

from magboltz_gui.database import GasDatabase


class SearchWidget(QDialog):

    def __init__(self, database : GasDatabase, parent=None):
        super().__init__(parent)
        self.database = database

        uic.loadUi("magboltz_gui/ui/search.ui", self)

        self._selected_gas_id : int = 0

        self.dialogButtons.accepted.connect(self.onAccept)
        self.dialogButtons.rejected.connect(self.reject)

        self.searchResultTable.cellDoubleClicked.connect(self.onAccept)
        self.searchBarText.textChanged.connect(self.refresh)

        self.refresh(self.searchBarText.text())

    def onAccept(self):

        row = self.searchResultTable.currentRow()

        if row != -1:
            id_item = self.searchResultTable.item(row, 0)  # Get the item in column 0 (ID column)
            if id_item:
                self._selected_gas_id = int(id_item.text())
                self.accept()
                return

        QMessageBox.warning(
            self,  # Parent
            "No Selection",  # Title
            "Please select a row first."  # Message
        )


    def refresh(self, search: str):

        self.searchResultTable.clear()

        self.searchResultTable.setColumnCount(3)

        self.searchResultTable.setHorizontalHeaderLabels(["ID", "Name", "Formula"])

        # Make "Gas name" stretch to fill available space
        header = self.searchResultTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.searchResultTable.verticalHeader().setVisible(False)
        self.searchResultTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.searchResultTable.setShowGrid(False)

        gas_filtered = []

        s = search.strip().lower()

        for gas in self.database.content:
            # This is the most inefficient search algorithm possible
            if (str(gas.id) == s or s in str(gas.name.lower()) or
                    (gas.formula is not None and s in gas.formula.lower()) or
                    (gas.year is not None and str(gas.year) == s) or
                    (gas.note is not None and s in gas.note.lower())):
                gas_filtered.append(gas)

        self.searchResultTable.setRowCount(len(gas_filtered))

        i  = 0
        for gas in gas_filtered:

            widget_id = QTableWidgetItem(str(gas.id))
            widget_id.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            widget_name = QTableWidgetItem(gas.name)

            widget_formula = QTableWidgetItem(gas.formula)

            widget_id.setFlags(widget_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget_name.setFlags(widget_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget_formula.setFlags(widget_formula.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.searchResultTable.setItem(i, 0, widget_id)
            self.searchResultTable.setItem(i, 1, widget_name)
            self.searchResultTable.setItem(i, 2, widget_formula)

            i += 1

    def setCurrentGasId(self, gas_id : int ) -> int:
        self._selected_gas_id = gas_id

    def getSelectedGasId(self) -> int:
        return self._selected_gas_id

    def accept(self):
        super().accept()