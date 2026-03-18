from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter, QStatusBar, QTabWidget, QTreeWidget, QVBoxLayout, QWidget

from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox

from models.building_model import BuildingModel
from .dialogue_manager import DialogueManager
from .file_manager import FileManager
from .header_bar import HeaderBar
from .interactive_canvas import InteractiveCanvas
from .state_manager import StateManager


COMPONENTS = [Envelope, RTU, VAVBox, SolarGains]
COMPONENT_ICON_NAMES = {
    "Envelope": ["WIP_ICON.png"],
    "RTU": ["WIP_ICON.png"],
    "VAVBox": ["WIP_ICON.png"],
    "SolarGains": ["WIP_ICON.png"],
}


def check_dependencies():
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
    def __init__(self):
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
        self.header_bar = HeaderBar(
            self.assets_path,
            COMPONENTS,
            COMPONENT_ICON_NAMES,
            callbacks = {
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
        self.setStatusBar(QStatusBar())
        self.setup_dependency_status_button()
        self.setup_mode_status_label()
        self.set_component_action_mode(None)
        self.refresh_component_list()

    def setup_dependency_status_button(self):
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
        label = QLabel("Mode: Normal")
        label.setStyleSheet("color: #000000; padding-right: 8px;")
        self.statusBar().addPermanentWidget(label)
        self.mode_status_label = label

    def build_dependency_tooltip(self):
        lines = ["Dependency status:"]
        for name, (ok, version) in self.dep_results.items():
            icon = "✓" if ok else "✗"
            version_text = version if version else "not found"
            lines.append(f"{icon} {name}: {version_text}")
        return "\n".join(lines)

    def create_left_panel(self):
        panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel.setLayout(panel_layout)
        side_tabs = QTabWidget()
        side_tabs.setDocumentMode(True)
        side_tabs.addTab(self.create_project_tab(), "Project")
        panel_layout.addWidget(side_tabs)
        return panel

    def _create_info_box(self, title):
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

    def _create_zoom_controls_box(self):
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
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        panel_layout.setSpacing(8)
        top_row = QHBoxLayout()
        top_row.addStretch()
        zone_box, self.zone_value_display = self._create_info_box("Zones:")
        top_row.addWidget(zone_box)
        top_row.addWidget(self._create_zoom_controls_box())
        panel_layout.addLayout(top_row)
        panel_layout.addWidget(self.canvas, 1)
        return panel

    def create_project_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
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
        self.canvas.add_component(component_name)
        self.statusBar().showMessage(f"Added {component_name}", 3000)

    def on_component_added(self, component_item):
        if not getattr(component_item, "component_id", None):
            component_item.component_id = self._generate_component_id()
        self._sync_next_component_id(component_item.component_id)
        component_name = component_item.label.toPlainText()
        self.refresh_component_list()
        self.statusBar().showMessage(f"Added {component_name} ({component_item.component_id})", 2500)

    def arm_delete_component(self):
        if self.pending_component_action == "delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Delete mode cancelled.", 3000)
            return
        self.set_component_action_mode("delete")
        self.statusBar().showMessage("Delete mode active: click a component on the canvas.", 5000)

    def arm_edit_component(self):
        if self.pending_component_action == "edit":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Edit mode cancelled.", 3000)
            return
        self.set_component_action_mode("edit")
        self.statusBar().showMessage("Edit mode active: click a component on the canvas.", 5000)

    def arm_area_delete(self):
        if self.pending_component_action == "area-delete":
            self.set_component_action_mode(None)
            self.statusBar().showMessage("Area delete mode cancelled.", 3000)
            return
        self.set_component_action_mode("area-delete")
        self.statusBar().showMessage("Area delete mode active: drag a box over components to remove.", 5000)

    def set_component_action_mode(self, mode):
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
            self.refresh_connection_list()
        self.statusBar().showMessage(message, 4000)
        src_item.setSelected(False)
        dst_item.setSelected(False)
        self.pending_connection_items.clear()
        self.set_component_action_mode(None)
        if not ok:
            self.dialogue_manager.show_info("Add Connection", message)

    def handle_component_click_action(self, component_item):
        if self.pending_component_action == "delete":
            component_name = component_item.label.toPlainText()
            self.canvas.remove_component_item(component_item)
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

    def run_simulation(self):
        self.building_model.run_simulation()
        self.statusBar().showMessage("Simulation run complete", 4000)
    def on_canvas_zoom_changed(self, zoom_percent):
        if self.zoom_value_display is not None:
            self.zoom_value_display.setText(f"{int(zoom_percent)}%")
    def _update_zone_display(self):
        self.state_manager.update_zone_display()
    def open_set_time_dialog(self):
        self.dialogue_manager.open_set_time_dialog()
    def refresh_component_list(self):
        self.state_manager.refresh_component_list()
    def refresh_connection_list(self):
        self.state_manager.refresh_connection_list()
    def on_area_deleted(self, count):
        self.refresh_component_list()
        self.set_component_action_mode(None)
        self.statusBar().showMessage(f"Deleted {count} component(s) in selected area.", 4000)

    def save_layout(self):
        component_items = [item for item in self.canvas.scene.items() if hasattr(item, "node") and hasattr(item, "label")]
        for item in component_items:
            if not getattr(item, "component_id", None):
                item.component_id = self._generate_component_id()
            self._sync_next_component_id(item.component_id)
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
        )
        self.statusBar().showMessage(f"Saved layout to {save_path}", 5000)
        return str(save_path)

    def load_layout(self):
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
        self.refresh_component_list()
        self.statusBar().showMessage(f"Loaded layout from {load_path}", 4000)
        return True
