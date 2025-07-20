import os

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import Qt
from typing import Any, Optional
import sys

from magboltz_gui.main_window import MagboltzGUI


def main() -> None:
    from PyQt6 import QtWidgets
    QtWidgets.QApplication.setStyle("Fusion")

    os.environ.pop('QT_QPA_PLATFORMTHEME', None)

    app: QApplication = QApplication(sys.argv)
    window: MagboltzGUI = MagboltzGUI()
    window.setWindowFlag(Qt.WindowType.Window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
