Workflow
========

Startup
-------

``magboltz_gui.main`` is the application entry point. It prepares platform
theme hints on Linux, creates the ``QApplication``, sets the desktop identity
and icon, and finally instantiates the main window.

Editing inputs
--------------

The main window works around an ``InputCards`` object that mirrors the subset
of Magboltz cards exposed by the GUI. The gas table combines:

- a numeric gas identifier
- a user-facing gas name from the bundled CSV catalogue
- a fraction that is normalised on save

Running Magboltz
----------------

``ProcessManager`` is responsible for starting ``magboltz``, feeding the input
file to stdin, and streaming stdout/stderr back into the console pane. When the
process finishes, the buffered stdout is handed to
``parse_magboltz_output``.

Parsing and export
------------------

The parser builds a ``RunResult`` object containing:

- run metadata and original input
- conditions and control flags
- mixture composition
- drift, diffusion, and collision-frequency summaries
- tabular sections such as convergence rows and energy distributions
- raw stdout plus parser warnings

The export dialog then selects one view of that structure and dispatches to the
CSV, JSON, or XML export functions.

Plotting
--------

The plot window uses the parsed ``RunResult`` rather than reparsing text or
calling Magboltz again. This keeps plotting and export consistent with the same
parsed representation of the run.
