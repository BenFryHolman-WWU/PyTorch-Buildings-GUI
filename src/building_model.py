import torch
from neuromancer.hvac.building import BuildingSystem
from graphlib import TopologicalSorter
from set_time_dialog import SetTimeDialog

class BuildingModel():
    def __init__(self, name):
        self.name = name
        self.componentItems = []
        self.connections = []

        # base values
        self.n_zones = 2
        self.t_start = 5*60*60  # 6 AM in seconds
        self.t_duration = 86400  # 24 hrs in seconds
        self.dt = 300  # 5 minutes

    def set_time_param_in_seconds(self):
        dlg = SetTimeDialog(self)
        dlg.exec()

    def update_nzones(self, value):
        self.n_zones = value
        for componentItem in self.componensItems:
            componentItem.component.n_zones = value

    def add_componentItem(self, componentItem):
        self.componentItems.append(componentItem)

    def remove_componentItem(self, componentItem):
        self.componentItems.remove(componentItem)
        for connection in self.connections:
            if (connection.srcNode == componentItem.node) or (connection.dstNode == componentItem.node):
                self.remove_connection(connection)

    def add_connection(self, connection):
        # Will connect srcNode output to some part of dstNode input. To be implemented
        self.connections.append(connection)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def run_simulation(self):
        # Will use self.nodes and self.connections to run the simulation
        # To test list of nodes here, set test_simulation to True
        test_simulation = False
        print("Running simulation")

        # ----------------------Simulation code-----------------------
        print("Current nodes in model:", [componentItem.node.name for componentItem in self.componentItems])
        # Use the list of connections to sort the list of nodes into a topological order
        graph_data = {}
        # In graph_data, each node will have the set of nodes that it depends on, initialize each set to empty
        for componentItem in self.componentItems:
            graph_data[componentItem.node] = set()

        # The connections will tell us which nodes every node depends on
        for connection in self.connections:
            graph_data[connection.dstNode].add(connection.srcNode)

        # Sorts the nodes in the appropriate order to be the input for the simulation
        # TopologicalSorter returns a TopologicalSorter object so we must convert it back to a list
        top_sort = TopologicalSorter(graph_data)
        sorted_nodes = list(top_sort.static_order())

        # This print will print the same as unsorted because connections themselves have not been implemennted into the GUI
        print("Topological node sort:", [node.name for node in sorted_nodes])
        if (test_simulation):
            t_rng = range(self.t_start, self.t_start + self.t_duration, self.dt)

            data = {}
            # Weather and occupancy disturbance variables
            # shape is (batch, steps, features)
            data["t"] = torch.tensor(t_rng).reshape(1, -1, 1)

            system = BuildingSystem(sorted_nodes)
            results = system.simulate(data=data)
            print(f"Simulation complete!")
            print(f"Results contain {len(results)} variables")
            print(f"Time steps: {results['t'].shape[1]}")
            print(f"Variables: {list(results.keys())}")