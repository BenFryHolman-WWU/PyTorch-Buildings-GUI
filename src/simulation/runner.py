"""Simulation execution and background-thread orchestration."""

import threading

import torch
from graphlib import CycleError, TopologicalSorter
from PyQt6.QtCore import QThread, pyqtSignal

from neuromancer.hvac.building import BuildingSystem
from simulation.input_data import load_input_csv
from simulation.plotter import select_variables


class SimulationError(Exception):
    pass


class SimulationRunner:

    _HVAC_EXECUTION_PRIORITY = {
        "solar": 0,
        "rtu": 1,
        "vav": 2,
        "envelope": 3,
    }

    _EXTERNAL_INPUT_KEYS = {
        "SolarGains": {
            "T_outdoor":      "T_outdoor",
            "weather_factor": "weather_factor",
        },
        "Envelope": {
            "Q_internal": "Q_internal",
        },
        "RTU": {
            "T_supply_setpoint":       "T_supply_setpoint",
            "supply_airflow_setpoint": "supply_airflow_setpoint",
        },
        "VAVBox": {
            "T_setpoint": "T_setpoint",
        },
    }

    _STANDALONE_INPUT_KEYS = {
        "rtu": {
            "T_return_zones": "T_return_zones",
            "return_airflow_zones": "return_airflow_zones",
        },
        "vav": {
            "T_zone": "T_zone",
            "T_supply_upstream": "T_supply_upstream",
            "P_duct": "P_duct",
        },
        "envelope": {
            "Q_solar": "Q_solar",
            "Q_hvac": "Q_hvac",
        },
    }


    def run(
        self,
        building_model,
        step_callback=None,
        stop_event=None,
        callback_interval=10,
        resume_from_step=0,
        initial_results=None,
    ):
        """
        Summary: Run.
        Args: building_model, initial_results
        Returns: Return the computed value.
        """
        component_items = [ci for ci in building_model.componentItems if ci is not None]
        if not component_items:
            raise SimulationError("No components on the canvas. Add components before running.")
        t_start = int(building_model.t_start)
        t_duration = int(building_model.t_duration)
        dt = int(building_model.dt)
        if t_duration <= 0:
            raise SimulationError("Simulation duration must be greater than 0 seconds.")
        if dt <= 0:
            raise SimulationError("Simulation time step must be greater than 0 seconds.")
        if dt > t_duration:
            raise SimulationError("Simulation time step cannot be longer than the duration.")
        full_times = list(range(t_start, t_start + t_duration, dt))
        total_steps = len(full_times)
        resume_from_step = max(0, min(int(resume_from_step or 0), max(total_steps - 1, 0)))
        t_rng = full_times[resume_from_step:]
        nodes = self._topological_sort(building_model)
        self._validate_nodes(nodes)
        self._apply_connection_input_maps(building_model)
        data = self._build_input_data(component_items, t_rng, building_model)
        output_keys = self._node_output_keys(nodes)
        seeded_keys = self._seed_resume_data(data, initial_results, output_keys) if resume_from_step else set()
        system = BuildingSystem(nodes, name="GUIBuildingSystem")
        if resume_from_step:
            def _resume_callback(step, _total, partial_data):
                if step_callback is None:
                    return
                merged = self._merge_resume_results(initial_results, partial_data, seeded_keys)
                step_callback(resume_from_step + step, total_steps, merged)

            results = system.forward(
                data,
                warmup=0,
                step_callback=_resume_callback,
                stop_event=stop_event,
                callback_interval=callback_interval,
            )
            results = self._merge_resume_results(initial_results, results, seeded_keys)
        else:
            results = system.simulate(
                data=data,
                step_callback=step_callback,
                stop_event=stop_event,
                callback_interval=callback_interval,
            )
        variables = select_variables(results)
        return results, variables, t_start


    def _node_output_keys(self, nodes):
        output_keys = set()
        for node in nodes:
            output_keys.update(getattr(node, "output_keys", []))
        return output_keys


    def _seed_resume_data(self, data, initial_results, output_keys):
        """
        Summary: Seed resume data.
        Args: data, initial_results, output_keys
        Returns: Return the computed value.
        """
        if not isinstance(initial_results, dict):
            return set()
        seeded_keys = set()
        for key in output_keys:
            value = initial_results.get(key)
            if not hasattr(value, "shape") or len(value.shape) < 2 or value.shape[1] <= 0:
                continue
            data[key] = value[:, -1:, ...].detach().clone()
            seeded_keys.add(key)
        return seeded_keys


    def _merge_resume_results(self, initial_results, resumed_results, seeded_keys):
        """
        Summary: Merge resume results.
        Args: initial_results, resumed_results
        Returns: Return the computed value.
        """
        if not isinstance(initial_results, dict):
            return resumed_results
        merged = dict(initial_results)
        for key, value in resumed_results.items():
            if key in seeded_keys and key in initial_results:
                prior = initial_results[key]
                if hasattr(prior, "shape") and hasattr(value, "shape") and len(prior.shape) >= 2 and len(value.shape) >= 2:
                    merged[key] = torch.cat([prior, value[:, 1:, ...]], dim=1)
                    continue
            if key not in merged:
                merged[key] = value
        return merged


    def _topological_sort(self, building_model):
        """
        Summary: Topological sort.
        Args: building_model
        Returns: Return the computed value.
        """
        graph = {node: set() for node in building_model.nodes}
        for connection in building_model.connections:
            if connection.srcNode.name != "control":
                graph[connection.dstNode].add(connection.srcNode)
        try:
            nodes = list(TopologicalSorter(graph).static_order())
        except CycleError:
            nodes = list(building_model.nodes)
            return self._sort_by_hvac_priority(nodes)
        if all(getattr(node, "name", None) in self._HVAC_EXECUTION_PRIORITY for node in nodes):
            return self._sort_by_hvac_priority(nodes)
        return nodes

    def _sort_by_hvac_priority(self, nodes):
        return sorted(
            nodes,
            key=lambda node: (
                self._HVAC_EXECUTION_PRIORITY.get(getattr(node, "name", ""), len(self._HVAC_EXECUTION_PRIORITY)),
                getattr(node, "name", ""),
            ),
        )


    def _validate_nodes(self, nodes):
        names = [getattr(node, "name", "") for node in nodes]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            duplicate_text = ", ".join(duplicates)
            raise SimulationError(
                "Simulation requires one component of each type. "
                f"Duplicate component node name(s): {duplicate_text}."
            )


    def _apply_connection_input_maps(self, building_model):
        """
        Summary: Apply connection input maps.
        Args: building_model
        """
        for node in building_model.nodes:
            standalone = self._STANDALONE_INPUT_KEYS.get(node.name, {})
            for keyword, data_key in standalone.items():
                current_keys = [key for key, mapped_keyword in node.input_map.items() if mapped_keyword == keyword]
                for current_key in current_keys:
                    node.input_map.pop(current_key, None)
                node.input_map[data_key] = keyword
        for connection in building_model.connections:
            for src_key, dst_keyword in getattr(connection, "mappings", []):
                current_keys = [
                    key for key, mapped_keyword in connection.dstNode.input_map.items()
                    if mapped_keyword == dst_keyword
                ]
                for current_key in current_keys:
                    connection.dstNode.input_map.pop(current_key, None)
                connection.dstNode.input_map[src_key] = dst_keyword
        for node in building_model.nodes:
            node.input_keys = list(node.input_map)

    def _apply_time_step_input(self, building_model):
        """Explicit opt-in hook for models that map dt into component inputs."""
        for node in building_model.nodes:
            node.input_map["dt"] = "dt"
            node.input_keys = list(node.input_map)

    def _detect_control_policy(self, building_model):
        """
        Summary: Detect control policy.
        Args: building_model
        Returns: Return the computed value.
        """
        if building_model is None:
            return None
        policy = None
        for connection in building_model.connections:
            if connection.srcNode.name == "control" and connection.dstNode.name == "rtu":
                policy = connection.srcNode.component
                break
        if policy is not None:
            return policy
        if (
            getattr(building_model, "use_control_policy_override", False)
            and all(hasattr(building_model, attr) for attr in ("tu_T_supply_setpoint", "rtu_supply_airflow_setpoint"))
        ):
            return building_model
        return None

    def _build_input_data(self, component_items, t_rng, building_model=None):
        """
        Summary: Build input data.
        Args: component_items, building_model
        Returns: Return the computed value.
        """
        data = {}
        data["t"] = torch.tensor(list(t_rng), dtype=torch.float32).reshape(1, -1, 1)
        dt = float(getattr(building_model, "dt", 1.0)) if building_model is not None else 1.0
        data["dt"] = torch.full_like(data["t"], dt)
        policy = self._detect_control_policy(building_model) if building_model is not None else None
        for ci in component_items:
            component = ci.component
            component_type = type(component).__name__
            key_map = self._EXTERNAL_INPUT_KEYS.get(component_type, {})
            if not key_map:
                continue
            try:
                input_fns = component.input_functions
            except Exception:
                continue
            for data_key, fn_key in key_map.items():
                if data_key in data:
                    continue
                if fn_key not in input_fns:
                    continue
                fn = input_fns[fn_key]
                try:
                    series = torch.stack(
                        [fn(t, batch_size=1) for t in t_rng], dim=1
                    )
                    data[data_key] = series
                except Exception as exc:
                    raise SimulationError(
                        f"Failed to build input '{data_key}' from {component_type}: {exc}"
                    ) from exc
        input_data_path = getattr(building_model, "input_data_path", None) if building_model is not None else None
        if input_data_path:
            try:
                csv_data, summary = load_input_csv(
                    input_data_path,
                    t_rng,
                    getattr(building_model, "n_zones", 1),
                    getattr(building_model, "t_start", 0),
                )
                data.update(csv_data)
                building_model.input_data_summary = summary
            except Exception as exc:
                raise SimulationError(f"Failed to load input data CSV: {exc}") from exc
        if policy:
            if hasattr(policy, "tu_T_supply_setpoint"):
                value = policy.tu_T_supply_setpoint
                data["T_supply_setpoint"] = torch.tensor([value for _ in t_rng], dtype=torch.float32).reshape(1, -1, 1)
            if hasattr(policy, "rtu_supply_airflow_setpoint"):
                value = policy.rtu_supply_airflow_setpoint
                data["supply_airflow_setpoint"] = torch.tensor([value for _ in t_rng], dtype=torch.float32).reshape(1, -1, 1)
        return data


class SimulationThread(QThread):

    step_update = pyqtSignal(int, int)
    finished_ok = pyqtSignal(object, list, float)
    error = pyqtSignal(str)

    def __init__(
        self,
        building_model,
        callback_interval=10,
        parent=None,
        resume_from_step=0,
        initial_results=None,
    ):
        """
        Summary: Init.
        Args: building_model, initial_results
        """
        super().__init__(parent)
        self.building_model = building_model
        self.callback_interval = callback_interval
        self.resume_from_step = int(resume_from_step or 0)
        self.initial_results = initial_results
        self._stop_event = threading.Event()
        self.partial_results = None
        self.was_stopped = False

    def stop(self):
        self.was_stopped = True
        self._stop_event.set()

    def run(self):
        """Summary: Run."""
        runner = SimulationRunner()

        def _callback(step, total, data):
            self.partial_results = data
            self.step_update.emit(step, total)

        try:
            results, variables, t_start = runner.run(
                self.building_model,
                step_callback=_callback,
                stop_event=self._stop_event,
                callback_interval=self.callback_interval,
                resume_from_step=self.resume_from_step,
                initial_results=self.initial_results,
            )
            self.partial_results = results
            self.was_stopped = self.was_stopped or self._stop_event.is_set()
            self.finished_ok.emit(results, variables, float(t_start))
        except SimulationError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            self.error.emit(f"Unexpected error:\n{exc}")
