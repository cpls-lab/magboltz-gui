from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtCore import QProcess

if TYPE_CHECKING:
    from magboltz_gui.window.main_window import MagboltzGUI


class ProcessManager:

    def __init__(self, main_window: MagboltzGUI):
        self.main_window = main_window
        self._stdout_buffer: list[str] = []

    def run(self) -> None:

        self.process = QProcess(self.main_window)

        # Connect QProcess signals
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.run_process()

    def run_process(self) -> None:

        if self.main_window._currentInputFile is None:
            self.main_window.show_error("Error", "You have to open an input file first")
            return

        cmd = str(self.main_window.magboltzPath) if self.main_window.magboltzPath is not None else "magboltz"
        self.process.start(cmd)
        self.main_window.consoleOutput.clear()
        self.main_window.consoleOutput.append(
            f"<span style='color:blue;'>{cmd} &lt; {self.main_window._currentInputFile}</span>"
        )
        self.main_window.consoleOutput.append(f"")
        self.main_window.consoleOutput.append("Starting process...")

        with self.main_window._currentInputFile.open("r") as f:
            for line in f.readlines():
                self.process.write(f"{line}\n".encode("utf-8"))

    def handle_stdout(self) -> None:
        data = self.process.readAllStandardOutput().data()
        text = data.decode("utf-8")
        self._stdout_buffer.append(text)
        self.main_window.consoleOutput.append(text)

    def handle_stderr(self) -> None:
        data = self.process.readAllStandardError().data()
        text = data.decode("utf-8")
        self.main_window.consoleOutput.append(f"<span style='color:red;'>{text}</span>")

    def process_finished(self) -> None:
        self.main_window.consoleOutput.append("")
        self.main_window.consoleOutput.append("Process finished.")
        stdout_text = "".join(self._stdout_buffer)
        try:
            from magboltz_gui.util.output_parser import parse_magboltz_output

            input_text = None
            input_path = str(self.main_window._currentInputFile) if self.main_window._currentInputFile else None
            if self.main_window._currentInputFile is not None:
                with self.main_window._currentInputFile.open("r", encoding="utf-8") as f:
                    input_text = f.read()
            self.main_window._last_run_result = parse_magboltz_output(
                stdout_text=stdout_text, input_text=input_text, input_path=input_path
            )
        except Exception as exc:
            self.main_window.show_error("Parse error", f"Failed to parse Magboltz output: {exc}")
        self.main_window.processes.remove(self)
