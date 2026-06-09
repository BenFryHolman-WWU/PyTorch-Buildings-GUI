"""Canvas interaction tools for zooming, dragging, dropping, and area selection."""

from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtWidgets import QGraphicsView


class CanvasToolManager:
    def __init__(self, canvas):
        """
        Summary: Init.
        Args: canvas
        """
        self.canvas = canvas
        self.zoom_step = 1.15
        self.button_zoom_initial_step_percent = 5
        self.button_zoom_accelerated_step_percent = 10
        self.button_zoom_acceleration_clicks = 2
        self.button_zoom_grid_percent = 5
        self.button_auto_center_min_percent = 30
        self._button_zoom_direction = 0
        self._button_zoom_clicks = 0
        self._panning = False
        self._pan_last_pos = None

    def get_zoom_percent(self):
        return int(round(self.canvas.zoom_factor * 100.0))

    def nearest_button_zoom_percent(self):
        percent = self.canvas.zoom_factor * 100.0
        grid = self.button_zoom_grid_percent
        return int(round(percent / grid) * grid)

    def minimum_zoom(self):
        scene_rect = self.canvas.scene.sceneRect()
        viewport_size = self.canvas.viewport().size()
        if scene_rect.width() <= 0 or scene_rect.height() <= 0:
            return self.canvas.min_zoom
        width_zoom = viewport_size.width() / scene_rect.width()
        height_zoom = viewport_size.height() / scene_rect.height()
        return max(self.canvas.min_zoom, min(width_zoom, height_zoom))

    def viewport_center(self):
        return self.canvas.mapToScene(self.canvas.viewport().rect().center())

    def scale_around_center(self, scale_factor):
        center = self.viewport_center()
        self.canvas.scale(scale_factor, scale_factor)
        self.canvas.centerOn(center)

    def enforce_zoom_bounds(self):
        target_zoom = min(self.canvas.max_zoom, max(self.minimum_zoom(), self.canvas.zoom_factor))
        if abs(target_zoom - self.canvas.zoom_factor) < 0.0001:
            return
        scale_factor = target_zoom / self.canvas.zoom_factor
        self.scale_around_center(scale_factor)
        self.canvas.zoom_factor = target_zoom
        self.canvas.zoom_changed.emit(self.get_zoom_percent())

    def apply_zoom(self, zoom_multiplier):
        requested_zoom = self.canvas.zoom_factor * zoom_multiplier
        self.reset_button_zoom_acceleration()
        self.set_zoom_factor(requested_zoom)

    def set_zoom_factor(self, requested_zoom):
        new_zoom = min(self.canvas.max_zoom, max(self.minimum_zoom(), requested_zoom))
        if abs(new_zoom - self.canvas.zoom_factor) < 0.0001:
            return False
        scale_factor = new_zoom / self.canvas.zoom_factor
        self.scale_around_center(scale_factor)
        self.canvas.zoom_factor = new_zoom
        self.canvas.zoom_changed.emit(self.get_zoom_percent())
        return True

    def reset_button_zoom_acceleration(self):
        self._button_zoom_direction = 0
        self._button_zoom_clicks = 0

    def _next_button_zoom_step(self, direction):
        if direction == self._button_zoom_direction:
            self._button_zoom_clicks += 1
        else:
            self._button_zoom_direction = direction
            self._button_zoom_clicks = 1
        if self._button_zoom_clicks > self.button_zoom_acceleration_clicks:
            return self.button_zoom_accelerated_step_percent
        return self.button_zoom_initial_step_percent

    def auto_center_after_button_zoom(self):
        if self.get_zoom_percent() >= self.button_auto_center_min_percent:
            self.canvas.center_view()

    def apply_button_zoom(self, direction):
        step_percent = self._next_button_zoom_step(direction)
        current_percent = self.nearest_button_zoom_percent()
        target_percent = current_percent + direction * step_percent
        if self.set_zoom_factor(target_percent / 100.0):
            self.auto_center_after_button_zoom()

    def zoom_in(self):
        self.apply_button_zoom(1)

    def zoom_out(self):
        self.apply_button_zoom(-1)

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
            if not getattr(self.canvas, "connection_delete_mode", False):
                self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.canvas.rubber_band.hide()
            self.canvas.rubber_band_origin = None


    def handle_mouse_press_event(self, event):
        """
        Summary: Handle mouse press event.
        Returns: Return the computed value.
        """
        if self.canvas.area_delete_mode and event.button() == Qt.MouseButton.LeftButton:
            self.canvas.rubber_band_origin = event.pos()
            self.canvas.rubber_band.setGeometry(QRect(self.canvas.rubber_band_origin, self.canvas.rubber_band_origin))
            self.canvas.rubber_band.show()
            event.accept()
            return True
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_last_pos = event.position().toPoint()
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return True
        return False


    def handle_mouse_move_event(self, event):
        """
        Summary: Handle mouse move event.
        Returns: Return the computed value.
        """
        if self._panning and self._pan_last_pos is not None:
            current_pos = event.position().toPoint()
            last_scene_pos = self.canvas.mapToScene(self._pan_last_pos)
            current_scene_pos = self.canvas.mapToScene(current_pos)
            center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
            self.canvas.centerOn(center + (last_scene_pos - current_scene_pos))
            self._pan_last_pos = current_pos
            event.accept()
            return True
        if self.canvas.area_delete_mode and self.canvas.rubber_band.isVisible() and self.canvas.rubber_band_origin is not None:
            self.canvas.rubber_band.setGeometry(QRect(self.canvas.rubber_band_origin, event.pos()).normalized())
            self.canvas.set_area_delete_preview(self._rubber_band_scene_rect())
            event.accept()
            return True
        return False


    def _rubber_band_scene_rect(self):
        selected_rect = self.canvas.rubber_band.geometry()
        top_left = self.canvas.mapToScene(selected_rect.topLeft())
        bottom_right = self.canvas.mapToScene(selected_rect.bottomRight())
        return QRectF(top_left, bottom_right).normalized()


    def handle_mouse_release_event(self, event):
        """
        Summary: Handle mouse release event.
        Returns: Return the computed value.
        """
        if self._panning and event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self._panning = False
            self._pan_last_pos = None
            self.canvas.unsetCursor()
            event.accept()
            return "handled"
        if not (self.canvas.area_delete_mode and event.button() == Qt.MouseButton.LeftButton):
            return None
        selected_rect = self.canvas.rubber_band.geometry()
        self.canvas.rubber_band.hide()
        self.canvas.rubber_band_origin = None
        if selected_rect.width() < 4 or selected_rect.height() < 4:
            self.canvas.clear_area_delete_preview()
            event.accept()
            return 0
        scene_rect = self._rubber_band_scene_rect()
        to_remove = self.canvas.set_area_delete_preview(scene_rect)
        if to_remove and callable(getattr(self.canvas, "area_delete_confirm_handler", None)):
            if not self.canvas.area_delete_confirm_handler(to_remove):
                self.canvas.clear_area_delete_preview()
                event.accept()
                return 0
        removed_count = self.canvas.delete_component_items(to_remove)
        self.canvas.clear_area_delete_preview()
        event.accept()
        return removed_count


    def handle_drag_enter_event(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()


    def handle_drag_move_event(self, event):
        name = event.mimeData().text()
        scene_pos = self.canvas.drag_preview_position(event.position().toPoint())
        if name and self.canvas.current_drag_item is None:
            self.canvas.current_drag_item = self.canvas.create_drag_preview_item(name, scene_pos)
        elif self.canvas.current_drag_item is not None:
            self.canvas.current_drag_item.setPos(scene_pos)
        event.acceptProposedAction()


    def handle_drop_event(self, event):
        name = event.mimeData().text()
        scene_pos = self.canvas.drag_preview_position(event.position().toPoint())
        if self.canvas.current_drag_item is not None:
            self.canvas.clear_drag_preview_item()
        if name:
            self.canvas.add_component(name, scene_pos)
        event.acceptProposedAction()
