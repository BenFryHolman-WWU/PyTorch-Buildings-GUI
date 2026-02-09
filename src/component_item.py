from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

class ComponentItem(QGraphicsRectItem):
    """A rectangle + text representing a building component on the canvas"""
    def __init__(self, name, pos):
        super().__init__(0, 0, 100, 50)  # Width=100, Height=50
        self.setPos(pos)  # Set initial position on the canvas
        self.setBrush(QColor(100, 200, 250, 180))  # Light blue fill

        # Allow the item to be movable and selectable
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )

        # Add a text label as a child of the rectangle
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(10, 10)  # Offset from top-left of rectangle

