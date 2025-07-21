from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QWidget, QMainWindow, QApplication


class ProcessManager:

    def __init__(self, main_window: 'MagboltzGUI'):
        self.main_window = main_window

    def run(self):

        self.process = QProcess(self.main_window)

        # Connect QProcess signals
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

        self.run_process()


    def run_process(self):
        self.main_window.consoleOutput.clear()
        self.main_window.consoleOutput.append("Starting process...\n")
        # Example: 'ping' on Linux or Windows
        self.process.start(str(self.main_window.magboltzPath) or "magboltz")

        with self.main_window._currentFile.open('r') as f:
            for line in f.readlines():
                self.process.write(f"{line}\n".encode("utf-8"))


    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8")
        self.main_window.consoleOutput.append(text)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8")
        self.main_window.consoleOutput.append(f"<span style='color:red;'>{text}</span>")

    def process_finished(self):
        self.main_window.consoleOutput.append("\nProcess finished.")
        self.main_window.processes.remove(self)
