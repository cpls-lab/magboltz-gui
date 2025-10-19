from importlib.resources import files

import sys

from magboltz_gui.util.platform import ensure_qt_runtime_or_explain


def main() -> None:

    ensure_qt_runtime_or_explain()

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from magboltz_gui.window.main_window import MagboltzGUI

    app: QApplication = QApplication(sys.argv)
    app.setApplicationName("Magboltz GUI")
    app.setOrganizationName("CERN")
    # IMPORTANT for Wayland/GNOME: this sets the app-id from a desktop file name
    app.setDesktopFileName(str(files("magboltz_gui.icons").joinpath("magboltz-gui.desktop")))
    app.setWindowIcon(QIcon(str(files("magboltz_gui.icons").joinpath("icon-192x192.png"))))
    window: MagboltzGUI = MagboltzGUI()
    window.setWindowFlag(Qt.WindowType.Window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":

    # Checking if we have QT available
    ensure_qt_runtime_or_explain()

    main()
