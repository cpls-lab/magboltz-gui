# Magboltz-GUI

A lightweight, cross-platform Qt6 GUI for Magboltz.

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
#   sudo apt install qt6-gtk-platformtheme qt6ct
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
#   sudo apt install qt6-gtk-platformtheme qt6ct
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

#### Linux theming note
- The app auto-detects platform themes on Linux and will log what it picks.
- If your desktop still looks “Fusion/disabled”, you can force a theme:
  ```bash
  QT_QPA_PLATFORMTHEME=qt6ct QT_STYLE_OVERRIDE=qt6ct-style magboltz-gui
  ```
  (assuming `qt6ct` / `qt6-gtk-platformtheme` are installed)

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
See [`LICENSE`](./LICENSE.md) for details.
