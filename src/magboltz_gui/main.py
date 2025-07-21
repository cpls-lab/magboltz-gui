import os
from importlib.resources import files

from PyQt6 import uic
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import Qt
from typing import Any, Optional
import sys

from src.magboltz_gui.main_window import MagboltzGUI

def main() -> None:
    app: QApplication = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(files("magboltz_gui.icons").joinpath("icon-192x192.png"))))
    window: MagboltzGUI = MagboltzGUI()
    window.setWindowFlag(Qt.WindowType.Window)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
