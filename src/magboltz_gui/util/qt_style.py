"""
Linux Qt styling helper.

Why this exists
---------------
- On GNOME/Wayland with system PyQt6, Qt may not find a platform theme plugin and
  falls back to the bare "Fusion" style, making widgets look disabled/flat.
- Users can fix it via env vars (QT_QPA_PLATFORMTHEME/QT_STYLE_OVERRIDE), but we
  add a light-touch, auto-detect fallback so the app looks usable out of the box.

Principles
----------
- Never override user choices: if env vars are already set, do nothing.
- Only set a platform theme if the matching plugin is actually present.
- Prefer gtk3 on GNOME. Avoid auto-selecting qt6ct on GNOME because an
  unconfigured qt6ct setup can emit noisy palette/font diagnostics on stderr.
- After QApplication is created, nudge the style away from Fusion if a better
  style is available.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _detect_platform_theme_plugin() -> Optional[str]:
    """
    Return a platform theme plugin key we can set via QT_QPA_PLATFORMTHEME, or None.
    Best-effort: if detection fails, return None.
    """
    try:
        from PyQt6.QtCore import QLibraryInfo

        plug_dir = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)) / "platformthemes"
    except Exception:
        return None

    candidates = _platform_theme_candidates()
    for cand in candidates:
        if any(cand in p.name.lower() for p in plug_dir.glob("libq*.so")):
            return cand
    return None


def _is_gnome_desktop() -> bool:
    current = os.environ.get("XDG_CURRENT_DESKTOP", "")
    session = os.environ.get("XDG_SESSION_DESKTOP", "")
    return "gnome" in f"{current}:{session}".lower()


def _platform_theme_candidates() -> tuple[str, ...]:
    if _is_gnome_desktop():
        return ("gtk3",)
    return ("qt6ct", "gtk3")


def set_linux_platform_theme_env_if_available() -> None:
    """
    If on Linux and the user hasn't set QT_QPA_PLATFORMTHEME, set it to a detected
    platform theme plugin when available.
    """
    if not sys.platform.startswith("linux"):
        return
    if "QT_QPA_PLATFORMTHEME" in os.environ:
        return

    cand = _detect_platform_theme_plugin()
    if cand:
        os.environ["QT_QPA_PLATFORMTHEME"] = cand


def apply_linux_style_fallback(app: object) -> None:
    """
    If on Linux and the user hasn't set QT_STYLE_OVERRIDE, try to pick a better
    style than Fusion when available.
    """
    from PyQt6.QtWidgets import QStyleFactory

    if not sys.platform.startswith("linux"):
        return
    if "QT_STYLE_OVERRIDE" in os.environ:
        return

    style_now = app.style().objectName().lower()
    if style_now != "fusion":
        print(f"[magboltz-gui] Qt style remains: {style_now}", file=sys.stderr)
        return

    available = [s.lower() for s in QStyleFactory.keys()]
    for candidate in ("adwaita", "breeze"):
        if candidate in available and candidate != style_now:
            app.setStyle(candidate)
            print(f"[magboltz-gui] Qt style fallback: {style_now} -> {candidate}", file=sys.stderr)
            break
    else:
        print(f"[magboltz-gui] Qt style remains: {style_now}", file=sys.stderr)
