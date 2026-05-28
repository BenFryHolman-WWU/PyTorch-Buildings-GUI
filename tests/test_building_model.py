import unittest

import torch

from test_support import CanvasStub, get_qapp

from PyQt6.QtCore import QPointF
from gui.interactive_canvas import ComponentItem
from models.building_model import BuildingModel


class BuildingModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def test_resize_zone_value_pads_vectors_and_matrices(self):
        model = BuildingModel("resize")

        self.assertEqual(model._resize_zone_value([1.0, 2.0], 4), [1.0, 2.0, 0.0, 0.0])
        self.assertEqual(model._resize_zone_value([1.0, 2.0, 3.0], 2), [1.0, 2.0])
        self.assertEqual(
            model._resize_zone_value([[1.0, 0.5], [0.5, 1.0]], 3),
            [[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 0.0]],
        )

    def test_resize_zone_value_preserves_tensor_dtype(self):
        model = BuildingModel("resize")
        tensor = torch.tensor([1.0, 2.0], dtype=torch.float64)

        resized = model._resize_zone_value(tensor, 3)

        self.assertIsInstance(resized, torch.Tensor)
        self.assertEqual(resized.dtype, torch.float64)
        self.assertEqual(resized.tolist(), [1.0, 2.0, 0.0])

    def test_update_n_zones_updates_existing_component_properties(self):
        model = BuildingModel("zones")
        canvas = CanvasStub()
        item = ComponentItem("VAVBox", QPointF(0, 0), model, canvas)
        model.add_componentItem(item)

        model.update_n_zones(4)

        self.assertEqual(model.n_zones, 4)
        self.assertEqual(item.component.n_zones, 4)
        self.assertEqual(len(item.component.airflow_min), 4)
        self.assertEqual(len(item.component.airflow_max), 4)

    def test_infer_n_zones_from_component_values(self):
        model = BuildingModel("infer")
        canvas = CanvasStub()
        item = ComponentItem("Envelope", QPointF(0, 0), model, canvas)
        item.component.R_env = torch.tensor([0.1, 0.2, 0.3])
        model.add_componentItem(item)

        self.assertEqual(model.infer_n_zones_from_components(), 3)

    def test_control_policy_settings_are_model_level(self):
        model = BuildingModel("control")

        model.set_control_policy(tu_T_supply_setpoint=288.15, rtu_supply_airflow_setpoint=1.75)

        self.assertEqual(
            model.get_control_policy_data(),
            {
                "tu_T_supply_setpoint": 288.15,
                "rtu_supply_airflow_setpoint": 1.75,
                "use_control_policy_override": True,
            },
        )

    def test_component_serialization_round_trip_applies_values(self):
        model = BuildingModel("serial")
        canvas = CanvasStub()
        item = ComponentItem("SolarGains", QPointF(0, 0), model, canvas)

        item.apply_serialized_values({"window_area": 42.0, "window_orientation": [0.0, 90.0]})
        values = item.serialize_values()

        self.assertEqual(values["window_area"], 42.0)
        self.assertEqual(values["window_orientation"], [0.0, 90.0])


if __name__ == "__main__":
    unittest.main()
