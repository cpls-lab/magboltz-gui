# --- Put this at the very top of main.py (before creating QApplication) ---

import os, sys, platform, re
from pathlib import Path

def _detect_linux_distro() -> str:
    """
    Returns a short distro key: 'debian', 'ubuntu', 'fedora', 'arch', 'opensuse', or 'linux'.
    """
    try:
        data = Path("/etc/os-release").read_text(errors="ignore")
    except Exception:
        return "linux"
    def get(k: str) -> str:
        m = re.search(rf'^{k}=(?:"([^"]+)"|([^\n]+))', data, flags=re.M)
        return (m.group(1) or m.group(2) or "").lower() if m else ""
    id_ = get("ID")
    like = get("ID_LIKE")
    # normalize some families
    if id_ in {"ubuntu"} or "ubuntu" in like:
        return "ubuntu"
    if id_ in {"debian"} or "debian" in like:
        return "debian"
    if id_ in {"fedora"} or "fedora" in like or "rhel" in like or "centos" in like:
        return "fedora"
    if id_ in {"arch", "manjaro", "endeavouros"} or "arch" in like:
        return "arch"
    if id_ in {"opensuse-leap", "opensuse-tumbleweed", "opensuse"} or "suse" in like:
        return "opensuse"
    return "linux"

def _print_install_help_for_missing_pyqt6() -> None:
    system = platform.system()
    if system == "Linux":
        d = _detect_linux_distro()
        print("\nPyQt6 (bindings) is not available.\n", file=sys.stderr)
        if d in {"debian", "ubuntu"}:
            print("Install system packages:", file=sys.stderr)
            print("  sudo apt update", file=sys.stderr)
            print("  sudo apt install python3-pyqt6 qt6-wayland qt6-gtk-platformtheme qt6-image-formats-plugins libqt6svg6", file=sys.stderr)
        elif d == "fedora":
            print("Install system packages:", file=sys.stderr)
            print("  sudo dnf install python3-qt6 qt6-qtwayland qt6-qtimageformats qt6-qtsvg", file=sys.stderr)
        elif d == "arch":
            print("Install system packages:", file=sys.stderr)
            print("  sudo pacman -S python-pyqt6 qt6-base qt6-wayland qt6-imageformats qt6-svg", file=sys.stderr)
        elif d == "opensuse":
            print("Install system packages (adjust python version if needed):", file=sys.stderr)
            print("  sudo zypper install python311-qt6 libqt6-qtwayland libqt6-qtimageformats libqt6-qtsvg", file=sys.stderr)
        else:
            print("Install your distro’s PyQt6 package and Qt6 Wayland/XCB plugins.", file=sys.stderr)
            print("Examples:", file=sys.stderr)
            print("  Debian/Ubuntu: sudo apt install python3-pyqt6 qt6-wayland", file=sys.stderr)
            print("  Fedora:        sudo dnf install python3-qt6 qt6-qtwayland", file=sys.stderr)
        print("\nAlternative (portable wheels):", file=sys.stderr)
        print("  pip install PyQt6 PyQt6-Qt6 PyQt6-Qt6-Data\n", file=sys.stderr)
    elif system == "Darwin":  # macOS
        print("\nPyQt6 is not available on macOS.\nInstall via PyPI wheels:", file=sys.stderr)
        print("  python3 -m pip install PyQt6 PyQt6-Qt6 PyQt6-Qt6-Data", file=sys.stderr)
        print("Or using Homebrew Qt + PyPI bindings:", file=sys.stderr)
        print("  brew install qt@6", file=sys.stderr)
        print("  python3 -m pip install PyQt6", file=sys.stderr)
        print("", file=sys.stderr)
    else:  # Windows / other
        print("\nPyQt6 is not available.\nInstall via PyPI:", file=sys.stderr)
        print("  py -m pip install PyQt6 PyQt6-Qt6 PyQt6-Qt6-Data\n", file=sys.stderr)

def _platform_plugins_ok() -> None:
    """
    On Linux: check that at least one platform plugin we can use is present (wayland/xcb).
    On macOS: cocoa is baked in; if import works, we're fine.
    Returns (ok: bool, hint: str|None)
    """
    try:
        from PyQt6.QtCore import QLibraryInfo as LI
        plug_dir = Path(LI.path(LI.LibraryPath.PluginsPath)) / "platforms"
        # plugin filenames vary by OS
        files = [p.name.lower() for p in plug_dir.glob("*")]
        system = platform.system()
        if system == "Linux":
            has_wayland = any("wayland" in f for f in files)
            has_xcb = any("xcb" in f for f in files)
            if has_wayland or has_xcb:
                return True, None
            return False, f"Qt platform plugins not found in: {plug_dir}"
        elif system == "Darwin":
            # Cocoa comes with the Qt framework; if PyQt6 imported, it's generally fine.
            return True, None
        else:
            return True, None
    except Exception as e:
        return False, f"Failed to inspect Qt plugins: {e}"

def ensure_qt_runtime_or_explain() -> None:
    # Prefer Wayland if present, let Qt fall back automatically.
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland")

    # 1) PyQt6 available?
    try:
        import PyQt6  # noqa: F401
    except Exception as e:
        _print_install_help_for_missing_pyqt6()
        print(f"Details: {e}\n", file=sys.stderr)
        sys.exit(1)

    # 2) Platform plugins present?
    ok, hint = _platform_plugins_ok()
    if not ok:
        system = platform.system()
        print("\nQt runtime is present, but platform plugins are missing.\n", file=sys.stderr)
        if system == "Linux":
            d = _detect_linux_distro()
            if d in {"debian", "ubuntu"}:
                print("Install platform plugins (Wayland/XCB):", file=sys.stderr)
                print("  sudo apt install qt6-wayland libxkbcommon-x11-0 libxcb-cursor0", file=sys.stderr)
                print("Optional for native theming/icons:", file=sys.stderr)
                print("  sudo apt install qt6-gtk-platformtheme qt6-image-formats-plugins libqt6svg6", file=sys.stderr)
            elif d == "fedora":
                print("Install platform plugins:", file=sys.stderr)
                print("  sudo dnf install qt6-qtwayland", file=sys.stderr)
            elif d == "arch":
                print("Install platform plugins:", file=sys.stderr)
                print("  sudo pacman -S qt6-wayland", file=sys.stderr)
            elif d == "opensuse":
                print("Install platform plugins:", file=sys.stderr)
                print("  sudo zypper install libqt6-qtwayland", file=sys.stderr)
            else:
                print("Install your distro’s Qt6 Wayland/XCB platform plugins.", file=sys.stderr)
            if os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11":
                print("\nYou appear to be on an X11 session; you can also force XCB:", file=sys.stderr)
                print("  QT_QPA_PLATFORM=xcb python3 -m magboltz_gui.main", file=sys.stderr)
        elif system == "Darwin":
            print("On macOS, use the PyPI wheels which bundle plugins:", file=sys.stderr)
            print("  python3 -m pip install PyQt6 PyQt6-Qt6 PyQt6-Qt6-Data", file=sys.stderr)
            print("Or install Qt via Homebrew and use PyQt6 bindings:", file=sys.stderr)
            print("  brew install qt@6 && python3 -m pip install PyQt6", file=sys.stderr)
        if hint:
            print(f"\nDetails: {hint}\n", file=sys.stderr)
        sys.exit(1)
