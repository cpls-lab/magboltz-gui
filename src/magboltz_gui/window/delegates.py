from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from typing_extensions import override


from PyQt6.QtCore import Qt, QModelIndex, QAbstractItemModel, QEvent
from PyQt6.QtWidgets import QDoubleSpinBox, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableWidget

from magboltz_gui.window.search_window import SearchWindow

if TYPE_CHECKING:
    from magboltz_gui.window.main_window import MagboltzGUI


class PercentSpinBox(QDoubleSpinBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSuffix(" %")
        self.setDecimals(1)
        self.setRange(0, 100)
        self.setSingleStep(0.5)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)


class PercentDelegate(QStyledItemDelegate):

    def __init__(self, main_window: MagboltzGUI, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._main_window = main_window

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QDoubleSpinBox(parent)
        editor.setSuffix(" %")
        editor.setDecimals(1)
        editor.setRange(0, 100)
        editor.setSingleStep(0.5)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight)
        return editor

    @override
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        assert isinstance(editor, QDoubleSpinBox)
        text = index.model().data(index, Qt.ItemDataRole.EditRole)
        value = float(str(text).replace(" %", "").strip())
        editor.setValue(value)

    @override
    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex) -> None:
        assert isinstance(editor, QDoubleSpinBox)
        editor.interpretText()
        value = editor.value()
        model.setData(index, f"{value:.1f} %", Qt.ItemDataRole.EditRole)

        self._main_window._currentCards.gases[index.row()].gas_frac = value
        self._main_window.refresh()


class GasNameDelegate(QStyledItemDelegate):

    def __init__(self, main_window: MagboltzGUI, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._main_window = main_window

    @override
    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> QWidget:
        # DO NOT return an editor. We’ll use a popup instead.
        return QWidget(parent)

    @override
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        pass  # Not needed

    @override
    def setModelData(
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex,
    ) -> None:
        pass  # Not needed

    @override
    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        if event.type() == event.Type.MouseButtonDblClick:
            # Create and show the SearchWidget as a modal dialog
            search_dialog = SearchWindow(self._main_window.database)
            if search_dialog.exec():  # exec() returns QDialog.Accepted if OK pressed

                selected_gas_id = search_dialog.getSelectedGasId()
                # Update Gas ID column (assume column 0 for Gas ID)
                gas_id_index = index.siblingAtColumn(0)
                model.setData(gas_id_index, selected_gas_id, Qt.ItemDataRole.EditRole)

                self._main_window._currentCards.gases[index.row()].gas_id = selected_gas_id
                self._main_window.refresh()
            return True
        return False
