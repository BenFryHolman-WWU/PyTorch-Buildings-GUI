"""Main window plot panel and plot-settings helpers."""

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QDoubleValidator, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QColorDialog, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget, QWidgetAction,
)

from .main_window_helpers import OPACITY_STEPS, LineStyleButton, LineStylePreviewButton, _button_style, _line_toggle_style, _plot_settings_title


class MainWindowPlotMixin:
    def _make_plot_panel(self):
        """Summary: Make plot panel."""
        from PyQt6.QtWidgets import QTabWidget
        from gui.plot_widget import MultiChartWidget
        from simulation.plotter import VARIABLE_META, ZONE_COLORS, PLOT_GROUPS, auto_title

        while self._plot_widget_layout.count():
            item = self._plot_widget_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._plot_progress_bar = QProgressBar()
        self._plot_progress_bar.setRange(0, 100)
        self._plot_progress_bar.setValue(0)
        self._plot_progress_bar.setTextVisible(True)
        self._plot_progress_bar.setFormat("Simulation %p%")
        self._plot_progress_bar.setStyleSheet(
            "QProgressBar { background: #f4f6fc; border: none; border-bottom: 1px solid #c8ccdc;"
            " height: 14px; color: #ffffff; font-size: 10px; text-align: center; }"
            "QProgressBar::chunk { background: #4a7fc1; }"
        )
        self._plot_widget_layout.addWidget(self._plot_progress_bar)

        self._multi_charts = []
        self._plot_tabs = QTabWidget()
        self._plot_tabs.setDocumentMode(True)
        self._plot_tabs.tabBar().setExpanding(True)
        self._plot_tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #f0f2f8; }
            QTabBar::tab {
                background: #e0e4f0; color: #5a6280;
                padding: 5px 4px; border: none; font-size: 11px; font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #f0f2f8; color: #1e2437; font-weight: 600;
                border-top: 2px solid #4878C8;
            }
            QTabBar::tab:hover:!selected { background: #d4d8ec; }
        """)
        t_start = self._last_t_start
        t_duration = self.building_model.t_duration
        dt = self.building_model.dt
        model_name = self.building_model.name

        for tab_name, group_vars in PLOT_GROUPS:
            prev_sel = self._plot_selected_by_group.get(tab_name, set())
            prev_ord = self._plot_order_by_group.get(tab_name, [])
            if not prev_sel:
                defaults = [v for v in group_vars if v in self._last_results]
                prev_sel = set(defaults)
                prev_ord = defaults
                self._plot_selected_by_group[tab_name] = prev_sel
                self._plot_order_by_group[tab_name] = prev_ord
            variables = [v for v in prev_ord if v in prev_sel and v in self._last_results]

            mc = MultiChartWidget()
            if variables:
                mc.load_results(self._last_results, variables, t_start, VARIABLE_META, ZONE_COLORS)
                title = auto_title(model_name, t_start, t_duration, dt, tab_name)
                mc.set_overall_title(title)
            self._multi_charts.append(mc)
            self._plot_tabs.addTab(mc, tab_name)

        self._plot_tabs.currentChanged.connect(self._on_plot_tab_changed)
        self._plot_widget_layout.addWidget(self._plot_tabs, 1)
        self._populate_var_list(self._last_results)
        self._sync_title_input()
        for tab_idx, (tab_name, _) in enumerate(PLOT_GROUPS):
            if tab_idx < len(self._multi_charts):
                mc = self._multi_charts[tab_idx]
                mc.variable_removed.connect(
                    lambda k, tn=tab_name: self._on_var_removed(tn, k)
                )
                mc.variable_added.connect(
                    lambda k, tn=tab_name: self._on_var_added(tn, k)
                )
                mc.charts_reordered.connect(
                    lambda keys, tn=tab_name: self._on_charts_reordered(tn, keys)
                )

    def _current_multi_chart(self):
        if not self._multi_charts or self._plot_tabs is None:
            return None
        idx = self._plot_tabs.currentIndex()
        if 0 <= idx < len(self._multi_charts):
            return self._multi_charts[idx]
        return None

    def _sync_title_input(self):
        mc = self._current_multi_chart()
        if mc is not None and hasattr(self, "_title_input"):
            self._title_input.blockSignals(True)
            self._title_input.setText(mc._overall_title)
            self._title_input.blockSignals(False)

    def _on_plot_tab_changed(self, _idx: int):
        self._sync_title_input()
        self._rebuild_plot_settings()
        if self._last_results is not None:
            self._populate_var_list(self._last_results)

    def _create_plots_tab(self):
        """
        Summary: Create plots tab.
        Returns: Return the computed value.
        """
        from gui.plot_widget import VarListWidget

        _SECTION_HDR = (
            "QLabel { background: #e2e6f0; color: #3a4468; border-radius: 3px;"
            " padding: 2px 6px; font-weight: 600; font-size: 10px; }"
        )
        _BTN = (
            "QPushButton { background: #4a7fc1; color: #fff; border: none;"
            " border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 500; }"
            "QPushButton:hover { background: #5a8fd1; }"
            "QPushButton:pressed { background: #3a6fb1; }"
        )
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        toolbar.addStretch()
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(_BTN)
        save_btn.clicked.connect(self._save_plot)
        toolbar.addWidget(save_btn)
        outer.addLayout(toolbar)
        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("Add a chart title…")
        self._title_input.setStyleSheet(
            "QLineEdit { border: none; border-bottom: 1px solid #d0d4e8;"
            " border-radius: 0; padding: 2px 4px; font-size: 11px;"
            " background: transparent; color: #3a4468; }"
            "QLineEdit:focus { border-bottom: 1px solid #4a7fc1; }"
        )
        self._title_input.editingFinished.connect(self._on_title_changed)
        outer.addWidget(self._title_input)
        _BTN_SM = (
            "QPushButton { background: transparent; color: #4a5578; border: 1px solid #c4c9dc;"
            " border-radius: 3px; font-size: 10px; padding: 1px 7px; }"
            "QPushButton:hover { background: #eaecf5; }"
            "QPushButton:pressed { background: #d8dbe9; }"
        )
        var_hdr_row = QHBoxLayout()
        var_hdr_row.setSpacing(4)
        var_hdr = QLabel("VARIABLES  (drag to plot)")
        var_hdr.setStyleSheet(_SECTION_HDR)
        var_hdr_row.addWidget(var_hdr, 1)
        default_btn = QPushButton("Default")
        default_btn.setStyleSheet(_BTN_SM)
        default_btn.setFixedHeight(20)
        default_btn.setToolTip("Load all available variables for this tab")
        default_btn.clicked.connect(self._load_default_vars)
        var_hdr_row.addWidget(default_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(_BTN_SM)
        clear_btn.setFixedHeight(20)
        clear_btn.setToolTip("Remove all variables from this tab's plot")
        clear_btn.clicked.connect(self._clear_all_vars)
        var_hdr_row.addWidget(clear_btn)
        outer.addLayout(var_hdr_row)

        self._var_list = VarListWidget()
        outer.addWidget(self._var_list)
        sub_hdr = QLabel("SUBPLOT SETTINGS")
        sub_hdr.setStyleSheet(_SECTION_HDR)
        outer.addWidget(sub_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #d4d8ea; border-radius: 5px; background: #f8f9fc; }"
        )
        settings_container = QWidget()
        settings_container.setStyleSheet("background: #f8f9fc;")
        settings_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._settings_layout = QVBoxLayout(settings_container)
        self._settings_layout.setContentsMargins(4, 4, 4, 4)
        self._settings_layout.setSpacing(3)
        self._settings_layout.addStretch()
        scroll.setWidget(settings_container)
        outer.addWidget(scroll, 1)

        return tab

    @staticmethod
    def _make_style_icon(style: str, w: int = 72, h: int = 18, line_width: int = 2) -> QIcon:
        """
        Summary: Make style icon.
        Args: line_width
        Returns: Return the computed value.
        """
        from gui.plot_widget import _PEN_STYLE
        px = QPixmap(w, h)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(58, 68, 104), max(1, int(line_width)), _PEN_STYLE.get(style, Qt.PenStyle.SolidLine))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        mid = h // 2
        p.drawLine(6, mid, w - 6, mid)
        p.end()
        return QIcon(px)

    @staticmethod
    def _make_fit_icon(size: int = 14) -> QIcon:
        """
        Summary: Make fit icon.
        Returns: Return the computed value.
        """
        px = QPixmap(size, size)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(74, 88, 128), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        m = 2
        leg = max(3, size // 3)
        p.drawLine(m, m, m + leg, m)
        p.drawLine(m, m, m, m + leg)
        p.drawLine(size - m, m, size - m - leg, m)
        p.drawLine(size - m, m, size - m, m + leg)
        p.drawLine(m, size - m, m + leg, size - m)
        p.drawLine(m, size - m, m, size - m - leg)
        p.drawLine(size - m, size - m, size - m - leg, size - m)
        p.drawLine(size - m, size - m, size - m, size - m - leg)
        p.end()
        return QIcon(px)

    def _rebuild_plot_settings(self):
        """
        Summary: Rebuild plot settings.
        Returns: Return the computed value.
        """
        mc = self._current_multi_chart()
        if mc is None or self._settings_layout is None:
            return
        while self._settings_layout.count():
            item = self._settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        _HDR_W = "QWidget { background: #eef0f8; border-radius: 4px; margin-top: 4px; }"
        _HDR_LBL = (
            "QLabel { background: transparent; color: #2c3868;"
            " font-weight: 700; font-size: 10px; border: none; }"
        )
        _FIT_BTN = (
            "QPushButton { background: transparent; color: #7a88b0; border: 1px solid transparent;"
            " border-radius: 3px; font-size: 10px; padding: 0 3px; }"
            "QPushButton:hover { color: #4878C8; border-color: #4878C8; }"
            "QPushButton:pressed { background: #dce7fb; border-color: #2f5f9f; }"
        )

        for chart_idx, chart in enumerate(mc.charts):
            hdr_w = QWidget()
            hdr_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdr_w.setStyleSheet(_HDR_W)
            hdr_row = QHBoxLayout(hdr_w)
            hdr_row.setContentsMargins(6, 3, 3, 3)
            hdr_row.setSpacing(4)
            hdr_lbl = QLabel(_plot_settings_title(chart.ylabel, f"Chart {chart_idx + 1}"))
            hdr_lbl.setStyleSheet(_HDR_LBL)
            hdr_lbl.setToolTip(chart.ylabel)
            hdr_lbl.setMinimumWidth(0)
            fit_btn = QPushButton()
            fit_btn.setIcon(self.canvas.icons.icon("plotcenter", "plot_center", "center", fallback_text="Center"))
            fit_btn.setIconSize(QSize(14, 14))
            fit_btn.setFixedSize(22, 18)
            fit_btn.setStyleSheet(_FIT_BTN)
            fit_btn.setToolTip("Reset zoom to full data range")
            fit_btn.clicked.connect(lambda _=False, c=chart: c.reset_view())
            edit_btn = QPushButton()
            edit_btn.setIcon(self.canvas.icons.icon("settings", "settings_asset", fallback_text="Settings"))
            edit_btn.setIconSize(QSize(14, 14))
            edit_btn.setFixedSize(22, 18)
            edit_btn.setStyleSheet(_FIT_BTN)
            edit_btn.setToolTip("Edit subplot")
            edit_btn.clicked.connect(lambda _=False, c=chart: self._open_subplot_edit_dialog(c))
            hdr_row.addWidget(hdr_lbl, 1)
            hdr_row.addWidget(fit_btn)
            hdr_row.addWidget(edit_btn)
            self._settings_layout.addWidget(hdr_w)
            for series in chart.series:
                row_w = QWidget()
                row_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                row_w.setStyleSheet(
                    "QWidget { background: #f4f6fc; border-radius: 4px; }"
                )
                row = QVBoxLayout(row_w)
                row.setContentsMargins(4, 4, 4, 4)
                row.setSpacing(3)
                top_row = QHBoxLayout()
                top_row.setContentsMargins(0, 0, 0, 0)
                top_row.setSpacing(4)
                swatch_wrap = QWidget()
                swatch_wrap.setFixedSize(20, 20)
                swatch_wrap.setStyleSheet("background: transparent;")
                swatch = QPushButton(swatch_wrap)
                swatch.setGeometry(0, 0, 16, 16)
                swatch.setToolTip("Click to change colour")
                swatch.setStyleSheet(
                    f"background-color: {series.color.name()};"
                    "border: none; border-radius: 3px;"
                )
                opacity_btn = QPushButton(swatch_wrap)
                opacity_btn.setGeometry(11, 11, 8, 8)
                opacity_btn.setToolTip("Toggle line on/off")
                opacity_btn.setStyleSheet(_line_toggle_style(series.visible))
                lbl = QLabel(_plot_settings_title(series.label, "Line"))
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                lbl.setStyleSheet("font-size: 10px; color: #2c3454; background: transparent;")

                def _color_h(ser, btn, c):
                    """
                    Summary: Color h.
                    Args: ser, btn, c
                    Returns: Return the computed value.
                    """
                    def _f():
                        picked = QColorDialog.getColor(ser.color, self, "Pick colour")
                        if picked.isValid():
                            ser.color = picked
                            btn.setStyleSheet(
                                f"background-color: {picked.name()};"
                                "border: none; border-radius: 3px;"
                            )
                            c.update()
                    return _f

                def _opacity_h(ser, btn, c):
                    def _f():
                        current = min(range(len(OPACITY_STEPS)), key=lambda idx: abs(OPACITY_STEPS[idx] - ser.opacity))
                        ser.opacity = OPACITY_STEPS[(current + 1) % len(OPACITY_STEPS)]
                        btn.setStyleSheet(_line_toggle_style(ser.visible))
                        c._hover_sample = None
                        c.refit_y_to_visible_series()
                        c.update()
                    return _f

                swatch.clicked.connect(_color_h(series, swatch, chart))
                opacity_btn.clicked.connect(_opacity_h(series, opacity_btn, chart))
                top_row.addWidget(swatch_wrap)
                top_row.addWidget(lbl, 1)
                row.addLayout(top_row)
                self._settings_layout.addWidget(row_w)

        self._settings_layout.addStretch()


    def _open_subplot_edit_dialog(self, chart):
        from gui.plot_widget import STYLE_OPTIONS, _padded_range

        _DIALOG_STYLE = """
            QDialog { background: #f5f7fc; color: #27314f; }
            QLabel { color: #2c3454; background: transparent; font-size: 11px; }
            QLabel#axisRowLabel { color: #1f2a44; font-size: 13px; font-weight: 600; }
            QLabel#dialogTitle { color: #1f2a44; font-size: 13px; font-weight: 700; }
            QLabel#sectionLabel {
                color: #3a4468; background: #e4e8f3; border-radius: 4px;
                padding: 3px 7px; font-size: 10px; font-weight: 700;
            }
            QWidget#lineCard {
                background: #ffffff; border: 1px solid #d7ddec; border-radius: 6px;
            }
            QLineEdit, QSpinBox {
                background: #ffffff; color: #26324f; border: 1px solid #c7cede;
                border-radius: 4px; padding: 3px 6px; min-height: 22px;
                selection-background-color: #dce7fb;
            }
            QLineEdit:hover, QSpinBox:hover { border-color: #9faccc; }
            QLineEdit:focus, QSpinBox:focus { border-color: #4878C8; }
            QPushButton {
                background: #ffffff; color: #3a4468; border: 1px solid #c4c9dc;
                border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: #eaf0fb; border-color: #9fb4d8; }
            QPushButton:pressed { background: #dce7fb; }
            QPushButton#primaryButton {
                background: #4a7fc1; color: #ffffff; border-color: #4a7fc1;
            }
            QPushButton#primaryButton:hover { background: #5a8fd1; border-color: #5a8fd1; }
            QPushButton#unitButton {
                border-radius: 12px; min-width: 24px; max-width: 24px;
                min-height: 24px; max-height: 24px; padding: 0; font-weight: 700;
            }
            QPushButton#unitButton:checked {
                background: #4a7fc1; color: #ffffff; border-color: #4a7fc1;
            }
            QPushButton#unitButton:!checked {
                background: #edf0f7; color: #9aa3b8; border-color: #d8deec;
            }
        """

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Subplot")
        dialog.setModal(True)
        dialog.setMinimumWidth(230)
        dialog.setStyleSheet(_DIALOG_STYLE)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(7)

        axis_label = QLabel("AXIS")
        axis_label.setObjectName("sectionLabel")
        layout.addWidget(axis_label)

        axis_rows = QGridLayout()
        axis_rows.setContentsMargins(0, 0, 0, 0)
        axis_rows.setHorizontalSpacing(3)
        axis_rows.setVerticalSpacing(6)
        axis_rows.setColumnMinimumWidth(0, 112)
        axis_row_idx = {"value": 0}

        def _axis_row(label_text, widget):
            label = QLabel(label_text)
            label.setObjectName("axisRowLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            axis_rows.addWidget(label, axis_row_idx["value"], 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            axis_rows.addWidget(widget, axis_row_idx["value"], 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            axis_row_idx["value"] += 1

        unit_buttons = {}
        unit_state = {"value": chart.value_unit}
        if chart.temperature_units_enabled:
            unit_row = QHBoxLayout()
            unit_row.setContentsMargins(0, 0, 0, 0)
            unit_row.setSpacing(6)
            for unit in ("C", "K"):
                btn = QPushButton(unit)
                btn.setObjectName("unitButton")
                btn.setCheckable(True)
                btn.setChecked(unit == unit_state["value"])
                unit_row.addWidget(btn)
                unit_buttons[unit] = btn
            unit_holder = QWidget()
            unit_holder.setLayout(unit_row)
            unit_holder.setFixedWidth(62)
            _axis_row("Temperature", unit_holder)

        validator = QDoubleValidator(-1e9, 1e9, 6, dialog)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        y_max = QLineEdit(f"{chart._vy_max:.6g}")
        y_min = QLineEdit(f"{chart._vy_min:.6g}")
        for field in (y_max, y_min):
            field.setValidator(validator)
            field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            field.setFixedWidth(96)
        _axis_row("Max", y_max)
        _axis_row("Min", y_min)

        auto_fit_requested = {"value": False}
        setting_spins = {"value": False}

        def _visible_y_range():
            valid = [s for s in chart.series if s.visible and len(s.y) > 0]
            if not valid:
                valid = [s for s in chart.series if len(s.y) > 0]
            if not valid:
                return chart._y_min, chart._y_max
            try:
                import numpy as np
                lo, hi = _padded_range(np.concatenate([s.y for s in valid]))
                if chart.temperature_units_enabled and unit_state["value"] != chart.value_unit:
                    delta = 273.15 if chart.value_unit == "C" and unit_state["value"] == "K" else -273.15
                    lo += delta
                    hi += delta
                return lo, hi
            except Exception:
                return chart._y_min, chart._y_max

        def _mark_manual():
            if not setting_spins["value"]:
                auto_fit_requested["value"] = False

        y_min.textEdited.connect(_mark_manual)
        y_max.textEdited.connect(_mark_manual)

        if unit_buttons:
            def _unit_changed(next_unit):
                previous = unit_state["value"]
                if previous == next_unit:
                    return
                delta = 273.15 if previous == "C" and next_unit == "K" else -273.15
                setting_spins["value"] = True
                try:
                    y_min.setText(f"{float(y_min.text()) + delta:.6g}")
                    y_max.setText(f"{float(y_max.text()) + delta:.6g}")
                except ValueError:
                    pass
                setting_spins["value"] = False
                unit_state["value"] = next_unit
                for unit, btn in unit_buttons.items():
                    btn.setChecked(unit == next_unit)

            for unit, btn in unit_buttons.items():
                btn.clicked.connect(lambda _=False, u=unit: _unit_changed(u))

        layout.addLayout(axis_rows)

        lines_label = QLabel("LINES")
        lines_label.setObjectName("sectionLabel")
        layout.addWidget(lines_label)

        series_rows = []
        show_series_labels = len(chart.series) > 1
        for idx, series in enumerate(chart.series):
            if show_series_labels:
                series_label = QLabel(series.label or f"Zone {idx + 1}")
                series_label.setObjectName("axisRowLabel")
                series_label.setToolTip(series.label)
                series_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                layout.addWidget(series_label)
            line_card = QWidget()
            line_card.setObjectName("lineCard")
            line_card_layout = QHBoxLayout(line_card)
            line_card_layout.setContentsMargins(6, 5, 6, 5)
            line_card_layout.setSpacing(6)
            style_btn = LineStyleButton(self._make_style_icon, series.style, series.width)
            style_btn.setMinimumWidth(118)
            style_btn.setStyleSheet(_button_style(font_size=10, padding="1px 4px"))
            width_state = {"value": series.width}
            width_stack = QWidget()
            width_stack.setFixedSize(24, 34)
            width_stack.setStyleSheet("background: transparent;")
            width_stack_layout = QVBoxLayout(width_stack)
            width_stack_layout.setContentsMargins(1, 1, 1, 1)
            width_stack_layout.setSpacing(2)
            width_up = QPushButton("▲")
            width_down = QPushButton("▼")
            arrow_style = _button_style(
                hover_bg="#e6e9f5",
                pressed_bg="#d0d4ea",
                radius=3,
                font_size=8,
                font_weight=700,
                padding="0",
            )
            for arrow in (width_up, width_down):
                arrow.setFixedSize(22, 15)
                arrow.setStyleSheet(arrow_style)
                arrow.setToolTip(f"Line thickness: {width_state['value']}")
            width_stack_layout.addWidget(width_up)
            width_stack_layout.addWidget(width_down)

            def _style_menu_h(btn, width_ref):
                def _f():
                    from PyQt6.QtWidgets import QMenu
                    menu = QMenu(btn)
                    menu.setStyleSheet(
                        "QMenu { background: #fafbfd; border: 1px solid #c4c9dc;"
                        " border-radius: 5px; padding: 2px; margin: 0; }"
                        "QMenu::item { padding: 0; margin: 0; }"
                    )
                    menu.setFixedWidth(206)
                    current_style = btn.line_style
                    for opt in STYLE_OPTIONS:
                        preview = LineStylePreviewButton(opt, self._make_style_icon(opt, 204, 18, width_ref["value"]), menu)
                        if opt == current_style:
                            preview.setStyleSheet(
                                "QPushButton { background: #dce7fb; border: 1px solid #7fa3d8;"
                                " border-radius: 3px; padding: 2px 0; }"
                                "QPushButton:hover { background: #d0def5; }"
                            )

                        def _choose(chosen_style=opt):
                            btn.set_line_appearance(chosen_style, width_ref["value"])
                            menu.close()

                        preview.selected.connect(_choose)
                        action = QWidgetAction(menu)
                        action.setDefaultWidget(preview)
                        menu.addAction(action)
                    menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
                return _f

            def _width_step(style_ctl, width_ref, delta, buttons):
                def _f():
                    width_ref["value"] = max(1, min(8, width_ref["value"] + delta))
                    style_ctl.set_line_appearance(style_ctl.line_style, width_ref["value"])
                    for button in buttons:
                        button.setToolTip(f"Line thickness: {width_ref['value']}")
                return _f

            style_btn.clicked.connect(_style_menu_h(style_btn, width_state))
            width_up.clicked.connect(_width_step(style_btn, width_state, 1, (width_up, width_down)))
            width_down.clicked.connect(_width_step(style_btn, width_state, -1, (width_up, width_down)))
            line_card_layout.addWidget(style_btn)
            line_card_layout.addWidget(width_stack)
            line_card.setFixedWidth(211)
            layout.addWidget(line_card)
            series_rows.append((series, style_btn, width_state))

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setObjectName("primaryButton")
        auto_fit_btn = QPushButton("Auto Fit")
        button_box.addButton(auto_fit_btn, QDialogButtonBox.ButtonRole.ActionRole)

        def _auto_fit():
            lo, hi = _visible_y_range()
            setting_spins["value"] = True
            y_min.setText(f"{lo:.6g}")
            y_max.setText(f"{hi:.6g}")
            setting_spins["value"] = False
            auto_fit_requested["value"] = True

        def _accept():
            try:
                min_value = float(y_min.text())
                max_value = float(y_max.text())
            except ValueError:
                QMessageBox.warning(dialog, "Invalid Range", "Enter numeric values for Min and Max.")
                return
            if max_value <= min_value:
                QMessageBox.warning(dialog, "Invalid Range", "Y max must be greater than Y min.")
                return
            if unit_buttons:
                chart.set_temperature_unit(unit_state["value"])
            for series, style_btn, width_state in series_rows:
                series.style = style_btn.line_style
                series.width = width_state["value"]
            if auto_fit_requested["value"]:
                chart.auto_fit_y_axis()
            else:
                chart.set_y_axis_range(min_value, max_value)
            chart.update()
            dialog.accept()

        auto_fit_btn.clicked.connect(_auto_fit)
        button_box.accepted.connect(_accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._rebuild_plot_settings()

    def _populate_var_list(self, results: dict):
        """
        Summary: Populate var list.
        Args: results
        """
        from simulation.plotter import VARIABLE_META, PLOT_GROUPS

        if self._var_list is None:
            return

        if results is None:
            self._var_list.clear()
            item = QListWidgetItem("Run a simulation first.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._var_list.addItem(item)
            return

        tab_idx = self._plot_tabs.currentIndex() if self._plot_tabs is not None else 0
        if tab_idx < 0 or tab_idx >= len(PLOT_GROUPS):
            tab_idx = 0
        _, group_vars = PLOT_GROUPS[tab_idx]

        available = [k for k in group_vars if k in results]
        if not available:
            self._var_list.clear()
            item = QListWidgetItem("No variables for this group in results.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._var_list.addItem(item)
            return

        self._var_list.populate(available, VARIABLE_META)

    def _rebuild_tab_chart(self, tab_name: str):
        """
        Summary: Rebuild tab chart.
        Args: tab_name
        """
        from simulation.plotter import PLOT_GROUPS, VARIABLE_META, ZONE_COLORS, auto_title
        tab_idx = next((i for i, (n, _) in enumerate(PLOT_GROUPS) if n == tab_name), None)
        if tab_idx is None or tab_idx >= len(self._multi_charts) or self._last_results is None:
            return
        mc = self._multi_charts[tab_idx]
        sel = self._plot_selected_by_group.get(tab_name, set())
        ord_ = self._plot_order_by_group.get(tab_name, [])
        selected = [v for v in ord_ if v in sel and v in self._last_results]
        mc.clear()
        if selected:
            mc.load_results(self._last_results, selected, self._last_t_start, VARIABLE_META, ZONE_COLORS)
            mc.set_overall_title(auto_title(
                self.building_model.name, self._last_t_start,
                self.building_model.t_duration, self.building_model.dt, tab_name,
            ))
        self._rebuild_plot_settings()

    def _on_var_removed(self, tab_name: str, var_key: str):
        sel = set(self._plot_selected_by_group.get(tab_name, set()))
        sel.discard(var_key)
        self._plot_selected_by_group[tab_name] = sel
        ord_ = list(self._plot_order_by_group.get(tab_name, []))
        if var_key in ord_:
            ord_.remove(var_key)
        self._plot_order_by_group[tab_name] = ord_
        self._rebuild_tab_chart(tab_name)

    def _on_var_added(self, tab_name: str, var_key: str):
        """
        Summary: On var added.
        Args: tab_name, var_key
        """
        if self._last_results is None or var_key not in self._last_results:
            return
        sel = set(self._plot_selected_by_group.get(tab_name, set()))
        if var_key in sel:
            return
        sel.add(var_key)
        self._plot_selected_by_group[tab_name] = sel
        ord_ = list(self._plot_order_by_group.get(tab_name, []))
        if var_key not in ord_:
            ord_.append(var_key)
        self._plot_order_by_group[tab_name] = ord_
        self._rebuild_tab_chart(tab_name)

    def _on_charts_reordered(self, tab_name: str, keys: list):
        self._plot_order_by_group[tab_name] = keys
        self._rebuild_plot_settings()

    def _load_default_vars(self):
        """Summary: Load default vars."""
        if self._last_results is None or self._plot_tabs is None:
            return
        from simulation.plotter import PLOT_GROUPS
        tab_idx = self._plot_tabs.currentIndex()
        if tab_idx < 0 or tab_idx >= len(PLOT_GROUPS):
            return
        tab_name, group_vars = PLOT_GROUPS[tab_idx]
        defaults = [v for v in group_vars if v in self._last_results]
        self._plot_selected_by_group[tab_name] = set(defaults)
        self._plot_order_by_group[tab_name] = defaults
        self._rebuild_tab_chart(tab_name)

    def _clear_all_vars(self):
        """Summary: Clear all vars."""
        if self._plot_tabs is None or not self._multi_charts:
            return
        from simulation.plotter import PLOT_GROUPS
        tab_idx = self._plot_tabs.currentIndex()
        if tab_idx < 0 or tab_idx >= len(PLOT_GROUPS):
            return
        tab_name, _ = PLOT_GROUPS[tab_idx]
        self._plot_selected_by_group[tab_name] = set()
        self._plot_order_by_group[tab_name] = []
        if tab_idx < len(self._multi_charts):
            self._multi_charts[tab_idx].clear()
        self._rebuild_plot_settings()

    def _on_title_changed(self):
        mc = self._current_multi_chart()
        if mc:
            mc.set_overall_title(self._title_input.text())

    def _on_font_size_changed(self, size: int):
        mc = self._current_multi_chart()
        if mc:
            mc.set_font_size(size)

    def _on_reset_zoom(self):
        mc = self._current_multi_chart()
        if mc:
            mc.reset_view()

    def _save_plot(self):
        """Summary: Save plot."""
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
