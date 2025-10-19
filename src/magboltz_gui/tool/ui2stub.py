#!/usr/bin/env python3
"""
ui2stub.py — Generate a .pyi typing stub from a Qt Designer .ui file (Qt6 / PyQt6)

Usage:
    python ui2stub.py path/to/mainwindow.ui
    # -> writes path/to/mainwindow.pyi (or use -o to change)

Place the .pyi next to the generated ui_*.py, or keep stubs in a typings/ dir
and add `mypy_path = ["typings"]` in your mypy config.
"""
from __future__ import annotations
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Tuple, Callable

# Module names for PyQt6. Adjust to PySide6 by changing imports in emit_pyi().
WIDGETS_MOD = "QtWidgets"
GUI_MOD = "QtGui"
CORE_MOD = "QtCore"

# Fallbacks
WIDGET_FALLBACK = f"{WIDGETS_MOD}.QWidget"
LAYOUT_FALLBACK = f"{WIDGETS_MOD}.QLayout"
ACTION_TYPE = f"{GUI_MOD}.QAction"
SPACER_TYPE = f"{WIDGETS_MOD}.QSpacerItem"

# Heuristics: most Qt6 widgets live in QtWidgets; QAction in QtGui
WIDGET_PREFIXES: Tuple[str, ...] = (
    "QWidget",
    "QMainWindow",
    "QDialog",
    "QFrame",
    "QGroupBox",
    "QPushButton",
    "QToolButton",
    "QRadioButton",
    "QCheckBox",
    "QComboBox",
    "QLineEdit",
    "QTextEdit",
    "QPlainTextEdit",
    "QLabel",
    "QListView",
    "QListWidget",
    "QTreeView",
    "QTreeWidget",
    "QTableView",
    "QTableWidget",
    "QTabWidget",
    "QStackedWidget",
    "QScrollArea",
    "QProgressBar",
    "QSlider",
    "QSpinBox",
    "QDoubleSpinBox",
    "QDateEdit",
    "QTimeEdit",
    "QDateTimeEdit",
    "QCalendarWidget",
    "QMenuBar",
    "QMenu",
    "QStatusBar",
    "QToolBar",
    "QDockWidget",
    "QGraphicsView",
)
LAYOUT_PREFIXES: Tuple[str, ...] = ("QVBoxLayout", "QHBoxLayout", "QGridLayout", "QFormLayout")


def qt_qualname(qt_class: str) -> str:
    """Map a Qt class name to a qualified PyQt6 name."""
    if qt_class == "Line":
        return "QtWidgets.QFrame"  # ← special case for Designer's "Line"
    if qt_class.startswith(LAYOUT_PREFIXES):
        return f"{WIDGETS_MOD}.{qt_class}"
    if qt_class.startswith(WIDGET_PREFIXES):
        return f"{WIDGETS_MOD}.{qt_class}"
    if qt_class == "QAction":
        return ACTION_TYPE
    # Best effort default (most widgets are in QtWidgets for PyQt6)
    return f"{WIDGETS_MOD}.{qt_class}"


def parse_ui(ui_path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    """
    Return (ui_class_name, top_widget_qualified_type, attributes)
    attributes: list[(name, qualified_type)]
    """
    tree = ET.parse(ui_path)
    root = tree.getroot()
    ns_strip: Callable[[str], str] = lambda tag: tag.split("}")[-1]  # strip XML namespace if present

    # Ui class name: Ui_{<class>} (matches pyuic)
    form_name = root.findtext("class") or "Form"
    ui_class = f"Ui_{form_name}"

    # Top-level widget (QMainWindow/QDialog/QWidget…) -> setupUi signature
    top_widget = root.find("widget")
    top_qt_class = top_widget.get("class") if top_widget is not None else "QWidget"
    assert top_qt_class is not None
    top_param_type = qt_qualname(top_qt_class)

    attrs: List[Tuple[str, str]] = []

    # Traverse all elements and collect named things we want to expose
    for elem in root.iter():
        tag = ns_strip(elem.tag)

        if tag == "widget":
            name = elem.get("name")
            qt_class = elem.get("class")
            if name and qt_class:
                attrs.append((name, qt_qualname(qt_class)))

        elif tag == "layout":
            name = elem.get("name")
            qt_class = elem.get("class", "QLayout")
            if name:
                q = LAYOUT_FALLBACK if qt_class == "QLayout" else qt_qualname(qt_class)
                attrs.append((name, q))

        elif tag == "action":
            name = elem.get("name")
            if name:
                attrs.append((name, ACTION_TYPE))

        elif tag == "spacer":
            name = elem.get("name")
            if name:
                attrs.append((name, SPACER_TYPE))

    # De-duplicate by name, keep first occurrence
    seen = set()
    dedup: List[Tuple[str, str]] = []
    for name, typ in attrs:
        if name not in seen:
            seen.add(name)
            dedup.append((name, typ))

    return ui_class, top_param_type, dedup


def emit_pyi(ui_class: str, top_param_type: str, attrs: Iterable[Tuple[str, str]]) -> str:
    """Emit .pyi text for Ui_* class."""
    lines: List[str] = []
    lines.append("from typing import Any")
    lines.append("from PyQt6 import QtCore, QtGui, QtWidgets")
    lines.append("")
    lines.append(f"class {ui_class}:")
    if not attrs:
        lines.append("    def setupUi(self, widget: " + top_param_type + ") -> None: ...")
        lines.append("    def retranslateUi(self, widget: " + top_param_type + ") -> None: ...")
        return "\n".join(lines)

    # Sort attributes alphabetically for stable diffs
    for name, typ in sorted(attrs, key=lambda x: x[0]):
        lines.append(f"    {name}: {typ}")

    lines.append(f"    def setupUi(self, widget: {top_param_type}) -> None: ...")
    lines.append(f"    def retranslateUi(self, widget: {top_param_type}) -> None: ...")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a .pyi stub from a Qt .ui file (PyQt6).")
    ap.add_argument("ui", type=Path, help="Path to .ui file")
    ap.add_argument("-o", "--out", type=Path, help="Output .pyi path (default: next to .ui)")
    args = ap.parse_args()

    ui_class, top_param_type, attrs = parse_ui(args.ui)
    text = emit_pyi(ui_class, top_param_type, attrs)

    out = args.out or args.ui.with_suffix(".pyi")
    out.write_text(text, encoding="utf-8")
    print(f"[ui2stub] Wrote {out}")


if __name__ == "__main__":
    main()
