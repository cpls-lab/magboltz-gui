from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QComboBox, QStyledItemDelegate, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QVariant

from magboltz_gui.input_cards import InputGas
from magboltz_gui.search_widget import SearchWidget


# 🌟 Custom Table Model
class GasListModel(QAbstractTableModel):
    def __init__(self, data, headers, combo_items):
        super().__init__()
        self._data = data  # List of [str, float] rows
        self._headers = headers
        self._combo_items = combo_items

    def rowCount(self, parent=None):

        if parent and parent.isValid():
            return 0

        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()

        row, col = index.row(), index.column()

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if row >= 0 and row < len(self._data):
                data_row : InputGas = self._data[row]
                if col == 0:
                    return data_row.gas_id
                elif col == 1:
                    return data_row.gas_frac

        return QVariant()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        row, col = index.row(), index.column()

        # if col == 0 and value in self._combo_items:
        #     self._data[row][col] = value
        # elif col == 1 and isinstance(value, float):
        #     self._data[row][col] = max(0.0, min(100.0, value))
        # else:
        #     return False

        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index):
       return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)


class GasNameDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        # Create your custom SearchWidget
        editor = SearchWidget(parent)
        # Connect editor's valueSelected signal to commit data
        editor.valueSelected.connect(self.commitAndCloseEditor)
        return editor

    def setEditorData(self, editor, index):
        # Get current gas name from model and set it
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setValue(str(value))

    def setModelData(self, editor, model, index):
        # Get selected gas name from editor and update model
        value = editor.getValue()
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def commitAndCloseEditor(self):
        editor = self.sender()
        if editor:
            self.commitData.emit(editor)
            self.closeEditor.emit(editor)


# 🌟 Delegate for SpinBox (column 1)
class GasFracSpinBoxDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setRange(0.0, 100.0)
        editor.setSuffix(" %")
        editor.setDecimals(2)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.setValue(float(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.ItemDataRole.EditRole)
