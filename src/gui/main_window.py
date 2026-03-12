import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from neuromancer.hvac.building_components import Envelope, RTU, SolarGains
from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox
from building_model import BuildingModel
from .drag_button import DragButton
from .interactive_canvas import InteractiveCanvas
from .set_time_dialog import SetTimeDialog

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

COMPONENTS = [Envelope, RTU, SolarGains]
COMPONENTS = [Envelope, RTU, VAVBox, SolarGains]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyTorch Buildings GUI")
        self.setGeometry(100, 100, 1500, 900)
        self.building_model = BuildingModel("Model")
        self.canvas = InteractiveCanvas(self.building_model)
        self.canvas.component_click_handler = self.handle_component_click_action
        self.canvas.component_added_handler = self.on_component_added
        self.canvas.area_delete_handler = self.on_area_deleted
        self.pending_component_action = None
        self.pending_connection_items = []
        self.next_component_id = 1
        self.action_buttons = []
        self.add_connection_btn = None
        self.area_delete_btn = None
        self.edit_component_btn = None
        self.delete_component_btn = None
        self.mode_status_label = None
        self.component_list = QTreeWidget()
        self.component_list.setColumnCount(2)
        self.component_list.setHeaderLabels(["Component", "Value"])
        self.component_list.setAlternatingRowColors(True)
        self.component_list.setRootIsDecorated(True)
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
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)
        central_widget.setLayout(root_layout)
        self.ribbon_tabs = self.create_ribbon_tabs()
        root_layout.addWidget(self.ribbon_tabs)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.create_left_panel())
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 1170])
        root_layout.addWidget(splitter)
        self.setStatusBar(QStatusBar())
        self.setup_dependency_status_button()
        self.setup_mode_status_label()
        self.set_component_action_mode(None)
        self.statusBar().showMessage("Ready")
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

    def _placeholder_icon(self):
        size = 32
        tile = 8
        pixmap = QPixmap(size, size)
        painter = QPainter(pixmap)
        white = QColor(255, 255, 255)
        black = QColor(0, 0, 0)
        for y in range(0, size, tile):
            for x in range(0, size, tile):
                use_white = ((x // tile) + (y // tile)) % 2 == 0
                painter.fillRect(x, y, tile, tile, white if use_white else black)
        painter.end()
        return QIcon(pixmap)

    def setup_mode_status_label(self):
        label = QLabel("Mode: Normal")
        label.setStyleSheet("color: #555; padding-right: 8px;")
        self.statusBar().addPermanentWidget(label)
        self.mode_status_label = label

    def _load_action_icon(self, *icon_names):
        icon_dirs = [
            self.assets_path / "icons",
            self.assets_path / "buttons",
            self.assets_path,
        ]
        extensions = [".png", ".svg", ".jpg", ".jpeg", ".webp", ".bmp"]

        for icon_name in icon_names:
            if not icon_name:
                continue
            provided_name = Path(icon_name)
            if provided_name.suffix:
                for icon_dir in icon_dirs:
                    icon_path = icon_dir / icon_name
                    if icon_path.exists():
                        return QIcon(str(icon_path))
            for icon_dir in icon_dirs:
                for extension in extensions:
                    icon_path = icon_dir / f"{icon_name}{extension}"
                    if icon_path.exists():
                        return QIcon(str(icon_path))

        return self._placeholder_icon()

    def create_action_button(self, label, callback, *icon_names):
        button = QToolButton()
        button.setText(label)
        button.setIcon(self._load_action_icon(*icon_names, label.lower().replace(" ", "_")))
        button.setIconSize(QSize(32, 32))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setAutoRaise(True)
        button.setMinimumSize(92, 66)
        button.setStyleSheet(
            """
            QToolButton {
                border: none;
                background: transparent;
                padding: 2px 4px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 6px;
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.09);
                border-radius: 6px;
            }
            QToolButton:checked {
                background-color: rgba(0, 0, 0, 0.12);
                border-radius: 6px;
            }
            """
        )
        button.clicked.connect(callback)
        self.action_buttons.append(button)
        return button

    def create_component_drag_button(self, label, component_name, *icon_names):
        button = DragButton(label, component_name)
        button.setIcon(self._load_action_icon(*icon_names, label.lower().replace(" ", "_")))
        button.setIconSize(QSize(32, 32))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setAutoRaise(True)
        button.setMinimumSize(92, 66)
        button.setStyleSheet(
            """
            QToolButton {
                border: none;
                background: transparent;
                padding: 2px 4px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 6px;
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.09);
                border-radius: 6px;
            }
            """
        )
        self.action_buttons.append(button)
        return button

    def build_dependency_tooltip(self):
        lines = ["Dependency status:"]
        for name, (ok, version) in self.dep_results.items():
            icon = "✓" if ok else "✗"
            version_text = version if version else "not found"
            lines.append(f"{icon} {name}: {version_text}")
        return "\n".join(lines)

    def create_ribbon_tabs(self):
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setMovable(False)
        tabs.addTab(self.create_home_tab(), "Home")
        tabs.addTab(self.create_components_tab(), "Components")
        tabs.addTab(self.create_tools_tab(), "Tools")
        return tabs

    def create_home_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        save_btn = self.create_action_button(
            "Save", self.save_layout, "save_asset", "save"
        )
        load_btn = self.create_action_button(
            "Load", self.load_layout, "load_asset", "load"
        )
        run_btn = self.create_action_button(
            "Run Simulation",
            self.run_simulation,
            "run_simulation_asset",
            "run_simulation",
            "run",
        )
        set_time_btn = self.create_action_button(
            "Set Time", self.open_set_time_dialog, "time_asset", "set_time", "time"
        )
        layout.addWidget(save_btn)
        layout.addWidget(load_btn)
        layout.addWidget(run_btn)
        layout.addWidget(set_time_btn)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_components_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        icon_name_by_component = {
            "Envelope": ["add_envelope_asset", "add_envelope"],
            "RTU": ["add_rtu_asset", "add_rtu"],
                "VAVBox": ["add_vavbox_asset", "add_vavbox"],
            "SolarGains": ["add_solargains_asset.png.png", "add_solargains_asset"],
        }
        for cls in COMPONENTS:
            icon_names = icon_name_by_component.get(
                cls.__name__, [f"add_{cls.__name__.lower()}_asset", cls.__name__.lower()]
            )
            button = self.create_component_drag_button(
                cls.__name__,
                cls.__name__,
                *icon_names,
                cls.__name__.lower(),
            )
            layout.addWidget(button)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def create_tools_tab(self):
        tab = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)
        add_connection_btn = self.create_action_button(
            "Add Connection",
            self.add_connection,
            "add_connection_asset",
            "add_connection",
            "connection",
        )
        layout.addWidget(add_connection_btn)
        self.add_connection_btn = add_connection_btn
        edit_component_btn = self.create_action_button(
            "Edit Component",
            self.arm_edit_component,
            "edit_component_asset",
            "edit_component",
            "edit",
        )
        edit_component_btn.setCheckable(True)
        layout.addWidget(edit_component_btn)
        self.edit_component_btn = edit_component_btn
        delete_component_btn = self.create_action_button(
            "Delete Component",
            self.arm_delete_component,
            "delete_component_asset",
            "delete_component",
            "delete",
        )
        delete_component_btn.setCheckable(True)
        layout.addWidget(delete_component_btn)
        self.delete_component_btn = delete_component_btn
        area_delete_btn = self.create_action_button(
            "Delete Area",
            self.arm_area_delete,
            "delete_area_asset",
            "delete_area",
            "delete",
        )
        area_delete_btn.setCheckable(True)
        layout.addWidget(area_delete_btn)
        self.area_delete_btn = area_delete_btn
        layout.addStretch()
        tab.setLayout(layout)
        return tab

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
        else:
            for button in self.action_buttons:
                button.setEnabled(button in mode_buttons)
            if self.mode_status_label is not None:
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
        ok, message = self.canvas.add_connection_between_items(src_item, dst_item, src_output="output", dst_input="input")
        if ok:
            self.refresh_connection_list()
        self.statusBar().showMessage(message, 4000)
        src_item.setSelected(False)
        dst_item.setSelected(False)
        self.pending_connection_items.clear()
        self.set_component_action_mode(None)
        if not ok:
            QMessageBox.information(self, "Add Connection", message)

    def handle_component_click_action(self, component_item):
        if self.pending_component_action == "delete":
            component_name = component_item.label.toPlainText()
            self.canvas.remove_component_item(component_item)
            self.refresh_component_list()
            self.statusBar().showMessage(f"Deleted {component_name}", 4000)
            self.set_component_action_mode(None)
        elif self.pending_component_action == "edit":
            component_name = component_item.label.toPlainText()
            component_item.edit_properties()
            self.refresh_component_list()
            self.statusBar().showMessage(f"Edited {component_name}", 4000)
            self.set_component_action_mode(None)
        elif self.pending_component_action == "connect":
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

    def open_set_time_dialog(self):
        dialog = SetTimeDialog(self.building_model, self)
        dialog.exec()

    def refresh_component_list(self):
        self.component_list.clear()
        component_count = 0
        for item in self.canvas.scene.items():
            if hasattr(item, "node") and hasattr(item, "label"):
                component_count += 1
                root = QTreeWidgetItem(self.component_list)
                root.setText(0, f"{component_count}. {item.label.toPlainText()}")
                values = item.serialize_values()
                for prop_name, prop_value in values.items():
                    child = QTreeWidgetItem(root)
                    child.setText(0, str(prop_name))
                    child.setText(1, self._format_property_value(prop_value))
        self.refresh_connection_list()

    def refresh_connection_list(self):
        self.connection_list.clear()
        for index, connection_data in enumerate(self.canvas.visual_connections, start=1):
            src_item = connection_data.get("src_item")
            dst_item = connection_data.get("dst_item")
            src_name = src_item.label.toPlainText() if src_item is not None else "Unknown"
            dst_name = dst_item.label.toPlainText() if dst_item is not None else "Unknown"
            root = QTreeWidgetItem(self.connection_list)
            root.setText(0, f"{index}. {src_name} -> {dst_name}")
            src_child = QTreeWidgetItem(root)
            src_child.setText(0, f"Source: {src_name}")
            dst_child = QTreeWidgetItem(root)
            dst_child.setText(0, f"Destination: {dst_name}")

    def _format_property_value(self, value):
        if isinstance(value, list):
            return "[" + ", ".join(self._format_property_value(v) for v in value) + "]"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def on_area_deleted(self, count):
        self.refresh_component_list()
        self.set_component_action_mode(None)
        self.statusBar().showMessage(f"Deleted {count} component(s) in selected area.", 4000)

    def _should_inline_list(self, value):
        if not isinstance(value, list):
            return False
        for item in value:
            if isinstance(item, dict):
                return False
            if isinstance(item, list) and not self._should_inline_list(item):
                return False
        return True

    def _format_json_with_inline_lists(self, value, indent_level=0):
        indent = "  " * indent_level
        child_indent = "  " * (indent_level + 1)
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            items = list(value.items())
            for index, (key, item_value) in enumerate(items):
                comma = "," if index < len(items) - 1 else ""
                value_str = self._format_json_with_inline_lists(item_value, indent_level + 1)
                lines.append(f"{child_indent}{json.dumps(key)}: {value_str}{comma}")
            lines.append(f"{indent}" + "}")
            return "\n".join(lines)

        if isinstance(value, list):
            if not value:
                return "[]"
            if self._should_inline_list(value):
                return json.dumps(value)
            lines = ["["]
            for index, item in enumerate(value):
                comma = "," if index < len(value) - 1 else ""
                item_str = self._format_json_with_inline_lists(item, indent_level + 1)
                lines.append(f"{child_indent}{item_str}{comma}")
            lines.append(f"{indent}]")
            return "\n".join(lines)
        return json.dumps(value)

    def save_layout(self):
        saved_dir = Path.cwd() / "saved"
        saved_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = saved_dir / f"building_layout_{timestamp}.json"
        component_items = [
            item
            for item in self.canvas.scene.items()
            if hasattr(item, "node") and hasattr(item, "label")
        ]
        component_index = {item: idx for idx, item in enumerate(component_items)}
        for item in component_items:
            if not getattr(item, "component_id", None):
                item.component_id = self._generate_component_id()
            self._sync_next_component_id(item.component_id)
        component_sections = {}
        for item in component_items:
            component_sections[item.component_id] = {
                "type": item.label.toPlainText(),
                "position": {
                    "x": item.pos().x(),
                    "y": item.pos().y(),
                },
                "values": item.serialize_values(),
            }
        payload = {
            "name": self.building_model.name,
            "components": [
                {
                    "id": item.component_id,
                    "type": item.label.toPlainText(),
                    "x": item.pos().x(),
                    "y": item.pos().y(),
                    "values": item.serialize_values(),
                }
                for item in component_items
            ],
            "component_sections": component_sections,
            "connections": [
                {
                    "src_id": getattr(conn_data["src_item"], "component_id", None),
                    "dst_id": getattr(conn_data["dst_item"], "component_id", None),
                    "src_output": conn_data["connection"].srcOutput,
                    "dst_input": conn_data["connection"].dstInput,
                    "src": component_index.get(conn_data["src_item"]),
                    "dst": component_index.get(conn_data["dst_item"]),
                }
                for conn_data in self.canvas.visual_connections
                if conn_data["src_item"] in component_index
                and conn_data["dst_item"] in component_index
            ],
            "time": {
                "t_start": self.building_model.t_start,
                "t_duration": self.building_model.t_duration,
                "dt": self.building_model.dt,
            },
        }
        with open(save_path, "w", encoding="utf-8") as json_file:
            json_file.write(self._format_json_with_inline_lists(payload) + "\n")
        self.statusBar().showMessage(f"Saved layout to {save_path}", 5000)

    def load_layout(self):
        saved_dir = Path.cwd() / "saved"
        load_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Layout",
            str(saved_dir if saved_dir.exists() else Path.cwd()),
            "JSON Files (*.json)",
        )
        if not load_path:
            return
        with open(load_path, "r", encoding="utf-8") as json_file:
            payload = json.load(json_file)
        self.canvas.clear_all()
        self.next_component_id = 1
        self.building_model.name = payload.get("name", self.building_model.name)
        component_sections = payload.get("component_sections", {})
        items = []
        items_by_id = {}
        for component_data in payload.get("components", []):
            component_id = component_data.get("id")
            component_section = component_sections.get(component_id, {})
            section_position = component_section.get("position", {})
            position_x = component_data.get("x", section_position.get("x", 0))
            position_y = component_data.get("y", section_position.get("y", 0))
            values = component_data.get("values", component_section.get("values", {}))
            item = self.canvas.add_component(
                component_data["type"],
                self.canvas.mapToScene(self.canvas.viewport().rect().center()),
                component_id=component_id,
                component_values=values,
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
                    component_id=component_id,
                    component_values=component_section.get("values", {}),
                )
                item.setPos(position.get("x", 0), position.get("y", 0))
                items.append(item)
                if item.component_id:
                    items_by_id[item.component_id] = item
                    self._sync_next_component_id(item.component_id)
        for connection_data in payload.get("connections", []):
            src_item = items_by_id.get(connection_data.get("src_id"))
            dst_item = items_by_id.get(connection_data.get("dst_id"))
            if src_item is None or dst_item is None:
                src_index = connection_data.get("src")
                dst_index = connection_data.get("dst")
                if (isinstance(src_index, int) and isinstance(dst_index, int) and 0 <= src_index < len(items) and 0 <= dst_index < len(items)):
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
                src_output=connection_data.get("src_output", "output"),
                dst_input=connection_data.get("dst_input", "input"),
            )
            src_item.setSelected(False)
            dst_item.setSelected(False)
        time_data = payload.get("time", {})
        self.building_model.t_start = float(time_data.get("t_start", self.building_model.t_start))
        self.building_model.t_duration = float(time_data.get("t_duration", self.building_model.t_duration))
        self.building_model.dt = float(time_data.get("dt", self.building_model.dt))
        self.refresh_component_list()
        self.statusBar().showMessage(f"Loaded layout from {load_path}", 4000)
