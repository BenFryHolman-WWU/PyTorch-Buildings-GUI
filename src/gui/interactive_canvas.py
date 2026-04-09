import math
import torch
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QRubberBand, QToolButton, QApplication, QGraphicsRectItem, QGraphicsTextItem, QMenu
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush, QPolygonF, QDrag
from PyQt6.QtCore import Qt, QLineF, QPointF, pyqtSignal, QMimeData, QPoint
from neuromancer.hvac.building import BuildingNode
from neuromancer.hvac.building_components import Envelope, RTU, SolarGains, VAVBox
from .canvas_tool_manager import CanvasToolManager
from .dialogue_manager import PropertyDialog, COMPONENT_MUTABLE_PROPERTIES
from .state_manager import Connection


class DragButton(QToolButton):
    """A toolbar button that supports drag and drop for components."""
    
    def __init__(self, label, component_name = None):
        """Initialize a drag button. Args: label (str), component_name (str, optional)."""
        super().__init__()
        self.setText(label)
        self.component_name = component_name or label
        self.drag_start_pos = QPoint()


    def mousePressEvent(self, event):
        """Handle mouse press to initiate drag. Args: event (QMouseEvent)."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """Handle mouse move to perform drag operation. Args: event (QMouseEvent)."""
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
        drag.exec(Qt.DropAction.MoveAction)
        self.setDown(False)


class ComponentItem(QGraphicsRectItem):
    """Represents a building component in the canvas with graphics and properties."""
    
    MUTABLE_PROPERTIES = COMPONENT_MUTABLE_PROPERTIES

    
    def __init__(self, name, pos, building_model, canvas, component_id = None):
        """Initialize a component item. Args: name (str), pos (QPointF), building_model (BuildingModel), canvas (InteractiveCanvas), component_id (str, optional)."""
        super().__init__(0, 0, 120, 50)
        self.building_model = building_model
        self.canvas = canvas
        self.component_id = component_id
        self.normal_pen = QPen(QColor(50, 150, 200), 2)
        self.selected_pen = QPen(QColor(30, 30, 30), 3)
        self.setPos(pos)
        self.setBrush(QColor(100, 200, 250, 180))
        self.setPen(self.normal_pen)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(60 - self.label.boundingRect().width() / 2, 25 - self.label.boundingRect().height() / 2)
        self.component, self.node = self.createComponent(name)


    def itemChange(self, change, value):
        """Handle item changes like position and selection. Args: change, value. Returns: value."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.canvas.update_connection_lines_for_item(self)
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.setPen(self.selected_pen if bool(value) else self.normal_pen)
        return super().itemChange(change, value)


    def mousePressEvent(self, event):
        """Handle mouse press on component. Args: event (QGraphicsSceneMouseEvent)."""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.canvas.notify_component_clicked(self)


    def _input_map_for(self, name):
        """Return the explicit input map for a named component, mirroring hvac_example.py. Args: name (str). Returns: dict."""
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
        """Pad or trim values list to zone count. Args: values (list), n_zones (int). Returns: list."""
        values = list(values)
        if len(values) > n_zones:
            return values[:n_zones]
        return values + [0.0] * (n_zones - len(values))


    def pad_matrix(self, values, n_zones):
        """Pad or trim matrix to zone count. Args: values (list), n_zones (int). Returns: list."""
        matrix = [list(row) for row in values[:n_zones]]
        for row_index, row in enumerate(matrix):
            if len(row) > n_zones:
                matrix[row_index] = row[:n_zones]
            elif len(row) < n_zones:
                matrix[row_index] = row + [0.0] * (n_zones - len(row))
        while len(matrix) < n_zones:
            matrix.append([0.0] * n_zones)
        return matrix


    def createComponent(self, name):
        """Create a component instance based on type. Args: name (str). Returns: tuple (component, node)."""
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
            case _:
                raise ValueError(f"Unsupported component type: {name}")
        return component, node


    def contextMenuEvent(self, event):
        """Handle right-click context menu. Args: event (QGraphicsSceneContextMenuEvent)."""
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        property_action = menu.addAction("Update properties")
        selected_action = menu.exec(event.screenPos())
        if selected_action == delete_action:
            self.canvas.remove_component_item(self)
        elif selected_action == property_action:
            self.edit_properties()


    def edit_properties(self):
        """Open the property editor dialog for this component."""
        PropertyDialog(self.component, n_zones=self.building_model.n_zones).exec()


    def get_mutable_property_names(self):
        """Get list of mutable property names for this component. Returns: list."""
        return self.MUTABLE_PROPERTIES.get(type(self.component).__name__, [])


    def serialize_values(self):
        """Serialize component property values to dict. Returns: dict."""
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
        """Apply serialized property values to component. Args: values (dict, optional)."""
        if not isinstance(values, dict):
            return
        for prop in self.get_mutable_property_names():
            if prop not in values:
                continue
            loaded_value = values[prop]
            if isinstance(loaded_value, (int, float, list)):
                setattr(self.component, prop, torch.tensor(loaded_value))


class InteractiveCanvas(QGraphicsView):
    """A graphics view for displaying and interacting with building components."""
    
    zoom_changed = pyqtSignal(int)


    def __init__(self, building_model):
        """Initialize the canvas. Args: building_model (BuildingModel)."""
        super().__init__()
        self.building_model = building_model
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setAcceptDrops(True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(240, 240, 245)))
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.current_drag_item = None
        self.visual_connections = []
        self.component_click_handler = None
        self.component_added_handler = None
        self.area_delete_handler = None
        self.area_delete_mode = False
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self.rubber_band_origin = None
        self.tool_manager = CanvasToolManager(self)
        self.draw_grid()
        self._emit_zoom_changed()


    def resizeEvent(self, event):
        """Handle canvas resize. Args: event (QResizeEvent)."""
        super().resizeEvent(event)


    def get_zoom_percent(self):
        """Get current zoom percentage. Returns: int."""
        return self.tool_manager.get_zoom_percent()


    def _emit_zoom_changed(self):
        """Emit zoom changed signal."""
        self.zoom_changed.emit(self.get_zoom_percent())


    def _apply_zoom(self, zoom_multiplier):
        """Apply zoom multiplier via tool manager. Args: zoom_multiplier (float)."""
        self.tool_manager.apply_zoom(zoom_multiplier)


    def zoom_in(self):
        """Zoom in via tool manager."""
        self.tool_manager.zoom_in()


    def zoom_out(self):
        """Zoom out via tool manager."""
        self.tool_manager.zoom_out()


    def center_view(self):
        """Center view on all component items."""
        component_items = [item for item in self.scene.items() if isinstance(item, ComponentItem)]
        if component_items:
            bounds = component_items[0].sceneBoundingRect()
            for item in component_items[1:]:
                bounds = bounds.united(item.sceneBoundingRect())
            self.centerOn(bounds.center())
        else:
            self.centerOn(0.0, 0.0)


    def draw_grid(self):
        """Draw background grid on the canvas."""
        pen = QPen(QColor(200, 200, 200))
        grid_size = 50
        grid_range = 2000
        for x in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(x, -grid_range, x, grid_range, pen)
        for y in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(-grid_range, y, grid_range, y, pen)


    def wheelEvent(self, event):
        """Handle mouse wheel zoom. Args: event (QWheelEvent)."""
        self.tool_manager.handle_wheel_event(event)


    def mousePressEvent(self, event):
        """Handle mouse press for rubber-band and component selection. Args: event (QMouseEvent)."""
        if self.tool_manager.handle_mouse_press_event(event):
            return
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """Handle mouse move for rubber-band updates. Args: event (QMouseEvent)."""
        if self.tool_manager.handle_mouse_move_event(event):
            return
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        """Handle mouse release for area selection deletion. Args: event (QMouseEvent)."""
        removed_count = self.tool_manager.handle_mouse_release_event(event)
        if removed_count is not None:
            if callable(self.area_delete_handler):
                self.area_delete_handler(removed_count)
            return
        super().mouseReleaseEvent(event)


    def set_area_delete_mode(self, enabled):
        """Enable/disable area delete mode. Args: enabled (bool)."""
        self.tool_manager.set_area_delete_mode(enabled)


    def dragEnterEvent(self, event):
        """Handle drag enter for dropping components. Args: event (QDragEnterEvent)."""
        self.tool_manager.handle_drag_enter_event(event)


    def dragMoveEvent(self, event):
        """Handle drag move for component movement preview. Args: event (QDragMoveEvent)."""
        self.tool_manager.handle_drag_move_event(event)


    def dropEvent(self, event):
        """Handle component drop. Args: event (QDropEvent)."""
        self.tool_manager.handle_drop_event(event)


    def add_component(self, name, scene_pos = None, component_id = None, component_values = None):
        """Add a component to the canvas. Args: name (str), scene_pos (QPointF, optional), component_id (str, optional), component_values (dict, optional). Returns: ComponentItem."""
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
        item = ComponentItem(name, scene_pos, self.building_model, self, component_id = component_id)
        item.apply_serialized_values(component_values)
        self.building_model.add_componentItem(item)
        self.scene.addItem(item)
        if callable(self.component_added_handler):
            self.component_added_handler(item)
        return item


    def clear_all(self):
        """Clear all components and connections from canvas."""
        for connection_data in list(self.visual_connections):
            self.scene.removeItem(connection_data["line_item"])
            self.scene.removeItem(connection_data["arrow_item"])
        self.visual_connections.clear()
        for item in list(self.scene.items()):
            if isinstance(item, ComponentItem):
                self.building_model.remove_componentItem(item)
                self.scene.removeItem(item)


    def remove_component_item(self, component_item):
        """Remove a component and its connections from canvas. Args: component_item."""
        for connection_data in list(self.visual_connections):
            if connection_data["src_item"] == component_item or connection_data["dst_item"] == component_item:
                self.scene.removeItem(connection_data["line_item"])
                self.scene.removeItem(connection_data["arrow_item"])
                if connection_data["connection"] in self.building_model.connections:
                    self.building_model.remove_connection(connection_data["connection"])
                self.visual_connections.remove(connection_data)
        self.building_model.remove_componentItem(component_item)
        self.scene.removeItem(component_item)


    def update_connection_lines_for_item(self, component_item):
        """Update connection line positions for component moves. Args: component_item."""
        for connection_data in self.visual_connections:
            if connection_data["src_item"] == component_item or connection_data["dst_item"] == component_item:
                src_rect = connection_data["src_item"].sceneBoundingRect()
                dst_rect = connection_data["dst_item"].sceneBoundingRect()
                src_point = self._point_on_rect_edge(src_rect, dst_rect.center())
                dst_point = self._point_on_rect_edge(dst_rect, src_rect.center())
                connection_data["line_item"].setLine(QLineF(src_point.x(), src_point.y(), dst_point.x(), dst_point.y()))
                self._update_arrow_item(connection_data["arrow_item"], src_point, dst_point)


    def _point_on_rect_edge(self, rect, toward_point):
        """Calculate intersection point on rect edge toward a point. Args: rect, toward_point. Returns: QPointF."""
        center = rect.center()
        dx = toward_point.x() - center.x()
        dy = toward_point.y() - center.y()
        half_w = rect.width() / 2.0
        half_h = rect.height() / 2.0
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return QPointF(center.x(), center.y())
        scale_x = abs(dx) / half_w if half_w > 0 else float("inf")
        scale_y = abs(dy) / half_h if half_h > 0 else float("inf")
        scale = max(scale_x, scale_y)
        if scale <= 0:
            return QPointF(center.x(), center.y())
        return QPointF(center.x() + dx / scale, center.y() + dy / scale)


    def _create_connection_graphics(self, src_item, dst_item):
        """Create graphics for a connection line and arrow. Args: src_item, dst_item. Returns: tuple (line_item, arrow_item)."""
        src_rect = src_item.sceneBoundingRect()
        dst_rect = dst_item.sceneBoundingRect()
        src_point = self._point_on_rect_edge(src_rect, dst_rect.center())
        dst_point = self._point_on_rect_edge(dst_rect, src_rect.center())
        line_pen = QPen(QColor(70, 70, 70), 2)
        line_item = self.scene.addLine(src_point.x(), src_point.y(), dst_point.x(), dst_point.y(), line_pen)
        arrow_item = self.scene.addPolygon(QPolygonF(), QPen(QColor(70, 70, 70), 2), QBrush(QColor(70, 70, 70)))
        self._update_arrow_item(arrow_item, src_point, dst_point)
        return line_item, arrow_item


    def _update_arrow_item(self, arrow_item, src_center, dst_center):
        """Update arrow polygon for connection endpoint. Args: arrow_item, src_center (QPointF), dst_center (QPointF)."""
        dx = dst_center.x() - src_center.x()
        dy = dst_center.y() - src_center.y()
        theta = math.atan2(dy, dx)
        arrow_size = 12.0
        tip = QPointF(dst_center.x(), dst_center.y())
        left = QPointF(dst_center.x() - arrow_size * math.cos(theta - math.pi / 6), dst_center.y() - arrow_size * math.sin(theta - math.pi / 6))
        right = QPointF(dst_center.x() - arrow_size * math.cos(theta + math.pi / 6), dst_center.y() - arrow_size * math.sin(theta + math.pi / 6))
        arrow_item.setPolygon(QPolygonF([tip, left, right]))


    def add_connection_between_items(self, src_item, dst_item, src_output = "output", dst_input = "input"):
        """Create a connection between two component items and add graphics. Args: src_item (ComponentItem), dst_item (ComponentItem), src_output (str), dst_input (str). Returns: tuple (bool, str)."""
        if src_item == dst_item:
            return False, "Source and destination components must be different."
        connection = Connection(src_item.node, src_output, dst_item.node, dst_input)
        self.building_model.add_connection(connection)
        line_item, arrow_item = self._create_connection_graphics(src_item, dst_item)
        self.visual_connections.append(
            {
                "src_item": src_item,
                "dst_item": dst_item,
                "line_item": line_item,
                "arrow_item": arrow_item,
                "connection": connection,
            }
        )
        src_name = src_item.label.toPlainText() if hasattr(src_item, "label") else getattr(src_item.node, "name", "Source")
        dst_name = dst_item.label.toPlainText() if hasattr(dst_item, "label") else getattr(dst_item.node, "name", "Destination")
        return True, f"Connection created: {src_name} -> {dst_name}."


    def add_connection_between_selected(self):
        """Create a connection between the two currently selected component items. Returns: tuple (bool, str)."""
        selected_items = [item for item in self.scene.selectedItems() if isinstance(item, ComponentItem)]
        if len(selected_items) != 2:
            return False, "Select exactly two components before adding a connection."
        src_item, dst_item = selected_items
        return self.add_connection_between_items(src_item, dst_item)


    def notify_component_clicked(self, component_item):
        """Fire the component click handler if one is registered. Args: component_item (ComponentItem)."""
        if callable(self.component_click_handler):
            self.component_click_handler(component_item)
