# Magboltz-GUI

A lightweight, cross-platform Qt6 GUI for Magboltz.

---

## Installation

### Option A — pipx with bundled Qt (recommended for most users)

```bash
pipx install magboltz-gui[qt]
```

- Works the same on Linux, macOS, and Windows.
- No system packages required; everything lives inside pipx’s venv.

### Option B — Use your **system Qt** (Linux/Debian/Ubuntu), then install via pip
 
If you want to reuse your distro’s Qt bindings, use instead:

```bash
# Debian/Ubuntu: install system PyQt6
sudo apt install python3-pyqt6
```
and then:
```bash
# Create venv that can see system site-packages
python3 -m venv .venv --system-site-packages
source .venv/bin/activate

# Then install magboltz-gui with access to system packages
pip install -e .
```

## Quick start

```bash
magboltz-gui
# or
python -m magboltz_gui
```

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

Install dev tools (mypy/black/etc.) with:

```bash
pip install -e ".[dev]"
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
See [`LICENSE`](./LICENSE.md) for details.
