#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

rm -rf dist/ build/

python3 -m pip install --upgrade build twine
python3 -m build

echo ""
echo "Build complete. Files are in dist/"
echo "Run 'python3 -m twine check dist/*' to verify metadata."
