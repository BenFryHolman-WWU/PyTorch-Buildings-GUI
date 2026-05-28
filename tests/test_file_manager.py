import json
import tempfile
import unittest
from pathlib import Path

from test_support import CanvasStub, get_qapp

from PyQt6.QtCore import QPointF
from gui.file_manager import FileManager
from gui.interactive_canvas import ComponentItem
from models.building_model import BuildingModel


class FileManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def test_build_payload_contains_components_connections_and_time(self):
        model = BuildingModel("payload")
        model.set_control_policy(tu_T_supply_setpoint=288.15, rtu_supply_airflow_setpoint=1.5)
        model.input_data_path = "/tmp/input.csv"
        model.input_data_summary = {"row_count": 2, "zone_count": 1, "mapped_keys": ["T_outdoor"]}
        canvas = CanvasStub()
        src = ComponentItem("SolarGains", QPointF(1, 2), model, canvas, component_id="component-0001")
        dst = ComponentItem("Envelope", QPointF(3, 4), model, canvas, component_id="component-0002")
        connection = type(
            "ConnectionStub",
            (),
            {"srcOutput": "solar.Q_solar", "dstInput": "Q_solar"},
        )()
        visual_connections = [{"src_item": src, "dst_item": dst, "connection": connection}]

        payload = FileManager(model).build_payload(
            "payload",
            2,
            [src, dst],
            visual_connections,
            {"t_start": 1.0, "t_duration": 2.0, "dt": 3.0},
        )

        self.assertEqual(payload["name"], "payload")
        self.assertEqual(len(payload["components"]), 2)
        self.assertEqual(payload["connections"][0]["src_id"], "component-0001")
        self.assertEqual(payload["connections"][0]["dst_id"], "component-0002")
        self.assertEqual(payload["connections"][0]["mappings"], None)
        self.assertEqual(payload["time"], {"t_start": 1.0, "t_duration": 2.0, "dt": 3.0})
        self.assertEqual(
            payload["control_policy"],
            {
                "tu_T_supply_setpoint": 288.15,
                "rtu_supply_airflow_setpoint": 1.5,
                "use_control_policy_override": True,
            },
        )
        self.assertEqual(
            payload["input_data"],
            {
                "path": "/tmp/input.csv",
                "summary": {"row_count": 2, "zone_count": 1, "mapped_keys": ["T_outdoor"]},
            },
        )

    def test_inline_json_formatter_writes_nested_lists_readably(self):
        model = BuildingModel("json")
        manager = FileManager(model)
        payload = {"matrix": [[1.0, 0.0], [0.0, 1.0]], "components": [{"id": "a"}]}

        rendered = manager._format_json_with_inline_lists(payload)
        loaded = json.loads(rendered)

        self.assertEqual(loaded, payload)
        self.assertIn('"matrix": [[1.0, 0.0], [0.0, 1.0]]', rendered)

    def test_load_payload_from_path_reads_saved_json(self):
        model = BuildingModel("load")
        manager = FileManager(model)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "layout.json"
            path.write_text('{"name": "loaded", "n_zones": 3}', encoding="utf-8")

            payload = manager.load_payload_from_path(path)

        self.assertEqual(manager.get_model_name(payload, "fallback"), "loaded")
        self.assertEqual(manager.get_n_zones(payload, 1), 3)

    def test_resolve_input_data_path_finds_file_beside_layout(self):
        model = BuildingModel("load")
        manager = FileManager(model)
        with tempfile.TemporaryDirectory() as tmp:
            layout_path = Path(tmp) / "layout.json"
            input_path = Path(tmp) / "inputs.csv"
            input_path.write_text("Time [s]\n0\n", encoding="utf-8")

            resolved = manager.resolve_input_data_path("/Users/example/Downloads/inputs.csv", layout_path)

        self.assertEqual(resolved, input_path)

    def test_input_data_dir_defaults_to_assets_saved_data(self):
        model = BuildingModel("load")
        manager = FileManager(model)

        self.assertEqual(manager.get_input_data_dir().name, "saved_data")
        self.assertEqual(manager.get_input_data_dir().parent.name, "assets")


if __name__ == "__main__":
    unittest.main()
