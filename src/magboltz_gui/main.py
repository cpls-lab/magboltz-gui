"""Qt application entry point for Magboltz-GUI."""

from __future__ import annotations

import os
import signal
import sys
from importlib.resources import files
from typing import Any

from magboltz_gui.util.platform import ensure_qt_runtime_or_explain
from magboltz_gui.util.qt_style import (
    apply_linux_style_fallback,
    set_linux_platform_theme_env_if_available,
)
from magboltz_gui.util.qt_messages import install_qt_message_filter
from magboltz_gui.util.icon_theme import ensure_icon_theme


def main() -> None:
    """Create the application, show the main window, and enter the event loop."""

    # Best-effort platform theme/style setup (Linux) without overriding user choices.
    set_linux_platform_theme_env_if_available()
    install_qt_message_filter()

    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QTimer
    from magboltz_gui.window.main_window import MagboltzGUI

    app: QApplication = QApplication(sys.argv)

    apply_linux_style_fallback(app)
    ensure_icon_theme()

    app.setApplicationName("Magboltz GUI")
    app.setOrganizationName("CERN")
    # IMPORTANT for Wayland/GNOME: this sets the app-id from a desktop file name
    app.setDesktopFileName(str(files("magboltz_gui.icons").joinpath("magboltz-gui.desktop")))
    # Prefer SVG app icon; keep PNG as fallback.
    app_icon_svg = files("magboltz_gui.icons").joinpath("icon.svg")
    app_icon_png = files("magboltz_gui.icons").joinpath("icon-192x192.png")
    if app_icon_svg.is_file():
        app.setWindowIcon(QIcon(str(app_icon_svg)))
    elif app_icon_png.is_file():
        app.setWindowIcon(QIcon(str(app_icon_png)))

    signal.signal(signal.SIGINT, _sigint_handler)

    _keep_alive = QTimer()
    _keep_alive.timeout.connect(lambda: None)
    _keep_alive.start(200)

    window: MagboltzGUI = MagboltzGUI()
    window.setWindowFlag(Qt.WindowType.Window)
    window.show()
    sys.exit(app.exec())


def _sigint_handler(*_: Any) -> None:
    """Terminate the Qt application cleanly on Ctrl-C."""
    from PyQt6.QtWidgets import QApplication

    QApplication.quit()
    sys.exit(130)


if __name__ == "__main__":

    # Checking if we have QT available
    ensure_qt_runtime_or_explain()

    main()
