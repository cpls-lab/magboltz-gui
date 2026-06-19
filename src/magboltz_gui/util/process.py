"""Manage one live Magboltz subprocess connected to the GUI."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QProcess

if TYPE_CHECKING:
    from magboltz_gui.window.main_window import MagboltzGUI


class ProcessManager:
    """Own one ``QProcess`` and bridge it with the main window state."""

    def __init__(
        self,
        main_window: MagboltzGUI,
        *,
        input_file: Path,
        cleanup_input_file: bool = False,
    ) -> None:
        self.main_window = main_window
        self.input_file = input_file
        self.cleanup_input_file = cleanup_input_file
        self._stdout_buffer: list[str] = []

    def run(self) -> None:
        """Create the process, wire its signals, and launch it."""

        self.process = QProcess(self.main_window)

        # Connect QProcess signals
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.run_process()

    def stop(self) -> None:
        """Attempt a graceful stop, then fall back to killing the process."""
        try:
            self.process.terminate()
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass

    def run_process(self) -> None:
        """Start ``magboltz`` and stream the current input card to stdin."""

        if not self.input_file.is_file():
            self.main_window.show_error("Error", f"Input file not found:\n{self.input_file}")
            self._finish_without_start()
            return

        cmd = str(self.main_window.magboltzPath) if self.main_window.magboltzPath is not None else "magboltz"
        self.process.start(cmd)
        self.main_window.consoleOutput.clear()
        self.main_window.consoleOutput.append(f"<span style='color:blue;'>{cmd} &lt; {self.input_file}</span>")
        self.main_window.consoleOutput.append(f"")
        if self.cleanup_input_file:
            self.main_window.consoleOutput.append("Input was not saved; running from a temporary input card.")
        self.main_window.consoleOutput.append("Starting process...")

        with self.input_file.open("r", encoding="utf-8") as f:
            for line in f.readlines():
                self.process.write(f"{line}\n".encode("utf-8"))

    def _finish_without_start(self) -> None:
        """Restore window state when the process cannot be started."""
        if self.cleanup_input_file:
            self.input_file.unlink(missing_ok=True)
        if self in self.main_window.processes:
            self.main_window.processes.remove(self)
        if not self.main_window.processes:
            self.main_window._set_running_state(False)

    def handle_stdout(self) -> None:
        """Append standard output to the console view and capture buffer."""
        data = self.process.readAllStandardOutput().data()
        text = data.decode("utf-8")
        self._stdout_buffer.append(text)
        self.main_window.consoleOutput.append(text)

    def handle_stderr(self) -> None:
        """Append standard error to the console view."""
        data = self.process.readAllStandardError().data()
        text = data.decode("utf-8")
        self.main_window.consoleOutput.append(f"<span style='color:red;'>{text}</span>")

    def process_finished(self) -> None:
        """Parse the finished run and update export/plot availability."""
        self.main_window.consoleOutput.append("")
        self.main_window.consoleOutput.append("Process finished.")
        stdout_text = "".join(self._stdout_buffer)
        try:
            from magboltz_gui.util.output_parser import parse_magboltz_output

            input_text = None
            input_path = str(self.input_file)
            if self.input_file.is_file():
                with self.input_file.open("r", encoding="utf-8") as f:
                    input_text = f.read()
            self.main_window._last_run_result = parse_magboltz_output(
                stdout_text=stdout_text, input_text=input_text, input_path=input_path
            )
            self.main_window.actionResultExport.setEnabled(True)
            self.main_window.btnResultExport.setEnabled(True)
            self.main_window.actionShowPlots.setEnabled(True)
            self.main_window.btnResultPlots.setEnabled(True)
        except Exception as exc:
            self.main_window.show_error("Parse error", f"Failed to parse Magboltz output: {exc}")
        finally:
            if self.cleanup_input_file:
                self.input_file.unlink(missing_ok=True)
        self.main_window.processes.remove(self)
        if not self.main_window.processes:
            self.main_window._set_running_state(False)
