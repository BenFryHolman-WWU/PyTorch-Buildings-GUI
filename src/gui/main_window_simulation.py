"""Main window simulation run-state and callback helpers."""

class MainWindowSimulationMixin:
    def _clear_cached_simulation_results(self, keep_plot_screen: bool = False):
        """
        Summary: Clear cached simulation results.
        Args: keep_plot_screen
        """
        if self._sim_thread is not None and self._sim_thread.isRunning():
            self._sim_reset_requested = True
            self._sim_thread.stop()
            self._sim_thread = None
        self._last_results = None
        self._plot_results_shown = None
        self._multi_charts = []
        self._plot_tabs = None
        self._plot_selected_by_group = {}
        self._plot_order_by_group = {}
        self._sim_resume_results = None
        self._sim_resume_step = 0
        self._sim_current_step = 0
        self._sim_total_steps = 0
        if self._run_btn is not None:
            self._run_btn.setText("Run Simulation")
            self._run_btn.setStyleSheet(self._run_btn_run_style)
            self._run_btn.setEnabled(True)
        if self._stop_btn is not None:
            self._stop_btn.setText("Stop Simulation")
            self._stop_btn.setStyleSheet(self._run_btn_stop_style)
            self._stop_btn.setEnabled(False)
        if self._sim_progress_bar is not None:
            self._sim_progress_bar.setVisible(False)
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(2 if keep_plot_screen else 0)
        self.refresh_setup_issues()
        self.refresh_input_data_label()

    def _invalidate_plots(self):
        """Summary: Invalidate plots."""
        if self._sim_thread is not None and self._sim_thread.isRunning():
            self._sim_thread.stop()
            self._sim_thread = None
            self._set_simulation_running_ui(False)
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(0)
        if self._left_tabs is not None:
            self._left_tabs.blockSignals(True)
            self._left_tabs.setCurrentIndex(0)
            self._left_tabs.blockSignals(False)
        self._last_results = None
        self._plot_results_shown = None
        self._multi_charts = []
        self._plot_tabs = None
        self._plot_selected_by_group = {}
        self._plot_order_by_group = {}
        self._plot_progress_bar = None
        self._sim_resume_results = None
        self._sim_resume_step = 0

    def _set_simulation_running_ui(self, running: bool, reset_progress: bool = True):
        """
        Summary: Set simulation running ui.
        Args: running, reset_progress
        """
        if self._run_btn is not None:
            if running:
                self._run_btn.setEnabled(True)
                self._run_btn.setText("Reset Simulation")
                self._run_btn.setStyleSheet(self._run_btn_resume_style)
            else:
                self._run_btn.setEnabled(True)
        if self._stop_btn is not None:
            self._stop_btn.setEnabled(running)
            self._stop_btn.setText("Stop Simulation")
            self._stop_btn.setStyleSheet(self._run_btn_stop_style)
        if self._sim_progress_bar is not None:
            if running:
                self._sim_progress_bar.setVisible(True)
                if reset_progress:
                    self._sim_progress_bar.setValue(0)
                    self._sim_progress_bar.setFormat("Simulation 0%")
            else:
                self._sim_progress_bar.setVisible(False)

    def _set_simulation_resume_ui(self):
        if self._run_btn is not None:
            self._run_btn.setEnabled(True)
        if self._stop_btn is not None:
            self._stop_btn.setText("Resume Simulation")
            self._stop_btn.setStyleSheet(self._run_btn_resume_style)
            self._stop_btn.setEnabled(True)
        if self._sim_progress_bar is not None:
            self._sim_progress_bar.setVisible(True)

    def _set_simulation_reset_ui(self):
        """Summary: Set simulation reset ui."""
        if self._run_btn is not None:
            self._run_btn.setEnabled(True)
            self._run_btn.setText("Reset Simulation")
            self._run_btn.setStyleSheet(self._run_btn_resume_style)
        if self._stop_btn is not None:
            self._stop_btn.setEnabled(False)
            self._stop_btn.setText("Stop Simulation")
            self._stop_btn.setStyleSheet(self._run_btn_stop_style)
        if self._sim_progress_bar is not None:
            self._sim_progress_bar.setVisible(False)

    def _update_simulation_progress(self, step: int, total: int):
        percent = 0 if total <= 0 else max(0, min(100, int(round(step * 100 / total))))
        for progress_bar in (self._sim_progress_bar, self._plot_progress_bar):
            if progress_bar is not None:
                progress_bar.setValue(percent)
                progress_bar.setFormat(f"Simulation {percent}%")

    def _completed_simulation_steps(self, results):
        """
        Summary: Completed simulation steps.
        Args: results
        Returns: Return the computed value.
        """
        if not isinstance(results, dict):
            return self._sim_current_step
        completed = 0
        for key, value in results.items():
            if "." not in key or not hasattr(value, "shape") or len(value.shape) < 2:
                continue
            length = int(value.shape[1])
            if length > 1:
                completed = max(completed, length - 1)
        return max(completed, self._sim_current_step)

    def view_plots(self):
        if self._last_results is None:
            self.canvas_stack.setCurrentIndex(2)
            return
        if self._plot_results_shown is not self._last_results:
            self._make_plot_panel()
            self._rebuild_plot_settings()
            self._plot_results_shown = self._last_results
        self.canvas_stack.setCurrentIndex(1)

    def _on_run_btn_clicked(self):
        if (
            (self._sim_thread is not None and self._sim_thread.isRunning())
            or self._last_results is not None
            or (self._run_btn is not None and self._run_btn.text() == "Reset Simulation")
        ):
            self._clear_cached_simulation_results(keep_plot_screen=True)
            self.statusBar().showMessage("Simulation reset.", 3000)
        else:
            self.run_simulation()

    def on_stop_resume_clicked(self):
        if self._sim_reset_requested:
            return
        if self._sim_thread is not None and self._sim_thread.isRunning():
            self.stop_simulation()
        elif self._stop_btn is not None and self._stop_btn.text().startswith("Resume"):
            self.resume_simulation()

    def stop_simulation(self):
        if self._sim_thread is not None and self._sim_thread.isRunning():
            self._sim_stop_requested = True
            self._sim_thread.stop()
            if self._stop_btn is not None:
                self._stop_btn.setText("Stopping...")
                self._stop_btn.setEnabled(False)
            self.statusBar().showMessage("Stopping simulation...", 3000)

    def run_simulation(self):
        """Summary: Run simulation."""
        from simulation.runner import SimulationThread
        if self._sim_thread is not None and self._sim_thread.isRunning():
            return
        self.refresh_setup_issues()

        component_items = [ci for ci in self.building_model.componentItems if ci is not None]
        if not component_items:
            self.dialogue_manager.show_error(
                "Simulation Error",
                "No components on the canvas. Add components before running.",
            )
            return
        self._plot_results_shown = None
        self._last_results = None
        self._multi_charts = []
        self._plot_tabs = None
        self._plot_selected_by_group = {}
        self._plot_order_by_group = {}
        self._plot_progress_bar = None
        self._sim_stop_requested = False
        self._sim_reset_requested = False
        self._sim_current_step = 0
        self._sim_total_steps = 0
        self._sim_resume_results = None
        self._sim_resume_step = 0
        self._set_simulation_running_ui(True)
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(2)

        self.statusBar().showMessage("Running simulation...")

        self._sim_thread = SimulationThread(self.building_model, callback_interval=5)
        self._sim_thread.step_update.connect(self._on_sim_step_update)
        self._sim_thread.finished_ok.connect(self._on_sim_finished_ok)
        self._sim_thread.error.connect(self._on_sim_error)
        self._sim_thread.start()

    def resume_simulation(self):
        """Summary: Resume simulation."""
        from simulation.runner import SimulationThread
        if self._sim_thread is not None and self._sim_thread.isRunning():
            return
        if self._sim_reset_requested:
            return
        if self._sim_resume_results is None or self._sim_resume_step <= 0:
            return
        if self._sim_total_steps and self._sim_resume_step >= self._sim_total_steps:
            self._set_simulation_running_ui(False)
            return
        self._sim_stop_requested = False
        self._set_simulation_running_ui(True, reset_progress=False)
        self.statusBar().showMessage("Resuming simulation...")
        self._sim_thread = SimulationThread(
            self.building_model,
            callback_interval=5,
            resume_from_step=self._sim_resume_step,
            initial_results=self._sim_resume_results,
        )
        self._sim_thread.step_update.connect(self._on_sim_step_update)
        self._sim_thread.finished_ok.connect(self._on_sim_finished_ok)
        self._sim_thread.error.connect(self._on_sim_error)
        self._sim_thread.start()

    def _on_sim_step_update(self, step: int, total: int):
        """
        Summary: On sim step update.
        Args: step, total
        """
        from simulation.plotter import VARIABLE_META, ZONE_COLORS, PLOT_GROUPS, auto_title
        data = self._sim_thread.partial_results if self._sim_thread else None
        if data is None:
            return

        self._sim_current_step = step
        self._sim_total_steps = total
        self._update_simulation_progress(step, total)
        if not self._multi_charts:
            self._last_results = data
            self._last_t_start = int(self.building_model.t_start)
            for tab_name, group_vars in PLOT_GROUPS:
                defaults = [v for v in group_vars if v in data]
                self._plot_selected_by_group[tab_name] = set(defaults)
                self._plot_order_by_group[tab_name] = defaults
            self._make_plot_panel()
            self._rebuild_plot_settings()
            self._plot_results_shown = self._last_results
            self._update_simulation_progress(step, total)
            self.canvas_stack.setCurrentIndex(1)
            return
        self._last_results = data
        for mc in self._multi_charts:
            mc.refresh_series_from_results(data, self._last_t_start, VARIABLE_META, ZONE_COLORS)
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(1)

    def _on_sim_finished_ok(self, results, variables, t_start):
        """
        Summary: On sim finished ok.
        Args: results, variables
        """
        from simulation.plotter import VARIABLE_META, ZONE_COLORS, PLOT_GROUPS, auto_title
        if self._sim_reset_requested:
            self._sim_thread = None
            self._sim_stop_requested = False
            self._sim_reset_requested = False
            self._clear_cached_simulation_results(keep_plot_screen=True)
            return
        self._last_results = results
        self._last_t_start = int(t_start)
        n_steps = results["t"].shape[1]
        completed_steps = self._completed_simulation_steps(results)
        if self._sim_total_steps <= 0:
            self._sim_total_steps = n_steps
        thread_stopped = bool(getattr(self._sim_thread, "was_stopped", False))
        stopped_early = thread_stopped or self._sim_stop_requested
        self._sim_current_step = completed_steps
        for mc in self._multi_charts:
            mc.refresh_series_from_results(results, self._last_t_start, VARIABLE_META, ZONE_COLORS)
        for tab_idx, (tab_name, _) in enumerate(PLOT_GROUPS):
            if tab_idx < len(self._multi_charts):
                title = auto_title(
                    self.building_model.name, self._last_t_start,
                    self.building_model.t_duration, self.building_model.dt, tab_name,
                )
                self._multi_charts[tab_idx].set_overall_title(title)

        self._plot_results_shown = results
        if not self._multi_charts:
            self._make_plot_panel()
            self._rebuild_plot_settings()
            self._plot_results_shown = results
        if hasattr(self, "canvas_stack"):
            self.canvas_stack.setCurrentIndex(1)
        if not stopped_early:
            self._update_simulation_progress(self._sim_total_steps, self._sim_total_steps)
        status_message = (
            f"Simulation stopped at {completed_steps} of {self._sim_total_steps} steps."
            if stopped_early
            else f"Simulation complete - {len(variables)} variables, {self._sim_total_steps} steps."
        )
        self.statusBar().showMessage(status_message, 6000)
        self._sim_thread = None
        if stopped_early:
            self._sim_resume_results = results
            self._sim_resume_step = completed_steps
            self._update_simulation_progress(completed_steps, self._sim_total_steps)
            self._set_simulation_resume_ui()
        else:
            self._sim_resume_results = None
            self._sim_resume_step = 0
            self._set_simulation_reset_ui()
        self._sim_stop_requested = False

    def _on_sim_error(self, message: str):
        self.statusBar().showMessage("Simulation failed", 4000)
        self.dialogue_manager.show_error("Simulation Error", message)
        self._sim_thread = None
        self._set_simulation_running_ui(False)
        self._sim_stop_requested = False
