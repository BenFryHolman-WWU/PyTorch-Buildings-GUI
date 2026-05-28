import unittest
from unittest.mock import patch

from test_support import get_qapp

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QMessageBox
from gui.main_window import MainWindow


class MainWindowToolModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = get_qapp()

    def test_exclusive_tool_mode_disables_surrounding_controls_until_canvas_cancel(self):
        window = MainWindow()
        window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        window.add_connection()

        self.assertEqual(window.pending_component_action, "connect")
        self.assertTrue(window.add_connection_btn.isEnabled())
        self.assertTrue(all(
            not button.isEnabled()
            for button in window.action_buttons
            if button is not window.add_connection_btn
        ))
        self.assertFalse(window._left_tabs.isEnabled())

        window.handle_canvas_click_action()

        self.assertIsNone(window.pending_component_action)
        self.assertTrue(window._left_tabs.isEnabled())
        self.assertTrue(window.add_connection_btn.isEnabled())
        window.is_dirty = False
        window.close()

    def test_active_tool_button_can_toggle_mode_off(self):
        window = MainWindow()
        window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        window.add_connection()
        window.add_connection()

        self.assertIsNone(window.pending_component_action)
        self.assertTrue(window._left_tabs.isEnabled())
        window.is_dirty = False
        window.close()

    def test_component_tools_are_disabled_when_canvas_has_no_components(self):
        window = MainWindow()

        self.assertFalse(window.add_connection_btn.isEnabled())
        self.assertFalse(window.edit_component_btn.isEnabled())
        self.assertFalse(window.delete_component_btn.isEnabled())
        self.assertFalse(window.area_delete_btn.isEnabled())
        self.assertFalse(window.delete_connection_btn.isEnabled())
        window.is_dirty = False
        window.close()

    def test_control_policy_toggle_enables_and_disables_override_fields(self):
        window = MainWindow()
        window.canvas_stack.setCurrentIndex(2)

        self.assertFalse(window.building_model.use_control_policy_override)
        self.assertFalse(window._control_policy_inputs["tu_T_supply_setpoint"].isEnabled())

        window._toggle_control_policy_override()

        self.assertTrue(window.building_model.use_control_policy_override)
        self.assertTrue(window._control_policy_inputs["tu_T_supply_setpoint"].isEnabled())

        window._toggle_control_policy_override()

        self.assertFalse(window.building_model.use_control_policy_override)
        self.assertFalse(window._control_policy_inputs["tu_T_supply_setpoint"].isEnabled())
        self.assertEqual(window.canvas_stack.currentIndex(), 2)
        window.is_dirty = False
        window.close()

    def test_run_button_resets_cached_results_after_completed_simulation(self):
        window = MainWindow()
        window._last_results = {"t": object()}
        window._sim_resume_results = {"partial": object()}
        window._sim_resume_step = 4
        window._set_simulation_resume_ui()
        window.canvas_stack.setCurrentIndex(1)

        window._on_run_btn_clicked()

        self.assertIsNone(window._last_results)
        self.assertIsNone(window._sim_resume_results)
        self.assertEqual(window._sim_resume_step, 0)
        self.assertEqual(window._run_btn.text(), "Run Simulation")
        self.assertFalse(window._stop_btn.isEnabled())
        self.assertEqual(window.canvas_stack.currentIndex(), 2)
        window.is_dirty = False
        window.close()

    def test_finished_simulation_sets_run_button_to_reset(self):
        window = MainWindow()

        window._set_simulation_reset_ui()

        self.assertEqual(window._run_btn.text(), "Reset Simulation")
        self.assertTrue(window._run_btn.isEnabled())
        self.assertFalse(window._stop_btn.isEnabled())
        window.is_dirty = False
        window.close()

    def test_running_simulation_shows_reset_button(self):
        window = MainWindow()

        window._set_simulation_running_ui(True)

        self.assertEqual(window._run_btn.text(), "Reset Simulation")
        self.assertTrue(window._run_btn.isEnabled())
        self.assertTrue(window._stop_btn.isEnabled())
        window.is_dirty = False
        window.close()

    def test_delete_component_tool_deletes_clicked_canvas_component(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        window.arm_delete_component()
        window.handle_component_click_action(item)

        self.assertIsNone(window.pending_component_action)
        self.assertNotIn(item, window.building_model.componentItems)
        window.is_dirty = False
        window.close()

    def test_area_delete_labels_include_component_names_and_ids(self):
        window = MainWindow()
        rtu = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu-1")
        envelope = window.canvas.add_component("Envelope", QPointF(150, 0), component_id="env-1")

        labels = window._area_delete_item_labels([rtu, envelope])

        self.assertEqual(labels, ["RTU (rtu-1)", "Envelope (env-1)"])
        window.is_dirty = False
        window.close()

    def test_area_delete_preview_highlights_components_and_connections(self):
        window = MainWindow()
        solar = window.canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = window.canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        ok, _message = window.canvas.add_connection_between_items(solar, envelope)
        self.assertTrue(ok)

        window.canvas.set_area_delete_preview(QRectF(-10, -10, 320, 120))

        self.assertTrue(solar._delete_preview)
        self.assertTrue(envelope._delete_preview)
        self.assertEqual(solar.brush().color().name(), "#ffffff")
        self.assertEqual(len(window.canvas.area_delete_preview_connections), 1)

        window.canvas.clear_area_delete_preview()

        self.assertFalse(solar._delete_preview)
        self.assertFalse(envelope._delete_preview)
        self.assertEqual(window.canvas.area_delete_preview_connections, [])
        window.is_dirty = False
        window.close()

    def test_new_project_confirmation_cancel_preserves_current_state(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        with patch("gui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.No) as question:
            window.new_page()

        question.assert_called_once()
        self.assertIn(item, window.building_model.componentItems)
        self.assertTrue(window.stack.canUndo())
        window.is_dirty = False
        window.close()

    def test_new_project_confirmation_resets_model_and_undo_redo_history(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        window.stack.undo()
        self.assertTrue(window.stack.canRedo())
        window.building_model.input_data_path = "/tmp/input.csv"
        window.building_model.input_data_summary = {"row_count": 1}
        window.building_model.set_control_policy(
            tu_T_supply_setpoint=290.0,
            rtu_supply_airflow_setpoint=2.0,
            enable_override=True,
        )

        with patch("gui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            window.new_page()

        self.assertNotIn(item, window.building_model.componentItems)
        self.assertEqual(window.building_model.name, "Model")
        self.assertEqual(window.building_model.n_zones, 2)
        self.assertIsNone(window.building_model.input_data_path)
        self.assertEqual(window.building_model.input_data_summary, {})
        self.assertFalse(window.building_model.use_control_policy_override)
        self.assertFalse(window.stack.canUndo())
        self.assertFalse(window.stack.canRedo())
        self.assertFalse(window.undo_btn.isEnabled())
        self.assertFalse(window.redo_btn.isEnabled())
        window.is_dirty = False
        window.close()

    def test_undo_redo_actions_include_ctrl_and_command_style_shortcuts(self):
        window = MainWindow()
        actions_by_name = {action.objectName(): action for action in window.actions()}

        undo_shortcuts = {
            shortcut.toString(QKeySequence.SequenceFormat.PortableText)
            for shortcut in actions_by_name["undo_action"].shortcuts()
        }
        redo_shortcuts = {
            shortcut.toString(QKeySequence.SequenceFormat.PortableText)
            for shortcut in actions_by_name["redo_action"].shortcuts()
        }

        self.assertEqual(undo_shortcuts, {"Ctrl+Z", "Meta+Z"})
        self.assertEqual(redo_shortcuts, {"Ctrl+Y", "Meta+Y"})
        window.is_dirty = False
        window.close()


if __name__ == "__main__":
    unittest.main()
