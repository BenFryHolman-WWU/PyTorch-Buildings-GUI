"""Main window UI construction and setup helpers."""

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .main_window_helpers import COMPONENTS, COMPONENT_ICON_NAMES, _button_style, _policy_toggle_style


class MainWindowUiMixin:
    def _window_ui_scale(self):
        width = self.width() if hasattr(self, "width") else 1500
        if width < 1180:
            return 0.95
        return min(1.45, max(1.0, width / 1500))

    def _component_drag_button_style(self, scale):
        font_size = round(10 * scale)
        radius = round(5 * scale)
        pad_v = round(5 * scale)
        pad_h = round(4 * scale)
        return (
            "QToolButton { border: 1px solid #d8ddeb; background: #ffffff;"
            f" padding: {pad_v}px {pad_h}px; color: #33405f; font-size: {font_size}px;"
            f" border-radius: {radius}px; }}"
            "QToolButton:hover { background: #ffffff; border-color: #8fb0df; color: #173b73; }"
            "QToolButton:pressed { background: #ffffff; border-color: #6f95d0; }"
        )

    def _sync_responsive_ui_scale(self):
        scale = self._window_ui_scale()
        scale_key = round(scale, 2)
        if getattr(self, "_last_sidebar_scale_key", None) == scale_key:
            return
        self._last_sidebar_scale_key = scale_key
        if getattr(self, "_left_tabs", None) is not None:
            self._left_tabs.setMinimumWidth(round(260 * scale))
        if getattr(self, "_component_palette_header", None) is not None:
            self._component_palette_header.setStyleSheet(
                "QLabel { background: transparent; color: #7a88b0; border: none;"
                f" font-size: {round(9 * scale)}px; font-weight: 700; letter-spacing: 1px; }}"
            )
        for button in getattr(self, "_component_palette_buttons", []):
            button.setIconSize(QSize(round(24 * scale), round(24 * scale)))
            button.setMinimumHeight(round(54 * scale))
            button.setStyleSheet(self._component_drag_button_style(scale))

    def _set_undo_enabled(self, enabled):
        if self.undo_btn is not None:
            self.undo_btn.setEnabled(bool(enabled) and self.pending_component_action is None)

    def _set_redo_enabled(self, enabled):
        if self.redo_btn is not None:
            self.redo_btn.setEnabled(bool(enabled) and self.pending_component_action is None)

    def _canvas_component_count(self):
        return len([item for item in self.building_model.componentItems if item is not None])

    def _button_for_component_action_mode(self, mode):
        return {
            "connect": self.add_connection_btn,
            "edit": self.edit_component_btn,
            "delete": self.delete_component_btn,
            "delete-connection": self.delete_connection_btn,
            "area-delete": self.area_delete_btn,
        }.get(mode)

    def _sync_action_button_availability(self):
        """Summary: Sync action button availability."""
        if self.pending_component_action is not None:
            active_button = self._button_for_component_action_mode(self.pending_component_action)
            for button in self.action_buttons:
                button.setEnabled(button is active_button)
            self._set_undo_enabled(False)
            self._set_redo_enabled(False)
            return

        has_components = self._canvas_component_count() > 0
        has_connections = bool(self.canvas.visual_connections)
        for button in self.action_buttons:
            button.setEnabled(True)
        for button in (
            self.add_connection_btn,
            self.edit_component_btn,
            self.delete_component_btn,
            self.area_delete_btn,
        ):
            if button is not None:
                button.setEnabled(has_components)
        if self.delete_connection_btn is not None:
            self.delete_connection_btn.setEnabled(has_connections)
        self._set_undo_enabled(self.stack.canUndo())
        self._set_redo_enabled(self.stack.canRedo())

    def setup_mode_status_label(self):
        self.mode_status_label = None

    def create_left_panel(self):
        self._left_tabs = QTabWidget()
        self._left_tabs.setDocumentMode(True)
        self._left_tabs.setMinimumWidth(260)
        self._left_tabs.addTab(self.create_project_tab(), "Project")
        self._left_tabs.addTab(self._create_simulation_tab(), "Simulation")
        self._left_tabs.addTab(self._create_plots_tab(), "Plots")
        self._left_tabs.tabBar().setExpanding(True)
        self._left_tabs.currentChanged.connect(self._on_left_tab_changed)
        return self._left_tabs

    def _on_left_tab_changed(self, index):
        """Summary: On left tab changed."""
        if index == 2 or (
            index == 1
            and (
                self._last_results is not None
                or self._plot_progress_bar is not None
                or (self._sim_thread is not None and self._sim_thread.isRunning())
            )
        ):
            self.view_plots()
        else:
            if hasattr(self, "canvas_stack"):
                self.canvas_stack.setCurrentIndex(0)

    def _create_info_box(self, title):
        """
        Summary: Create info box.
        Returns: Return the computed value.
        """
        box = QWidget()
        box.setStyleSheet(
            "background: #fafbfd; border: 1px solid #d0d4e8;"
            " border-radius: 5px; color: #2c3454;"
        )
        layout = QHBoxLayout(box)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; border: none; background: transparent; font-size: 11px;")
        value_label = QLabel("-")
        value_label.setStyleSheet("border: none; background: transparent; font-size: 11px;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return box, value_label

    def _create_zone_controls_box(self):
        """
        Summary: Create zone controls box.
        Returns: Return the computed value.
        """
        _BTN = (
            "QPushButton { background: #4878C8; color: #fff; border: none;"
            " border-radius: 3px; font-weight: 700; font-size: 11px; }"
            "QPushButton:hover { background: #5a8fd1; }"
            "QPushButton:pressed { background: #3a68b8; }"
        )
        box = QWidget()
        box.setStyleSheet(
            "background: #fafbfd; border: 1px solid #d0d4e8;"
            " border-radius: 5px; color: #2c3454;"
        )
        layout = QHBoxLayout(box)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)
        title_label = QLabel("Zones:")
        title_label.setStyleSheet("font-weight: 600; border: none; background: transparent; font-size: 10px;")
        zone_dec_btn = QPushButton("−")
        zone_dec_btn.setFixedSize(18, 18)
        zone_dec_btn.setStyleSheet(_BTN)
        zone_dec_btn.clicked.connect(lambda: self._change_n_zones(-1))
        self.zone_value_display = QLabel(str(int(self.building_model.n_zones)))
        self.zone_value_display.setStyleSheet("border: none; background: transparent; min-width: 18px; font-size: 10px;")
        self.zone_value_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zone_inc_btn = QPushButton("+")
        zone_inc_btn.setFixedSize(18, 18)
        zone_inc_btn.setStyleSheet(_BTN)
        zone_inc_btn.clicked.connect(lambda: self._change_n_zones(1))
        layout.addWidget(title_label)
        layout.addWidget(zone_dec_btn)
        layout.addWidget(self.zone_value_display)
        layout.addWidget(zone_inc_btn)
        return box

    def _change_n_zones(self, delta):
        new_n = max(1, int(self.building_model.n_zones) + delta)
        self.building_model.update_n_zones(new_n)
        self._invalidate_plots()
        self._update_zone_display()
        self.refresh_component_list()

    def _create_zoom_controls_box(self):
        """
        Summary: Create zoom controls box.
        Returns: Return the computed value.
        """
        _BTN = (
            "QPushButton { background: #4878C8; color: #fff; border: none;"
            " border-radius: 3px; font-weight: 700; font-size: 11px; }"
            "QPushButton:hover { background: #5a8fd1; }"
            "QPushButton:pressed { background: #3a68b8; }"
        )
        _CENTER_BTN = (
            "QPushButton { background: transparent; color: #4a5578; border: 1px solid transparent;"
            " border-radius: 3px; padding: 1px; }"
            "QPushButton:hover { background: transparent; border-color: #8fb0df; }"
            "QPushButton:pressed { background: #eef1f7; border-color: #d0d4e8; }"
        )
        box = QWidget()
        box.setStyleSheet(
            "background: #fafbfd; border: 1px solid #d0d4e8;"
            " border-radius: 5px; color: #2c3454;"
        )
        layout = QHBoxLayout(box)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(2)
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedSize(18, 18)
        zoom_out_btn.setStyleSheet(_BTN)
        zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        self.zoom_value_display = QLineEdit(str(self.canvas.get_zoom_percent()))
        self.zoom_value_display.setValidator(QIntValidator(25, 250, self.zoom_value_display))
        self.zoom_value_display.setFixedWidth(30)
        self.zoom_value_display.setStyleSheet(
            "QLineEdit { border: 1px solid transparent; background: transparent;"
            " font-size: 10px; padding: 1px 0; }"
            "QLineEdit:focus { border: 1px solid #9db8e4; background: #ffffff; border-radius: 3px; }"
        )
        self.zoom_value_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_value_display.editingFinished.connect(self.apply_canvas_zoom_entry)
        zoom_percent_label = QLabel("%")
        zoom_percent_label.setStyleSheet("border: none; background: transparent; font-size: 10px;")
        zoom_percent_label.setFixedWidth(10)
        zoom_percent_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(18, 18)
        zoom_in_btn.setStyleSheet(_BTN)
        zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        center_btn = QPushButton()
        center_btn.setIcon(self.canvas.icons.icon("center", "center_asset", fallback_text="Center"))
        center_btn.setIconSize(QSize(16, 16))
        center_btn.setFixedSize(26, 22)
        center_btn.setToolTip("Center canvas")
        center_btn.setStyleSheet(_CENTER_BTN)
        center_btn.clicked.connect(self.canvas.center_view)
        layout.addWidget(zoom_out_btn)
        layout.addWidget(self.zoom_value_display)
        layout.addWidget(zoom_percent_label)
        layout.addSpacing(2)
        layout.addWidget(zoom_in_btn)
        layout.addSpacing(2)
        layout.addWidget(center_btn)
        return box

    def create_right_panel(self):
        """
        Summary: Create right panel.
        Returns: Return the computed value.
        """
        from PyQt6.QtWidgets import QStackedWidget

        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        self.canvas_stack = QStackedWidget()
        self.canvas_stack.addWidget(self.canvas)
        self._plot_widget = QWidget()
        self._plot_widget_layout = QVBoxLayout(self._plot_widget)
        self._plot_widget_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_widget_layout.setSpacing(0)
        self.canvas_stack.addWidget(self._plot_widget)
        self._no_sim_widget = self._create_no_sim_placeholder()
        self.canvas_stack.addWidget(self._no_sim_widget)
        panel_layout.addWidget(self.canvas_stack, 1)
        return panel

    def _create_no_sim_placeholder(self):
        """
        Summary: Create no sim placeholder.
        Returns: Return the computed value.
        """
        w = QWidget()
        w.setStyleSheet("background: #f0f2f8;")
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = QLabel("No simulation has been run yet.\nRun a simulation to view plots.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            "color: #8898b8; font-size: 14px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(msg)
        return w

    def create_project_tab(self):
        """
        Summary: Create project tab.
        Returns: Return the computed value.
        """
        from .interactive_canvas import DragButton
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(6)
        controls_row.addWidget(self._create_zoom_controls_box())
        controls_row.addWidget(self._create_zone_controls_box())
        layout.addLayout(controls_row)

        palette_box = QWidget()
        palette_box.setStyleSheet(
            "QWidget#palette { background: #f7f8fb; border: 1px solid #d8ddeb;"
            " border-radius: 6px; }"
        )
        palette_box.setObjectName("palette")
        palette_layout = QVBoxLayout(palette_box)
        palette_layout.setContentsMargins(6, 5, 6, 6)
        palette_layout.setSpacing(4)

        pal_hdr = QLabel("COMPONENTS")
        self._component_palette_header = pal_hdr
        palette_layout.addWidget(pal_hdr)

        from PyQt6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scale = self._window_ui_scale()
        drag_button_style = self._component_drag_button_style(scale)
        for i, cls in enumerate(COMPONENTS):
            btn = DragButton(cls.__name__, cls.__name__)
            btn.setIcon(self.icons.icon(
                *COMPONENT_ICON_NAMES.get(cls.__name__, (cls.__name__,)),
                fallback_text=cls.__name__,
            ))
            btn.setIconSize(QSize(round(24 * scale), round(24 * scale)))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setAutoRaise(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(round(54 * scale))
            btn.setStyleSheet(drag_button_style)
            grid.addWidget(btn, i // 2, i % 2)
            self._component_palette_buttons.append(btn)
        self._sync_responsive_ui_scale()
        palette_layout.addLayout(grid)
        layout.addWidget(palette_box)

        layout.addWidget(self.component_list, 1)
        layout.addWidget(self.connection_list, 1)
        return tab

    def _create_simulation_tab(self):
        """
        Summary: Create simulation tab.
        Returns: Return the computed value.
        """
        import math

        _SECTION_HDR = (
            "QLabel { background: #e2e6f0; color: #3a4468; border-radius: 3px;"
            " padding: 2px 6px; font-weight: 700; font-size: 9px; letter-spacing: 1px; }"
        )
        _FIELD = (
            "QLineEdit { border: 1px solid #c8ccdc; border-radius: 4px;"
            " padding: 3px 6px; font-size: 11px; background: #fafbfd; color: #2c3454; }"
            "QLineEdit:focus { border-color: #4a7fc1; }"
            "QLineEdit:disabled { background: #e3e7f1; color: #8d97ae; border-color: #d3d8e6; }"
        )
        _HINT = "QLabel { font-size: 10px; color: #8898b8; background: transparent; }"
        _DATA_HINT = "QLabel { font-size: 12px; color: #5f6f90; background: transparent; }"
        _LBL  = "QLabel { font-size: 11px; color: #3a4468; background: transparent; }"
        def _fmt_time(secs):
            try:
                secs = float(secs) % 86400
                h = int(secs // 3600)
                m = int((secs % 3600) // 60)
                h12 = ((h - 1) % 12) + 1
                return f"{h12}:{m:02d} {'AM' if h < 12 else 'PM'}"
            except Exception:
                return ""

        def _fmt_hours(secs):
            try:
                return f"{float(secs) / 3600:.1f} hrs"
            except Exception:
                return ""

        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(10)
        data_hdr = QLabel("INPUT DATA")
        data_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(data_hdr)
        data_box = QWidget()
        data_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        data_box.setStyleSheet(
            "QWidget { background: #f8f9fc; border: 1px solid #d0d4e8; border-radius: 6px; }"
        )
        data_layout = QVBoxLayout(data_box)
        data_layout.setContentsMargins(10, 8, 10, 8)
        data_layout.setSpacing(6)
        self._input_data_label = QLabel("Using generated simulation inputs.")
        self._input_data_label.setWordWrap(True)
        self._input_data_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._input_data_label.setStyleSheet(_DATA_HINT)
        data_layout.addWidget(self._input_data_label, 0)
        data_btn_row = QHBoxLayout()
        data_btn_row.setSpacing(6)
        load_data_btn = QPushButton("Load CSV")
        load_data_btn.setStyleSheet(
            "QPushButton { background: #fafbfd; color: #3a4468; border: 1px solid #c4c9dc;"
            " border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background: #eaecf5; border-color: #a8b0cc; }"
        )
        load_data_btn.clicked.connect(self.load_input_data)
        clear_data_btn = QPushButton("Clear")
        clear_data_btn.setStyleSheet(load_data_btn.styleSheet())
        clear_data_btn.clicked.connect(self.clear_input_data)
        data_btn_row.addWidget(load_data_btn)
        data_btn_row.addWidget(clear_data_btn)
        data_btn_row.addStretch(1)
        data_layout.addLayout(data_btn_row)
        outer.addWidget(data_box)
        self.refresh_input_data_label()
        time_hdr = QLabel("TIME SETTINGS")
        time_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(time_hdr)

        time_box = QWidget()
        time_box.setStyleSheet(
            "QWidget { background: #f8f9fc; border: 1px solid #d0d4e8; border-radius: 6px; }"
        )
        time_form = QVBoxLayout(time_box)
        time_form.setContentsMargins(10, 8, 10, 8)
        time_form.setSpacing(8)

        def _time_row(label_text, current_val, on_change, hint_fn):
            """
            Summary: Time row.
            Args: label_text, current_val, on_change, hint_fn
            Returns: Return the computed value.
            """
            row_w = QWidget()
            row_w.setStyleSheet("QWidget { background: transparent; border: none; }")
            row = QVBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(_LBL)
            field = QLineEdit(str(current_val))
            field.setStyleSheet(_FIELD)
            hint = QLabel(hint_fn(current_val))
            hint.setStyleSheet(_HINT)
            top.addWidget(lbl)
            top.addWidget(field, 1)
            top.addWidget(hint)
            row.addLayout(top)

            def _changed():
                try:
                    v = float(field.text())
                    on_change(v)
                    hint.setText(hint_fn(v))
                    self._clear_cached_simulation_results()
                except ValueError:
                    pass

            field.editingFinished.connect(_changed)
            return row_w

        time_form.addWidget(_time_row(
            "Start (s)",
            self.building_model.t_start,
            lambda v: setattr(self.building_model, "t_start", v),
            _fmt_time,
        ))
        time_form.addWidget(_time_row(
            "Duration (s)",
            self.building_model.t_duration,
            lambda v: setattr(self.building_model, "t_duration", v),
            _fmt_hours,
        ))
        time_form.addWidget(_time_row(
            "Time step (s)",
            self.building_model.dt,
            lambda v: setattr(self.building_model, "dt", v),
            lambda v: f"{int(float(v))} sec" if v else "",
        ))
        outer.addWidget(time_box)
        policy_hdr = QLabel("CONTROL POLICY")
        policy_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(policy_hdr)

        policy_box = QWidget()
        policy_box.setStyleSheet(
            "QWidget { background: #f8f9fc; border: 1px solid #d0d4e8; border-radius: 6px; }"
        )
        policy_form = QVBoxLayout(policy_box)
        policy_form.setContentsMargins(10, 8, 10, 8)
        policy_form.setSpacing(8)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(6)
        self._control_policy_toggle_btn = QPushButton()
        self._control_policy_toggle_btn.setFixedSize(14, 14)
        self._control_policy_toggle_btn.setToolTip("Toggle control policy override")
        self._control_policy_toggle_btn.clicked.connect(self._toggle_control_policy_override)
        self._control_policy_toggle_label = QLabel()
        self._control_policy_toggle_label.setStyleSheet(_LBL)
        toggle_row.addWidget(self._control_policy_toggle_btn)
        toggle_row.addWidget(self._control_policy_toggle_label)
        toggle_row.addStretch(1)

        def _policy_row(label_text, attr, hint_text):
            """
            Summary: Policy row.
            Args: label_text, attr, hint_text
            Returns: Return the computed value.
            """
            row_w = QWidget()
            row_w.setStyleSheet("QWidget { background: transparent; border: none; }")
            row = QVBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(_LBL)
            field = QLineEdit(str(getattr(self.building_model, attr)))
            self._control_policy_inputs[attr] = field
            field.setStyleSheet(_FIELD)
            hint = QLabel(hint_text)
            hint.setStyleSheet(_HINT)
            top.addWidget(lbl)
            top.addWidget(field, 1)
            top.addWidget(hint)
            row.addLayout(top)

            def _changed():
                """Summary: Changed."""
                try:
                    value = float(field.text())
                except ValueError:
                    field.setText(str(getattr(self.building_model, attr)))
                    return
                if attr == "tu_T_supply_setpoint":
                    self.building_model.set_control_policy(tu_T_supply_setpoint=value)
                elif attr == "rtu_supply_airflow_setpoint":
                    self.building_model.set_control_policy(rtu_supply_airflow_setpoint=value)
                else:
                    setattr(self.building_model, attr, value)
                self._clear_cached_simulation_results()

            field.editingFinished.connect(_changed)
            return row_w

        policy_form.addWidget(_policy_row(
            "Supply temp",
            "tu_T_supply_setpoint",
            "K",
        ))
        policy_form.addWidget(_policy_row(
            "Supply airflow",
            "rtu_supply_airflow_setpoint",
            "kg/s",
        ))
        policy_form.addLayout(toggle_row)
        self._sync_control_policy_inputs()
        outer.addWidget(policy_box)
        run_hdr = QLabel("RUN")
        run_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(run_hdr)

        self._run_btn = QPushButton("Run Simulation")
        self._run_btn.setStyleSheet(self._run_btn_run_style)
        self._run_btn.setFixedHeight(40)
        self._run_btn.clicked.connect(self._on_run_btn_clicked)
        outer.addWidget(self._run_btn)
        self._stop_btn = QPushButton("Stop Simulation")
        self._stop_btn.setStyleSheet(self._run_btn_stop_style)
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.clicked.connect(self.on_stop_resume_clicked)
        self._stop_btn.setEnabled(False)
        outer.addWidget(self._stop_btn)
        issues_hdr = QLabel("POTENTIAL ISSUES")
        issues_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(issues_hdr)
        self._setup_issue_list = QTreeWidget()
        self._setup_issue_list.setHeaderHidden(True)
        self._setup_issue_list.setRootIsDecorated(False)
        self._setup_issue_list.setMinimumHeight(90)
        self._setup_issue_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_issue_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._setup_issue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._setup_issue_list.setStyleSheet(
            "QTreeWidget { background: #f8f9fc; border: 1px solid #d0d4e8;"
            " border-radius: 6px; padding: 3px; font-size: 10px; color: #3a4468; }"
            "QTreeWidget::item { padding: 2px 3px; }"
            "QScrollBar:vertical { background: transparent; width: 7px; margin: 5px 2px 5px 0; }"
            "QScrollBar::handle:vertical { background: #b8c1d8; border-radius: 3px; min-height: 24px; }"
            "QScrollBar::handle:vertical:hover { background: #92a0c0; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )
        outer.addWidget(self._setup_issue_list, 1)
        self.refresh_setup_issues()

        return tab

    def _sync_control_policy_inputs(self):
        """Summary: Sync control policy inputs."""
        for attr, field in self._control_policy_inputs.items():
            field.blockSignals(True)
            field.setText(str(getattr(self.building_model, attr)))
            field.setEnabled(bool(self.building_model.use_control_policy_override))
            field.blockSignals(False)
        if self._control_policy_toggle_btn is not None:
            enabled = bool(self.building_model.use_control_policy_override)
            self._control_policy_toggle_btn.setStyleSheet(_policy_toggle_style(enabled))
            self._control_policy_toggle_btn.setToolTip(
                "Control policy override enabled" if enabled else "Control policy override disabled"
            )
        if self._control_policy_toggle_label is not None:
            self._control_policy_toggle_label.setText(
                "Using custom values" if self.building_model.use_control_policy_override else "Using generated values"
            )

    def _toggle_control_policy_override(self):
        self.building_model.use_control_policy_override = not bool(self.building_model.use_control_policy_override)
        self._sync_control_policy_inputs()
        keep_plot_screen = hasattr(self, "canvas_stack") and self.canvas_stack.currentIndex() in (1, 2)
        self._clear_cached_simulation_results(keep_plot_screen=keep_plot_screen)

    def _zone_value_shape(self, value):
        """
        Summary: Zone value shape.
        Returns: Return the computed value.
        """
        if hasattr(value, "shape"):
            shape = tuple(int(dim) for dim in value.shape)
            if len(shape) == 1:
                return (shape[0],)
            if len(shape) == 2:
                return shape
            return ()
        if isinstance(value, list):
            if value and isinstance(value[0], list):
                return (len(value), max((len(row) for row in value), default=0))
            return (len(value),)
        return ()

    def _numeric_values(self, value):
        """
        Summary: Numeric values.
        Returns: Return the computed value.
        """
        if hasattr(value, "detach"):
            value = value.detach().cpu().tolist()
        if isinstance(value, list):
            numbers = []
            for item in value:
                numbers.extend(self._numeric_values(item))
            return numbers
        try:
            return [float(value)]
        except (TypeError, ValueError):
            return []

    def _matrix_rows(self, value):
        if hasattr(value, "detach"):
            value = value.detach().cpu().tolist()
        if isinstance(value, list) and value and isinstance(value[0], list):
            return value
        return []

    def collect_setup_issues(self):
        """
        Summary: Collect setup issues.
        Returns: Return the computed value.
        """
        issues = []
        component_items = [ci for ci in self.building_model.componentItems if ci is not None]
        if not component_items:
            return ["No components on the canvas."]

        component_names = [ci.label.toPlainText() for ci in component_items]
        duplicate_names = sorted({name for name in component_names if component_names.count(name) > 1})
        if duplicate_names:
            issues.append("Duplicate component types: " + ", ".join(duplicate_names))

        expected = {"Envelope", "RTU", "VAVBox", "SolarGains"}
        missing = sorted(expected - set(component_names))
        if missing:
            issues.append("Full HVAC setup is missing: " + ", ".join(missing))

        if len(component_items) > 1 and not self.building_model.connections:
            issues.append("No component connections have been created.")

        connected_nodes = set()
        for connection in self.building_model.connections:
            connected_nodes.add(connection.srcNode)
            connected_nodes.add(connection.dstNode)
        isolated = [
            ci.label.toPlainText()
            for ci in component_items
            if getattr(ci, "node", None) not in connected_nodes and len(component_items) > 1
        ]
        if isolated:
            issues.append("Component with no connections: " + ", ".join(sorted(isolated)))

        n_zones = int(self.building_model.n_zones)
        zone_attrs = {
            "Envelope": ["R_env", "C_env", "adjacency"],
            "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max"],
            "SolarGains": ["window_orientation"],
        }
        positive_attrs = {
            "Envelope": ["R_env", "C_env", "R_internal"],
            "VAVBox": ["airflow_max", "control_gain"],
            "SolarGains": ["window_area", "window_shgc", "max_solar_irradiance"],
        }
        nonnegative_attrs = {
            "VAVBox": ["airflow_min", "Q_reheat_max"],
        }
        for ci in component_items:
            component = ci.component
            component_name = type(component).__name__
            if hasattr(component, "n_zones") and int(component.n_zones) != n_zones:
                issues.append(f"{component_name} zone count is {component.n_zones}, expected {n_zones}.")
            for attr in zone_attrs.get(component_name, []):
                if not hasattr(component, attr):
                    continue
                shape = self._zone_value_shape(getattr(component, attr))
                if shape and any(dim != n_zones for dim in shape):
                    issues.append(f"{component_name}.{attr} has shape {shape}, expected {n_zones}.")
            for attr in positive_attrs.get(component_name, []):
                if not hasattr(component, attr):
                    continue
                if any(value <= 0 for value in self._numeric_values(getattr(component, attr))):
                    issues.append(f"{component_name}.{attr} has zero or negative values; update zone data.")
            for attr in nonnegative_attrs.get(component_name, []):
                if not hasattr(component, attr):
                    continue
                if any(value < 0 for value in self._numeric_values(getattr(component, attr))):
                    issues.append(f"{component_name}.{attr} has negative values; update zone data.")
            if component_name == "Envelope" and hasattr(component, "adjacency"):
                rows = self._matrix_rows(getattr(component, "adjacency"))
                zero_rows = [
                    index + 1 for index, row in enumerate(rows[:n_zones])
                    if len(row) < n_zones or not any(float(value) != 0.0 for value in row[:n_zones])
                ]
                if zero_rows:
                    issues.append(
                        "Envelope.adjacency has disconnected zone row(s): "
                        + ", ".join(str(index) for index in zero_rows)
                        + "."
                    )
            if component_name == "VAVBox" and hasattr(component, "airflow_min") and hasattr(component, "airflow_max"):
                mins = self._numeric_values(component.airflow_min)
                maxes = self._numeric_values(component.airflow_max)
                invalid_zones = [
                    index + 1 for index, (min_value, max_value) in enumerate(zip(mins, maxes))
                    if max_value <= min_value
                ]
                if invalid_zones:
                    issues.append(
                        "VAVBox airflow_max must be greater than airflow_min for zone(s): "
                        + ", ".join(str(index) for index in invalid_zones)
                        + "."
                    )

        if float(self.building_model.t_duration) <= 0:
            issues.append("Simulation duration must be greater than 0.")
        if float(self.building_model.dt) <= 0:
            issues.append("Simulation time step must be greater than 0.")
        elif float(self.building_model.dt) > float(self.building_model.t_duration):
            issues.append("Simulation time step is longer than the duration.")
        if float(self.building_model.rtu_supply_airflow_setpoint) <= 0:
            issues.append("Supply airflow setpoint should be greater than 0.")
        input_summary = self.building_model.input_data_summary or {}
        input_zone_count = int(input_summary.get("zone_count") or 0)
        if self.building_model.input_data_path and input_zone_count and input_zone_count != n_zones:
            issues.append(f"Input data has {input_zone_count} zones, project has {n_zones}.")
        if self.building_model.input_data_path and not input_summary.get("mapped_keys"):
            issues.append("Input data file has no supported simulation input columns.")

        return issues

    def refresh_setup_issues(self):
        """Summary: Refresh setup issues."""
        if self._setup_issue_list is None:
            return
        self._setup_issue_list.clear()
        issues = self.collect_setup_issues()
        if not issues:
            item = QTreeWidgetItem(["No setup issues detected."])
            item.setForeground(0, QColor("#2f8a5f"))
            self._setup_issue_list.addTopLevelItem(item)
            return
        for issue in issues:
            item = QTreeWidgetItem([issue])
            item.setForeground(0, QColor("#9a5b1f"))
            self._setup_issue_list.addTopLevelItem(item)

    def refresh_input_data_label(self):
        """Summary: Refresh input data label."""
        if self._input_data_label is None:
            return
        if not self.building_model.input_data_path:
            self._input_data_label.setText("Using generated simulation inputs.")
            return
        summary = self.building_model.input_data_summary or {}
        file_name = Path(self.building_model.input_data_path).name
        mapped = ", ".join(summary.get("mapped_keys", [])) or "no supported columns"
        self._input_data_label.setText(
            f"{file_name}\n{summary.get('row_count', 0)} rows, "
            f"{summary.get('zone_count', 0)} zones, mapped: {mapped}"
        )

    def load_input_data(self):
        """Summary: Load input data."""
        from simulation.input_data import inspect_input_csv
        start_dir = self.file_manager.get_input_data_dir()
        path = self.dialogue_manager.prompt_input_data_path(start_dir)
        if path is None:
            return
        try:
            self.building_model.input_data_summary = inspect_input_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Input Data Error", f"Could not read input data:\n{exc}")
            return
        self.building_model.input_data_path = str(path)
        self.last_dir = Path(path).parent
        self._clear_cached_simulation_results()
        self.refresh_input_data_label()
        self.refresh_setup_issues()
        self.statusBar().showMessage(f"Loaded input data from {path}", 4000)

    def clear_input_data(self):
        self.building_model.input_data_path = None
        self.building_model.input_data_summary = {}
        self._clear_cached_simulation_results()
        self.refresh_input_data_label()
        self.refresh_setup_issues()
        self.statusBar().showMessage("Using generated simulation inputs.", 3000)
