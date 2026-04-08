GUI Layer
=========

The Qt layer lives in ``magboltz_gui.window`` and is documented here as a
design overview rather than a full autodoc dump.

Main windows and dialogs
------------------------

``main_window.py``
  Owns the central application state, wires actions to handlers, loads the gas
  database, and coordinates save/run/export/plot workflows.

``export_window.py``
  Presents export formats and options, then collects the parameters used by the
  export controller.

``plots_window.py``
  Builds the result visualisations from a parsed ``RunResult`` using
  matplotlib-backed canvases inside Qt tabs.

``search_window.py``
  Implements gas selection/search support for the mixture editor.

Supporting widgets
------------------

``delegates.py``
  Table-item delegates for gas names and numeric mixture values.

``gas_pie_widget.py``
  Pie-chart widget used to visualise the mixture composition.

Generated UI code
-----------------

The ``.ui`` files under ``src/magboltz_gui/ui`` are the editable source of
truth for the Qt forms. Python bindings are generated from them during
development and consumed by the window classes at runtime.
