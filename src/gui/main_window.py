from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QStatusBar, QTabWidget, QTreeWidget, QVBoxLayout, QWidget

from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox

from models.building_model import BuildingModel
from .dialogue_manager import DialogueManager
from .file_manager import FileManager
from .header_bar import HeaderBar
from .interactive_canvas import InteractiveCanvas
from .state_manager import StateManager
from .interactive_canvas import ControlPolicy


COMPONENTS = [Envelope, RTU, VAVBox, SolarGains, ControlPolicy]
COMPONENT_ICON_NAMES = {
    "Envelope": ["WIP_ICON.png"],
    "RTU": ["WIP_ICON.png"],
    "VAVBox": ["WIP_ICON.png"],
    "SolarGains": ["WIP_ICON.png"],
    "ControlPolicy": ["WIP_ICON.png"]
}


def check_dependencies():
    """Check versions of all required dependencies. Returns: dict."""
    results = {}
    try:
        import torch
        results["torch"] = (True, torch.__version__)
    except Exception:
        results["torch"] = (False, "")

    try:
        import torchdiffeq
        results["torchdiffeq"] = (True, torchdiffeq.__version__)
    except Exception:
        results["torchdiffeq"] = (False, "")

    try:
        import numpy as np
        results["numpy"] = (True, np.__version__)
    except Exception:
        results["numpy"] = (False, "")

    try:
        import matplotlib
        results["matplotlib"] = (True, matplotlib.__version__)
    except Exception:
        results["matplotlib"] = (False, "")

    try:
        from PyQt6 import QtCore
        results["PyQt6"] = (True, QtCore.PYQT_VERSION_STR)
    except Exception:
        results["PyQt6"] = (False, "")

    try:
        import neuromancer as nm
        results["neuromancer"] = (True, nm.__version__)
    except Exception:
        results["neuromancer"] = (False, "")

    return results


class MainWindow(QMainWindow):
    """Main application window for the PyTorch Buildings GUI."""

    def __init__(self):
        """Initialize the main window with canvas, panels, and managers."""
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1500, 900)
        self.building_model = BuildingModel("Model")
        self.canvas = InteractiveCanvas(self.building_model)
        self.canvas.zoom_changed.connect(self.on_canvas_zoom_changed)
        self.canvas.component_click_handler = self.handle_component_click_action
        self.canvas.component_added_handler = self.on_component_added
        self.canvas.area_delete_handler = self.on_area_deleted
        self.file_manager = FileManager(self.building_model)
        self.dialogue_manager = DialogueManager(self, self.building_model)
        self.pending_component_action = None
        self.pending_connection_items = []
        self.next_component_id = 1
        self.action_buttons = []
        self.add_connection_btn = None
        self.area_delete_btn = None
        self.edit_component_btn = None
        self.delete_component_btn = None
        self.mode_status_label = None
        self.zone_value_display = None
        self.zoom_value_display = None
        self.component_list = QTreeWidget()
        self.component_list.setColumnCount(2)
        self.component_list.setHeaderLabels(["Component", "Value"])
        self.component_list.setAlternatingRowColors(True)
        self.component_list.setRootIsDecorated(True)
        self.component_list.setIndentation(12)
        self.component_list.header().setStretchLastSection(True)
        self.connection_list = QTreeWidget()
        self.connection_list.setColumnCount(1)
        self.connection_list.setHeaderLabels(["Connection"])
        self.connection_list.setAlternatingRowColors(True)
        self.connection_list.setRootIsDecorated(True)
        self.connection_list.header().setStretchLastSection(True)
        self.dep_results = check_dependencies()
        self.assets_path = Path(__file__).resolve().parents[2] / "assets"
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("color: #000000;")
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)
        central_widget.setLayout(root_layout)
        self._last_results = None
        self._last_t_start = 0
        self._multi_charts: list = []
        self._plot_tabs = None
        self._plot_results_shown = None
        self._left_tabs = None
        self._settings_layout = None
        self._var_checkboxes: dict = {}
        self._var_layout = None
        self._selected_plot_vars: list = []
        self.header_bar = HeaderBar(
            self.assets_path,
            COMPONENTS,
            COMPONENT_ICON_NAMES,
            callbacks = {
                "save_as": self.save_as_layout,
                "save": self.save_layout,
                "load": self.load_layout,
                "run": self.run_simulation,
                "set_time": self.open_set_time_dialog,
                "add_connection": self.add_connection,
                "edit_component": self.arm_edit_component,
                "delete_component": self.arm_delete_component,
                "area_delete": self.arm_area_delete,
            },
        )
        self.action_buttons = self.header_bar.action_buttons
        self.add_connection_btn = self.header_bar.add_connection_btn
        self.edit_component_btn = self.header_bar.edit_component_btn
        self.delete_component_btn = self.header_bar.delete_component_btn
        self.area_delete_btn = self.header_bar.area_delete_btn
        root_layout.addWidget(self.header_bar)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.create_left_panel())
        splitter.addWidget(self.create_right_panel())
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 1170])
        root_layout.addWidget(splitter)
        self.state_manager = StateManager(
            self.building_model,
            self.canvas,
            self.component_list,
            self.connection_list,
            self.zone_value_display,
        )
        self.state_manager.set_zone_value_display(self.zone_value_display)
        self.setStatusBar(QStatusBar())
        self.setup_dependency_status_button()
        self.setup_mode_status_label()
        self.set_component_action_mode(None)
        self.refresh_component_list()
        self.file_path = None
        # add control s shortcut for save
        save_action = QAction(self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_layout)
        self.addAction(save_action)


    def setup_dependency_status_button(self):
        """Setup status bar button displaying dependency check results."""
        all_ok = all(ok for ok, _ in self.dep_results.values())
        icon = "✓" if all_ok else "✗"
        button = QPushButton(icon)
        button.setToolTip(self.build_dependency_tooltip())
        button.setFixedSize(24, 24)
        button.setFlat(True)
        button.setStyleSheet("font-weight: bold;")
        self.statusBar().addWidget(button)
        self.dep_status_button = button


    def setup_mode_status_label(self):
        """Setup status bar label displaying current operation mode."""
        label = QLabel("Mode: Normal")
        label.setStyleSheet("color: #000000; padding-right: 8px;")
        self.statusBar().addPermanentWidget(label)
        self.mode_status_label = label


    def build_dependency_tooltip(self):
        """Build tooltip text listing all dependencies and their versions. Returns: str."""
        lines = ["Dependency status:"]
        for name, (ok, version) in self.dep_results.items():
            icon = "✓" if ok else "✗"
            version_text = version if version else "not found"
            lines.append(f"{icon} {name}: {version_text}")
        return "\n".join(lines)


    def create_left_panel(self):
        """Create left sidebar panel with project details and plot controls. Returns: QWidget."""
        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel.setLayout(panel_layout)
        self._left_tabs = QTabWidget()
        self._left_tabs.setDocumentMode(True)
        self._left_tabs.addTab(self.create_project_tab(), "Project")
        self._left_tabs.addTab(self._create_plots_tab(), "Plots")
        self._left_tabs.tabBar().setExpanding(True)
        self._left_tabs.currentChanged.connect(self._on_left_tab_changed)
        panel_layout.addWidget(self._left_tabs)
        return panel


    def _on_left_tab_changed(self, index):
        """Switch canvas_stack to match the selected left tab. Args: index (int)."""
        if index == 1:
            self.view_plots()
        else:
            if hasattr(self, "canvas_stack"):
                self.canvas_stack.setCurrentIndex(0)


    def _create_info_box(self, title):
        """Create info display box with label and value. Args: title (str). Returns: tuple (QWidget, QLabel)."""
        box = QWidget()
        box.setStyleSheet("background: rgba(255, 255, 255, 220); border: 1px solid #b0b0b0; border-radius: 4px; color: #000000;")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; border: none; background: transparent;")
        value_label = QLabel("-")
        value_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return box, value_label


    def _create_zone_controls_box(self):
        """Create zone count controls box with +/- buttons. Returns: QWidget."""
        box = QWidget()
        box.setStyleSheet("background: rgba(255, 255, 255, 220); border: 1px solid #b0b0b0; border-radius: 4px; color: #000000;")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        title_label = QLabel("Zones:")
        title_label.setStyleSheet("font-weight: 600; border: none; background: transparent;")
        zone_dec_btn = QPushButton("-")
        zone_dec_btn.setFixedSize(24, 24)
        zone_dec_btn.clicked.connect(lambda: self._change_n_zones(-1))
        self.zone_value_display = QLabel(str(int(self.building_model.n_zones)))
        self.zone_value_display.setStyleSheet("border: none; background: transparent; min-width: 24px;")
        self.zone_value_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_inc_btn = QPushButton("+")
        zone_inc_btn.setFixedSize(24, 24)
        zone_inc_btn.clicked.connect(lambda: self._change_n_zones(1))
        layout.addWidget(title_label)
        layout.addWidget(zone_dec_btn)
        layout.addWidget(self.zone_value_display)
        layout.addWidget(zone_inc_btn)
        return box


    def _change_n_zones(self, delta):
        """Increment or decrement n_zones. Args: delta (int)."""
        new_n = max(1, int(self.building_model.n_zones) + delta)
        self.building_model.update_n_zones(new_n)
        self._invalidate_plots()
        self._update_zone_display()
        self.refresh_component_list()


    def _create_zoom_controls_box(self):
        """Create zoom control buttons (+, -, center). Returns: QWidget."""
        box = QWidget()
        box.setStyleSheet("background: rgba(255, 255, 255, 220); border: 1px solid #b0b0b0; border-radius: 4px; color: #000000;")
        layout = QHBoxLayout(box)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(24, 24)
        zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        self.zoom_value_display = QLabel(f"{self.canvas.get_zoom_percent()}%")
        self.zoom_value_display.setStyleSheet("border: none; background: transparent; min-width: 48px;")
        self.zoom_value_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(24, 24)
        zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        center_btn = QPushButton(" Center ")
        center_btn.clicked.connect(self.canvas.center_view)
        layout.addWidget(zoom_out_btn)
        layout.addWidget(self.zoom_value_display)
        layout.addWidget(zoom_in_btn)
        layout.addWidget(center_btn)
        return box


    def create_right_panel(self):
        """Create right panel with canvas/plot stack. Returns: QWidget."""
        from PyQt6.QtWidgets import QStackedWidget

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(8)
        self.canvas_stack = QStackedWidget()
        self.canvas_stack.addWidget(self.canvas)
        self._plot_widget = QWidget()
        self._plot_widget_layout = QVBoxLayout(self._plot_widget)
        self._plot_widget_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_widget_layout.setSpacing(4)
        self.canvas_stack.addWidget(self._plot_widget)
        panel_layout.addWidget(self.canvas_stack, 1)
        return panel


    def _make_plot_panel(self):
        """Build a MultiChartWidget for the currently selected variables."""
        from PyQt6.QtWidgets import QTabWidget
        from gui.plot_widget import MultiChartWidget
        from simulation.plotter import VARIABLE_META, ZONE_COLORS, DEFAULT_PLOT_VARS, select_variables, auto_title

        while self._plot_widget_layout.count():
            item = self._plot_widget_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._multi_charts = []
        self._plot_tabs = QTabWidget()
        self._plot_tabs.setDocumentMode(True)
        t_start = self._last_t_start
        t_duration = self.building_model.t_duration
        dt = self.building_model.dt
        model_name = self.building_model.name

        wanted = self._selected_plot_vars if self._selected_plot_vars else DEFAULT_PLOT_VARS
        variables = [v for v in wanted if v in self._last_results]
        if not variables:
            variables = select_variables(self._last_results)

        mc = MultiChartWidget()
        mc.load_results(self._last_results, variables, t_start, VARIABLE_META, ZONE_COLORS)
        title = auto_title(model_name, t_start, t_duration, dt)
        mc.set_overall_title(title)
        self._multi_charts.append(mc)
        self._plot_tabs.addTab(mc, "Results")

        self._plot_tabs.currentChanged.connect(self._on_plot_tab_changed)
        self._plot_widget_layout.addWidget(self._plot_tabs, 1)
        self._sync_title_input()


    def _current_multi_chart(self):
        """Return the MultiChartWidget for the currently active plot tab."""
        if not self._multi_charts or self._plot_tabs is None:
            return None
        idx = self._plot_tabs.currentIndex()
        if 0 <= idx < len(self._multi_charts):
            return self._multi_charts[idx]
        return None


    def _sync_title_input(self):
        """Update the title QLineEdit to reflect the active tab's stored title."""
        mc = self._current_multi_chart()
        if mc is not None and hasattr(self, "_title_input"):
            self._title_input.blockSignals(True)
            self._title_input.setText(mc._overall_title)
            self._title_input.blockSignals(False)


    def _on_plot_tab_changed(self, _idx: int):
        """Sync title input and rebuild settings when the active plot tab changes. Args: _idx (int)."""
        self._sync_title_input()
        self._rebuild_plot_settings()


    def create_project_tab(self):
        """Create project tab with zone/zoom controls, component and connection lists. Returns: QWidget."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)
        controls_row = QHBoxLayout()
        controls_row.addWidget(self._create_zone_controls_box())
        controls_row.addWidget(self._create_zoom_controls_box())
        layout.addLayout(controls_row)
        components_title = QLabel("Current Components")
        components_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(components_title)
        layout.addWidget(self.component_list)
        connections_title = QLabel("Current Connections")
        connections_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        layout.addWidget(connections_title)
        layout.addWidget(self.connection_list)
        tab.setLayout(layout)
        return tab


    def _create_plots_tab(self):
        """Create the Plots sidebar tab with settings. Returns: QWidget."""
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(5)

        self._grid_check = QCheckBox("Show grid")
        self._grid_check.setChecked(True)
        self._grid_check.toggled.connect(self._on_grid_toggled)
        outer.addWidget(self._grid_check)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("Overall plot title")
        self._title_input.editingFinished.connect(self._on_title_changed)
        title_row.addWidget(self._title_input)
        outer.addLayout(title_row)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Font size:"))
        self._font_spin = QSpinBox()
        self._font_spin.setRange(7, 20)
        self._font_spin.setValue(9)
        self._font_spin.setFixedWidth(48)
        self._font_spin.valueChanged.connect(self._on_font_size_changed)
        font_row.addWidget(self._font_spin)
        font_row.addStretch()
        outer.addLayout(font_row)

        save_btn = QPushButton("Save Plot…")
        save_btn.clicked.connect(self._save_plot)
        outer.addWidget(save_btn)

        reset_btn = QPushButton("Reset Zoom (or double-click)")
        reset_btn.clicked.connect(self._on_reset_zoom)
        outer.addWidget(reset_btn)

        var_sep = QLabel("Plot Variables")
        var_sep.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 4px;")
        outer.addWidget(var_sep)

        var_scroll = QScrollArea()
        var_scroll.setWidgetResizable(True)
        var_scroll.setMaximumHeight(160)
        var_scroll.setStyleSheet("QScrollArea { border: 1px solid #ccc; border-radius: 3px; }")
        var_container = QWidget()
        self._var_layout = QVBoxLayout(var_container)
        self._var_layout.setContentsMargins(4, 4, 4, 4)
        self._var_layout.setSpacing(2)
        no_sim_lbl = QLabel("Run a simulation to select variables.")
        no_sim_lbl.setStyleSheet("color: #888; font-size: 10px;")
        self._var_layout.addWidget(no_sim_lbl)
        var_scroll.setWidget(var_container)
        outer.addWidget(var_scroll)

        sep = QLabel("Subplots & Lines")
        sep.setStyleSheet("font-weight: bold; font-size: 11px; margin-top: 4px;")
        outer.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ccc; border-radius: 3px; }")
        settings_container = QWidget()
        self._settings_layout = QVBoxLayout(settings_container)
        self._settings_layout.setContentsMargins(4, 4, 4, 4)
        self._settings_layout.setSpacing(4)
        self._settings_layout.addStretch()
        scroll.setWidget(settings_container)
        outer.addWidget(scroll, 1)

        return tab


    def _rebuild_plot_settings(self):
        """Populate per-subplot and per-line controls for the active plot tab."""
        from gui.plot_widget import STYLE_OPTIONS
        mc = self._current_multi_chart()
        if mc is None or self._settings_layout is None:
            return
        while self._settings_layout.count():
            item = self._settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for chart_idx, chart in enumerate(mc.charts):
            hdr = QLabel(chart.ylabel or f"Chart {chart_idx + 1}")
            hdr.setStyleSheet(
                "font-weight: bold; font-size: 10px; color: #222;"
                "border-bottom: 1px solid #bbb; padding-bottom: 2px; margin-top: 6px;"
            )
            self._settings_layout.addWidget(hdr)

            # Subplot title
            sub_row = QHBoxLayout()
            sub_row.addWidget(QLabel("Subplot title:"))
            sub_title = QLineEdit(chart.subplot_title)
            sub_title.setPlaceholderText("(optional)")

            def _sub_title_h(c, field):
                def _f():
                    c.subplot_title = field.text()
                    c.update()
                return _f

            sub_title.editingFinished.connect(_sub_title_h(chart, sub_title))
            sub_row.addWidget(sub_title)
            sub_w = QWidget(); sub_w.setLayout(sub_row)
            self._settings_layout.addWidget(sub_w)

            # Relative height
            h_row = QHBoxLayout()
            h_row.addWidget(QLabel("Height:"))
            h_spin = QSpinBox()
            h_spin.setRange(1, 10); h_spin.setValue(1)
            h_spin.setFixedWidth(46)
            h_spin.setToolTip("Relative height of this subplot (1–10)")

            def _height_h(idx, m):
                def _f(v): m.set_chart_height_weight(idx, v)
                return _f

            h_spin.valueChanged.connect(_height_h(chart_idx, mc))
            h_row.addWidget(h_spin); h_row.addStretch()
            h_w = QWidget(); h_w.setLayout(h_row)
            self._settings_layout.addWidget(h_w)

            # Y axis range
            y_w = QWidget()
            y_row = QHBoxLayout(y_w)
            y_row.setContentsMargins(0, 0, 0, 0); y_row.setSpacing(3)
            y_row.addWidget(QLabel("Y:"))
            y_min_s = QDoubleSpinBox()
            y_min_s.setRange(-1e8, 1e8); y_min_s.setDecimals(2); y_min_s.setSingleStep(1.0)
            y_min_s.setFixedWidth(78); y_min_s.setValue(chart._vy_min)
            y_row.addWidget(y_min_s)
            y_row.addWidget(QLabel("–"))
            y_max_s = QDoubleSpinBox()
            y_max_s.setRange(-1e8, 1e8); y_max_s.setDecimals(2); y_max_s.setSingleStep(1.0)
            y_max_s.setFixedWidth(78); y_max_s.setValue(chart._vy_max)
            y_row.addWidget(y_max_s)
            y_row.addStretch()
            self._settings_layout.addWidget(y_w)

            # X axis range + Auto button
            x_w = QWidget()
            x_row = QHBoxLayout(x_w)
            x_row.setContentsMargins(0, 0, 0, 0); x_row.setSpacing(3)
            x_row.addWidget(QLabel("X:"))
            x_min_s = QDoubleSpinBox()
            x_min_s.setRange(-1e8, 1e8); x_min_s.setDecimals(2); x_min_s.setSingleStep(1.0)
            x_min_s.setFixedWidth(78); x_min_s.setValue(chart._vx_min)
            x_row.addWidget(x_min_s)
            x_row.addWidget(QLabel("–"))
            x_max_s = QDoubleSpinBox()
            x_max_s.setRange(-1e8, 1e8); x_max_s.setDecimals(2); x_max_s.setSingleStep(1.0)
            x_max_s.setFixedWidth(78); x_max_s.setValue(chart._vx_max)
            x_row.addWidget(x_max_s)
            auto_btn = QPushButton("Auto")
            auto_btn.setFixedSize(40, 22)
            auto_btn.setToolTip("Reset both axes to full data range")
            x_row.addWidget(auto_btn)
            x_row.addStretch()
            self._settings_layout.addWidget(x_w)

            def _apply_y(c, lo, hi):
                def _f(): c.set_y_view_range(lo.value(), hi.value())
                return _f

            def _apply_x(c, lo, hi):
                def _f(): c.set_x_view_range(lo.value(), hi.value())
                return _f

            def _auto_h(c, yl, yh, xl, xh):
                def _f():
                    c.reset_view()
                    for s, v in [(yl, c._vy_min), (yh, c._vy_max), (xl, c._vx_min), (xh, c._vx_max)]:
                        s.blockSignals(True); s.setValue(v); s.blockSignals(False)
                return _f

            y_min_s.editingFinished.connect(_apply_y(chart, y_min_s, y_max_s))
            y_max_s.editingFinished.connect(_apply_y(chart, y_min_s, y_max_s))
            x_min_s.editingFinished.connect(_apply_x(chart, x_min_s, x_max_s))
            x_max_s.editingFinished.connect(_apply_x(chart, x_min_s, x_max_s))
            auto_btn.clicked.connect(_auto_h(chart, y_min_s, y_max_s, x_min_s, x_max_s))

            # Per-series line controls
            for series in chart.series:
                row_w = QWidget()
                row = QHBoxLayout(row_w)
                row.setContentsMargins(0, 1, 0, 1)
                row.setSpacing(4)
                swatch = QPushButton()
                swatch.setFixedSize(18, 18)
                swatch.setToolTip("Click to change colour")
                swatch.setStyleSheet(
                    f"background-color: {series.color.name()};"
                    "border: 1px solid #888; border-radius: 2px;"
                )
                lbl = QLabel(series.label)
                lbl.setStyleSheet("font-size: 11px;")
                w_spin = QSpinBox()
                w_spin.setRange(1, 8); w_spin.setValue(series.width)
                w_spin.setFixedWidth(38); w_spin.setToolTip("Line width")
                s_combo = QComboBox()
                for opt in STYLE_OPTIONS:
                    s_combo.addItem(opt)
                s_combo.setCurrentText(series.style)
                s_combo.setFixedWidth(80); s_combo.setToolTip("Line style")

                def _color_h(ser, btn, c):
                    def _f():
                        picked = QColorDialog.getColor(ser.color, self, "Pick colour")
                        if picked.isValid():
                            ser.color = picked
                            btn.setStyleSheet(
                                f"background-color: {picked.name()};"
                                "border: 1px solid #888; border-radius: 2px;"
                            )
                            c.update()
                    return _f

                def _width_h(ser, c):
                    def _f(v): ser.width = v; c.update()
                    return _f

                def _style_h(ser, c):
                    def _f(txt): ser.style = txt; c.update()
                    return _f

                swatch.clicked.connect(_color_h(series, swatch, chart))
                w_spin.valueChanged.connect(_width_h(series, chart))
                s_combo.currentTextChanged.connect(_style_h(series, chart))
                row.addWidget(swatch)
                row.addWidget(lbl, 1)
                row.addWidget(w_spin)
                row.addWidget(s_combo)
                self._settings_layout.addWidget(row_w)

        self._settings_layout.addStretch()


    def _populate_var_checkboxes(self, results: dict):
        """Populate variable checkboxes from simulation results. Args: results (dict)."""
        from simulation.plotter import VARIABLE_META, DEFAULT_PLOT_VARS

        if self._var_layout is None:
            return

        while self._var_layout.count():
            item = self._var_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._var_checkboxes.clear()

        prev = set(self._selected_plot_vars) if self._selected_plot_vars else set(DEFAULT_PLOT_VARS)

        for key, meta in VARIABLE_META.items():
            if key not in results:
                continue
            cb = QCheckBox(meta["label"])
            cb.setChecked(key in prev)
            cb.toggled.connect(self._apply_variable_selection)
            self._var_layout.addWidget(cb)
            self._var_checkboxes[key] = cb

        if not self._var_checkboxes:
            lbl = QLabel("No plottable variables found.")
            lbl.setStyleSheet("color: #888; font-size: 10px;")
            self._var_layout.addWidget(lbl)


    def _apply_variable_selection(self):
        """Rebuild the plot using the currently checked variables."""
        if self._last_results is None:
            return
        selected = [k for k, cb in self._var_checkboxes.items() if cb.isChecked()]
        if not selected:
            return
        self._selected_plot_vars = selected
        self._make_plot_panel()
        self._rebuild_plot_settings()
        self._plot_results_shown = self._last_results
        self.canvas_stack.setCurrentIndex(1)


    def _on_grid_toggled(self, checked: bool):
        """Toggle grid visibility on the active plot. Args: checked (bool)."""
        mc = self._current_multi_chart()
        if mc:
            mc.set_grid(checked)


    def _on_title_changed(self):
        """Apply the title input text to the active plot."""
        mc = self._current_multi_chart()
        if mc:
            mc.set_overall_title(self._title_input.text(), self._font_spin.value() + 2)


    def _on_font_size_changed(self, size: int):
        """Apply a new font size to the active plot. Args: size (int)."""
        mc = self._current_multi_chart()
        if mc:
            mc.set_font_size(size)


    def _on_reset_zoom(self):
        """Reset zoom to full data range on the active plot."""
        mc = self._current_multi_chart()
        if mc:
            mc.reset_view()


    def _save_plot(self):
        """Save the active plot tab to a PNG or JPEG file."""
        mc = self._current_multi_chart()
        if mc is None:
            QMessageBox.information(self, "No Plot", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot",
            str(Path.home() / "simulation_results.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg)",
        )
        if not path:
            return
        mc.save_to_file(path, chart_width=1200, chart_height=240)
        self.statusBar().showMessage(f"Plot saved to {path}", 4000)


    def _generate_component_id(self):
        """Generate next sequential component ID. Returns: str."""
        component_id = f"component-{self.next_component_id:04d}"
        self.next_component_id += 1
        return component_id


    def _extract_component_id_number(self, component_id):
        """Extract numeric suffix from component ID. Args: component_id (str). Returns: int or None."""
        if not isinstance(component_id, str):
            return None
        prefix = "component-"
        if not component_id.startswith(prefix):
            return None
        suffix = component_id[len(prefix):]
        if suffix.isdigit():
            return int(suffix)
        return None


    def _sync_next_component_id(self, component_id):
        """Update next component ID counter based on loaded ID. Args: component_id (str)."""
        suffix_number = self._extract_component_id_number(component_id)
        if suffix_number is None:
            return
        self.next_component_id = max(self.next_component_id, suffix_number + 1)


    def add_component(self, component_name):
        """Add component to canvas by name. Args: component_name (str)."""
        self.canvas.add_component(component_name)
        self.statusBar().showMessage(f"Added {component_name}", 3000)


    def on_component_added(self, component_item):
        """Handle component added to canvas event. Args: component_item (ComponentItem)."""
        if not getattr(component_item, "component_id", None):
            component_item.component_id = self._generate_component_id()
        self._sync_next_component_id(component_item.component_id)
        component_name = component_item.label.toPlainText()
        self._invalidate_plots()
        self.refresh_component_list()
        self.statusBar().showMessage(f"Added {component_name} ({component_item.component_id})", 2500)


    def arm_delete_component(self):
        """Toggle delete component mode on/off."""
        if self.pending_component_action == "delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Delete mode cancelled.", 3000)
            return
        self.set_component_action_mode("delete")
        self.statusBar().showMessage("Delete mode active: click a component on the canvas.", 5000)


    def arm_edit_component(self):
        """Toggle edit component mode on/off."""
        if self.pending_component_action == "edit":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Edit mode cancelled.", 3000)
            return
        self.set_component_action_mode("edit")
        self.statusBar().showMessage("Edit mode active: click a component on the canvas.", 5000)


    def arm_area_delete(self):
        """Toggle area delete mode (rubber-band selection) on/off."""
        if self.pending_component_action == "area-delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Area delete mode cancelled.", 3000)
            return
        self.set_component_action_mode("area-delete")
        self.statusBar().showMessage("Area delete mode active: drag a box over components to remove.", 5000)


    def set_component_action_mode(self, mode):
        """Set current operation mode and sync button states. Args: mode (str or None)."""
        self.pending_component_action = mode
        if self.add_connection_btn is not None:
            self.add_connection_btn.setChecked(mode == "connect")
        if self.edit_component_btn is not None:
            self.edit_component_btn.setChecked(mode == "edit")
        if self.delete_component_btn is not None:
            self.delete_component_btn.setChecked(mode == "delete")
        if self.area_delete_btn is not None:
            self.area_delete_btn.setChecked(mode == "area-delete")
        self.canvas.set_area_delete_mode(mode == "area-delete")
        mode_buttons = {self.add_connection_btn, self.edit_component_btn, self.delete_component_btn, self.area_delete_btn}
        mode_buttons.discard(None)
        if mode is None:
            for button in self.action_buttons:
                button.setEnabled(True)
            self.pending_connection_items.clear()
            self.canvas.scene.clearSelection()
            if self.mode_status_label is not None:
                self.mode_status_label.setText("Mode: Normal")
            return
        for button in self.action_buttons:
            button.setEnabled(button in mode_buttons)
        if self.mode_status_label is None:
            return
        if mode == "connect":
            self.mode_status_label.setText("Mode: Connect (select source and destination)")
        elif mode == "area-delete":
            self.mode_status_label.setText("Mode: Delete Area (drag a selection box)")
        else:
            self.mode_status_label.setText(f"Mode: {mode.title()} (click a component)")


    def _handle_connect_click(self, component_item):
        """Handle component click in connection mode. Args: component_item (ComponentItem)."""
        if component_item in self.pending_connection_items:
            self.pending_connection_items.remove(component_item)
            component_item.setSelected(False)
            self.statusBar().showMessage("Component removed from connection selection.", 2500)
            return
        if len(self.pending_connection_items) >= 2:
            for selected_item in self.pending_connection_items:
                selected_item.setSelected(False)
            self.pending_connection_items.clear()
        self.pending_connection_items.append(component_item)
        component_item.setSelected(True)
        if len(self.pending_connection_items) == 1:
            self.statusBar().showMessage("Connection mode: select destination component.", 3000)
            return
        src_item, dst_item = self.pending_connection_items
        ok, message = self.canvas.add_connection_between_items(src_item, dst_item, src_output = "output", dst_input = "input")
        if ok:
            self._invalidate_plots()
            self.refresh_connection_list()
        self.statusBar().showMessage(message, 4000)
        src_item.setSelected(False)
        dst_item.setSelected(False)
        self.pending_connection_items.clear()
        self.set_component_action_mode(None)
        if not ok:
            self.dialogue_manager.show_info("Add Connection", message)


    def handle_component_click_action(self, component_item):
        """Route component click to appropriate handler based on current mode. Args: component_item (ComponentItem)."""
        if self.pending_component_action == "delete":
            component_name = component_item.label.toPlainText()
            self.canvas.remove_component_item(component_item)
            self._invalidate_plots()
            self.refresh_component_list()
            self.statusBar().showMessage(f"Deleted {component_name}", 4000)
            self.set_component_action_mode(None)
            return
        if self.pending_component_action == "edit":
            component_name = component_item.label.toPlainText()
            component_item.edit_properties()
            self.refresh_component_list()
            self.statusBar().showMessage(f"Edited {component_name}", 4000)
            self.set_component_action_mode(None)
            return
        if self.pending_component_action == "connect":
            self._handle_connect_click(component_item)


    def add_connection(self):
        """Toggle connection mode on/off."""
        if self.pending_component_action == "connect":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Connection mode cancelled.", 3000)
            return
        if self.pending_component_action in {"edit", "delete", "area-delete"}:
            self.statusBar().showMessage("Finish current mode before creating a connection.", 3500)
            return
        self.pending_connection_items.clear()
        self.canvas.scene.clearSelection()
        self.set_component_action_mode("connect")
        self.statusBar().showMessage("Connection mode active: select source component, then destination.", 5000)


    def _invalidate_plots(self):
        """Return to canvas view and clear stored results when canvas state changes."""
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(0)
        if self._left_tabs is not None:
            self._left_tabs.blockSignals(True)
            self._left_tabs.setCurrentIndex(0)
            self._left_tabs.blockSignals(False)
        self._last_results = None
        self._plot_results_shown = None
        self._multi_charts = []
        self._plot_tabs = None


    def view_plots(self):
        """Show the plots in the right panel, rebuilding only when results are new."""
        if self._last_results is None:
            return
        if self._plot_results_shown is not self._last_results:
            self._make_plot_panel()
            self._rebuild_plot_settings()
            self._plot_results_shown = self._last_results
        self.canvas_stack.setCurrentIndex(1)


    def run_simulation(self):
        """Execute building model simulation."""
        from simulation.runner import SimulationError
        self.statusBar().showMessage("Running simulation…")
        try:
            results, variables, t_start = self.building_model.run_simulation()
        except SimulationError as e:
            self.statusBar().showMessage("Simulation failed", 4000)
            QMessageBox.critical(self, "Simulation Error", str(e))
            return
        except Exception as e:
            self.statusBar().showMessage("Simulation failed", 4000)
            QMessageBox.critical(self, "Simulation Error", f"Unexpected error:\n{e}")
            return
        self._last_results = results
        self._last_t_start = t_start
        self._plot_results_shown = None
        n_steps = results["t"].shape[1]
        self.statusBar().showMessage(
            f"Simulation complete — {len(variables)} variables, {n_steps} steps.", 6000
        )
        self._populate_var_checkboxes(results)
        if self._left_tabs is not None:
            self._left_tabs.blockSignals(True)
            self._left_tabs.setCurrentIndex(1)
            self._left_tabs.blockSignals(False)
        self.view_plots()


    def on_canvas_zoom_changed(self, zoom_percent):
        """Update zoom display when canvas zoom changes. Args: zoom_percent (int)."""
        if self.zoom_value_display is not None:
            self.zoom_value_display.setText(f"{int(zoom_percent)}%")


    def _update_zone_display(self):
        """Update zone count display in state manager."""
        self.state_manager.update_zone_display()


    def open_set_time_dialog(self):
        """Open time parameters dialog."""
        self.dialogue_manager.open_set_time_dialog()


    def refresh_component_list(self):
        """Refresh component list display."""
        self.state_manager.refresh_component_list()


    def refresh_connection_list(self):
        """Refresh connection list display."""
        self.state_manager.refresh_connection_list()


    def on_area_deleted(self, count):
        """Handle area delete completion. Args: count (int)."""
        self._invalidate_plots()
        self.refresh_component_list()
        self.set_component_action_mode(None)
        self.statusBar().showMessage(f"Deleted {count} component(s) in selected area.", 4000)


    def save_as_layout(self):
        """Save current building layout to JSON file. Returns: str."""
        component_items = [item for item in self.canvas.scene.items() if hasattr(item, "node") and hasattr(item, "label")]
        for item in component_items:
            if not getattr(item, "component_id", None):
                item.component_id = self._generate_component_id()
            self._sync_next_component_id(item.component_id)

        save_path = self.dialogue_manager.prompt_save_layout_path(self.file_manager.get_saved_dir())
        if save_path is None:
            return False
        save_path = self.file_manager.save_layout(
            model_name = self.building_model.name,
            n_zones = self.building_model.n_zones,
            component_items = component_items,
            visual_connections = self.canvas.visual_connections,
            time_data = {
                "t_start": self.building_model.t_start,
                "t_duration": self.building_model.t_duration,
                "dt": self.building_model.dt,
            },
            save_path = save_path,
        )
        self.statusBar().showMessage(f"Saved layout to {save_path}", 5000)
        self.file_path = save_path
        return str(save_path)
    
    def save_layout(self):
        """Save current building layout to JSON file. Returns: str."""
        component_items = [item for item in self.canvas.scene.items() if hasattr(item, "node") and hasattr(item, "label")]
        for item in component_items:
            if not getattr(item, "component_id", None):
                item.component_id = self._generate_component_id()
            self._sync_next_component_id(item.component_id)

        save_path = self.file_path
        if save_path is None:
            return self.save_as_layout()
        save_path = self.file_manager.save_layout(
            model_name = self.building_model.name,
            n_zones = self.building_model.n_zones,
            component_items = component_items,
            visual_connections = self.canvas.visual_connections,
            time_data = {
                "t_start": self.building_model.t_start,
                "t_duration": self.building_model.t_duration,
                "dt": self.building_model.dt,
            },
            save_path = save_path,
        )
        self.statusBar().showMessage(f"Saved layout to {save_path}", 5000)
        return str(save_path)


    def load_layout(self):
        """Load building layout from JSON file. Returns: bool."""
        load_path = self.dialogue_manager.prompt_load_layout_path(self.file_manager.get_saved_dir())
        if load_path is None:
            return False
        payload = self.file_manager.load_payload_from_path(load_path)
        self.canvas.clear_all()
        self.next_component_id = 1
        self.building_model.name = self.file_manager.get_model_name(payload, self.building_model.name)
        loaded_n_zones = self.file_manager.get_n_zones(payload, self.building_model.n_zones)
        self.building_model.update_n_zones(loaded_n_zones)
        self._update_zone_display()
        component_sections = self.file_manager.get_component_sections(payload)
        items = []
        items_by_id = {}
        for component_data in self.file_manager.get_components(payload):
            component_id = component_data.get("id")
            component_section = component_sections.get(component_id, {})
            section_position = component_section.get("position", {})
            position_x = component_data.get("x", section_position.get("x", 0))
            position_y = component_data.get("y", section_position.get("y", 0))
            values = component_data.get("values", component_section.get("values", {}))
            item = self.canvas.add_component(
                component_data["type"],
                self.canvas.mapToScene(self.canvas.viewport().rect().center()),
                component_id = component_id,
                component_values = values,
            )
            item.setPos(position_x, position_y)
            items.append(item)
            if item.component_id:
                items_by_id[item.component_id] = item
                self._sync_next_component_id(item.component_id)
        if not items and component_sections:
            for component_id, component_section in component_sections.items():
                component_type = component_section.get("type")
                if not component_type:
                    continue
                position = component_section.get("position", {})
                item = self.canvas.add_component(
                    component_type,
                    self.canvas.mapToScene(self.canvas.viewport().rect().center()),
                    component_id = component_id,
                    component_values = component_section.get("values", {}),
                )
                item.setPos(position.get("x", 0), position.get("y", 0))
                items.append(item)
                if item.component_id:
                    items_by_id[item.component_id] = item
                    self._sync_next_component_id(item.component_id)
        inferred_n_zones = self.building_model.infer_n_zones_from_components()
        effective_n_zones = max(int(loaded_n_zones), int(inferred_n_zones))
        if effective_n_zones != int(self.building_model.n_zones):
            self.building_model.update_n_zones(effective_n_zones)
        self._update_zone_display()
        for connection_data in self.file_manager.get_connections(payload):
            src_item = items_by_id.get(connection_data.get("src_id"))
            dst_item = items_by_id.get(connection_data.get("dst_id"))
            if src_item is None or dst_item is None:
                src_index = connection_data.get("src")
                dst_index = connection_data.get("dst")
                if isinstance(src_index, int) and isinstance(dst_index, int) and 0 <= src_index < len(items) and 0 <= dst_index < len(items):
                    src_item = items[src_index]
                    dst_item = items[dst_index]
            if src_item is None or dst_item is None or src_item == dst_item:
                continue
            self.canvas.scene.clearSelection()
            src_item.setSelected(True)
            dst_item.setSelected(True)
            self.canvas.add_connection_between_items(
                src_item,
                dst_item,
                src_output = connection_data.get("src_output", "output"),
                dst_input = connection_data.get("dst_input", "input"),
            )
            src_item.setSelected(False)
            dst_item.setSelected(False)
        time_data = self.file_manager.get_time_data(payload)
        self.building_model.t_start = float(time_data.get("t_start", self.building_model.t_start))
        self.building_model.t_duration = float(time_data.get("t_duration", self.building_model.t_duration))
        self.building_model.dt = float(time_data.get("dt", self.building_model.dt))
        self._invalidate_plots()
        self.refresh_component_list()
        self.canvas.center_view()
        self.statusBar().showMessage(f"Loaded layout from {load_path}", 4000)
        self.file_path = load_path
        return True
