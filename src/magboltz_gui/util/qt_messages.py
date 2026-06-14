"""Qt message filtering for known third-party platform-theme noise."""

from __future__ import annotations

import os
import sys


_NOISY_QT_PREFIXES = (
    "QFont::fromString: Invalid description '(empty)'",
    "virtual const QPalette* Qt6CTPlatformTheme::palette(",
    "virtual QVariant Qt6CTPlatformTheme::themeHint(",
)


def install_qt_message_filter() -> None:
    """Suppress known harmless Qt/qt6ct stderr noise while preserving other messages."""
    if os.environ.get("MAGBOLTZ_GUI_SHOW_QT_NOISE"):
        return

    from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

    def handler(mode: QtMsgType, _context, message: str) -> None:
        if _is_noisy_qt_message(message):
            return
        print(message, file=sys.stderr)
        if mode == QtMsgType.QtFatalMsg:
            raise SystemExit(1)

    qInstallMessageHandler(handler)


def _is_noisy_qt_message(message: str) -> bool:
    return any(message.startswith(prefix) for prefix in _NOISY_QT_PREFIXES)
