from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QPushButton
from PyQt6.QtGui import QPen, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt

from component_item import ComponentItem
from drag_button import DragButton


class InteractiveCanvas(QGraphicsView):
    """Interactive canvas with zoom, pan, and drag/drop"""

    def __init__(self):
        super().__init__()

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

        self.draw_grid()

    # -----------------------------
    # Public API
    # -----------------------------
    #---- Just used the component_item init instead -----
    # def create_component(self, name, scene_pos):
    #     item = ComponentItem(name, scene_pos)
    #     self.scene.addItem(item)
    #     return item

    # -----------------------------
    # Grid
    # -----------------------------
    def draw_grid(self):
        pen = QPen(QColor(200, 200, 200))
        grid_size = 50
        grid_range = 2000

        for x in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(x, -grid_range, x, grid_range, pen)

        for y in range(-grid_range, grid_range, grid_size):
            self.scene.addLine(-grid_range, y, grid_range, y, pen)

    # -----------------------------
    # Zoom
    # -----------------------------
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_factor = 1.15 if delta > 0 else 1 / 1.15

        new_zoom = self.zoom_factor * zoom_factor

        if self.min_zoom <= new_zoom <= self.max_zoom:
            self.scale(zoom_factor, zoom_factor)
            self.zoom_factor = new_zoom

        event.accept()

    # -----------------------------
    # Drag & Drop
    # -----------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        name = event.mimeData().text()
        scene_pos = self.mapToScene(event.position().toPoint())
        if name and self.current_drag_item is None:
            item = ComponentItem(name, scene_pos)
            self.scene.addItem(item)
        elif self.current_drag_item:
            self.current_drag_item.setPos(scene_pos)
        self.current_drag_item = None
        event.acceptProposedAction()