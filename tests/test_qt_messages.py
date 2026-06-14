"""Tests for Qt message filtering."""

from magboltz_gui.util.qt_messages import _is_noisy_qt_message


def test_qt_message_filter_matches_known_qt6ct_noise() -> None:
    assert _is_noisy_qt_message("QFont::fromString: Invalid description '(empty)'")
    assert _is_noisy_qt_message(
        "virtual const QPalette* Qt6CTPlatformTheme::palette(QPlatformTheme::Palette) const QPlatformTheme::SystemPalette"
    )
    assert _is_noisy_qt_message("virtual QVariant Qt6CTPlatformTheme::themeHint(QPlatformTheme::ThemeHint) const")


def test_qt_message_filter_keeps_unknown_messages() -> None:
    assert not _is_noisy_qt_message("QPixmap: Must construct a QGuiApplication before a QPixmap")
