import unittest

import torch

from test_support import get_qapp

from gui.main_window import MainWindow


class SetupIssueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def test_zone_increase_with_default_zero_padding_is_reported(self):
        window = MainWindow()
        try:
            window.canvas.add_component("Envelope")
            window.canvas.add_component("VAVBox")
            window.building_model.update_n_zones(4)

            issues = window.collect_setup_issues()
        finally:
            window.close()

        issue_text = "\n".join(issues)
        self.assertIn("Envelope.R_env has zero or negative values", issue_text)
        self.assertIn("Envelope.C_env has zero or negative values", issue_text)
        self.assertIn("Envelope.adjacency has disconnected zone row", issue_text)
        self.assertIn("VAVBox.airflow_max has zero or negative values", issue_text)
        self.assertIn("VAVBox airflow_max must be greater than airflow_min", issue_text)

    def test_completed_simulation_steps_ignores_full_length_external_inputs(self):
        window = MainWindow()
        try:
            window._sim_current_step = 11
            results = {
                "t": torch.zeros(1, 2016, 1),
                "T_outdoor": torch.zeros(1, 2016, 1),
                "T_setpoint": torch.zeros(1, 2016, 5),
                "rtu.T_supply": torch.zeros(1, 12, 1),
                "vav.supply_airflow": torch.zeros(1, 11, 5),
            }

            completed = window._completed_simulation_steps(results)
        finally:
            window.close()

        self.assertEqual(completed, 11)


if __name__ == "__main__":
    unittest.main()
