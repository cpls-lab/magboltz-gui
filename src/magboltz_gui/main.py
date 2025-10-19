import signal
from importlib.resources import files

import sys
from typing import Any

from PyQt6.QtCore import QTimer

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

    signal.signal(signal.SIGINT, _sigint_handler)

    _keep_alive = QTimer()
    _keep_alive.timeout.connect(lambda: None)
    _keep_alive.start(200)


    window: MagboltzGUI = MagboltzGUI()
    window.setWindowFlag(Qt.WindowType.Window)
    window.show()
    sys.exit(app.exec())


def _sigint_handler(*_ : Any) -> None:
    from PyQt6.QtWidgets import QApplication
    QApplication.quit()
    sys.exit(130)

if __name__ == "__main__":

    # Checking if we have QT available
    ensure_qt_runtime_or_explain()

    main()
