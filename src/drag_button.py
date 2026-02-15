from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QMimeData
from component_item import ComponentItem

class DragButton(QPushButton):
    """Button that creates draggable component items"""

    def __init__(self, name, canvas):
        super().__init__(name)
        self.canvas = canvas

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:

            scene_pos = self.canvas.mapToScene(
                self.canvas.mapFromGlobal(event.globalPosition().toPoint())
            )
            
            item = ComponentItem(self.text(), scene_pos)
            self.canvas.scene.addItem(item)
            self.canvas.current_drag_item = item

            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.text())
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)