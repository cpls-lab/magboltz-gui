"""
Icon theme helper for Linux.

Why
---
- When using system Qt with platform themes like qt6ct, Qt may not pick up the
  desktop icon theme automatically, causing themed icons (document-open, etc.)
  to appear blank.
- We add a lightweight fallback that keeps user overrides intact and only acts
  if no themed icons are found.

Behavior
--------
- Linux-only.
- Does nothing if any standard theme icon is already available.
- Otherwise, sets theme search paths to include common system icon dirs plus
  our package icons, and picks a sensible default theme (Adwaita) if present.
"""

from __future__ import annotations

import sys
from pathlib import Path
from importlib.resources import files
from typing import Iterable

from PyQt6.QtGui import QIcon


def _probe_has_theme_icons(names: Iterable[str]) -> bool:
    return any(QIcon.hasThemeIcon(name) for name in names)


def ensure_icon_theme() -> None:
    if not sys.platform.startswith("linux"):
        return

    probe = ("document-new", "document-open", "document-save", "edit-delete", "go-up")
    if _probe_has_theme_icons(probe):
        return

    # Build search paths, preserving existing ones.
    paths = list(dict.fromkeys(QIcon.themeSearchPaths()))  # de-duplicate, preserve order
    for p in ("/usr/share/icons", "/usr/local/share/icons", str(files("magboltz_gui.icons"))):
        if p not in paths:
            paths.append(p)
    QIcon.setThemeSearchPaths(paths)

    if Path("/usr/share/icons/Adwaita").is_dir():
        QIcon.setThemeName("Adwaita")
