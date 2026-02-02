#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DESKTOP_SRC="$ROOT_DIR/src/magboltz_gui/icons/magboltz-gui.desktop"
ICON_SVG="$ROOT_DIR/src/magboltz_gui/icons/icon.svg"
ICON_PNG="$ROOT_DIR/src/magboltz_gui/icons/icon-192x192.png"

APPS_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor"

mkdir -p "$APPS_DIR"
mkdir -p "$ICON_DIR/scalable/apps"
mkdir -p "$ICON_DIR/192x192/apps"

cp "$DESKTOP_SRC" "$APPS_DIR/magboltz-gui.desktop"

if [[ -f "$ICON_SVG" ]]; then
  cp "$ICON_SVG" "$ICON_DIR/scalable/apps/magboltz-gui.svg"
fi

if [[ -f "$ICON_PNG" ]]; then
  cp "$ICON_PNG" "$ICON_DIR/192x192/apps/magboltz-gui.png"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$ICON_DIR" >/dev/null || true
fi

echo "Installed desktop entry to $APPS_DIR/magboltz-gui.desktop"
echo "Installed icons under $ICON_DIR"
