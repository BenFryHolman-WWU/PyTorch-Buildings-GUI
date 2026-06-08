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
        if self.component_item is not None:
            # Restore the original item rather than creating a new one
            self.canvas._restore_component_item(self.component_item)
        else:
            self.component_item = self.canvas.internal_add_component(
                self.name, self.scene_pos,
                self.component_id, self.component_values
            )

    def undo(self):
        self.canvas.internal_remove_component_item(self.component_item)


class DeleteComponentCommand(QUndoCommand):
    def __init__(self, canvas, component_item):
        super().__init__("Delete Component")
        self.canvas = canvas
        self.component_item = component_item
        # Snapshot the connections involving this component before deletion
        self.connection_data_list = [
            cd for cd in canvas.visual_connections
            if cd["src_item"] == component_item or cd["dst_item"] == component_item
        ]

    def redo(self):
        self.canvas.internal_remove_component_item(self.component_item)

    def undo(self):
        self.canvas._restore_component_item(self.component_item)
        for connection_data in self.connection_data_list:
            self.canvas._restore_connection_data(connection_data)




class AddConnectionCommand(QUndoCommand):
    def __init__(self, canvas, src_item, dst_item, src_output="output", dst_input="input", mappings=None):
        super().__init__("Add Connection")
        self.canvas = canvas
        self.src_item = src_item
        self.dst_item = dst_item
        self.src_output = src_output
        self.dst_input = dst_input
        self.mappings = mappings
        self.connection_data = None
        self.success = False
        self.msg = ""

    def redo(self):
        if self.connection_data is not None:
            # Re-add the exact same connection object, don't create a new one
            self.canvas._restore_connection_data(self.connection_data)
        else:
            self.success, self.msg, self.connection_data = (
                self.canvas.internal_add_connection_between_items(
                    self.src_item, self.dst_item,
                    self.src_output, self.dst_input, self.mappings
                )
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
        self.success = self.canvas.internal_remove_connection_data(
            self.connection_data, self.notify
        )

    def undo(self):
        self.canvas._restore_connection_data(self.connection_data)


class MoveComponentCommand(QUndoCommand):
    def __init__(self, component_item, start_pos, end_pos):
        super().__init__("Move Component")
        self.component_item = component_item
        self.start_pos = start_pos
        self.end_pos = end_pos

    def redo(self):
        self.component_item.setPos(self.end_pos)

    def undo(self):
        self.component_item.setPos(self.start_pos)