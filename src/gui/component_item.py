import io
from contextlib import redirect_stdout
import torch
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu
from neuromancer.hvac.building import BuildingNode
from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox
from .property_dialog import PropertyDialog

class ComponentItem(QGraphicsRectItem):
    MUTABLE_PROPERTIES = {
        "RTU": [
            "airflow_max",
            "airflow_oa_min",
            "Q_coil_max",
            "fan_power_per_flow",
            "cooling_COP",
            "heating_efficiency",
        ],
        "Envelope": ["R_env", "C_env", "R_internal", "adjacency"],
        "VAVBox": [
            "airflow_min",
            "airflow_max",
            "control_gain",
            "Q_reheat_max",
            "reheat_efficiency",
        ],
        "SolarGains": [
            "window_area",
            "window_orientation",
            "window_shgc",
            "latitude_deg",
            "max_solar_irradiance",
        ],
    }

    def __init__(self, name, pos, building_model, canvas, component_id=None):
        super().__init__(0, 0, 120, 50)
        self.building_model = building_model
        self.canvas = canvas
        self.component_id = component_id
        self.normal_pen = QPen(QColor(50, 150, 200), 2)
        self.selected_pen = QPen(QColor(30, 30, 30), 3)
        self.setPos(pos)
        self.setBrush(QColor(100, 200, 250, 180))
        self.setPen(self.normal_pen)
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(60 - self.label.boundingRect().width() / 2, 25 - self.label.boundingRect().height() / 2)
        self.component, self.node = self.createComponent(name)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.canvas.update_connection_lines_for_item(self)
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.setPen(self.selected_pen if bool(value) else self.normal_pen)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.canvas.notify_component_clicked(self)

    def auto_input_map(self, component):
        state_keys = list(getattr(component, "_state_ranges", {}).keys())
        external_keys = list(getattr(component, "_external_ranges", {}).keys())
        keywords = state_keys + external_keys
        if not keywords:
            keywords = list(getattr(component, "input_keywords", []) or [])

        return {key: key for key in keywords}

    def createComponent(self, name):
        n_zones = 2
        match name:
            case "RTU":
                component = RTU(
                    n_zones=n_zones,
                    airflow_max=4.0,
                    airflow_oa_min=0.4,
                    Q_coil_max=20000.0,
                    fan_power_per_flow=800.0,
                    cooling_COP=3.2,
                    heating_efficiency=0.88,
                )
                node = BuildingNode(component, input_map=self.auto_input_map(component), name="rtu")
            case "Envelope":
                component = Envelope(
                    n_zones=n_zones,
                    R_env=[0.1, 0.12],
                    C_env=[1.2e6, 1.0e6],
                    R_internal=0.05,
                    adjacency=[[1.0, 0.0], [0.0, 1.0]],
                )
                node = BuildingNode(component, input_map=self.auto_input_map(component), name="envelope")
            case "VAVBox":
                  component = VAVBox(
                        n_zones=n_zones,
                        airflow_min=[0.1, 0.08],
                        airflow_max=[0.8, 0.6],
                        control_gain=[2.5, 2.0],
                        Q_reheat_max=[3000, 2500],
                        reheat_efficiency=0.95,
                  )
                  node = BuildingNode(component, input_map=self.auto_input_map(component), name="vav")
            case "SolarGains":
                component = SolarGains(
                    n_zones=n_zones,
                    window_area=25.0,
                    window_orientation=[0.0, 90.0],
                    window_shgc=0.6,
                    latitude_deg=40.0,
                    max_solar_irradiance=800.0,
                )
                node = BuildingNode(component, input_map=self.auto_input_map(component), name="solar")
            case _:
                raise ValueError(f"Unsupported component type: {name}")
        return component, node

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        property_action = menu.addAction("Update properties")
        selected_action = menu.exec(event.screenPos())
        if selected_action == delete_action:
            self.canvas.remove_component_item(self)
        elif selected_action == property_action:
            self.edit_properties()

    def edit_properties(self):
        dialog = PropertyDialog(self.component)
        dialog.exec()

    def get_mutable_property_names(self):
        return self.MUTABLE_PROPERTIES.get(type(self.component).__name__, [])

    def serialize_values(self):
        values = {}
        for prop in self.get_mutable_property_names():
            if not hasattr(self.component, prop):
                continue
            raw_value = getattr(self.component, prop)
            if isinstance(raw_value, torch.Tensor):
                values[prop] = raw_value.tolist()
            else:
                values[prop] = raw_value
        return values

    def apply_serialized_values(self, values):
        if not isinstance(values, dict):
            return
        for prop in self.get_mutable_property_names():
            if prop not in values:
                continue
            loaded_value = values[prop]
            if isinstance(loaded_value, (int, float, list)):
                setattr(self.component, prop, torch.tensor(loaded_value))
