import torch
from neuromancer.hvac.building import BuildingSystem
from graphlib import TopologicalSorter


class BuildingModel:
    def __init__(self, name):
        self.name = name
        self.componentItems = []
        self.nodes = []
        self.connections = []
        self.n_zones = 2
        self.t_start = 5 * 60 * 60
        self.t_duration = 86400
        self.dt = 300

    def set_time_param_in_seconds(self, t_start = None, t_duration = None, dt = None):
        if t_start is not None:
            self.t_start = float(t_start)
        if t_duration is not None:
            self.t_duration = float(t_duration)
        if dt is not None:
            self.dt = float(dt)

    def _resize_zone_value(self, value, n_zones):
        if isinstance(value, torch.Tensor):
            if value.ndim == 1:
                return torch.tensor(self._resize_zone_value(value.tolist(), n_zones), dtype = value.dtype)
            if value.ndim == 2:
                return torch.tensor(self._resize_zone_value(value.tolist(), n_zones), dtype = value.dtype)
            return value
        if isinstance(value, list):
            if value and isinstance(value[0], list):
                resized_rows = value[:n_zones]
                resized_rows = [row[:n_zones] for row in resized_rows]
                while len(resized_rows) < n_zones:
                    resized_rows.append([])
                for idx, row in enumerate(resized_rows):
                    if len(row) < n_zones:
                        resized_rows[idx] = row + [0.0] * (n_zones - len(row))
                return resized_rows
            resized = value[:n_zones]
            if len(resized) < n_zones:
                resized = resized + [0.0] * (n_zones - len(resized))
            return resized
        return value

    def update_n_zones(self, n_zones):
        zone_dependent_attr = {
            "Envelope": ["R_env", "C_env", "adjacency"],
            "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max"],
            "SolarGains": ["window_orientation"],
        }
        self.n_zones = int(n_zones)
        for component_item in self.componentItems:
            if component_item is None or component_item.component is None:
                continue
            component = component_item.component
            component.n_zones = self.n_zones
            component_name = component.__class__.__name__
            for attr in zone_dependent_attr.get(component_name, []):
                if not hasattr(component, attr):
                    continue
                setattr(component, attr, self._resize_zone_value(getattr(component, attr), self.n_zones))

    def _infer_zone_count_from_value(self, value):
        if isinstance(value, torch.Tensor):
            if value.ndim == 1:
                return int(value.shape[0])
            if value.ndim == 2:
                return int(max(value.shape[0], value.shape[1]))
            return None
        if isinstance(value, list):
            if value and isinstance(value[0], list):
                row_count = len(value)
                col_count = max((len(row) for row in value), default = 0)
                return max(row_count, col_count)
            return len(value)
        return None

    def infer_n_zones_from_components(self):
        zone_dependent_attr = {
            "Envelope": ["R_env", "C_env", "adjacency"],
            "VAVBox": ["airflow_min", "airflow_max", "control_gain", "Q_reheat_max"],
            "SolarGains": ["window_orientation"],
        }
        inferred = 1
        for component_item in self.componentItems:
            if component_item is None or component_item.component is None:
                continue
            component = component_item.component
            component_name = component.__class__.__name__
            for attr in zone_dependent_attr.get(component_name, []):
                if not hasattr(component, attr):
                    continue
                zone_count = self._infer_zone_count_from_value(getattr(component, attr))
                if zone_count is not None:
                    inferred = max(inferred, int(zone_count))
        return inferred

    def add_node(self, node):
        self.nodes.append(node)
    def add_componentItem(self, component_item):
        self.componentItems.append(component_item)
        if component_item.node not in self.nodes:
            self.add_node(component_item.node)
    def remove_node(self, node):
        for connection in list(self.connections):
            if connection.srcNode == node or connection.dstNode == node:
                self.remove_connection(connection)
        if node in self.nodes:
            self.nodes.remove(node)
    def remove_componentItem(self, component_item):
        if component_item in self.componentItems:
            self.componentItems.remove(component_item)
        self.remove_node(component_item.node)
    def add_connection(self, connection):
        self.connections.append(connection)
    def remove_connection(self, connection):
        self.connections.remove(connection)

    def run_simulation(self):
        print("Running simulation")
        print("Current nodes in model:", [node.name for node in self.nodes])
        graph_data = {}
        for node in self.nodes:
            graph_data[node] = set()
        for connection in self.connections:
            graph_data[connection.dstNode].add(connection.srcNode)
        top_sort = TopologicalSorter(graph_data)
        sorted_nodes = list(top_sort.static_order())
        print("Sorted nodes in model:", [node.name for node in sorted_nodes])
        t_rng = range(self.t_start, self.t_start + self.t_duration, self.dt)
        data = {}
        data["t"] = torch.tensor(t_rng).reshape(1, -1, 1)
        system = BuildingSystem(sorted_nodes)
        results = system.simulate(data = data)
        print("Simulation complete!")
        print(f"Results contain {len(results)} variables")
        print(f"Time steps: {results['t'].shape[1]}")
        print(f"Variables: {list(results.keys())}")
