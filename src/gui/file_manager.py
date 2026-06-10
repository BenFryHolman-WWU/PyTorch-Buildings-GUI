"""Project and input-data file persistence helpers."""

import json
import math
from pathlib import Path


class LayoutFileError(Exception):
    """A user-facing layout file error that is safe to display."""


class FileManager:
    _MAX_LAYOUT_BYTES = 10 * 1024 * 1024
    _COMPONENT_TYPES = {"Envelope", "RTU", "VAVBox", "SolarGains", "ControlPolicy"}

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
        """
        Summary: Format json with inline lists.
        Args: indent_level
        Returns: Return the computed value.
        """
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

    def get_saved_dir(self, last_dir):
        """
        Summary: Return saved dir.
        Args: last_dir
        Returns: Return the computed value.
        """
        if last_dir is not None:
            return last_dir

        base_dir = Path(__file__).resolve().parents[2]
        saved_dir = base_dir / "saved"

        if saved_dir.exists():
            return saved_dir

        return base_dir

    def get_input_data_dir(self, last_dir=None):
        """
        Summary: Return input data dir.
        Args: last_dir
        Returns: Return the computed value.
        """
        if last_dir is not None and Path(last_dir).exists():
            return Path(last_dir)

        for directory in self.get_input_data_search_dirs():
            if directory.exists():
                return directory

        default_dir = Path(__file__).resolve().parents[2] / "assets" / "saved_data"
        default_dir.mkdir(parents=True, exist_ok=True)
        return default_dir

    def get_input_data_search_dirs(self, layout_path=None):
        """
        Summary: Return input data search dirs.
        Args: layout_path
        Returns: Return the computed value.
        """
        base_dir = Path(__file__).resolve().parents[2]
        dirs = []

        if layout_path is not None:
            dirs.append(Path(layout_path).parent)

        dirs.extend([
            base_dir / "saved" / "inputdata",
            base_dir / "assets" / "saved_data",
            base_dir / "assets",
            Path.home() / "Downloads",
        ])

        unique_dirs = []
        seen = set()
        for directory in dirs:
            resolved = Path(directory).expanduser()
            key = str(resolved)
            if key not in seen:
                unique_dirs.append(resolved)
                seen.add(key)
        return unique_dirs

    def resolve_input_data_path(self, saved_path, layout_path=None):
        """
        Summary: Resolve input data path.
        Args: saved_path, layout_path
        Returns: Return the computed value.
        """
        if not saved_path:
            return None

        path = Path(saved_path).expanduser()
        if path.exists():
            return path

        candidates = []
        if not path.is_absolute():
            candidates.append(Path(__file__).resolve().parents[2] / path)
        for directory in self.get_input_data_search_dirs(layout_path):
            candidates.append(directory / path.name)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return path

    def build_payload(self, model_name, n_zones, component_items, visual_connections, time_data):
        """
        Summary: Build payload.
        Args: model_name, n_zones, component_items, visual_connections, time_data
        Returns: Return the computed value.
        """
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
                    "mappings": getattr(conn_data["connection"], "mappings", None),
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
            "control_policy": self.building_model.get_control_policy_data(),
            "input_data": {
                "path": self.building_model.input_data_path,
                "summary": self.building_model.input_data_summary,
            },
        }
        return payload

    def save_layout(self, model_name, n_zones, component_items, visual_connections, time_data, save_path):
        payload = self.build_payload(model_name, n_zones, component_items, visual_connections, time_data)
        self.validate_payload(payload)
        path = Path(save_path)
        if path.suffix.lower() != ".json":
            raise LayoutFileError("Layouts can only be saved as .json files.")
        try:
            with path.open("w", encoding="utf-8") as json_file:
                json_file.write(self._format_json_with_inline_lists(payload) + "\n")
        except OSError:
            raise LayoutFileError("The layout could not be saved to the selected location.") from None
        return path

    def load_payload_from_path(self, load_path):
        path = Path(load_path)
        if path.suffix.lower() != ".json":
            raise LayoutFileError("Select a JSON layout file ending in .json.")
        try:
            if path.stat().st_size > self._MAX_LAYOUT_BYTES:
                raise LayoutFileError("The selected layout is too large to open safely.")
            with path.open("r", encoding="utf-8") as json_file:
                payload = json.load(json_file)
        except LayoutFileError:
            raise
        except json.JSONDecodeError as exc:
            raise LayoutFileError(
                f"The layout contains invalid JSON near line {exc.lineno}, column {exc.colno}."
            ) from None
        except UnicodeDecodeError:
            raise LayoutFileError("The layout must be a UTF-8 encoded JSON file.") from None
        except OSError:
            raise LayoutFileError("The selected layout could not be read.") from None
        self.validate_payload(payload)
        return payload

    def validate_payload(self, payload):
        """Validate a layout completely before it can modify the active project."""
        if not isinstance(payload, dict):
            raise LayoutFileError("The layout must contain a JSON object at its top level.")

        name = payload.get("name", "Model")
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise LayoutFileError("The project name must be non-empty text shorter than 200 characters.")

        n_zones = self._finite_number(payload.get("n_zones", 2), "n_zones", integer=True)
        if not 1 <= n_zones <= 100:
            raise LayoutFileError("n_zones must be between 1 and 100.")

        components = payload.get("components", [])
        sections = payload.get("component_sections", {})
        connections = payload.get("connections", [])
        time_data = payload.get("time", {})
        control_policy = payload.get("control_policy", {})
        input_data = payload.get("input_data", {})
        if not isinstance(components, list):
            raise LayoutFileError("components must be a JSON list.")
        if not isinstance(sections, dict):
            raise LayoutFileError("component_sections must be a JSON object.")
        if not isinstance(connections, list):
            raise LayoutFileError("connections must be a JSON list.")
        if not isinstance(time_data, dict):
            raise LayoutFileError("time must be a JSON object.")
        if not isinstance(control_policy, dict):
            raise LayoutFileError("control_policy must be a JSON object.")
        if not isinstance(input_data, dict):
            raise LayoutFileError("input_data must be a JSON object.")
        if len(components) > 500 or len(sections) > 500 or len(connections) > 5000:
            raise LayoutFileError("The layout contains more components or connections than supported.")

        component_ids = set()
        for index, component in enumerate(components):
            self._validate_component(component, f"components[{index}]", component_ids)
        for component_id, section in sections.items():
            if not isinstance(component_id, str) or not component_id:
                raise LayoutFileError("Every component section must have a non-empty text ID.")
            if not isinstance(section, dict):
                raise LayoutFileError(f"component_sections.{component_id} must be a JSON object.")
            self._validate_component(section, f"component_sections.{component_id}", None, component_id)

        for index, connection in enumerate(connections):
            self._validate_connection(connection, index, component_ids, len(components))

        t_start = self._finite_number(time_data.get("t_start", self.building_model.t_start), "time.t_start")
        duration = self._finite_number(time_data.get("t_duration", self.building_model.t_duration), "time.t_duration")
        dt = self._finite_number(time_data.get("dt", self.building_model.dt), "time.dt")
        if t_start < 0:
            raise LayoutFileError("time.t_start cannot be negative.")
        if duration <= 0 or dt <= 0 or dt > duration:
            raise LayoutFileError("Simulation duration and time step must be positive, and dt cannot exceed duration.")

        self._validate_json_values(control_policy, "control_policy")
        self._validate_json_values(input_data.get("summary", {}), "input_data.summary", allow_text=True)
        input_path = input_data.get("path")
        if input_path is not None and (not isinstance(input_path, str) or len(input_path) > 4096):
            raise LayoutFileError("input_data.path must be a valid text path.")
        return payload

    def _validate_component(self, component, location, component_ids=None, fallback_id=None):
        if not isinstance(component, dict):
            raise LayoutFileError(f"{location} must be a JSON object.")
        component_type = component.get("type")
        if component_type not in self._COMPONENT_TYPES:
            raise LayoutFileError(f"{location}.type is not a supported component type.")
        component_id = component.get("id", fallback_id)
        if component_id is not None:
            if not isinstance(component_id, str) or not component_id or len(component_id) > 200:
                raise LayoutFileError(f"{location}.id must be non-empty text.")
            if component_ids is not None:
                if component_id in component_ids:
                    raise LayoutFileError(f"Duplicate component ID: {component_id}.")
                component_ids.add(component_id)
        position = component.get("position", {})
        if position is not None and not isinstance(position, dict):
            raise LayoutFileError(f"{location}.position must be a JSON object.")
        self._finite_number(component.get("x", position.get("x", 0)), f"{location}.x")
        self._finite_number(component.get("y", position.get("y", 0)), f"{location}.y")
        values = component.get("values", {})
        if not isinstance(values, dict):
            raise LayoutFileError(f"{location}.values must be a JSON object.")
        self._validate_json_values(values, f"{location}.values")

    def _validate_connection(self, connection, index, component_ids, component_count):
        location = f"connections[{index}]"
        if not isinstance(connection, dict):
            raise LayoutFileError(f"{location} must be a JSON object.")
        for key in ("src_id", "dst_id"):
            value = connection.get(key)
            if value is not None and (not isinstance(value, str) or value not in component_ids):
                raise LayoutFileError(f"{location}.{key} does not reference a loaded component.")
        for key in ("src", "dst"):
            value = connection.get(key)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < component_count
            ):
                raise LayoutFileError(f"{location}.{key} must reference a valid component index.")
        mappings = connection.get("mappings")
        if mappings is not None:
            if not isinstance(mappings, list):
                raise LayoutFileError(f"{location}.mappings must be a JSON list.")
            for mapping in mappings:
                if not (
                    isinstance(mapping, (list, tuple))
                    and len(mapping) == 2
                    and all(isinstance(value, str) and value for value in mapping)
                ):
                    raise LayoutFileError(f"{location}.mappings contains an invalid signal mapping.")

    def _validate_json_values(self, value, location, depth=0, allow_text=False):
        if depth > 8:
            raise LayoutFileError(f"{location} is nested too deeply.")
        if isinstance(value, dict):
            if len(value) > 1000:
                raise LayoutFileError(f"{location} contains too many values.")
            for key, child in value.items():
                if not isinstance(key, str) or len(key) > 200:
                    raise LayoutFileError(f"{location} contains an invalid key.")
                self._validate_json_values(child, f"{location}.{key}", depth + 1, allow_text)
            return
        if isinstance(value, list):
            if len(value) > 1000:
                raise LayoutFileError(f"{location} contains too many values.")
            for index, child in enumerate(value):
                self._validate_json_values(child, f"{location}[{index}]", depth + 1, allow_text)
            return
        if value is None or isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                raise LayoutFileError(f"{location} must contain only finite numbers.")
            return
        if allow_text and isinstance(value, str) and len(value) <= 4096:
            return
        raise LayoutFileError(f"{location} contains an unsupported value.")

    def _finite_number(self, value, location, integer=False):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LayoutFileError(f"{location} must be a number.")
        number = float(value)
        if not math.isfinite(number):
            raise LayoutFileError(f"{location} must be a finite number.")
        if integer and number != int(number):
            raise LayoutFileError(f"{location} must be a whole number.")
        return int(number) if integer else number

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


    def get_control_policy_data(self, payload):
        return payload.get("control_policy", {})


    def get_input_data(self, payload):
        return payload.get("input_data", {})
