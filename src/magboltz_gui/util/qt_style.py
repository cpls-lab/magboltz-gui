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
- Prefer qt6ct (good GNOME integration), then gtk3; otherwise leave defaults.
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
    Prefers qt6ct, then gtk3. Best-effort: if detection fails, return None.
    """
    try:
        from PyQt6.QtCore import QLibraryInfo

        plug_dir = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)) / "platformthemes"
    except Exception:
        return None

    candidates = ("qt6ct", "gtk3")
    for cand in candidates:
        if any(cand in p.name.lower() for p in plug_dir.glob("libq*.so")):
            return cand
    return None


def set_linux_platform_theme_env_if_available() -> None:
    """
    If on Linux and the user hasn't set QT_QPA_PLATFORMTHEME, set it to a detected
    platform theme plugin (qt6ct or gtk3) when available.
    """
    if not sys.platform.startswith("linux"):
        return
    if "QT_QPA_PLATFORMTHEME" in os.environ:
        return

    cand = _detect_platform_theme_plugin()
    if cand:
        os.environ["QT_QPA_PLATFORMTHEME"] = cand


def apply_linux_style_fallback(app) -> None:
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
    available = [s.lower() for s in QStyleFactory.keys()]
    for candidate in ("qt6ct-style", "gtk3", "fusion"):
        if candidate in available and candidate != style_now:
            app.setStyle(candidate)
            print(f"[magboltz-gui] Qt style fallback: {style_now} -> {candidate}", file=sys.stderr)
            break
    else:
        print(f"[magboltz-gui] Qt style remains: {style_now}", file=sys.stderr)
