from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDoubleSpinBox, QStyledItemDelegate

from magboltz_gui.search_widget import SearchWidget


class PercentSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSuffix(" %")
        self.setDecimals(1)
        self.setRange(0, 100)
        self.setSingleStep(0.5)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)


class PercentDelegate(QStyledItemDelegate):

    def __init__(self, main_window: "MagbxoltzGUI", parent=None):
        super().__init__(parent)
        self._main_window = main_window

    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setSuffix(" %")
        editor.setDecimals(1)
        editor.setRange(0, 100)
        editor.setSingleStep(0.5)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.ItemDataRole.EditRole)
        value = float(str(text).replace(" %", "").strip())
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        editor.interpretText()
        value = editor.value()
        model.setData(index, f"{value:.1f} %", Qt.ItemDataRole.EditRole)

        self._main_window._currentCards.gases[index.row()].gas_frac = value
        self._main_window.refresh()

class GasNameDelegate(QStyledItemDelegate):

    def __init__(self, main_window: "MagbxoltzGUI", parent=None):
        super().__init__(parent)
        self._main_window = main_window

    def createEditor(self, parent, option, index):
        # DO NOT return an editor. We’ll use a popup instead.
        return None

    def setEditorData(self, editor, index):
        pass  # Not needed

    def setModelData(self, editor, model, index):
        pass  # Not needed

    def editorEvent(self, event, model, option, index):
        if event.type() == event.Type.MouseButtonDblClick:
            # Create and show the SearchWidget as a modal dialog
            search_dialog = SearchWidget(self._main_window.database)
            if search_dialog.exec():  # exec() returns QDialog.Accepted if OK pressed

                selected_gas_id = search_dialog.getSelectedGasId()
                # Update Gas ID column (assume column 0 for Gas ID)
                gas_id_index = index.siblingAtColumn(0)
                model.setData(gas_id_index, selected_gas_id, Qt.ItemDataRole.EditRole)

                self._main_window._currentCards.gases[index.row()].gas_id = selected_gas_id
                self._main_window.refresh()
            return True
        return False