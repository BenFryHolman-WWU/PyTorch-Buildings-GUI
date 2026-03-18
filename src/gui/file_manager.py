import json
from datetime import datetime
from pathlib import Path


class FileManager:


    def __init__(self, building_model):
        self.building_model = building_model


    def _should_inline_list(self, value):
        if not isinstance(value, list):
            return False
        for item in value:
            if isinstance(item, dict):
                return False
            if isinstance(item, list) and not self._should_inline_list(item):
                return False
        return True


    def _format_json_with_inline_lists(self, value, indent_level = 0):
        indent = "  " * indent_level
        child_indent = "  " * (indent_level + 1)
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            items = list(value.items())
            for index, (key, item_value) in enumerate(items):
                comma = "," if index < len(items) - 1 else ""
                value_str = self._format_json_with_inline_lists(item_value, indent_level + 1)
                lines.append(f"{child_indent}{json.dumps(key)}: {value_str}{comma}")
            lines.append(f"{indent}" + "}")
            return "\n".join(lines)
        if isinstance(value, list):
            if not value:
                return "[]"
            if self._should_inline_list(value):
                return json.dumps(value)
            lines = ["["]
            for index, item in enumerate(value):
                comma = "," if index < len(value) - 1 else ""
                item_str = self._format_json_with_inline_lists(item, indent_level + 1)
                lines.append(f"{child_indent}{item_str}{comma}")
            lines.append(f"{indent}]")
            return "\n".join(lines)
        return json.dumps(value)


    def get_saved_dir(self):
        saved_dir = Path.cwd() / "saved"
        saved_dir.mkdir(parents = True, exist_ok = True)
        return saved_dir


    def build_payload(self, model_name, n_zones, component_items, visual_connections, time_data):
        component_index = {item: idx for idx, item in enumerate(component_items)}
        component_sections = {}
        for item in component_items:
            component_sections[item.component_id] = {
                "type": item.label.toPlainText(),
                "position": {"x": item.pos().x(), "y": item.pos().y()},
                "values": item.serialize_values(),
            }
        payload = {
            "name": model_name,
            "n_zones": int(n_zones),
            "components": [
                {
                    "id": item.component_id,
                    "type": item.label.toPlainText(),
                    "x": item.pos().x(),
                    "y": item.pos().y(),
                    "values": item.serialize_values(),
                }
                for item in component_items
            ],
            "component_sections": component_sections,
            "connections": [
                {
                    "src_id": getattr(conn_data["src_item"], "component_id", None),
                    "dst_id": getattr(conn_data["dst_item"], "component_id", None),
                    "src_output": conn_data["connection"].srcOutput,
                    "dst_input": conn_data["connection"].dstInput,
                    "src": component_index.get(conn_data["src_item"]),
                    "dst": component_index.get(conn_data["dst_item"]),
                }
                for conn_data in visual_connections
                if conn_data["src_item"] in component_index and conn_data["dst_item"] in component_index
            ],
            "time": {
                "t_start": time_data.get("t_start", self.building_model.t_start),
                "t_duration": time_data.get("t_duration", self.building_model.t_duration),
                "dt": time_data.get("dt", self.building_model.dt),
            },
        }
        return payload


    def save_layout(self, model_name, n_zones, component_items, visual_connections, time_data):
        saved_dir = self.get_saved_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = saved_dir / f"building_layout_{timestamp}.json"
        payload = self.build_payload(model_name, n_zones, component_items, visual_connections, time_data)
        with open(save_path, "w", encoding = "utf-8") as json_file:
            json_file.write(self._format_json_with_inline_lists(payload) + "\n")
        return save_path


    def load_payload_from_path(self, load_path):
        with open(load_path, "r", encoding = "utf-8") as json_file:
            payload = json.load(json_file)
        return payload


    def get_model_name(self, payload, default_name):
        return payload.get("name", default_name)


    def get_n_zones(self, payload, default_n_zones):
        return int(payload.get("n_zones", default_n_zones))


    def get_components(self, payload):
        return payload.get("components", [])


    def get_component_sections(self, payload):
        return payload.get("component_sections", {})


    def get_connections(self, payload):
        return payload.get("connections", [])


    def get_time_data(self, payload):
        return payload.get("time", {})
