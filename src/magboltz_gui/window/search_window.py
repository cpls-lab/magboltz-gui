from importlib.resources import files
from typing import Optional

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QHeaderView, QTableWidget, QMessageBox, QWidget

from magboltz_gui.data.database import GasDatabase
from magboltz_gui.generated.ui_search import Ui_SearchGasForm


class SearchWindow(QDialog, Ui_SearchGasForm):

    def __init__(self, database: GasDatabase, parent: Optional[QWidget] = None) -> None:

        super().__init__(parent)
        self.database = database

        self.setupUi(self)
        # uic.loadUi(files("magboltz_gui.ui").joinpath("search.ui"), self) <- Not needed anymore because we use pyuic6

        self._selected_gas_id: int = 0

        self.dialogButtons.accepted.connect(self.onAccept)
        self.dialogButtons.rejected.connect(self.reject)

        self.searchResultTable.cellDoubleClicked.connect(self.onAccept)
        self.searchResultTable.itemSelectionChanged.connect(self.onSelectedRowChanged)
        self.searchBarText.textChanged.connect(self.refresh)

        self.refresh(self.searchBarText.text())
        self.onSelectedRowChanged()

    def onSelectedRowChanged(self) -> None:

        row = self.searchResultTable.currentRow()
        if row != -1:
            gas_id = int(self.searchResultTable.item(row, 0).text())
            gas = self.database.get(gas_id)
            self.label_year.setText(str(gas.year) if gas.year is not None else "-")
            self.label_rating.setText(f"{'★' * gas.rating}{'☆' * (5 - gas.rating)}" if gas.rating is not None else "-")
            self.label_note.setText(gas.note if gas.note is not None else "")
        else:
            self.label_year.setText("")
            self.label_rating.setText("")
            self.label_note.setText("")

    def onAccept(self) -> None:

        row = self.searchResultTable.currentRow()

        if row != -1:
            id_item = self.searchResultTable.item(row, 0)
            if id_item:
                self._selected_gas_id = int(id_item.text())
                self.accept()
                return

        QMessageBox.warning(self, "No Selection", "Please select a row first.")  # Parent  # Title  # Message

    def refresh(self, search: str) -> None:

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
        self.searchResultTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.searchResultTable.setShowGrid(False)

        gas_filtered = []

        s = search.strip().lower()

        for gas in self.database.content:
            # This is the most inefficient search algorithm possible
            if (
                str(gas.id) == s
                or s in str(gas.name.lower())
                or (gas.formula is not None and s in gas.formula.lower())
                or (gas.year is not None and str(gas.year) == s)
                or (gas.note is not None and s in gas.note.lower())
            ):
                gas_filtered.append(gas)

        self.searchResultTable.setRowCount(len(gas_filtered))

        i = 0
        for gas in gas_filtered:

            widget_id = QTableWidgetItem(str(gas.id))
            widget_id.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            widget_name = QTableWidgetItem(gas.name)

            widget_formula = QTableWidgetItem(gas.formula or "")

            widget_id.setFlags(widget_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget_name.setFlags(widget_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget_formula.setFlags(widget_formula.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.searchResultTable.setItem(i, 0, widget_id)
            self.searchResultTable.setItem(i, 1, widget_name)
            self.searchResultTable.setItem(i, 2, widget_formula)

            i += 1

    def setCurrentGasId(self, gas_id: int) -> None:
        self._selected_gas_id = gas_id

    def getSelectedGasId(self) -> int:
        return self._selected_gas_id

    def accept(self) -> None:
        super().accept()
