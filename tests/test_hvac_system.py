import unittest

import torch

from test_support import ROOT

from neuromancer.hvac.building import BuildingSystem, Node
from neuromancer.hvac.building_components import Envelope


class HvacSystemTests(unittest.TestCase):
    def test_unique_name_check_rejects_duplicates(self):
        node_a = Node(lambda x: x, ["x"], ["y"], name="duplicate")
        node_b = Node(lambda y: y, ["y"], ["z"], name="duplicate")

        with self.assertRaisesRegex(AssertionError, "unique names"):
            BuildingSystem([node_a, node_b])

    def test_direct_simulate_uses_duration_relative_to_start_time(self):
        system = BuildingSystem([])

        results = system.simulate(t_start=18000.0, t_duration=600.0, t_dt=300.0)

        self.assertEqual(tuple(results["t"].shape), (1, 2, 1))
        self.assertEqual(results["t"][0, :, 0].tolist(), [18000.0, 18300.0])

    def test_direct_simulate_validates_time_arguments(self):
        system = BuildingSystem([])

        with self.assertRaisesRegex(ValueError, "duration"):
            system.simulate(t_duration=0.0)
        with self.assertRaisesRegex(ValueError, "time step"):
            system.simulate(t_dt=0.0)

    def test_standalone_envelope_simulation_expands_external_inputs(self):
        envelope = Envelope(n_zones=2, R_env=[0.1, 0.12], C_env=[1.2e6, 1.0e6])
        node = __import__("neuromancer.hvac.building", fromlist=["BuildingNode"]).BuildingNode(
            envelope,
            input_map={
                "envelope.T_zones": "T_zones",
                "T_outdoor": "T_outdoor",
                "solar.Q_solar": "Q_solar",
                "Q_internal": "Q_internal",
                "vav.Q_supply_flow": "Q_hvac",
            },
            name="envelope",
        )
        system = BuildingSystem([node])
        data = {"t": torch.tensor([[[18000.0], [18300.0], [18600.0]]])}

        results = system.simulate(data=data)

        self.assertEqual(tuple(results["T_outdoor"].shape), (1, 3, 1))
        self.assertEqual(tuple(results["Q_internal"].shape), (1, 3, 2))
        self.assertIn("envelope.T_zones", results)


if __name__ == "__main__":
    unittest.main()
