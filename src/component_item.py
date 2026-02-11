from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt


class ComponentItem(QGraphicsRectItem):
    """Rectangle + text representing a building component"""

    def __init__(self, name, pos):
        super().__init__(0, 0, 120, 50)

        self.setPos(pos)
        self.setBrush(QColor(100, 200, 250, 180))

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(10, 10)

    # -----------------------------
    # Context Menu
    # -----------------------------
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        selected_action = menu.exec(event.screenPos())

        if selected_action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)
