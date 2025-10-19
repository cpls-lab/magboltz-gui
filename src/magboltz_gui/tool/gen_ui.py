from pathlib import Path
import subprocess
import sys


def compile_ui(ui_dir: str, out_dir: str) -> int:
    src = Path(ui_dir)
    out = Path(out_dir)
    here = Path(__file__).resolve().parent

    out.mkdir(parents=True, exist_ok=True)

    ui_files = sorted(src.glob("*.ui"))
    if not ui_files:
        print(f"[gen-ui] No .ui files found in {src.resolve()}")
        return 0

    # Generate ui_*.py files
    for ui in ui_files:
        py_name = f"ui_{ui.stem}.py"
        dst = out / py_name
        cmd = ["pyuic6", "-o", str(dst), str(ui)]
        print("[gen-ui] $", " ".join(cmd))
        subprocess.check_call(cmd)  # raises on failure

    # Generate ui_*.pyi files
    for ui in ui_files:
        py_name = f"ui_{ui.stem}.pyi"
        dst = out / py_name
        cmd = ["python3", str(here / "ui2stub.py"), "-o", str(dst), str(ui)]
        print("[ui2stub.py] $", " ".join(cmd))
        subprocess.check_call(cmd)  # raises on failure

    print(f"[gen-ui] Generated {2 * len(ui_files)} file(s) in {out.resolve()}")
    return 0


def main() -> None:
    # Optional: take directories from argv: uv run gen-ui ui generated
    ui_dir = sys.argv[1] if len(sys.argv) > 1 else "src/magboltz_gui/ui"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "src/magboltz_gui/generated"
    raise SystemExit(compile_ui(ui_dir, out_dir))
