from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QMimeData

class DragButton(QPushButton):
    """Button that creates draggable component items"""

    def __init__(self, name, canvas):
        super().__init__(name)
        self.canvas = canvas
        self.setStyleSheet("""
            QPushButton {
                background-color: palette(button);
                border: 1px solid palette(mid);
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
            QPushButton:pressed {
                background-color: palette(button);
            }
        """)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.text())
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
            self.setDown(False)