"""Undo command definitions for canvas operations."""

from PyQt6.QtGui import QUndoCommand
from PyQt6.QtWidgets import QGraphicsRectItem


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
            self.canvas.set_dirty(True)

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
        self.canvas.remove_connection_data(self.connection_data)


class DeleteConnectionCommand(QUndoCommand):
    def __init__(self, canvas, connection_data):
        super().__init__("Delete Connection")
        self.canvas = canvas
        self.connection_data = connection_data

    def redo(self):
        self.canvas.remove_connection_data(self.connection_data, notify=False)
        self.canvas.set_dirty(True)

    def undo(self):
        data = self.connection_data
        if data in self.canvas.visual_connections:
            return
        if data["line_item"].scene() is not self.canvas.scene:
            self.canvas.scene.addItem(data["line_item"])
        if data["arrow_item"].scene() is not self.canvas.scene:
            self.canvas.scene.addItem(data["arrow_item"])
        if data["connection"] not in self.canvas.building_model.connections:
            self.canvas.building_model.add_connection(data["connection"])
        self.canvas.visual_connections.append(data)
        self.canvas._set_connection_highlight(data, False)
        self.canvas._update_connection_line_and_arrow(data)
        self.canvas._update_connection_pair_lines(data["src_item"], data["dst_item"])
        self.canvas.hovered_connection_data = None
        self.canvas.set_dirty(True)


class DeleteComponentsCommand(QUndoCommand):
    def __init__(self, canvas, component_items):
        super().__init__("Delete Components")
        self.canvas = canvas
        self.component_items = list(component_items)
        self.component_set = set(self.component_items)
        self.connection_data = [
            data for data in list(canvas.visual_connections)
            if data["src_item"] in self.component_set or data["dst_item"] in self.component_set
        ]

    def redo(self):
        for data in list(self.connection_data):
            if data in self.canvas.visual_connections:
                self.canvas.remove_connection_data(data, notify=False)
        for item in self.component_items:
            self.canvas.area_delete_preview_items.discard(item)
            if item in self.canvas.building_model.componentItems:
                self.canvas.building_model.remove_componentItem(item)
            if item.scene() is self.canvas.scene:
                self.canvas.scene.removeItem(item)
        self.canvas.clear_area_delete_preview()
        self.canvas.set_dirty(True)

    def undo(self):
        for item in self.component_items:
            if item.scene() is not self.canvas.scene:
                self.canvas.scene.addItem(item)
            if item not in self.canvas.building_model.componentItems:
                self.canvas.building_model.add_componentItem(item)
            item.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, self.canvas.editing_enabled)
            item.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, self.canvas.editing_enabled)
            item.set_delete_preview(False)
        for data in self.connection_data:
            if data not in self.canvas.visual_connections:
                if data["line_item"].scene() is not self.canvas.scene:
                    self.canvas.scene.addItem(data["line_item"])
                if data["arrow_item"].scene() is not self.canvas.scene:
                    self.canvas.scene.addItem(data["arrow_item"])
                if data["connection"] not in self.canvas.building_model.connections:
                    self.canvas.building_model.add_connection(data["connection"])
                self.canvas.visual_connections.append(data)
                self.canvas._set_connection_highlight(data, False)
                self.canvas._update_connection_line_and_arrow(data)
            else:
                self.canvas._set_connection_highlight(data, False)
        touched_pairs = {
            (data["src_item"], data["dst_item"])
            for data in self.connection_data
        }
        for src_item, dst_item in touched_pairs:
            self.canvas._update_connection_pair_lines(src_item, dst_item)
        self.canvas.hovered_connection_data = None
        self.canvas.area_delete_preview_connections.clear()
        self.canvas.set_dirty(True)
