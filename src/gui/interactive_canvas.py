from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QRubberBand
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QLineF, QPointF, QRect
import math

from .component_item import ComponentItem
from .node_connection import Connection


class InteractiveCanvas(QGraphicsView):

    def __init__(self, building_model):
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
        self.draw_grid()

    def draw_grid(self):
        pen = QPen(QColor(200, 200, 200))
        grid_size = 50
        grid_range = 2000
        for x in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(x, -grid_range, x, grid_range, pen)
        for y in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(-grid_range, y, grid_range, y, pen)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_factor = 1.15 if delta > 0 else 1 / 1.15
        new_zoom = self.zoom_factor * zoom_factor
        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.scale(zoom_factor, zoom_factor)
            self.zoom_factor = new_zoom
        event.accept()

    def mousePressEvent(self, event):
        if self.area_delete_mode and event.button() == Qt.MouseButton.LeftButton:
            self.rubber_band_origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.rubber_band_origin, self.rubber_band_origin))
            self.rubber_band.show()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.area_delete_mode and self.rubber_band.isVisible() and self.rubber_band_origin is not None:
            self.rubber_band.setGeometry(QRect(self.rubber_band_origin, event.pos()).normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.area_delete_mode and event.button() == Qt.MouseButton.LeftButton:
            selected_rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            self.rubber_band_origin = None
            if selected_rect.width() < 4 or selected_rect.height() < 4:
                event.accept()
                return
            top_left = self.mapToScene(selected_rect.topLeft())
            bottom_right = self.mapToScene(selected_rect.bottomRight())
            scene_rect = QRect(int(min(top_left.x(), bottom_right.x())), int(min(top_left.y(), bottom_right.y())), int(abs(bottom_right.x() - top_left.x())), int(abs(bottom_right.y() - top_left.y())))
            to_remove = []
            for item in self.scene.items():
                if isinstance(item, ComponentItem) and scene_rect.intersects(item.sceneBoundingRect().toRect()):
                    to_remove.append(item)
            for item in to_remove:
                self.remove_component_item(item)
            if callable(self.area_delete_handler):
                self.area_delete_handler(len(to_remove))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def set_area_delete_mode(self, enabled):
        self.area_delete_mode = bool(enabled)
        if self.area_delete_mode:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.rubber_band.hide()
            self.rubber_band_origin = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        name = event.mimeData().text()
        scene_pos = self.mapToScene(event.position().toPoint())
        if name and self.current_drag_item is None:
            self.add_component(name, scene_pos)
        elif self.current_drag_item:
            self.current_drag_item.setPos(scene_pos)
        self.current_drag_item = None
        event.acceptProposedAction()

    def add_component(self, name, scene_pos=None, component_id=None, component_values=None):
        if scene_pos is None:
            scene_pos = self.mapToScene(self.viewport().rect().center())
        item = ComponentItem(name, scene_pos, self.building_model, self, component_id=component_id)
        item.apply_serialized_values(component_values)
        self.building_model.add_node(item.node)
        self.scene.addItem(item)
        if callable(self.component_added_handler):
            self.component_added_handler(item)
        return item

    def clear_all(self):
        for connection_data in list(self.visual_connections):
            self.scene.removeItem(connection_data["line_item"])
            self.scene.removeItem(connection_data["arrow_item"])
        self.visual_connections.clear()
        for item in list(self.scene.items()):
            if isinstance(item, ComponentItem):
                self.building_model.remove_node(item.node)
                self.scene.removeItem(item)

    def remove_component_item(self, component_item):
        for connection_data in list(self.visual_connections):
            if (connection_data["src_item"] == component_item or connection_data["dst_item"] == component_item):
                self.scene.removeItem(connection_data["line_item"])
                self.scene.removeItem(connection_data["arrow_item"])
                if connection_data["connection"] in self.building_model.connections:
                    self.building_model.remove_connection(connection_data["connection"])
                self.visual_connections.remove(connection_data)
        if component_item.node in self.building_model.nodes:
            self.building_model.remove_node(component_item.node)
        self.scene.removeItem(component_item)

    def update_connection_lines_for_item(self, component_item):
        for connection_data in self.visual_connections:
            if (connection_data["src_item"] == component_item or connection_data["dst_item"] == component_item):
                src_rect = connection_data["src_item"].sceneBoundingRect()
                dst_rect = connection_data["dst_item"].sceneBoundingRect()
                src_point = self._point_on_rect_edge(src_rect, dst_rect.center())
                dst_point = self._point_on_rect_edge(dst_rect, src_rect.center())
                connection_data["line_item"].setLine(QLineF(src_point.x(), src_point.y(), dst_point.x(), dst_point.y()))
                self._update_arrow_item(connection_data["arrow_item"], src_point, dst_point)

    def _point_on_rect_edge(self, rect, toward_point):
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
        dx = dst_center.x() - src_center.x()
        dy = dst_center.y() - src_center.y()
        theta = math.atan2(dy, dx)
        arrow_size = 12.0
        tip = QPointF(dst_center.x(), dst_center.y())
        left = QPointF(dst_center.x() - arrow_size * math.cos(theta - math.pi / 6), dst_center.y() - arrow_size * math.sin(theta - math.pi / 6))
        right = QPointF(dst_center.x() - arrow_size * math.cos(theta + math.pi / 6), dst_center.y() - arrow_size * math.sin(theta + math.pi / 6))
        arrow_item.setPolygon(QPolygonF([tip, left, right]))

    def add_connection_between_items(self, src_item, dst_item, src_output="output", dst_input="input"):
        if src_item == dst_item:
            return False, "Source and destination components must be different."
        connection = Connection(src_item.node, src_output, dst_item.node, dst_input)
        self.building_model.add_connection(connection)
        line_item, arrow_item = self._create_connection_graphics(src_item, dst_item)
        self.visual_connections.append(
            {"src_item": src_item, "dst_item": dst_item, "line_item": line_item, "arrow_item": arrow_item, "connection": connection}
        )
        return True, f"Connection created: {src_output} -> {dst_input}."

    def add_connection_between_selected(self):
        selected_items = [
            item
            for item in self.scene.selectedItems()
            if isinstance(item, ComponentItem)
        ]
        if len(selected_items) != 2:
            return False, "Select exactly two components before adding a connection."
        src_item, dst_item = selected_items
        return self.add_connection_between_items(src_item, dst_item)

    def notify_component_clicked(self, component_item):
        if callable(self.component_click_handler):
            self.component_click_handler(component_item)
