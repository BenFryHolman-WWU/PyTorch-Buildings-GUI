"""Graphics items used by the interactive canvas."""

import torch
from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QMimeData
from PyQt6.QtGui import QBrush, QColor, QDrag, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsTextItem, QMenu, QToolButton, QDialog

from neuromancer.hvac.building import BuildingNode
from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox

from .dialogue_manager import COMPONENT_MUTABLE_PROPERTIES, PropertyDialog


COMPONENT_GAP = 24.0
COMPONENT_ICON_NAMES = {
    "Envelope": ("RTU", "rtu", "rooftop_unit"),
    "RTU": ("Envelope", "envelope", "building_envelope"),
    "VAVBox": ("Vavbox", "vav_box", "vav"),
    "SolarGains": ("SolarGains", "solar_gains", "solar"),
}


class DragButton(QToolButton):

    def __init__(self, label, component_name = None):
        super().__init__()
        self.setText(label)
        self.component_name = component_name or label
        self.drag_start_pos = QPoint()


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """Summary: Mousemoveevent."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.component_name)
        drag.setMimeData(mime)
        pixmap = QPixmap(1, 1)
        pixmap.fill(Qt.GlobalColor.transparent)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(0, 0))
        drag.exec(Qt.DropAction.MoveAction)
        self.setDown(False)


class ComponentItem(QGraphicsRectItem):

    MUTABLE_PROPERTIES = COMPONENT_MUTABLE_PROPERTIES


    def __init__(self, name, pos, building_model, canvas, component_id = None, preview_only=False):
        """
        Summary: Init.
        Args: building_model, canvas, component_id
        """
        super().__init__(0, 0, 132, 74)
        self.building_model = building_model
        self.canvas = canvas
        self.component_id = component_id
        self.preview_only = preview_only
        self.icon_provider = getattr(canvas, "icons", None)
        self.normal_pen = QPen(QColor("#9db8e4"), 1.5)
        self.hover_pen = QPen(QColor("#6f95d0"), 1.8)
        self.selected_pen = QPen(QColor("#2f5f9f"), 2.4)
        self.delete_preview_pen = QPen(QColor("#c04040"), 2.4)
        self.normal_brush = QBrush(QColor("#ffffff"))
        self.hover_brush = QBrush(QColor("#ffffff"))
        self.delete_preview_brush = QBrush(QColor("#ffffff"))
        self._is_dragging = False
        self._delete_preview = False
        self.setPos(pos)
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setAcceptHoverEvents(True)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.icon_item = QGraphicsPixmapItem(self)
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(QColor("#2c3454"))
        self._layout_contents()
        if self.preview_only:
            self.component = None
            self.node = None
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.setAcceptHoverEvents(False)
            self.setFlags(QGraphicsRectItem.GraphicsItemFlag(0))
            self.setOpacity(0.45)
            self.setZValue(20)
        else:
            self.component, self.node = self.createComponent(name)


    def _component_icon_pixmap(self):
        if self.icon_provider is None:
            return QPixmap()
        icon = self.icon_provider.icon(
            *COMPONENT_ICON_NAMES.get(self.label.toPlainText(), (self.label.toPlainText(),)),
            fallback_text=self.label.toPlainText(),
        )
        return icon.pixmap(34, 34)


    def _layout_contents(self):
        pixmap = self._component_icon_pixmap()
        if not pixmap.isNull():
            self.icon_item.setPixmap(pixmap)
            self.icon_item.setPos(49, 8)
        text_width = self.label.boundingRect().width()
        self.label.setPos(66 - text_width / 2, 48)

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(self.normal_brush)
        painter.drawRect(self.rect())


    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.canvas.update_connection_lines_for_item(self)
            self.canvas.set_dirty(True)
            self._update_overlap_preview()
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            if not self._delete_preview:
                self.setPen(self.selected_pen if bool(value) else self.normal_pen)
        return super().itemChange(change, value)


    def _component_items(self):
        if self.scene() is None:
            return []
        return [
            item for item in self.scene().items()
            if (
                item is not self
                and isinstance(item, ComponentItem)
                and not getattr(item, "preview_only", False)
            )
        ]


    def _barrier_rect_for(self, item):
        return item.sceneBoundingRect().adjusted(
            -COMPONENT_GAP,
            -COMPONENT_GAP,
            COMPONENT_GAP,
            COMPONENT_GAP,
        )


    def _candidate_rect_at(self, pos):
        return QRectF(pos, self.rect().size())


    def _overlaps_component_barrier(self, pos=None):
        candidate_rect = self._candidate_rect_at(pos if pos is not None else self.pos())
        return any(
            candidate_rect.intersects(self._barrier_rect_for(item))
            for item in self._component_items()
        )


    def _update_overlap_preview(self):
        if self._is_dragging and self._overlaps_component_barrier():
            self.setOpacity(0.45)
        else:
            self.setOpacity(1.0)


    def _non_overlapping_position(self, proposed_pos):
        """
        Summary: Non overlapping position.
        Args: proposed_pos
        Returns: Return the computed value.
        """
        if self.scene() is None or not isinstance(proposed_pos, QPointF):
            return proposed_pos
        adjusted_pos = QPointF(proposed_pos)
        for _ in range(3):
            changed = False
            candidate_rect = self._candidate_rect_at(adjusted_pos)
            for item in self._component_items():
                barrier_rect = self._barrier_rect_for(item)
                if not candidate_rect.intersects(barrier_rect):
                    continue
                candidate_center = candidate_rect.center()
                barrier_center = barrier_rect.center()
                if candidate_center.x() < barrier_center.x():
                    shift_x = barrier_rect.left() - candidate_rect.right()
                else:
                    shift_x = barrier_rect.right() - candidate_rect.left()
                if candidate_center.y() < barrier_center.y():
                    shift_y = barrier_rect.top() - candidate_rect.bottom()
                else:
                    shift_y = barrier_rect.bottom() - candidate_rect.top()
                if abs(shift_x) <= abs(shift_y):
                    adjusted_pos.setX(adjusted_pos.x() + shift_x)
                else:
                    adjusted_pos.setY(adjusted_pos.y() + shift_y)
                candidate_rect = self._candidate_rect_at(adjusted_pos)
                changed = True
            if not changed:
                break
        return adjusted_pos


    def hoverEnterEvent(self, event):
        if getattr(self.canvas, "exclusive_action_mode", None) == "delete":
            self.set_delete_preview(True)
            super().hoverEnterEvent(event)
            return
        if not self.isSelected():
            self.setPen(self.hover_pen)
        self.setBrush(self.hover_brush)
        super().hoverEnterEvent(event)


    def hoverLeaveEvent(self, event):
        if getattr(self.canvas, "exclusive_action_mode", None) == "delete":
            area_preview_items = getattr(self.canvas, "area_delete_preview_items", set())
            if self not in area_preview_items:
                self.set_delete_preview(False)
            super().hoverLeaveEvent(event)
            return
        self.setPen(self.selected_pen if self.isSelected() else self.normal_pen)
        self.setBrush(self.normal_brush)
        super().hoverLeaveEvent(event)


    def set_delete_preview(self, enabled):
        self._delete_preview = bool(enabled)
        if self._delete_preview:
            self.setPen(self.delete_preview_pen)
            self.setBrush(self.delete_preview_brush)
        else:
            self.setPen(self.selected_pen if self.isSelected() else self.normal_pen)
            self.setBrush(self.normal_brush)


    def mousePressEvent(self, event):
        if not getattr(self.canvas, "editing_enabled", True):
            super().mousePressEvent(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.canvas.notify_component_clicked(self)


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            if self._overlaps_component_barrier():
                self.setPos(self._non_overlapping_position(self.pos()))
            self._update_overlap_preview()


    def _input_map_for(self, name):
        """
        Summary: Input map for.
        Returns: Return the computed value.
        """
        maps = {
            "solar": {
                "T_outdoor":      "T_outdoor",
                "weather_factor": "weather_factor",
            },
            "rtu": {
                "T_outdoor":                  "T_outdoor",
                "envelope.T_zones":           "T_return_zones",
                "vav.supply_airflow":         "return_airflow_zones",
                "T_supply_setpoint":          "T_supply_setpoint",
                "supply_airflow_setpoint":    "supply_airflow_setpoint",
                "rtu.damper_position":        "damper_position",
                "rtu.valve_position":         "valve_position",
                "rtu.T_supply":               "T_supply",
                "rtu.integral_accumulator":   "integral_accumulator",
            },
            "vav": {
                "envelope.T_zones":   "T_zone",
                "T_setpoint":         "T_setpoint",
                "rtu.T_supply":       "T_supply_upstream",
                "rtu.P_supply":       "P_duct",
                "vav.damper_position":"damper_position",
                "vav.reheat_position":"reheat_position",
            },
            "envelope": {
                "envelope.T_zones":  "T_zones",
                "T_outdoor":         "T_outdoor",
                "solar.Q_solar":     "Q_solar",
                "Q_internal":        "Q_internal",
                "vav.Q_supply_flow": "Q_hvac",
            },
        }
        return maps.get(name, {})


    def pad_attribute(self, values, n_zones):
        values = list(values)
        if len(values) > n_zones:
            return values[:n_zones]
        last = values[-1] if values else 0.0
        return values + [last] * (n_zones - len(values))


    def pad_matrix(self, values, n_zones):
        """
        Summary: Pad matrix.
        Args: n_zones
        Returns: Return the computed value.
        """
        matrix = [list(row) for row in values[:n_zones]]
        for row_index, row in enumerate(matrix):
            if len(row) > n_zones:
                matrix[row_index] = row[:n_zones]
            elif len(row) < n_zones:
                matrix[row_index] = row + [0.0] * (n_zones - len(row))
        while len(matrix) < n_zones:
            new_row = [0.0] * n_zones
            new_row[len(matrix)] = 1.0
            matrix.append(new_row)
        return matrix


    def createComponent(self, name):
        """
        Summary: Createcomponent.
        Returns: Return the computed value.
        """
        n_zones = int(getattr(self.building_model, "n_zones", 2))
        match name:
            case "RTU":
                component = RTU(
                    n_zones = n_zones,
                    airflow_max = 4.0,
                    airflow_oa_min = 0.4,
                    Q_coil_max = 20000.0,
                    fan_power_per_flow = 800.0,
                    cooling_COP = 3.2,
                    heating_efficiency = 0.88,
                )
                node = BuildingNode(component, input_map = self._input_map_for("rtu"), name = "rtu")
            case "Envelope":
                component = Envelope(
                    n_zones = n_zones,
                    R_env = self.pad_attribute([0.1, 0.12], n_zones),
                    C_env = self.pad_attribute([1.2e6, 1.0e6], n_zones),
                    R_internal = 0.05,
                    adjacency = self.pad_matrix([[1.0, 0.0], [0.0, 1.0]], n_zones),
                )
                node = BuildingNode(component, input_map = self._input_map_for("envelope"), name = "envelope")
            case "VAVBox":
                component = VAVBox(
                    n_zones = n_zones,
                    airflow_min = self.pad_attribute([0.1, 0.08], n_zones),
                    airflow_max = self.pad_attribute([0.8, 0.6], n_zones),
                    control_gain = self.pad_attribute([2.5, 2.0], n_zones),
                    Q_reheat_max = self.pad_attribute([3000, 2500], n_zones),
                    reheat_efficiency = 0.95,
                )
                node = BuildingNode(component, input_map = self._input_map_for("vav"), name = "vav")
            case "SolarGains":
                component = SolarGains(
                    n_zones = n_zones,
                    window_area = 25.0,
                    window_orientation = self.pad_attribute([0.0, 90.0], n_zones),
                    window_shgc = 0.6,
                    latitude_deg = 40.0,
                    max_solar_irradiance = 800.0,
                )
                node = BuildingNode(component, input_map = self._input_map_for("solar"), name = "solar")
            case "ControlPolicy":
                component = ControlPolicy(
                    n_zones = n_zones
                )
                node = BuildingNode(component, input_map = {}, name = "control")
            case _:
                raise ValueError(f"Unsupported component type: {name}")
        return component, node


    def contextMenuEvent(self, event):
        """Summary: Contextmenuevent."""
        if not getattr(self.canvas, "editing_enabled", True) or getattr(self.canvas, "exclusive_action_mode", None):
            event.ignore()
            return
        menu = QMenu()
        property_action = menu.addAction("Edit Component")
        delete_action = menu.addAction("Delete Component")
        selected_action = menu.exec(event.screenPos())
        if selected_action == delete_action:
            self.canvas.delete_component_items([self])
        elif selected_action == property_action:
            self.edit_properties()

    def edit_properties(self):
        """Summary: Edit properties."""
        before = self.serialize_values()

        dialog = PropertyDialog(self.component, n_zones=self.building_model.n_zones, parent=self.canvas)

        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            after = self.serialize_values()
            if before != after:
                self.canvas.set_dirty(True)


    def get_mutable_property_names(self):
        return self.MUTABLE_PROPERTIES.get(type(self.component).__name__, [])


    def serialize_values(self):
        """
        Summary: Serialize values.
        Returns: Return the computed value.
        """
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
        """Summary: Apply serialized values."""
        if not isinstance(values, dict):
            return
        for prop in self.get_mutable_property_names():
            if prop not in values:
                continue
            loaded_value = values[prop]
            if isinstance(loaded_value, (int, float, list)):
                tensor_value = torch.tensor(loaded_value)
                setattr(self.component, prop, tensor_value)
                if prop == "airflow_max" and hasattr(self.component, "damper"):
                    self.component.damper.max_airflow = tensor_value
                elif prop == "Q_reheat_max" and hasattr(self.component, "electric_reheat_coil"):
                    self.component.electric_reheat_coil.max_thermal_output = tensor_value

class ControlPolicy(QGraphicsRectItem):
    def __init__(self, n_zones, tu_T_supply_setpoint=torch.tensor(285.15), rtu_supply_airflow_setpoint=torch.tensor(1)):
        self.tu_T_supply_setpoint = tu_T_supply_setpoint
        self.rtu_supply_airflow_setpoint = rtu_supply_airflow_setpoint
        self._state_ranges = {}
        self._external_ranges = {}
        super().__init__()
