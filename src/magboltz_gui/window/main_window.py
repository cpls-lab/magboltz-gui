from __future__ import annotations
import platform
from importlib.resources import files
from pathlib import Path
from typing import Optional, List, Tuple, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QStyle
from PyQt6.QtWidgets import (
    QMainWindow,
    QDialog,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QTableWidgetItem,
    QHeaderView,
    QTableWidget,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.pyplot import colormaps, get_cmap
from matplotlib.rcsetup import cycler

from magboltz_gui.data.database import GasDatabase
from magboltz_gui.data.input_cards import InputCards, InputGas
from magboltz_gui.generated.ui_main import Ui_MainWindow
from magboltz_gui.util import parser
from magboltz_gui.window.delegates import GasNameDelegate, AmountDelegate
from magboltz_gui.util.process import ProcessManager
from magboltz_gui.util.run_result import RunResult
from magboltz_gui.window.campaign_widget import CampaignWidget
from magboltz_gui.window.export_window import ExportDialog
from magboltz_gui.window.preferences_window import (
    PreferencesDialog,
    load_magboltz_executable_setting,
    load_use_qt_standard_icons_setting,
)
from magboltz_gui.util.export_controller import export_to_file
from magboltz_gui.util.export_types import ExportFormat, ExportType, CsvOptions, JsonOptions, XmlOptions


class MagboltzGUI(QMainWindow, Ui_MainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        # uic.loadUi(files("magboltz_gui.ui").joinpath("main.ui"), self) <- Not needed anymore because we use pyuic6

        cw = self.centralWidget()
        assert cw is not None
        cw.setVisible(False)

        self._currentInputFile: Optional[Path] = None
        self._currentResultFile: Optional[Path] = None

        self._currentCards: InputCards = InputCards()
        self._currentModified: bool = False
        self._last_run_result: Optional[RunResult] = None
        self.magboltzPath: Optional[Path] = load_magboltz_executable_setting()
        self.useQtStandardIcons: bool = load_use_qt_standard_icons_setting()

        # Associating button to actions
        self.btnGasAdd.setDefaultAction(self.actionGasAdd)
        self.btnGasRemove.setDefaultAction(self.actionGasRemove)
        self.btnGasNormalize.setDefaultAction(self.actionGasNormalize)
        self.btnCmdCopyToClipbord.setDefaultAction(self.actionCmdCopyToClipboard)
        self.btnResultSave.setDefaultAction(self.actionResultSave)
        self.btnResultOpen.setDefaultAction(self.actionResultOpen)
        self.btnResultExport.setDefaultAction(self.actionResultExport)
        self.btnResultPlots.setDefaultAction(self.actionShowPlots)
        self.btnGraphSave.setDefaultAction(self.actionGraphSave)
        self.btnGasUp.setDefaultAction(self.actionGasMoveUp)
        self.btnGasDown.setDefaultAction(self.actionGasMoveDown)

        # Associating actions to methods
        self.actionNew.triggered.connect(self.newDocument)
        self.actionOpen.triggered.connect(self.openDocument)
        self.actionSave.triggered.connect(self.saveDocument)
        self.actionSaveAs.triggered.connect(self.saveDocumentAs)
        self.actionClose.triggered.connect(self.fileClose)
        self.actionRun.triggered.connect(self.runDocument)
        self.actionStop.triggered.connect(self.stopDocument)
        self.actionGasAdd.triggered.connect(self.gasAdd)
        self.actionGasRemove.triggered.connect(self.gasRemove)
        self.actionCmdCopyToClipboard.triggered.connect(self.cmdCopyToClipboard)
        self.actionResultCopy.triggered.connect(self.resultCopyToClipboard)
        self.actionResultClear.triggered.connect(self.resultClear)
        self.actionResultSave.triggered.connect(self.saveResult)
        self.actionResultOpen.triggered.connect(self.openResultFile)
        self.actionResultExport.triggered.connect(self.openExportWindow)
        self.actionShowPlots.triggered.connect(self.showPlotsWindow)
        self.actionGasMoveUp.triggered.connect(self.gasMoveUp)
        self.actionGasMoveDown.triggered.connect(self.gasMoveDown)
        self.actionGraphSave.triggered.connect(self.graphSave)
        self.actionAbout.triggered.connect(self.show_about_dialog)
        self._install_preferences_action()

        self.executionSingleTab = self.tabExecution
        self.executionSingleTab.setObjectName("executionSingleTab")
        self.mainTab.setCurrentWidget(self.tabConfiguration)
        self.campaignTab = CampaignWidget(
            get_current_cards=lambda: self._currentCards,
            get_magboltz_executable=lambda: str(self.magboltzPath or "magboltz"),
            set_current_cards=self._set_current_cards_from_campaign,
            show_info=self.show_info,
            show_error=self.show_error,
            parent=self.mainTab,
        )
        self.mainTab.addTab(self.campaignTab, "Campaign")
        self.executionCampaignTab = self.campaignTab.executionTab
        self.executionCampaignTab.setObjectName("executionCampaignTab")
        self.campaignExecutionTab = self.executionCampaignTab
        self.mainTab.addTab(self.executionCampaignTab, "Execution")
        self._install_result_actions()
        self._install_mode_selector()
        self.campaignTab.runningChanged.connect(self._set_running_state)
        self.mainTab.currentChanged.connect(self._sync_mode_selector_from_tab)
        self._apply_mode_tab_visibility("Single")

        self.fillColorMap()

        self.createPieChart()

        self.cmbLabelFormat.currentIndexChanged.connect(self.refresh_pie)
        self.cmbColorMap.currentIndexChanged.connect(self.refresh_pie)

        # Ensure icons are visible even when the desktop icon theme is missing.
        self._apply_icon_fallbacks()

        self.gasListTable.setColumnCount(4)
        # Make "Gas name" stretch to fill available space
        header = self.gasListTable.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Gas ID shrinks to content
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Gas name fills extra space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Gas ratio
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Gas percent

        header.setMinimumSectionSize(50)

        self.database = GasDatabase()
        self.database.load(Path(str(files("magboltz_gui.database").joinpath("database.csv"))))

        self.processes: List[ProcessManager] = []
        # Gas normalize button is obsolete with amount/percent split.
        self.btnGasNormalize.setVisible(False)
        self.actionGasNormalize.setEnabled(False)
        self.actionGasNormalize.setVisible(False)
        self.actionNew.trigger()
        self.actionResultExport.setEnabled(False)
        self.btnResultExport.setEnabled(False)
        self.actionShowPlots.setEnabled(False)
        self.btnResultPlots.setEnabled(False)
        self.actionResultOpen.setEnabled(True)
        self.btnResultOpen.setEnabled(True)
        self.actionStop.setVisible(False)

    def _set_current_cards_from_campaign(self, cards: InputCards) -> None:
        self._currentCards = cards
        self._currentInputFile = None
        self._currentModified = True
        self.connect()
        self.actionResultExport.setEnabled(False)
        self.btnResultExport.setEnabled(False)
        self.actionShowPlots.setEnabled(False)
        self.btnResultPlots.setEnabled(False)
        self.actionStop.setVisible(False)

    def _install_result_actions(self) -> None:
        before_action = self.actionResultSave
        self.menuRun.insertAction(before_action, self.actionResultOpen)

    def _install_preferences_action(self) -> None:
        self.actionPreferences = QAction(QIcon.fromTheme("preferences-system"), "Preferences...", self)
        self.actionPreferences.triggered.connect(self.openPreferences)
        self.menu_Edit.addSeparator()
        self.menu_Edit.addAction(self.actionPreferences)

    def _install_mode_selector(self) -> None:
        self.modeSelectorWidget = QWidget(self)
        layout = QHBoxLayout(self.modeSelectorWidget)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(4)

        self.modeSelectorLabel = QLabel("Mode", self.modeSelectorWidget)
        self.modeSelectorCombo = QComboBox(self.modeSelectorWidget)
        self.modeSelectorCombo.addItems(["Single", "Campaign"])
        self.modeSelectorCombo.setToolTip("Choose whether the toolbar actions target a single run or a campaign workflow.")
        self.modeSelectorCombo.currentTextChanged.connect(self._on_mode_selector_changed)

        layout.addWidget(self.modeSelectorLabel)
        layout.addWidget(self.modeSelectorCombo)

        self.modeSelectorSpacer = QWidget(self)
        self.modeSelectorSpacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.mainToolBar.addWidget(self.modeSelectorSpacer)
        self.mainToolBar.addSeparator()
        self.mainToolBar.addWidget(self.modeSelectorWidget)

    def _on_mode_selector_changed(self, mode: str) -> None:
        self.mainTab.blockSignals(True)
        self._apply_mode_tab_visibility(mode)
        self.mainTab.blockSignals(False)

    def _sync_mode_selector_from_tab(self) -> None:
        current_widget = self.mainTab.currentWidget()
        if current_widget == self.tabConfiguration:
            return
        campaign_widgets = {self.campaignTab, self.executionCampaignTab}
        mode = "Campaign" if current_widget in campaign_widgets else "Single"
        if self.modeSelectorCombo.currentText() == mode:
            return
        self.modeSelectorCombo.blockSignals(True)
        self.modeSelectorCombo.setCurrentText(mode)
        self.modeSelectorCombo.blockSignals(False)
        self._apply_mode_tab_visibility(mode)

    def _apply_mode_tab_visibility(self, mode: str) -> None:
        show_campaign = mode == "Campaign"
        self._set_tab_visible(self.tabConfiguration, True)
        self._set_tab_visible(self.executionSingleTab, not show_campaign)
        self._set_tab_visible(self.campaignTab, show_campaign)
        self._set_tab_visible(self.executionCampaignTab, show_campaign)

    def _set_tab_visible(self, widget: QWidget, visible: bool) -> None:
        index = self.mainTab.indexOf(widget)
        if index >= 0:
            self.mainTab.setTabVisible(index, visible)

    def createPieChart(self) -> None:
        fig = Figure(figsize=(3, 3))
        canvas = FigureCanvasQTAgg(fig)  # type:ignore

        # 2. Create an Axes and draw something (pie chart)
        ax = fig.add_subplot(111)
        ax.pie([], labels=[], autopct="%1.1f%%")

        # 3. Add the canvas to the QWidget container
        layout = QVBoxLayout(self.pieContainer)
        layout.setContentsMargins(0, 0, 0, 0)  # remove spacing
        layout.addWidget(canvas)

        self._gas_fig = fig
        self._gas_ax = ax
        self._gas_canvas = canvas

        self.splitterGases.setSizes([600, 200])

    def _apply_icon_fallbacks(self) -> None:
        """
        Assign toolbar icons.

        On macOS, bundled icons are the default because Qt's StandardPixmap set
        still exposes some conservative/old-looking toolbar icons. Users can
        opt back into the default Qt/Cocoa icons from Preferences.
        """
        system = platform.system()
        if system == "Darwin":
            if self.useQtStandardIcons:
                self._apply_standard_action_icons(force=True)
            else:
                self._apply_darwin_action_icons()
            return

        # On Linux, force bundled icons for Gas Add/Remove (clear "+" / "-" visuals)
        if system == "Linux":
            linux_icons_dir = files("magboltz_gui.icons").joinpath("linux_icons")
            add_icon = linux_icons_dir.joinpath("addition-color-icon.svg")
            remove_icon = linux_icons_dir.joinpath("subtract-color-icon.svg")
            if add_icon.is_file():
                self.actionGasAdd.setIcon(QIcon(str(add_icon)))
            if remove_icon.is_file():
                self.actionGasRemove.setIcon(QIcon(str(remove_icon)))

        self._apply_standard_action_icons(force=False)

    def _apply_darwin_action_icons(self) -> None:
        icons_dir = files("magboltz_gui.icons").joinpath("macOS_icons")
        mapping: dict[QAction, str] = {
            self.actionNew: "new_file.png",
            self.actionOpen: "open.png",
            self.actionSave: "save.png",
            self.actionSaveAs: "save_as.png",
            self.actionRevert: "revert.png",
            self.actionClose: "remove.png",
            self.actionQuit: "remove.png",
            self.actionRun: "execute.png",
            self.actionStop: "remove.png",
            self.actionGasAdd: "add_fill.png",
            self.actionGasRemove: "remove_fill.png",
            self.actionGasMoveUp: "up.png",
            self.actionGasMoveDown: "down.png",
            self.actionGasNormalize: "normalize.png",
            self.actionCmdCopyToClipboard: "copy.png",
            self.actionResultCopy: "copy.png",
            self.actionResultClear: "remove.png",
            self.actionResultSave: "save.png",
            self.actionResultOpen: "open.png",
            self.actionPreferences: "normalize.png",
            self.actionResultExport: "export.png",
            self.actionShowPlots: "graph.png",
            self.actionGraphSave: "graph.png",
        }

        for action, icon_name in mapping.items():
            icon_path = icons_dir.joinpath(icon_name)
            if icon_path.is_file():
                action.setIcon(QIcon(str(icon_path)))

    def _apply_standard_action_icons(self, *, force: bool) -> None:
        style = self.style()
        assert style is not None

        mapping: dict[QAction, QStyle.StandardPixmap] = {
            self.actionNew: QStyle.StandardPixmap.SP_FileIcon,
            self.actionOpen: QStyle.StandardPixmap.SP_DialogOpenButton,
            self.actionSave: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.actionSaveAs: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.actionRevert: QStyle.StandardPixmap.SP_BrowserReload,
            self.actionClose: QStyle.StandardPixmap.SP_DialogCloseButton,
            self.actionQuit: QStyle.StandardPixmap.SP_TitleBarCloseButton,
            self.actionRun: QStyle.StandardPixmap.SP_MediaPlay,
            self.actionStop: QStyle.StandardPixmap.SP_MediaStop,
            self.actionGasAdd: QStyle.StandardPixmap.SP_FileDialogNewFolder,
            self.actionGasRemove: QStyle.StandardPixmap.SP_TrashIcon,
            self.actionGasMoveUp: QStyle.StandardPixmap.SP_ArrowUp,
            self.actionGasMoveDown: QStyle.StandardPixmap.SP_ArrowDown,
            self.actionGasNormalize: QStyle.StandardPixmap.SP_BrowserReload,
            self.actionCmdCopyToClipboard: QStyle.StandardPixmap.SP_FileDialogListView,
            self.actionResultCopy: QStyle.StandardPixmap.SP_FileDialogListView,
            self.actionResultClear: QStyle.StandardPixmap.SP_TrashIcon,
            self.actionResultSave: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.actionResultOpen: QStyle.StandardPixmap.SP_DialogOpenButton,
            self.actionPreferences: QStyle.StandardPixmap.SP_FileDialogDetailedView,
            self.actionResultExport: QStyle.StandardPixmap.SP_DialogSaveButton,
            self.actionShowPlots: QStyle.StandardPixmap.SP_FileDialogDetailedView,
            self.actionGraphSave: QStyle.StandardPixmap.SP_DialogSaveButton,
        }

        for action, sp in mapping.items():
            if force or action.icon().isNull():
                action.setIcon(style.standardIcon(sp))

    def _is_campaign_mode(self) -> bool:
        return self.modeSelectorCombo.currentText() == "Campaign"

    def newDocument(self) -> None:
        if self._is_campaign_mode():
            self.campaignTab.new_campaign()
        else:
            self.fileNew()

    def openDocument(self) -> None:
        if self._is_campaign_mode():
            self.campaignTab.open_campaign()
        else:
            self.fileOpen()

    def saveDocument(self) -> None:
        if self._is_campaign_mode():
            self.campaignTab.save_campaign()
        else:
            self.fileSave()

    def saveDocumentAs(self) -> None:
        if self._is_campaign_mode():
            self.campaignTab.save_campaign_as()
        else:
            self.fileSaveAs()

    def runDocument(self) -> None:
        if self._is_campaign_mode():
            self.mainTab.setCurrentWidget(self.executionCampaignTab)
            self.campaignTab.run_campaign()
        else:
            self.run()

    def stopDocument(self) -> None:
        if self._is_campaign_mode():
            self.campaignTab.cancel_campaign()
        else:
            self.stopRun()

    def fileNew(self) -> None:
        self._currentCards = InputCards()
        self._currentInputFile = None
        self._currentModified = False
        self._currentResultFile = None
        self.connect()

    def fileOpen(self) -> None:

        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")

        if file_name:  # If user picked a file (not Cancel)
            self._currentCards = parser.load(Path(file_name))
            self._currentInputFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()
            self.connect()

    def fileSaveAs(self) -> None:

        if not self.checkInputOpen():
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            str(self._currentInputFile) if self._currentInputFile else "input.txt",
            "All Files (*);;Text Files (*.txt)",
        )

        if file_name:
            parser.save(self._currentCards, Path(file_name))
            self._currentInputFile = Path(file_name)
            self._currentModified = False
            self.updateCmdLine()

    def fileSave(self) -> None:
        if not self.checkInputOpen():
            return

        if self._currentInputFile is None:
            self.fileSaveAs()
        else:
            parser.save(self._currentCards, self._currentInputFile)
            self._currentModified = False
            self.updateCmdLine()

    def fileClose(self) -> None:
        if self._currentCards is not None:

            response = self.show_save_question()

            if response is None:
                return

            if response == True:
                self.fileSave()

            self._currentInputFile = None
            self._currentResultFile = None

            self._currentCards = InputCards()
            self._currentModified = False

            self.updateCmdLine()
            self.disconnect_ui()

    def cmdCopyToClipboard(self) -> None:
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        clipboard.setText(self.commandLine.text())

    def resultCopyToClipboard(self) -> None:
        clipboard = QApplication.clipboard()
        assert clipboard is not None
        clipboard.setText(self.consoleOutput.toPlainText())

    def resultClear(self) -> None:
        self.consoleOutput.clear()

    def show_about_dialog(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("About Magboltz GUI")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(
            "<b>Magboltz GUI</b><br><br>"
            "<b>Credits</b><br>"
            'Michele Renda &lt;<a href="mailto:michele.renda@cern.ch">michele.renda@cern.ch</a>&gt;<br>'
            'Dan Andrei Ciubotaru &lt;<a href="mailto:dan.andrei.ciubotaru@cern.ch">dan.andrei.ciubotaru@cern.ch</a>&gt;<br><br>'
            "<b>In memory of Stephen Francis Biagi</b><br><br>"
            "Stephen Francis Biagi was the creator of Magboltz, a cornerstone of modern gaseous detector physics.<br>"
            "Through this work, he provided a precise and enduring description of electron transport in gases, "
            "enabling accurate simulation and understanding across an extraordinary range of applications.<br><br>"
            "This dedication honors a contribution whose impact is profound, lasting, and woven into the history "
            "of detector physics."
        )
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def checkInputOpen(self) -> bool:
        if self._currentCards is None:
            self.show_error("Error", "File was not open")
            return False
        return True

    def saveResult(self) -> None:

        if not self.checkInputOpen():
            return

        if not self.consoleOutput.toPlainText().strip():
            self.show_info("File Saved", f"First run Magboltz to save the results")

            return

        currentResultFileName, _ = QFileDialog.getSaveFileName(
            self,
            "Save Result",
            str(self._currentResultFile) if self._currentResultFile else "output.txt",
            "All Files (*);;Text Files (*.txt)",
        )

        if currentResultFileName is not None:

            currentResultFile = Path(currentResultFileName)

            text = self.consoleOutput.toPlainText()

            try:
                with open(currentResultFile, "w", encoding="utf-8") as file:
                    file.write(text)
            except Exception as e:
                self.show_error("Error", f"Could not save result: {e}")

            else:
                self.show_info("Success", f"File saved successfully:\n{currentResultFile}")
                self._currentResultFile = currentResultFile

    def openResultFile(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Result", "", "All Files (*);;Text Files (*.txt)")
        if not file_name:
            return
        try:
            text = Path(file_name).read_text(encoding="utf-8")
            self.consoleOutput.setPlainText(text)
            from magboltz_gui.util.output_parser import parse_magboltz_output

            self._last_run_result = parse_magboltz_output(stdout_text=text)
            self.actionResultExport.setEnabled(True)
            self.btnResultExport.setEnabled(True)
            self.actionShowPlots.setEnabled(True)
            self.btnResultPlots.setEnabled(True)
            self.show_info("Result loaded", f"Loaded result file:\n{file_name}")
        except Exception as exc:
            self.show_error("Error", f"Could not open result file: {exc}")

    def openExportWindow(self) -> None:
        if self._last_run_result is None:
            self.show_error("No results", "No parsed results available. Run Magboltz first.")
            return

        dialog = ExportDialog(self._last_run_result, self)
        if dialog.exec():
            export_type, fmt, path, csv_opts, json_opts, xml_opts = dialog.export_settings()
            try:
                export_to_file(
                    self._last_run_result,
                    export_type,
                    fmt,
                    path,
                    csv_options=csv_opts,
                    json_options=json_opts,
                    xml_options=xml_opts,
                )
                self.show_info("Export complete", f"Exported to:\n{path}")
            except Exception as exc:
                self.show_error("Export failed", str(exc))

    def showPlotsWindow(self) -> None:
        if self._last_run_result is None:
            self.show_error("No results", "No parsed results available. Run Magboltz first.")
            return
        from magboltz_gui.window.plots_window import PlotsWindow

        window = PlotsWindow(self._last_run_result, self)
        window.show()

    def openPreferences(self) -> None:
        dialog = PreferencesDialog(self.magboltzPath, self.useQtStandardIcons, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dialog.save()
        self.magboltzPath = dialog.magboltz_path()
        self.useQtStandardIcons = dialog.use_qt_standard_icons()
        self._apply_icon_fallbacks()
        self.updateCmdLine()
        self.campaignTab.refresh_executable()

    def run(self) -> None:

        if self._currentCards is None:
            self.show_error("To run the magboltz process, you must to open the input file")
            return

        if self._currentInputFile is None:
            self.show_error("Error", "To run the magboltz process, you must to save the file")
            return

        invalid_rows = [
            idx + 1 for idx, gas in enumerate(self._currentCards.gases) if gas.gas_id <= 0
        ]
        if invalid_rows:
            rows = ", ".join(str(r) for r in invalid_rows)
            self.show_error("Missing gas", f"Select a gas for each row (missing: {rows})")
            return

        if self._currentModified is False:
            self.fileSave()

        self.mainTab.setCurrentWidget(self.tabExecution)

        process = ProcessManager(self)
        self.processes.append(process)
        self._set_running_state(True)
        self.actionShowPlots.setEnabled(False)
        self.btnResultPlots.setEnabled(False)
        process.run()

    def stopRun(self) -> None:
        if not self.processes:
            return
        for process in list(self.processes):
            process.stop()
        self._set_running_state(False)

    def _set_running_state(self, running: bool) -> None:
        self.actionRun.setVisible(not running)
        self.actionStop.setVisible(running)

    def updateCmdLine(self) -> None:

        if self._currentInputFile is not None:
            self.commandLine.setText(f"{self.magboltzPath or 'magboltz'} < {self._currentInputFile}")
        else:
            self.commandLine.setText("")

    def onFinalEnergyAutoChanged(self, state: int) -> None:
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            self.spinFinalEnergy.setValue(0.0)
        else:
            self.spinFinalEnergy.setValue(50.0)

    def show_error(
        self,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:
        self.show_message(QMessageBox.Icon.Critical, title, message, buttons, default)

    def show_info(
        self,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:
        self.show_message(QMessageBox.Icon.Information, title, message, buttons, default)

    def show_message(
        self,
        icon: QMessageBox.Icon,
        title: str,
        message: str,
        buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
        default: QMessageBox.StandardButton | None = None,
    ) -> None:

        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(message)

        # Buttons
        msg.setStandardButtons(buttons)
        if default is not None:
            msg.setDefaultButton(default)

        # Resize automatically based on content
        msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg.adjustSize()

        # Center relative to parent window
        parent_geom = self.geometry()
        msg_geom = msg.frameGeometry()

        x = parent_geom.center().x() - msg_geom.width() // 2
        y = parent_geom.center().y() - msg_geom.height() // 2
        msg.move(x, y)

        msg.exec()

    def show_save_question(self) -> Optional[bool]:
        reply = QMessageBox.question(
            self,
            "Save Changes?",
            "Do you want to save changes before closing?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            return True
        elif reply == QMessageBox.StandardButton.No:
            return False
        else:
            return None

    def connect(self) -> None:

        cw = self.centralWidget()
        assert cw is not None
        cw.setVisible(True)

        self.spinRealInteractions.setValue(self._currentCards.number_of_real_collisions)
        self.checkPenning.setChecked(self._currentCards.enable_penning)
        self.checkThermal.setChecked(self._currentCards.enable_thermal)
        self.spinFinalEnergy.setValue(self._currentCards.final_energy)
        self.checkFinalEnergyAuto.setChecked(self._currentCards.final_energy == 0.0)
        self.spinGasTemperature.setValue(self._currentCards.gas_temperature)
        self.spinGasPressure.setValue(self._currentCards.gas_pressure)
        self.spinElectricField.setValue(self._currentCards.electric_field)
        self.spinMagneticField.setValue(self._currentCards.magnetic_field)
        self.spinAngle.setValue(self._currentCards.angle)

        self.spinRealInteractions.valueChanged.connect(self.onRealInteractionsChanged)
        self.checkPenning.stateChanged.connect(self.onPenningChanged)
        self.checkThermal.stateChanged.connect(self.onThermalChanged)
        self.checkFinalEnergyAuto.stateChanged.connect(self.onFinalEnergyAutoChanged)
        self.spinFinalEnergy.valueChanged.connect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.connect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.connect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.connect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.connect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.connect(self.onAngleChanged)

        self.gasListTable.cellChanged.connect(self.refresh_pie)

        gas_name_delegate = GasNameDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(1, gas_name_delegate)

        delegate = AmountDelegate(self, self.gasListTable)
        self.gasListTable.setItemDelegateForColumn(2, delegate)

        self.refresh()

    def get_colors(self, cmap_name: str, n: int) -> List[Tuple[float, float, float, float]]:
        cmap = get_cmap(cmap_name)

        # print("===============================")
        # print("Name:", cmap.name)
        # print("Type:", type(cmap))
        # print("N:", cmap.N)
        # print("Has colors:", hasattr(cmap, "colors"))
        # print("First color:", cmap.colors[0])
        # print("Bad color:", cmap._rgba_bad)

        if isinstance(cmap, ListedColormap):
            if cmap.N < 256:
                return list(cmap.colors)  # type: ignore
            else:
                return list(cmap.resampled(n).colors)  # type: ignore
        else:
            return [cmap(i / (n - 1 if n > 1 else 1)) for i in range(n)]

    def refresh_pie(self) -> None:

        self._gas_ax.clear()

        gas_fracs = []
        gas_labels = []

        total = sum(g.gas_frac for g in self._currentCards.gases)
        for gas in self._currentCards.gases:

            try:
                db_item = self.database.get(gas.gas_id)

                match self.cmbLabelFormat.currentIndex():
                    case 0:
                        gas_name = db_item.as_formula
                    case 1:
                        gas_name = db_item.as_name
                    case 2:
                        gas_name = db_item.as_name_formula
                    case 3:
                        gas_name = ""
                    case _:
                        gas_name = db_item.as_formula
            except KeyError:
                gas_name = "?"

            if total > 0:
                gas_fracs.append(gas.gas_frac * 100.0 / total)
            gas_labels.append(gas_name)

        if len(gas_fracs) > 0:
            colors = self.get_colors(self.cmbColorMap.currentText(), len(gas_fracs))
            self._gas_ax.set_prop_cycle(cycler(color=colors))

        self._gas_ax.pie(
            gas_fracs if sum(gas_fracs) > 0 else [],
            labels=gas_labels if sum(gas_fracs) > 0 else [],
            autopct="%1.1f%%",
            wedgeprops={"edgecolor": "black", "linewidth": 1},
        )

        self._gas_ax.set_aspect("equal")
        self._gas_canvas.draw()  # type:ignore

    def refresh(self) -> None:

        self.gasListTable.clear()
        self.gasListTable.setRowCount(0)
        self.gasListTable.setColumnCount(4)

        self.gasListTable.setHorizontalHeaderLabels(["Gas ID", "Gas name", "Gas ratio", "Gas percent"])

        vheader = self.gasListTable.verticalHeader()
        assert vheader is not None
        vheader.setVisible(False)
        self.gasListTable.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.gasListTable.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.gasListTable.setShowGrid(False)

        i = 0
        total = sum(g.gas_frac for g in self._currentCards.gases)
        for gas in self._currentCards.gases:
            gas_id_widget = QTableWidgetItem(str(gas.gas_id))
            gas_id_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            gas_id_widget.setFlags(gas_id_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)

            try:
                gas_name = self.database.get(gas.gas_id).as_name_formula
            except KeyError:
                gas_name = "(select gas)"

            gas_name_widget = QTableWidgetItem(gas_name)

            gas_ratio_widget = QTableWidgetItem(f"{gas.gas_frac:.3f}")
            gas_ratio_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            percent = gas.gas_frac * 100.0 / total if total > 0 else 0.0
            gas_percent_widget = QTableWidgetItem(f"{percent:.1f} %")
            gas_percent_widget.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            gas_percent_widget.setFlags(gas_percent_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.gasListTable.insertRow(i)
            self.gasListTable.setItem(i, 0, gas_id_widget)
            self.gasListTable.setItem(i, 1, gas_name_widget)
            self.gasListTable.setItem(i, 2, gas_ratio_widget)
            self.gasListTable.setItem(i, 3, gas_percent_widget)
            i += 1

        self.refresh_pie()
        self.refreshNeedNormalize()

    def refreshNeedNormalize(self) -> None:
        self.lblNeedNormalize.setVisible(False)

    def gasAdd(self) -> None:

        row_index = self.gasListTable.rowCount()
        self.gasListTable.insertRow(row_index)
        self._currentCards.gases.append(InputGas(80, 0.0))
        self.refresh()
        self.gasListTable.setCurrentCell(row_index, 0)

    def gasRemove(self) -> None:
        row = self.gasListTable.currentRow()

        if row >= 0:
            self._currentCards.gases.pop(row)
            self.refresh()
        else:
            self.show_error("Error", "Select a row to remove")

    def gasNormalize(self) -> None:
        fraction_sum = 0.0
        for gas in self._currentCards.gases:
            fraction_sum += gas.gas_frac

        if fraction_sum > 0.0:

            for gas in self._currentCards.gases:
                gas.gas_frac = round(gas.gas_frac * 100.0 / fraction_sum, 2)
        else:
            # Split evenly
            for gas in self._currentCards.gases:
                gas.gas_frac = round(100.0 / len(self._currentCards.gases), 2)

        self.refresh()

    def gasMoveUp(self) -> None:

        row = self.gasListTable.currentRow()

        if row >= 0:
            if row > 0:
                self._currentCards.gases[row], self._currentCards.gases[row - 1] = (
                    self._currentCards.gases[row - 1],
                    self._currentCards.gases[row],
                )
                self.refresh()
                self.gasListTable.setCurrentCell(row - 1, 0)
        else:
            self.show_error("Error", "Select a row to move")

    def gasMoveDown(self) -> None:

        row = self.gasListTable.currentRow()

        if row >= 0:
            if row < len(self._currentCards.gases) - 1:
                self._currentCards.gases[row], self._currentCards.gases[row + 1] = (
                    self._currentCards.gases[row + 1],
                    self._currentCards.gases[row],
                )
                self.refresh()
                self.gasListTable.setCurrentCell(row + 1, 0)
        else:
            self.show_error("Error", "Select a row to move")

    def graphSave(self) -> None:
        canvas = self._gas_fig.canvas
        types = canvas.get_supported_filetypes()
        items: List[Tuple[str, str]] = []
        for ext, desc in sorted(types.items()):
            items.append((f"{desc} (*.{ext})", ext))

        dict_items = {
            g: [k[1] for k in items if k[0].startswith(g)] for g in set(" ".join(v[0].split()[:-1]) for v in items)
        }
        dict_items["All files"] = []

        fn_format_ext: Callable[[str], str] = lambda x: f"*.{x}" if x else "*"

        group_items = [
            (format_name + " (" + " ".join(fn_format_ext(x) for x in format_exts) + ")", " ".join(format_exts))
            for format_name, format_exts in dict_items.items()
        ]

        filter_str = ";;".join(name for name, _ in group_items)

        path_str, selected = QFileDialog.getSaveFileName(self, "Save chart", "", filter_str)

        if not path_str:
            return

        path = Path(path_str)

        # Decide the format/extension
        ext = path.suffix.lower().lstrip(".")
        if not ext:
            # No extension typed → infer from selected filter (take its mapped ext)
            for name, mapped_ext in group_items:
                if name == selected:
                    ext = mapped_ext
                    break
            # If still unknown, default to PNG
            if not ext:
                ext = "png"
            path = path.with_suffix(f".{ext}")

        # Save with tight bbox, decent DPI
        self._gas_fig.savefig(
            path,
            format=ext,
            dpi=300,
            bbox_inches="tight",
            facecolor=self._gas_fig.get_facecolor(),  # keep current background
        )

    def onRealInteractionsChanged(self, value: int) -> None:

        self._currentCards.number_of_real_collisions = value

    def onPenningChanged(self, value: int) -> None:

        self._currentCards.enable_penning = Qt.CheckState(value) == Qt.CheckState.Checked

    def onThermalChanged(self, value: int) -> None:

        self._currentCards.enable_thermal = Qt.CheckState(value) == Qt.CheckState.Checked

    def onFinalEnergyChanged(self, value: float) -> None:

        self.checkFinalEnergyAuto.setChecked(value == 0.0)
        self._currentCards.final_energy = value

    def onGasTemperatureChanged(self, value: float) -> None:

        self._currentCards.gas_temperature = value

    def onGasPressureChanged(self, value: float) -> None:

        self._currentCards.gas_pressure = value

    def onElectricFieldChanged(self, value: float) -> None:

        self._currentCards.electric_field = value

    def onMagneticFieldChanged(self, value: float) -> None:

        self._currentCards.magnetic_field = value

    def onAngleChanged(self, value: float) -> None:

        self._currentCards.angle = value

    def disconnect_ui(self) -> None:

        cw = self.centralWidget()
        assert cw is not None
        cw.setVisible(False)

        self.spinRealInteractions.valueChanged.disconnect(self.onRealInteractionsChanged)
        self.checkPenning.stateChanged.disconnect(self.onPenningChanged)
        self.checkThermal.stateChanged.disconnect(self.onThermalChanged)
        self.checkFinalEnergyAuto.stateChanged.disconnect(self.onFinalEnergyAutoChanged)
        self.spinFinalEnergy.valueChanged.disconnect(self.onFinalEnergyChanged)
        self.spinGasTemperature.valueChanged.disconnect(self.onGasTemperatureChanged)
        self.spinGasPressure.valueChanged.disconnect(self.onGasPressureChanged)
        self.spinElectricField.valueChanged.disconnect(self.onElectricFieldChanged)
        self.spinMagneticField.valueChanged.disconnect(self.onMagneticFieldChanged)
        self.spinAngle.valueChanged.disconnect(self.onAngleChanged)

        # self.btnGasAdd.triggered.disconnect(self.onBtnGasAdd)
        # self.btnGasRemove.triggered.disconnect(self.onBtnGasRemove)
        # self.btnGasNormalize.triggered.disconnect(self.onBtnGasNormalize)
        # self.btnExport.triggered.disconnect(self.onBtnExport)

        self.gasListTable.clear()

    def fillColorMap(self) -> None:
        self.cmbColorMap.clear()

        names = [name for name in colormaps() if hasattr(get_cmap(name), "colors")]

        names.sort()

        # self.cmbColorMap.setIconSize(self.cmbColorMap.iconSize())  # keep default or adjust via setIconSize()
        for name in names:
            self.cmbColorMap.addItem(name, userData=name)

        # Default to Pastel1 if available
        idx = self.cmbColorMap.findText("Pastel1")
        if idx >= 0:
            self.cmbColorMap.setCurrentIndex(idx)
