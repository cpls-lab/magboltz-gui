"""Tests for Qt styling heuristics."""

from __future__ import annotations

import sys

from magboltz_gui.util import qt_style


def test_platform_theme_candidates_avoid_platform_theme_on_gnome(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    monkeypatch.delenv("XDG_SESSION_DESKTOP", raising=False)

    assert qt_style._platform_theme_candidates() == ()


def test_platform_theme_candidates_keep_qt6ct_off_gnome(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.delenv("XDG_SESSION_DESKTOP", raising=False)

    assert qt_style._platform_theme_candidates() == ("qt6ct", "gtk3")


def test_platform_theme_env_respects_user_choice(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("QT_QPA_PLATFORMTHEME", "qt6ct")
    monkeypatch.setattr(qt_style, "_detect_platform_theme_plugin", lambda: "gtk3")

    qt_style.set_linux_platform_theme_env_if_available()

    assert qt_style.os.environ["QT_QPA_PLATFORMTHEME"] == "qt6ct"
