from PyQt6.QtWidgets import QToolButton, QApplication
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QMimeData, QPoint

class DragButton(QToolButton):

    def __init__(self, label, component_name=None):
        super().__init__()
        self.setText(label)
        self.component_name = component_name or label
        self.drag_start_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
