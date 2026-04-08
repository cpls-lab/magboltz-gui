Overview
========

`Magboltz-GUI` wraps the existing `Magboltz` program in a desktop workflow that
is easier to approach than the traditional text-card interface.

The project is organised around one Python package in ``src/magboltz_gui``:

- ``data`` contains the local gas catalogue and the editable input-card model
- ``util`` contains parsers, runtime helpers, the run-result model, and export
  logic
- ``window`` contains the Qt dialogs and widgets that build the GUI
- ``tool`` contains developer helpers such as UI code generation

The most useful entry points for code readers are:

- ``magboltz_gui.main`` for application startup
- ``magboltz_gui.data.input_cards`` for the editable configuration model
- ``magboltz_gui.util.output_parser`` for stdout parsing
- ``magboltz_gui.util.export_controller`` for CSV/JSON/XML export
- ``magboltz_gui.window.main_window`` for the main application window
