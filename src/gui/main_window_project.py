"""Main window project, component, and file action helpers."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QMessageBox


class MainWindowProjectMixin:
    def _generate_component_id(self):
        component_id = f"component-{self.next_component_id:04d}"
        self.next_component_id += 1
        return component_id

    def _extract_component_id_number(self, component_id):
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
        suffix_number = self._extract_component_id_number(component_id)
        if suffix_number is None:
            return
        self.next_component_id = max(self.next_component_id, suffix_number + 1)

    def add_component(self, component_name):
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before editing components.", 3000)
            return
        self.canvas.add_component(component_name)
        self.statusBar().showMessage(f"Added {component_name}", 3000)

    def on_component_added(self, component_item):
        if not getattr(component_item, "component_id", None):
            component_item.component_id = self._generate_component_id()
        self._sync_next_component_id(component_item.component_id)
        component_name = component_item.label.toPlainText()
        self._invalidate_plots()
        self.refresh_component_list()
        self.statusBar().showMessage(f"Added {component_name} ({component_item.component_id})", 2500)
        self.set_dirty(True)

    def arm_delete_component(self):
        """Summary: Arm delete component."""
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before deleting components.", 3000)
            return
        if self._canvas_component_count() == 0:
            self.statusBar().showMessage("Add a component before deleting components.", 3000)
            return
        if self.pending_component_action == "delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Delete component mode cancelled.", 3000)
            return
        self.set_component_action_mode("delete")
        self.statusBar().showMessage("Delete component mode active: click a component on the canvas.", 5000)

    def arm_edit_component(self):
        """Summary: Arm edit component."""
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before editing components.", 3000)
            return
        if self._canvas_component_count() == 0:
            self.statusBar().showMessage("Add a component before editing components.", 3000)
            return
        if self.pending_component_action == "edit":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Edit mode cancelled.", 3000)
            return
        self.set_component_action_mode("edit")
        self.statusBar().showMessage("Edit mode active: click a component on the canvas.", 5000)

    def arm_area_delete(self):
        """Summary: Arm area delete."""
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before deleting components.", 3000)
            return
        if self._canvas_component_count() == 0:
            self.statusBar().showMessage("Add a component before deleting an area.", 3000)
            return
        if self.pending_component_action == "area-delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Area delete mode cancelled.", 3000)
            return
        self.set_component_action_mode("area-delete")
        self.statusBar().showMessage("Area delete mode active: drag a box over components to remove.", 5000)

    def arm_delete_connection(self):
        """Summary: Arm delete connection."""
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before editing connections.", 3000)
            return
        if self.pending_component_action == "delete-connection":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Delete connection mode cancelled.", 3000)
            return
        if not self.canvas.visual_connections:
            self.statusBar().showMessage("No connections to delete.", 3000)
            return
        self.set_component_action_mode("delete-connection")
        self.statusBar().showMessage("Delete connection mode active: hover a connection, then click to remove it.", 5000)

    def set_component_action_mode(self, mode):
        """Summary: Set component action mode."""
        self.pending_component_action = mode
        self.canvas.exclusive_action_mode = mode
        if self.add_connection_btn is not None:
            self.add_connection_btn.setChecked(mode == "connect")
        if self.edit_component_btn is not None:
            self.edit_component_btn.setChecked(mode == "edit")
        if self.delete_component_btn is not None:
            self.delete_component_btn.setChecked(mode == "delete")
        if self.delete_connection_btn is not None:
            self.delete_connection_btn.setChecked(mode == "delete-connection")
        if self.area_delete_btn is not None:
            self.area_delete_btn.setChecked(mode == "area-delete")
        self.canvas.set_area_delete_mode(mode == "area-delete")
        self.canvas.set_connection_delete_mode(mode == "delete-connection")
        if mode is None:
            if self._left_tabs is not None:
                self._left_tabs.setEnabled(True)
            self._sync_action_button_availability()
            self.pending_connection_items.clear()
            self.canvas.scene.clearSelection()
            if self.mode_status_label is not None:
                self.mode_status_label.setText("Mode: Normal")
            return
        self._sync_action_button_availability()
        if self._left_tabs is not None:
            self._left_tabs.setEnabled(False)
        if self.mode_status_label is None:
            return
        if mode == "connect":
            self.mode_status_label.setText("Mode: Connect (select source and destination)")
        elif mode == "area-delete":
            self.mode_status_label.setText("Mode: Delete Area (drag a selection box)")
        elif mode == "delete-connection":
            self.mode_status_label.setText("Mode: Delete Connection (hover and click a line)")
        elif mode == "delete":
            self.mode_status_label.setText("Mode: Delete Component (click a component)")
        else:
            self.mode_status_label.setText(f"Mode: {mode.title()} (click a component)")

    def _handle_connect_click(self, component_item):
        """
        Summary: Handle connect click.
        Args: component_item
        """
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
        mappings = self.canvas.available_connection_mappings(src_item, dst_item)
        if mappings is not None and len(mappings) > 1:
            mappings = self.dialogue_manager.prompt_connection_mappings(mappings)
            if mappings is None:
                self.statusBar().showMessage("Connection cancelled.", 3000)
                src_item.setSelected(False)
                dst_item.setSelected(False)
                self.pending_connection_items.clear()
                self.set_component_action_mode(None)
                return
        ok, message = self.canvas.add_connection_between_items(src_item, dst_item, mappings = mappings)
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
        """
        Summary: Handle component click action.
        Args: component_item
        """
        if self.pending_component_action == "edit":
            component_name = component_item.label.toPlainText()
            component_item.edit_properties()
            self.refresh_component_list()
            self.statusBar().showMessage(f"Edited {component_name}", 4000)
            self.set_component_action_mode(None)
            return
        if self.pending_component_action == "delete":
            component_name = component_item.label.toPlainText()
            self.canvas.delete_component_items([component_item])
            self._invalidate_plots()
            self.refresh_component_list()
            self.statusBar().showMessage(f"Deleted {component_name}", 4000)
            self.set_component_action_mode(None)
            return
        if self.pending_component_action == "connect":
            self._handle_connect_click(component_item)

    def handle_canvas_click_action(self):
        if self.pending_component_action in {"connect", "edit", "delete", "delete-connection"}:
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Tool mode cancelled.", 3000)

    def add_connection(self):
        """Summary: Add connection."""
        if self._simulation_running:
            self.statusBar().showMessage("Stop the simulation before editing connections.", 3000)
            return
        if self._canvas_component_count() == 0:
            self.statusBar().showMessage("Add components before creating a connection.", 3000)
            return
        if self.pending_component_action == "connect":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Connection mode cancelled.", 3000)
            return
        if self.pending_component_action in {"edit", "delete", "area-delete", "delete-connection"}:
            self.statusBar().showMessage("Finish current mode before creating a connection.", 3500)
            return
        self.pending_connection_items.clear()
        self.canvas.scene.clearSelection()
        self.set_component_action_mode("connect")
        self.statusBar().showMessage("Connection mode active: select source component, then destination.", 5000)

    def on_canvas_zoom_changed(self, zoom_percent):
        if self.zoom_value_display is not None:
            if isinstance(self.zoom_value_display, QLineEdit) and self.zoom_value_display.hasFocus():
                return
            self.zoom_value_display.setText(str(int(zoom_percent)))

    def apply_canvas_zoom_entry(self):
        """Summary: Apply canvas zoom entry."""
        if self.zoom_value_display is None:
            return
        raw_text = self.zoom_value_display.text().strip()
        try:
            zoom_percent = int(raw_text)
        except ValueError:
            zoom_percent = self.canvas.get_zoom_percent()
        zoom_percent = max(25, min(250, zoom_percent))
        self.canvas.tool_manager.reset_button_zoom_acceleration()
        self.canvas.tool_manager.set_zoom_factor(zoom_percent / 100.0)
        if zoom_percent >= self.canvas.tool_manager.button_auto_center_min_percent:
            self.canvas.center_view()
        self.zoom_value_display.setText(str(zoom_percent))

    def _update_zone_display(self):
        self.state_manager.update_zone_display()

    def open_set_time_dialog(self):
        self.dialogue_manager.open_set_time_dialog()

    def refresh_component_list(self):
        self.state_manager.refresh_component_list()
        self.refresh_setup_issues()
        self._sync_action_button_availability()

    def refresh_connection_list(self):
        self.state_manager.refresh_connection_list()
        self.refresh_setup_issues()
        self._sync_action_button_availability()

    def on_area_deleted(self, count):
        self._invalidate_plots()
        self.refresh_component_list()
        self.set_component_action_mode(None)
        if count > 0:
            self.statusBar().showMessage(f"Deleted {count} component(s) in selected area.", 4000)

    def _area_delete_item_labels(self, items):
        labels = []
        for item in items:
            name = item.label.toPlainText() if hasattr(item, "label") else "Component"
            component_id = getattr(item, "component_id", None)
            labels.append(f"{name} ({component_id})" if component_id else name)
        return labels

    def confirm_area_delete_items(self, items):
        labels = self._area_delete_item_labels(items)
        return self.dialogue_manager.confirm_delete_items(labels)

    def on_connection_deleted(self, connection_data):
        src_item = connection_data.get("src_item")
        dst_item = connection_data.get("dst_item")
        src_name = src_item.label.toPlainText() if src_item is not None else "Unknown"
        dst_name = dst_item.label.toPlainText() if dst_item is not None else "Unknown"
        self._invalidate_plots()
        self.refresh_connection_list()
        self.set_component_action_mode(None)
        self.statusBar().showMessage(f"Deleted connection: {src_name} -> {dst_name}", 4000)

    def _is_pristine_empty_new_project(self):
        model = self.building_model
        return (
            self.file_path is None
            and self._canvas_component_count() == 0
            and not self.canvas.visual_connections
            and not model.componentItems
            and not model.nodes
            and not model.connections
            and model.name == "Model"
            and int(model.n_zones) == 2
            and float(model.t_start) == 5 * 60 * 60
            and float(model.t_duration) == 86400
            and float(model.dt) == 300
            and float(model.tu_T_supply_setpoint) == 285.15
            and float(model.rtu_supply_airflow_setpoint) == 1.0
            and not model.use_control_policy_override
            and model.input_data_path is None
            and not model.input_data_summary
        )

    def _has_unsaved_changes(self):
        return bool(self.is_dirty) and not self._is_pristine_empty_new_project()

    def set_dirty(self, is_true):
        self.is_dirty = bool(is_true) and not self._is_pristine_empty_new_project()

    def _confirm_new_project(self):
        return self.dialogue_manager.confirm_new_project(self._has_unsaved_changes())

    def _reset_project_state(self):
        """Summary: Reset project state."""
        self.set_component_action_mode(None)
        self.pending_connection_items.clear()
        self.canvas.scene.clearSelection()
        self.canvas.clear_area_delete_preview()
        self.canvas.highlight_connection(None)
        self.canvas.clear_all()
        self.stack.clear()
        self._set_undo_enabled(False)
        self._set_redo_enabled(False)
        self.next_component_id = 1
        self.building_model.name = "Model"
        self.building_model.update_n_zones(2)
        self.building_model.set_time_param_in_seconds(
            t_start = 5 * 60 * 60,
            t_duration = 86400,
            dt = 300,
        )
        self.building_model.set_control_policy(
            tu_T_supply_setpoint = 285.15,
            rtu_supply_airflow_setpoint = 1.0,
            enable_override = False,
        )
        self.building_model.input_data_path = None
        self.building_model.input_data_summary = {}
        self._sync_control_policy_inputs()
        self._update_zone_display()
        self._clear_cached_simulation_results()
        self.refresh_component_list()
        self.refresh_connection_list()
        self.canvas.center_view()
        self.file_path = None
        self.is_dirty = False

    def new_page(self):
        if not self._confirm_new_project():
            return
        self._reset_project_state()
        self.statusBar().showMessage("Created new project", 4000)

    def save_as_layout(self):
        """
        Summary: Save as layout.
        Returns: Return the computed value.
        """
        component_items = [item for item in self.canvas.scene.items() if hasattr(item, "node") and hasattr(item, "label")]
        for item in component_items:
            if not getattr(item, "component_id", None):
                item.component_id = self._generate_component_id()
            self._sync_next_component_id(item.component_id)

        save_path = self.dialogue_manager.prompt_save_layout_path(self.file_manager.get_saved_dir(self.last_dir))
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
        self.last_dir = Path(save_path).parent
        self.is_dirty = False
        self.stack.setClean()
        return str(save_path)

    def save_layout(self):
        """
        Summary: Save layout.
        Returns: Return the computed value.
        """
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
        self.last_dir = Path(save_path).parent
        self.is_dirty = False
        self.stack.setClean()
        return str(save_path)

    def load_layout(self):
        """
        Summary: Load layout.
        Returns: Return the computed value.
        """
        if self._has_unsaved_changes():
            if not self.dialogue_manager.confirm_load_project():
                return

        load_path = self.dialogue_manager.prompt_load_layout_path(self.file_manager.get_saved_dir(self.last_dir))
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
            if component_data.get("type") == "ControlPolicy":
                self._apply_control_policy_values(component_data.get("values", {}))
                continue
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
                if component_type == "ControlPolicy":
                    self._apply_control_policy_values(component_section.get("values", {}))
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
                mappings = connection_data.get("mappings"),
            )
            src_item.setSelected(False)
            dst_item.setSelected(False)
        time_data = self.file_manager.get_time_data(payload)
        self.building_model.t_start = float(time_data.get("t_start", self.building_model.t_start))
        self.building_model.t_duration = float(time_data.get("t_duration", self.building_model.t_duration))
        self.building_model.dt = float(time_data.get("dt", self.building_model.dt))
        self._apply_control_policy_values(self.file_manager.get_control_policy_data(payload))
        input_data = self.file_manager.get_input_data(payload)
        if isinstance(input_data, dict):
            saved_input_path = input_data.get("path")
            resolved_input_path = self.file_manager.resolve_input_data_path(saved_input_path, load_path)
            if resolved_input_path is not None and not Path(resolved_input_path).exists():
                QMessageBox.information(
                    self,
                    "Locate Input Data",
                    "The saved input data file was not found. Select its new location, or cancel to use generated inputs.",
                )
                resolved_input_path = self.dialogue_manager.prompt_input_data_path(
                    self.file_manager.get_input_data_dir()
                )
                if resolved_input_path:
                    try:
                        from simulation.input_data import inspect_input_csv
                        input_data["summary"] = inspect_input_csv(resolved_input_path)
                    except Exception as exc:
                        QMessageBox.critical(self, "Input Data Error", f"Could not read input data:\n{exc}")
                        resolved_input_path = None
            self.building_model.input_data_path = str(resolved_input_path) if resolved_input_path else None
            self.building_model.input_data_summary = input_data.get("summary", {}) if resolved_input_path else {}
        else:
            self.building_model.input_data_path = None
            self.building_model.input_data_summary = {}
        self.refresh_input_data_label()
        self._invalidate_plots()
        self.refresh_component_list()
        self.canvas.center_view()
        self.stack.clear()
        self._set_undo_enabled(False)
        self._set_redo_enabled(False)
        self.statusBar().showMessage(f"Loaded layout from {load_path}", 4000)
        self.file_path = load_path
        self.last_dir = Path(load_path).parent
        self.is_dirty = False
        return True

    def closeEvent(self, event):
        if self._has_unsaved_changes():
            if not self.dialogue_manager.confirm_exit():
                event.ignore()
                return

        event.accept()

    def _apply_control_policy_values(self, values):
        """Summary: Apply control policy values."""
        if not isinstance(values, dict):
            return
        supply_temp = values.get("tu_T_supply_setpoint")
        supply_airflow = values.get("rtu_supply_airflow_setpoint")
        if isinstance(supply_temp, list):
            supply_temp = supply_temp[0] if supply_temp else None
        if isinstance(supply_airflow, list):
            supply_airflow = supply_airflow[0] if supply_airflow else None
        self.building_model.set_control_policy(
            tu_T_supply_setpoint=supply_temp,
            rtu_supply_airflow_setpoint=supply_airflow,
            enable_override=bool(values.get("use_control_policy_override", False)),
        )
        self._sync_control_policy_inputs()


    def on_connection_added(self):
        self._invalidate_plots()
        self.refresh_connection_list()
