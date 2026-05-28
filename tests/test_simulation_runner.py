import threading
import unittest

import torch

from test_support import CanvasStub, get_qapp

from PyQt6.QtCore import QPointF
from gui.interactive_canvas import ComponentItem, InteractiveCanvas
from models.building_model import BuildingModel
from simulation.runner import SimulationError, SimulationRunner


class SimulationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def _model_with_components(self, names=("SolarGains", "Envelope", "RTU", "VAVBox")):
        model = BuildingModel("sim")
        canvas = CanvasStub()
        for index, name in enumerate(names):
            item = ComponentItem(name, QPointF(index * 150, 0), model, canvas, component_id=name)
            model.add_componentItem(item)
        return model

    def test_empty_model_raises_clear_error(self):
        model = BuildingModel("empty")

        with self.assertRaisesRegex(SimulationError, "No components"):
            SimulationRunner().run(model)

    def test_invalid_time_settings_raise_clear_errors(self):
        model = self._model_with_components(("SolarGains",))
        cases = [
            (0, 300, "duration"),
            (600, 0, "time step"),
            (600, -1, "time step"),
            (300, 600, "longer than the duration"),
        ]

        for duration, dt, message in cases:
            with self.subTest(duration=duration, dt=dt):
                model.set_time_param_in_seconds(t_duration=duration, dt=dt)
                with self.assertRaisesRegex(SimulationError, message):
                    SimulationRunner().run(model)

    def test_duplicate_component_nodes_raise_clear_error(self):
        model = self._model_with_components(("Envelope", "Envelope"))
        model.set_time_param_in_seconds(t_duration=600, dt=300)

        with self.assertRaisesRegex(SimulationError, "Duplicate component node"):
            SimulationRunner().run(model)

    def test_hvac_nodes_use_example_execution_order(self):
        model = self._model_with_components(("Envelope", "SolarGains", "VAVBox", "RTU"))

        nodes = SimulationRunner()._topological_sort(model)

        self.assertEqual([node.name for node in nodes], ["solar", "rtu", "vav", "envelope"])

    def test_canvas_connections_use_hvac_example_mappings(self):
        model = BuildingModel("connections")
        canvas = InteractiveCanvas(model)
        solar = canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        rtu = canvas.add_component("RTU", QPointF(300, 0), component_id="rtu")

        ok, message = canvas.add_connection_between_items(solar, envelope)

        self.assertTrue(ok, message)
        self.assertEqual(model.connections[0].srcOutput, "solar.Q_solar")
        self.assertEqual(model.connections[0].dstInput, "Q_solar")
        self.assertEqual(model.connections[0].mappings, [("solar.Q_solar", "Q_solar")])

        ok, message = canvas.add_connection_between_items(solar, rtu)

        self.assertFalse(ok)
        self.assertIn("not part of the HVAC example wiring", message)

    def test_canvas_connection_can_use_selected_mapping_and_label(self):
        model = BuildingModel("selected-connection")
        canvas = InteractiveCanvas(model)
        rtu = canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        vav = canvas.add_component("VAVBox", QPointF(150, 0), component_id="vav")

        ok, message = canvas.add_connection_between_items(
            rtu,
            vav,
            mappings=[("rtu.T_supply", "T_supply_upstream")],
        )

        self.assertTrue(ok, message)
        self.assertEqual(model.connections[0].srcOutput, "rtu.T_supply")
        self.assertEqual(model.connections[0].dstInput, "T_supply_upstream")
        self.assertEqual(model.connections[0].mappings, [("rtu.T_supply", "T_supply_upstream")])
        self.assertNotIn("label_item", canvas.visual_connections[0])

    def test_bidirectional_connections_share_line_and_combined_label(self):
        model = BuildingModel("two-way")
        canvas = InteractiveCanvas(model)
        rtu = canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        vav = canvas.add_component("VAVBox", QPointF(180, 0), component_id="vav")

        ok, message = canvas.add_connection_between_items(rtu, vav)
        self.assertTrue(ok, message)
        ok, message = canvas.add_connection_between_items(vav, rtu)
        self.assertTrue(ok, message)

        forward_line = canvas.visual_connections[0]["line_item"].line()
        reverse_line = canvas.visual_connections[1]["line_item"].line()
        self.assertEqual(forward_line.y1(), reverse_line.y2())
        self.assertEqual(forward_line.y2(), reverse_line.y1())
        self.assertNotIn("label_item", canvas.visual_connections[0])
        self.assertNotIn("label_item", canvas.visual_connections[1])

    def test_connections_update_component_input_maps_for_simulation(self):
        model = BuildingModel("maps")
        canvas = InteractiveCanvas(model)
        solar = canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        canvas.add_connection_between_items(solar, envelope)

        SimulationRunner()._apply_connection_input_maps(model)

        self.assertEqual(envelope.node.input_map["solar.Q_solar"], "Q_solar")
        self.assertNotIn("Q_solar", envelope.node.input_map)

    def test_canvas_delete_connection_removes_visual_and_model_connection(self):
        model = BuildingModel("delete-connection")
        canvas = InteractiveCanvas(model)
        solar = canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        canvas.add_connection_between_items(solar, envelope)
        connection_data = canvas.visual_connections[0]

        canvas.highlight_connection(connection_data)
        removed = canvas.remove_connection_data(connection_data, notify=False)

        self.assertTrue(removed)
        self.assertEqual(canvas.visual_connections, [])
        self.assertEqual(model.connections, [])
        self.assertIsNone(canvas.hovered_connection_data)

    def test_build_input_data_contains_external_series_with_expected_shapes(self):
        model = self._model_with_components(("SolarGains", "Envelope", "RTU", "VAVBox"))
        model.set_time_param_in_seconds(t_start=18000, t_duration=900, dt=300)
        t_rng = range(int(model.t_start), int(model.t_start + model.t_duration), int(model.dt))

        data = SimulationRunner()._build_input_data(model.componentItems, t_rng)

        self.assertEqual(tuple(data["t"].shape), (1, 3, 1))
        for key in ("T_outdoor", "weather_factor", "Q_internal", "T_supply_setpoint", "T_setpoint"):
            self.assertIn(key, data)
            self.assertIsInstance(data[key], torch.Tensor)
            self.assertEqual(data[key].shape[0], 1)
            self.assertEqual(data[key].shape[1], 3)

    def test_model_control_policy_overrides_rtu_external_inputs(self):
        model = self._model_with_components(("RTU",))
        model.set_control_policy(tu_T_supply_setpoint=289.0, rtu_supply_airflow_setpoint=1.25)
        t_rng = range(0, 900, 300)

        data = SimulationRunner()._build_input_data(model.componentItems, t_rng, model)

        self.assertTrue(torch.allclose(data["T_supply_setpoint"], torch.full((1, 3, 1), 289.0)))
        self.assertTrue(torch.allclose(data["supply_airflow_setpoint"], torch.full((1, 3, 1), 1.25)))

    def test_model_defaults_do_not_override_example_control_schedules(self):
        model = self._model_with_components(("RTU",))
        t_rng = range(5 * 60 * 60, 5 * 60 * 60 + 900, 300)

        data = SimulationRunner()._build_input_data(model.componentItems, t_rng, model)

        self.assertFalse(model.use_control_policy_override)
        self.assertFalse(torch.allclose(data["supply_airflow_setpoint"], torch.full((1, 3, 1), 1.0)))

    def test_short_full_system_simulation_succeeds(self):
        model = self._model_with_components()
        model.set_time_param_in_seconds(t_start=18000, t_duration=600, dt=300)

        results, variables, t_start = SimulationRunner().run(model)

        self.assertEqual(t_start, 18000)
        self.assertEqual(tuple(results["t"].shape), (1, 2, 1))
        self.assertIn("envelope.T_zones", results)
        self.assertIn("rtu.total_power", results)
        self.assertGreaterEqual(len(variables), 1)

    def test_stop_event_allows_early_rollout_stop(self):
        model = self._model_with_components()
        model.set_time_param_in_seconds(t_start=18000, t_duration=1800, dt=300)
        stop_event = threading.Event()
        calls = []

        def callback(step, total, data):
            calls.append((step, total))
            stop_event.set()

        results, _, _ = SimulationRunner().run(
            model,
            step_callback=callback,
            stop_event=stop_event,
            callback_interval=1,
        )

        self.assertEqual(calls[0], (1, 6))
        self.assertLess(results["t"].shape[1], 7)

    def test_resume_from_partial_results_continues_to_end(self):
        model = self._model_with_components()
        model.set_time_param_in_seconds(t_start=18000, t_duration=1800, dt=300)
        stop_event = threading.Event()

        def callback(step, _total, _data):
            if step == 2:
                stop_event.set()

        partial, _, _ = SimulationRunner().run(
            model,
            step_callback=callback,
            stop_event=stop_event,
            callback_interval=1,
        )

        resumed_steps = []
        resumed, _, _ = SimulationRunner().run(
            model,
            step_callback=lambda step, total, _data: resumed_steps.append((step, total)),
            callback_interval=1,
            resume_from_step=2,
            initial_results=partial,
        )

        self.assertEqual(resumed_steps[0], (3, 6))
        self.assertEqual(resumed_steps[-1], (6, 6))
        self.assertEqual(tuple(resumed["t"].shape), (1, 6, 1))
        self.assertEqual(tuple(resumed["envelope.T_zones"].shape), (1, 7, 2))


if __name__ == "__main__":
    unittest.main()
