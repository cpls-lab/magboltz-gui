from PyQt6 import uic
from PyQt6.QtWidgets import QWidget


class SearchWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        uic.loadUi("magboltz_gui/ui/search.ui", self)
