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




class AddConnectionCommand(QUndoCommand):
    def __init__(self, canvas, src_item, dst_item, src_output="output", dst_input="input", mappings=None):
        super().__init__("Add Connection")

        self.canvas = canvas
        self.src_item = src_item
        self.dst_item = dst_item
        self.src_output = src_output
        self.dst_input = dst_input
        self.mappings = mappings

        # this will be filled during redo
        self.connection_data = None
        self.success = False
        self.msg = ""

    def redo(self):
        # create the connection through the canvas
        self.success, self.msg, self.connection_data = self.canvas.internal_add_connection_between_items(
            self.src_item,
            self.dst_item,
            self.src_output,
            self.dst_input,
            self.mappings
        )

    def undo(self):
        self.canvas.internal_remove_connection_data(self.connection_data)



class DeleteConnectionCommand(QUndoCommand):
    def __init__(self, canvas, connection_data, notify=True):
        super().__init__("Delete Connection")

        self.canvas = canvas
        self.connection_data = connection_data
        self.notify = notify
        self.success = False

    def redo(self):
        self.success = self.canvas.internal_remove_connection_data(self.connection_data, self.notify)

    def undo(self):
        _, _, self.connection_data = self.canvas.internal_add_connection_between_items(
            self.connection_data["src_item"],
            self.connection_data["dst_item"],
            self.connection_data["connection"].srcOutput,
            self.connection_data["connection"].dstInput,
            getattr(self.connection_data["connection"], "mappings", None)
        )
