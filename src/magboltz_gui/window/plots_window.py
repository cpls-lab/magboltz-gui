from __future__ import annotations

from typing import List, TypedDict

from matplotlib.figure import Figure
from matplotlib.pyplot import get_cmap, colormaps
from matplotlib.rcsetup import cycler
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QFileDialog,
    QSpinBox,
)
from PyQt6.QtGui import QIcon
from importlib.resources import files

from magboltz_gui.util.run_result import RunResult


class PlotsWindow(QDialog):
    def __init__(self, run: RunResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Results plots")
        self.resize(900, 800)
        icon_path = files("magboltz_gui.icons").joinpath("icon.svg")
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._run = run
        self._cmap_name = "Pastel1"
        self._energy_style = "Line"
        self._init_ui()
        self._render_all()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        menubar = QMenuBar(self)
        menu = menubar.addMenu("File")
        assert menu is not None
        action_save = menu.addAction("Save current plot...")
        assert action_save is not None
        action_save.triggered.connect(self._save_current_plot)
        layout.setMenuBar(menubar)

        # Palette selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Palette"))
        self.cmbPalette = QComboBox()
        names = [name for name in colormaps() if hasattr(get_cmap(name), "colors")]
        names.sort()
        for name in names:
            self.cmbPalette.addItem(name, userData=name)
        idx = self.cmbPalette.findText(self._cmap_name)
        if idx >= 0:
            self.cmbPalette.setCurrentIndex(idx)
        self.cmbPalette.currentIndexChanged.connect(self._on_palette_changed)
        top.addWidget(self.cmbPalette)

        top.addSpacing(16)
        top.addWidget(QLabel("Energy style"))
        self.cmbEnergyStyle = QComboBox()
        self.cmbEnergyStyle.addItems(["Line", "Bars"])
        self.cmbEnergyStyle.currentIndexChanged.connect(self._on_energy_style_changed)
        top.addWidget(self.cmbEnergyStyle)
        top.addStretch(1)
        layout.addLayout(top)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._tab_energy = self._make_tab()
        self.tabs.addTab(self._tab_energy["widget"], "Energy distribution")

        self._tab_convergence = self._make_tab()
        self.tabs.addTab(self._tab_convergence["widget"], "Convergence")

        self._tab_collfreq = self._make_collfreq_tab()
        self.tabs.addTab(self._tab_collfreq["widget"], "Collision frequencies")

        self._tab_total = self._make_tab()
        self.tabs.addTab(self._tab_total["widget"], "Total frequencies")

        self._tab_drift = self._make_tab()
        self.tabs.addTab(self._tab_drift["widget"], "Drift velocities")

        self._tab_diff = self._make_tab()
        self.tabs.addTab(self._tab_diff["widget"], "Diffusion")

    class _PlotTab(TypedDict):
        widget: QWidget
        fig: Figure
        canvas: FigureCanvasQTAgg

    def _make_tab(self) -> _PlotTab:
        fig = Figure(figsize=(5, 4))
        canvas = FigureCanvasQTAgg(fig)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(canvas)
        return {"widget": widget, "fig": fig, "canvas": canvas}

    class _CollfreqTab(TypedDict):
        widget: QWidget

    def _make_collfreq_tab(self) -> _CollfreqTab:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Top processes (0 = all)"))
        self.spinCollFreqTop = QSpinBox()
        self.spinCollFreqTop.setRange(0, 999)
        self.spinCollFreqTop.setValue(12)
        self.spinCollFreqTop.valueChanged.connect(self._plot_collfreq)
        controls.addWidget(self.spinCollFreqTop)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.collfreqTabs = QTabWidget()
        self.collfreqTabs.setTabPosition(QTabWidget.TabPosition.West)
        layout.addWidget(self.collfreqTabs)

        return {"widget": widget}

    def _colors(self, n: int) -> List[object]:
        cmap = get_cmap(self._cmap_name)
        if hasattr(cmap, "colors") and getattr(cmap, "N", 0) >= n:
            return list(cmap.colors)[:n]  # type: ignore
        return [cmap(i / max(1, n - 1)) for i in range(n)]

    def _on_palette_changed(self) -> None:
        self._cmap_name = self.cmbPalette.currentText()
        self._render_all()

    def _render_all(self) -> None:
        self._plot_energy()
        self._plot_convergence()
        self._plot_collfreq()
        self._plot_total_freq()
        self._plot_drift()
        self._plot_diffusion()

    def _plot_energy(self) -> None:
        fig = self._tab_energy["fig"]
        fig.clear()
        ax = fig.add_subplot(111)
        rows = self._run.tables.energy_distribution
        if rows:
            x = [r.E_eV for r in rows]
            y = [r.spec for r in rows]
            if self._energy_style == "Bars":
                ax.bar(x, y, color=self._colors(1)[0], width=0.08, align="center")
            else:
                ax.plot(x, y, color=self._colors(1)[0])
            ax.set_xlabel("E (eV)")
            ax.set_ylabel("SPEC")
            ax.set_title("Normalised energy distribution")
        self._tab_energy["canvas"].draw()

    def _on_energy_style_changed(self) -> None:
        self._energy_style = self.cmbEnergyStyle.currentText()
        self._plot_energy()

    def _save_current_plot(self) -> None:
        idx = self.tabs.currentIndex()
        tab = [
            self._tab_energy,
            self._tab_convergence,
            self._tab_collfreq,
            self._tab_total,
            self._tab_drift,
            self._tab_diff,
        ][idx]
        fig = tab["fig"]
        path, _ = QFileDialog.getSaveFileName(self, "Save plot", "plot.png", "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if path:
            fig.savefig(path, dpi=300, bbox_inches="tight")

    def _plot_convergence(self) -> None:
        fig = self._tab_convergence["fig"]
        fig.clear()
        rows = self._run.tables.convergence_table
        if rows:
            x = [r.count for r in rows]
            ax1 = fig.add_subplot(221)
            ax2 = fig.add_subplot(222)
            ax3 = fig.add_subplot(223)
            ax4 = fig.add_subplot(224)
            colors = self._colors(4)
            ax1.plot(x, [r.vel for r in rows], color=colors[0])
            ax1.set_title("Velocity")
            ax2.plot(x, [r.energy for r in rows], color=colors[1])
            ax2.set_title("Energy")
            ax3.plot(x, [r.difxx for r in rows], color=colors[2], label="DIFXX")
            ax3.plot(x, [r.difyy for r in rows], color=colors[3], label="DIFYY")
            ax3.set_title("Diffusion (T)")
            ax3.legend()
            ax4.plot(x, [r.difzz for r in rows], color=colors[0])
            ax4.set_title("Diffusion (L)")
            for ax in (ax1, ax2, ax3, ax4):
                ax.set_xlabel("Count")
        self._tab_convergence["canvas"].draw()

    def _plot_collfreq(self) -> None:
        gases = self._run.frequencies_by_gas
        # Preserve current tab
        current_name = self.collfreqTabs.tabText(self.collfreqTabs.currentIndex()) if self.collfreqTabs.count() else ""
        # Clear and rebuild tabs
        self.collfreqTabs.clear()

        if not gases:
            return

        top_n = self.spinCollFreqTop.value()
        for i, gas in enumerate(gases):
            rows = [
                (p.label, p.freq_1e12_s or 0.0)
                for p in gas.processes
                if (p.freq_1e12_s or 0.0) > 0
            ]
            if not rows:
                continue
            rows.sort(key=lambda x: x[1], reverse=True)
            if top_n > 0:
                rows = rows[:top_n]

            fig = Figure(figsize=(5, 4))
            canvas = FigureCanvasQTAgg(fig)
            ax = fig.add_subplot(111)
            labels = [r[0] for r in rows]
            values = [r[1] for r in rows]
            ax.barh(labels, values, color=self._colors(1)[0])
            ax.invert_yaxis()
            ax.set_title(gas.gas_name)
            ax.set_xlabel("Freq (1e12/s)")
            ax.tick_params(axis="y", labelsize=8)
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.addWidget(canvas)
            self.collfreqTabs.addTab(tab, gas.gas_name)
        # Restore previous tab if possible
        if current_name:
            for i in range(self.collfreqTabs.count()):
                if self.collfreqTabs.tabText(i) == current_name:
                    self.collfreqTabs.setCurrentIndex(i)
                    break

    def _plot_total_freq(self) -> None:
        fig = self._tab_total["fig"]
        fig.clear()
        ax = fig.add_subplot(111)
        freq = self._run.frequencies_total
        labels = ["total", "elastic", "inelastic", "ionisation", "attachment"]
        values = [
            freq.total_coll_freq_1e12_s or 0.0,
            freq.elastic_coll_freq_1e12_s or 0.0,
            freq.inelastic_coll_freq_1e12_s or 0.0,
            freq.ionisation_coll_freq_1e12_s or 0.0,
            freq.attachment_coll_freq_1e12_s or 0.0,
        ]
        ax.bar(labels, values, color=self._colors(len(labels)))
        ax.set_ylabel("Freq (1e12/s)")
        ax.set_title("Total collision frequencies")
        self._tab_total["canvas"].draw()

    def _plot_drift(self) -> None:
        fig = self._tab_drift["fig"]
        fig.clear()
        ax = fig.add_subplot(111)
        vx = self._run.transport.vx_um_ns.v_um_ns if self._run.transport.vx_um_ns else 0.0
        vy = self._run.transport.vy_um_ns.v_um_ns if self._run.transport.vy_um_ns else 0.0
        vz = self._run.transport.vz_um_ns.v_um_ns if self._run.transport.vz_um_ns else 0.0
        vals = [vx, vy, vz]
        ax.bar(["Vx", "Vy", "Vz"], vals, color=self._colors(3))
        ax.set_ylabel("Velocity (um/ns)")
        ax.set_title("Drift velocities")
        self._tab_drift["canvas"].draw()

    def _plot_diffusion(self) -> None:
        fig = self._tab_diff["fig"]
        fig.clear()
        ax = fig.add_subplot(111)
        dt = self._run.transport.diffusion.transverse.get("DT_cm2_s")
        dl = self._run.transport.diffusion.longitudinal.get("DL_cm2_s")
        vals = [dt.value if dt else 0.0, dl.value if dl else 0.0]
        ax.bar(["DT", "DL"], vals, color=self._colors(2))
        ax.set_ylabel("Diffusion (cm^2/s)")
        ax.set_title("Diffusion summary")
        self._tab_diff["canvas"].draw()
