from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import QGraphicsView


class CanvasToolManager:


    def __init__(self, canvas):
        self.canvas = canvas
        self.zoom_step = 1.15


    def get_zoom_percent(self):
        return int(round(self.canvas.zoom_factor * 100.0))


    def apply_zoom(self, zoom_multiplier):
        new_zoom = self.canvas.zoom_factor * zoom_multiplier
        if self.canvas.min_zoom <= new_zoom <= self.canvas.max_zoom:
            self.canvas.scale(zoom_multiplier, zoom_multiplier)
            self.canvas.zoom_factor = new_zoom
            self.canvas.zoom_changed.emit(self.get_zoom_percent())


    def zoom_in(self):
        self.apply_zoom(self.zoom_step)


    def zoom_out(self):
        self.apply_zoom(1.0 / self.zoom_step)


    def handle_wheel_event(self, event):
        delta = event.angleDelta().y()
        zoom_factor = self.zoom_step if delta > 0 else 1 / self.zoom_step
        self.apply_zoom(zoom_factor)
        event.accept()


    def set_area_delete_mode(self, enabled):
        self.canvas.area_delete_mode = bool(enabled)
        if self.canvas.area_delete_mode:
            self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.canvas.rubber_band.hide()
            self.canvas.rubber_band_origin = None


    def handle_mouse_press_event(self, event):
        if self.canvas.area_delete_mode and event.button() == Qt.MouseButton.LeftButton:
            self.canvas.rubber_band_origin = event.pos()
            self.canvas.rubber_band.setGeometry(QRect(self.canvas.rubber_band_origin, self.canvas.rubber_band_origin))
            self.canvas.rubber_band.show()
            event.accept()
            return True
        return False


    def handle_mouse_move_event(self, event):
        if self.canvas.area_delete_mode and self.canvas.rubber_band.isVisible() and self.canvas.rubber_band_origin is not None:
            self.canvas.rubber_band.setGeometry(QRect(self.canvas.rubber_band_origin, event.pos()).normalized())
            event.accept()
            return True
        return False


    def handle_mouse_release_event(self, event):
        if not (self.canvas.area_delete_mode and event.button() == Qt.MouseButton.LeftButton):
            return None
        selected_rect = self.canvas.rubber_band.geometry()
        self.canvas.rubber_band.hide()
        self.canvas.rubber_band_origin = None
        if selected_rect.width() < 4 or selected_rect.height() < 4:
            event.accept()
            return 0
        top_left = self.canvas.mapToScene(selected_rect.topLeft())
        bottom_right = self.canvas.mapToScene(selected_rect.bottomRight())
        scene_rect = QRect(
            int(min(top_left.x(), bottom_right.x())),
            int(min(top_left.y(), bottom_right.y())),
            int(abs(bottom_right.x() - top_left.x())),
            int(abs(bottom_right.y() - top_left.y())),
        )
        to_remove = []
        for item in self.canvas.scene.items():
            if hasattr(item, "component") and hasattr(item, "node") and scene_rect.intersects(item.sceneBoundingRect().toRect()):
                to_remove.append(item)
        for item in to_remove:
            self.canvas.remove_component_item(item)
        event.accept()
        return len(to_remove)


    def handle_drag_enter_event(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()


    def handle_drag_move_event(self, event):
        event.acceptProposedAction()


    def handle_drop_event(self, event):
        name = event.mimeData().text()
        scene_pos = self.canvas.mapToScene(event.position().toPoint())
        if name and self.canvas.current_drag_item is None:
            self.canvas.add_component(name, scene_pos)
        elif self.canvas.current_drag_item:
            self.canvas.current_drag_item.setPos(scene_pos)
        self.canvas.current_drag_item = None
        event.acceptProposedAction()
