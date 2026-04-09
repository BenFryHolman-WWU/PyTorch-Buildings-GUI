from PyQt6.QtWidgets import QTreeWidgetItem


class Connection:
    """Represents a connection between two nodes with input/output ports."""
    
    def __init__(self, srcNode, srcOutput, dstNode, dstInput):
        """Initialize a connection. Args: srcNode (Node), srcOutput (str), dstNode (Node), dstInput (str)."""
        self.srcNode = srcNode
        self.srcOutput = srcOutput
        self.dstNode = dstNode
        self.dstInput = dstInput


class StateManager:
    """Manages the display state of UI components including component and connection lists."""
    
    def __init__(self, building_model, canvas, component_list, connection_list, zone_value_display = None):
        """Initialize the state manager. Args: building_model (BuildingModel), canvas (InteractiveCanvas), component_list (QTreeWidget), connection_list (QTreeWidget), zone_value_display (QLabel, optional)."""
        self.building_model = building_model
        self.canvas = canvas
        self.component_list = component_list
        self.connection_list = connection_list
        self.zone_value_display = zone_value_display


    def set_zone_value_display(self, zone_value_display):
        """Set or update the zone value display label. Args: zone_value_display (QLabel)."""
        self.zone_value_display = zone_value_display


    def update_zone_display(self):
        """Update the zone value display with current zone count."""
        if self.zone_value_display is not None:
            self.zone_value_display.setText(str(int(self.building_model.n_zones)))

    def _format_property_value(self, value):
        """Format a property value for display. Args: value. Returns: str."""
        if isinstance(value, list):
            return "[" + ", ".join(self._format_property_value(v) for v in value) + "]"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def refresh_component_list(self):
        """Refresh the component list tree widget with all components and their properties."""
        self.update_zone_display()
        expanded = set()
        for i in range(self.component_list.topLevelItemCount()):
            item = self.component_list.topLevelItem(i)
            if item.isExpanded():
                expanded.add(item.text(0))
        self.component_list.clear()
        component_count = 0
        for item in self.canvas.scene.items():
            if hasattr(item, "node") and hasattr(item, "label"):
                component_count += 1
                root = QTreeWidgetItem(self.component_list)
                root.setText(0, f"{component_count}. {item.label.toPlainText()}")
                values = item.serialize_values()
                for prop_name, prop_value in values.items():
                    child = QTreeWidgetItem(root)
                    child.setText(0, str(prop_name))
                    child.setText(1, self._format_property_value(prop_value))
                if root.text(0) in expanded:
                    root.setExpanded(True)
        self.refresh_connection_list()

    def refresh_connection_list(self):
        """Refresh the connection list tree widget with all active connections."""
        self.connection_list.clear()
        for index, connection_data in enumerate(self.canvas.visual_connections, start = 1):
            src_item = connection_data.get("src_item")
            dst_item = connection_data.get("dst_item")
            src_name = src_item.label.toPlainText() if src_item is not None else "Unknown"
            dst_name = dst_item.label.toPlainText() if dst_item is not None else "Unknown"
            root = QTreeWidgetItem(self.connection_list)
            root.setText(0, f"{index}. {src_name} -> {dst_name}")
            src_child = QTreeWidgetItem(root)
            src_child.setText(0, f"Source: {src_name}")
            dst_child = QTreeWidgetItem(root)
            dst_child.setText(0, f"Destination: {dst_name}")
