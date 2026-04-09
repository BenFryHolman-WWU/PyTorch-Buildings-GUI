import torch
from graphlib import TopologicalSorter

from neuromancer.hvac.building import BuildingSystem
from simulation.plotter import select_variables


class SimulationError(Exception):
    pass


class SimulationRunner:
    """Runs a building HVAC simulation from the current canvas state."""

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


    def run(self, building_model):
        """Execute the simulation. Args: building_model (BuildingModel). Returns: tuple (results, variables, t_start). Raises: SimulationError."""
        component_items = [ci for ci in building_model.componentItems if ci is not None]
        if not component_items:
            raise SimulationError("No components on the canvas. Add components before running.")
        t_start = int(building_model.t_start)
        t_duration = int(building_model.t_duration)
        dt = int(building_model.dt)
        t_rng = range(t_start, t_start + t_duration, dt)
        nodes = self._topological_sort(building_model)
        data = self._build_input_data(component_items, t_rng)
        system = BuildingSystem(nodes, name = "GUIBuildingSystem")
        results = system.simulate(data = data)
        variables = select_variables(results)
        return results, variables, t_start


    def _topological_sort(self, building_model):
        """Return nodes in topological order based on GUI connections. Args: building_model (BuildingModel). Returns: list."""
        graph = {node: set() for node in building_model.nodes}
        for connection in building_model.connections:
            graph[connection.dstNode].add(connection.srcNode)
        return list(TopologicalSorter(graph).static_order())


    def _build_input_data(self, component_items, t_rng):
        """Pre-compute time-series tensors for all external inputs. Args: component_items (list), t_rng (range). Returns: dict."""
        data = {}
        data["t"] = torch.tensor(list(t_rng), dtype = torch.float32).reshape(1, -1, 1)
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
                        [fn(t, batch_size = 1) for t in t_rng], dim = 1
                    )
                    data[data_key] = series
                except Exception as exc:
                    raise SimulationError(
                        f"Failed to build input '{data_key}' from {component_type}: {exc}"
                    ) from exc
        return data
