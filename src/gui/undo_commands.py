"""Undo command definitions for canvas operations."""

from PyQt6.QtGui import QUndoCommand


class AddComponentCommand(QUndoCommand):
    def __init__(self, canvas, name, scene_pos=None, component_id=None, component_values=None):
        super().__init__("Add Component")

        self.canvas = canvas
        self.name = name
        self.scene_pos = scene_pos
        self.component_id = component_id
        self.component_values = component_values
        self.component_item = None

    def redo(self):
        """Summary: Redo."""
        if self.component_item is None:
            self.component_item = self.canvas.internal_add_component(
                self.name,
                self.scene_pos,
                self.component_id,
                self.component_values
            )
        else:
            self.canvas.scene.addItem(self.component_item)
            self.canvas.building_model.add_componentItem(self.component_item)

    def undo(self):
        self.canvas.remove_component_item(self.component_item)
