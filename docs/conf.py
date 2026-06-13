"""Sphinx configuration for Magboltz-GUI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

project = "Magboltz-GUI"
author = "Michele Renda, Dan Andrei Ciubotaru"
release = "0.3.1"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True

autodoc_mock_imports = [
    "PyQt6",
    "matplotlib",
]

html_theme = "alabaster"
