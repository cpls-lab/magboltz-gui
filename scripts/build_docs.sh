#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 -m sphinx -b html \
  "${ROOT}/docs" \
  "${ROOT}/docs/_build/html"
