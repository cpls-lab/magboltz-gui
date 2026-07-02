#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf dist/ build/

PYTHON_BIN="${PYTHON:-python3}"
if "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 1)'; then
  BUILD_PYTHON="$PYTHON_BIN"
else
  BUILD_VENV="${MAGBOLTZ_GUI_BUILD_VENV:-.build-venv}"
  "$PYTHON_BIN" -m venv "$BUILD_VENV"
  BUILD_PYTHON="$BUILD_VENV/bin/python"
fi

"$BUILD_PYTHON" -m pip install --upgrade build twine
"$BUILD_PYTHON" -m build

echo ""
echo "Build complete. Files are in dist/"
echo "Run '$BUILD_PYTHON -m twine check dist/*' to verify metadata."
