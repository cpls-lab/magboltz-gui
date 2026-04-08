Architecture
============

The application follows a straightforward desktop workflow:

1. the main window edits an in-memory ``InputCards`` object
2. the current cards are written to a Magboltz input file
3. a ``QProcess`` runs ``magboltz`` and streams the input through stdin
4. the captured stdout is parsed into a ``RunResult`` structure
5. the result becomes available to export dialogs and plot windows

Main layers
-----------

Data model
~~~~~~~~~~

The data layer lives in ``magboltz_gui.data`` and contains two central pieces:

- ``GasDatabase`` for the bundled gas lookup table
- ``InputCards`` / ``InputGas`` for the editable Magboltz card state

Runtime and parsing
~~~~~~~~~~~~~~~~~~~

The runtime helpers live in ``magboltz_gui.util``:

- ``parser`` reads and writes Magboltz card files
- ``process`` manages the live subprocess tied to the main window
- ``output_parser`` turns raw stdout into a structured ``RunResult``
- ``run_result`` defines the nested dataclasses used by export and plotting

Export layer
~~~~~~~~~~~~

Exports are implemented in two small layers:

- ``export_types`` defines the public export modes and option dataclasses
- ``export_controller`` turns a ``RunResult`` into CSV, JSON, or XML output

GUI layer
~~~~~~~~~

The Qt layer is implemented in ``magboltz_gui.window``. The GUI classes are
described in :doc:`gui_layer`; they are intentionally not autodocumented here
because they depend directly on generated Qt bindings and runtime GUI imports.
