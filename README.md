# Magboltz-GUI

A lightweight, cross-platform Qt6 GUI for Magboltz.

---

## Documentation

Published documentation:

- https://cpls.gitlab.io/magboltz-gui/

Project documentation sources live in [`docs/`](docs/).

To build the HTML documentation locally:

```bash
./scripts/build_docs.sh
```

The generated site is written to:

```text
docs/_build/html/index.html
```

---

## Installation

### With uv

#### Option A — bundled Qt (pip)

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[qt]"
```

#### Option B — system Qt (Linux/Debian/Ubuntu)

```bash
# Debian/Ubuntu: install system PyQt6
sudo apt install python3-pyqt6
# Recommended for proper theming on GNOME/Wayland:
#   sudo apt install qt6-gtk-platformtheme qt6ct adwaita-qt6
```
and then:
```bash
uv venv --system-site-packages
source .venv/bin/activate
uv pip install -e .
```

### Without uv

#### Option A — bundled Qt (pip)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[qt]"
```

#### Option B — system Qt (Linux/Debian/Ubuntu)

```bash
# Debian/Ubuntu: install system PyQt6
sudo apt install python3-pyqt6
# Recommended for proper theming on GNOME/Wayland:
#   sudo apt install qt6-gtk-platformtheme qt6ct adwaita-qt6
```
and then:
```bash
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -e .
```

## Quick start

```bash
magboltz-gui
# or
python -m magboltz_gui
```

`magboltz-gui` can prepare input cards without a local Magboltz executable.
Running simulations from the GUI requires a local `magboltz` binary on `PATH`,
or a custom executable path configured in the application. The current
regression reference is based on `MAGBOLTZ 2 VERSION 11.19`.

#### Linux theming note
- The app auto-detects platform themes on Linux and will log what it picks.
- On Debian/GNOME, `qt6-gtk-platformtheme` alone may still leave Qt in a
  Fusion-looking or disabled-looking style. Installing either `qt6ct` or
  `adwaita-qt6` fixes this on tested systems.
- If your desktop still looks “Fusion/disabled”, you can force the `qt6ct`
  theme selector:
  ```bash
  QT_QPA_PLATFORMTHEME=qt6ct magboltz-gui
  ```
  (assuming `qt6ct` is installed)

---

## Developer notes

### Regenerate Qt UI bindings

The `.ui` files in `src/magboltz_gui/ui/` are the source of truth. The Python bindings
in `src/magboltz_gui/generated/` are generated artifacts.

To regenerate them (requires `pyuic6` from PyQt6):

```bash
python -m magboltz_gui.tool.gen_ui
```

This will update both `ui_*.py` and `ui_*.pyi` files under `src/magboltz_gui/generated/`.

### Development dependencies

With uv:

```bash
uv sync --group dev
```

Without uv:

```bash
pip install -e ".[dev]"
```

Both install the same dev tools (black/mypy/stubs); use whichever matches your workflow.

### Run tests

Install the lightweight test dependencies:

```bash
pip install -e ".[test]"
```

```bash
python -m pytest -q
```

The test suite includes parser/export checks and an Ar/CO2 70/30 reference
case. The reference test checks that the GUI input-card representation
round-trips semantically and that selected native Magboltz 11.19 output values
are preserved through CSV, JSON, and XML export.

Default tests intentionally avoid Qt and external Magboltz execution. Tests
that require Qt should be marked `gui` and placed under `tests/gui/`; tests that
execute a real Magboltz binary should be marked `magboltz`.

To run the Qt smoke tests locally:

```bash
pip install -e ".[test-gui]"
QT_QPA_PLATFORM=offscreen python -m pytest -q -m gui
```

The GUI tests cover main-window initialization, gas add/remove, parameter
widget bindings, result-file loading, command-line clipboard copying, run-error
paths, export-dialog state transitions, and export-dialog settings writing
CSV/JSON/XML files through the core export layer.

To run the opt-in tests that execute a real Magboltz binary:

```bash
MAGBOLTZ_TEST_BIN=/path/to/magboltz python -m pytest -q -m magboltz
```

These tests are intentionally excluded from the default path because they run a
local Fortran Magboltz executable. `MAGBOLTZ_TEST_TIMEOUT`
controls the per-run timeout in seconds and defaults to `900`.

### Build the documentation

If you prefer to install the documentation stack in a virtual environment:

```bash
uv pip install -e ".[docs]"
./scripts/build_docs.sh
```

---

## Academic & Research Use

This software is distributed in the spirit of open scientific collaboration.  
If you use **magboltz-gui** in academic or research work, please cite:

- S. F. Biagi, *Nucl. Instrum. Met.* A 421 (1999) 234–240.  
- **M. Renda, D. A. Ciubotaru**, *magboltz-gui* (year, version, DOI/URL) — **(to be completed).**

Citation is not legally required by the license but is encouraged to support reproducibility and credit the original authors.

---

## Authors & Contact

- **Michele Renda** — <michele.renda@cern.ch>  
- **Dan Andrei Ciubotaru**

---

## License

Released under the **MIT License**.  
See [`LICENSE`](./LICENSE.txt) for details.
