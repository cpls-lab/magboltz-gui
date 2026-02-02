"""
Module entry point: allows `python -m magboltz_gui` to launch the GUI.
Keeps the same behavior as the console script `magboltz-gui`.
"""

from magboltz_gui.util.platform import ensure_qt_runtime_or_explain
from magboltz_gui import main as _main


def run() -> None:
    ensure_qt_runtime_or_explain()
    _main.main()


if __name__ == "__main__":
    run()
