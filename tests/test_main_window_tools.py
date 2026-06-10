import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from test_support import get_qapp

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QKeySequence
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

    def test_delete_component_tool_undo_redo_restores_clicked_component(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        window.arm_delete_component()
        window.handle_component_click_action(item)

        self.assertNotIn(item, window.building_model.componentItems)
        self.assertEqual(window.component_list.topLevelItemCount(), 0)

        window.stack.undo()

        self.assertIn(item, window.building_model.componentItems)
        self.assertIs(item.scene(), window.canvas.scene)
        self.assertEqual(window.component_list.topLevelItemCount(), 1)

        window.stack.redo()

        self.assertNotIn(item, window.building_model.componentItems)
        self.assertIsNone(item.scene())
        self.assertEqual(window.component_list.topLevelItemCount(), 0)
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

    def test_area_delete_preview_uses_actual_component_rect(self):
        window = MainWindow()
        rtu = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        highlighted = window.canvas.set_area_delete_preview(QRectF(-20, -20, 10, 10))

        self.assertEqual(highlighted, [])
        self.assertFalse(rtu._delete_preview)
        window.is_dirty = False
        window.close()

    def test_area_delete_undo_redo_restores_all_components_and_connections(self):
        window = MainWindow()
        solar = window.canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = window.canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        ok, _message = window.canvas.add_connection_between_items(solar, envelope)
        self.assertTrue(ok)
        window.canvas.set_area_delete_preview(QRectF(-10, -10, 320, 120))

        removed_count = window.canvas.delete_component_items([solar, envelope])

        self.assertEqual(removed_count, 2)
        self.assertNotIn(solar, window.building_model.componentItems)
        self.assertNotIn(envelope, window.building_model.componentItems)
        self.assertEqual(len(window.canvas.visual_connections), 0)

        window.stack.undo()

        self.assertIn(solar, window.building_model.componentItems)
        self.assertIn(envelope, window.building_model.componentItems)
        self.assertEqual(len(window.canvas.visual_connections), 1)
        self.assertEqual(len(window.building_model.connections), 1)
        self.assertEqual(window.canvas.visual_connections[0]["line_item"].pen().color().name(), "#5c6f96")

        window.stack.redo()

        self.assertNotIn(solar, window.building_model.componentItems)
        self.assertNotIn(envelope, window.building_model.componentItems)
        self.assertEqual(len(window.canvas.visual_connections), 0)
        self.assertEqual(len(window.building_model.connections), 0)
        window.is_dirty = False
        window.close()

    def test_delete_connection_enables_undo_and_restores_connection(self):
        window = MainWindow()
        solar = window.canvas.add_component("SolarGains", QPointF(0, 0), component_id="solar")
        envelope = window.canvas.add_component("Envelope", QPointF(150, 0), component_id="envelope")
        ok, _message = window.canvas.add_connection_between_items(solar, envelope)
        self.assertTrue(ok)
        connection_data = window.canvas.visual_connections[0]
        window.stack.clear()
        window._set_undo_enabled(window.stack.canUndo())

        removed = window.canvas.delete_connection_data(connection_data)

        self.assertTrue(removed)
        self.assertTrue(window.stack.canUndo())
        self.assertTrue(window.undo_btn.isEnabled())
        self.assertEqual(len(window.canvas.visual_connections), 0)
        self.assertEqual(len(window.building_model.connections), 0)

        window.stack.undo()

        self.assertEqual(len(window.canvas.visual_connections), 1)
        self.assertEqual(len(window.building_model.connections), 1)
        self.assertIs(window.canvas.visual_connections[0], connection_data)

        window.stack.redo()

        self.assertEqual(len(window.canvas.visual_connections), 0)
        self.assertEqual(len(window.building_model.connections), 0)
        window.is_dirty = False
        window.close()

    def test_new_project_confirmation_cancel_preserves_current_state(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")

        with patch.object(window.dialogue_manager, "confirm_new_project", return_value=False) as question:
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

        with patch.object(window.dialogue_manager, "confirm_new_project", return_value=True):
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

    def test_empty_new_project_after_undo_loads_without_unsaved_confirmation(self):
        window = MainWindow()
        window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        window.stack.undo()

        with patch.object(window.dialogue_manager, "confirm_load_project") as confirm_load:
            with patch.object(window.dialogue_manager, "prompt_load_layout_path", return_value=None):
                window.load_layout()

        confirm_load.assert_not_called()
        self.assertFalse(window.is_dirty)
        window.close()

    def test_empty_new_project_after_delete_loads_without_unsaved_confirmation(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        window.canvas.remove_component_item(item)

        with patch.object(window.dialogue_manager, "confirm_load_project") as confirm_load:
            with patch.object(window.dialogue_manager, "prompt_load_layout_path", return_value=None):
                window.load_layout()

        confirm_load.assert_not_called()
        self.assertFalse(window.is_dirty)
        window.close()

    def test_invalid_json_layout_shows_error_without_clearing_project(self):
        window = MainWindow()
        item = window.canvas.add_component("RTU", QPointF(0, 0), component_id="rtu")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text('{"name": "invalid",', encoding="utf-8")
            with patch.object(window.dialogue_manager, "confirm_load_project", return_value=True):
                with patch.object(window.dialogue_manager, "prompt_load_layout_path", return_value=str(path)):
                    with patch.object(window.dialogue_manager, "show_error") as show_error:
                        loaded = window.load_layout()

        self.assertFalse(loaded)
        show_error.assert_called_once()
        self.assertIn(item, window.building_model.componentItems)
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
