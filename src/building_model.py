import torch
from neuromancer.hvac.building import BuildingSystem
from node_connection import Connection
from graphlib import TopologicalSorter
from component_item import ComponentItem

class BuildingModel():
    def __init__(self, name):
        self.name = name
        self.nodes = []
        self.connections = []

    def set_time_param_in_seconds(self, t_start, t_duration, dt):
        self.t_start = t_start
        self.t_duration = t_duration
        self.dt = dt

    def add_node(self, node):
        self.nodes.append(node)
    
    def remove_node(self, node):
        # removes any connections associated with that node
        for connection in self.connections:
            if (connection.srcNode == node) or (connection.dstNode == node):
                self.remove_connection(connection)
        # removes the node itself
        self.nodes.remove(node)

    def add_connection(self, connection):
        # Will connect srcNode output to some part of dstNode input. To be implemented
        self.connections.append(connection)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def run_simulation(self):
        # Will use self.nodes and self.connections to run the simulation
        print("Running simulation")
        print("Current nodes in model:", [node.name for node in self.nodes])

        # ----------------------Simulation code-----------------------

        # Use the list of connections to sort the list of nodes into a topological order
        graph_data = {}
        # In graph_data, each node will have the set of nodes that it depends on, initialize each set to empty
        for node in self.nodes:
            graph_data[node] = set()

        # The connections will tell us which nodes every node depends on
        for connection in self.connections:
            graph_data[connection.dstNode].add(connection.srcNode)

        # Sorts the nodes in the appropriate order to be the input for the simulation
        # TopologicalSorter returns a TopologicalSorter object so we must convert it back to a list
        top_sort = TopologicalSorter(graph_data)
        sorted_nodes = list(top_sort.static_order())

        # This print will print the same as unsorted because connections themselves have not been implemennted into the GUI
        print("Sorted nodes in model:", [node.name for node in sorted_nodes])

        t_rng = range(self.t_start, self.t_start + self.t_duration, self.dt)

        data = {}
        data["t"] = torch.tensor(t_rng).reshape(1, -1, 1)

        # Weather and occupancy disturbance variables
        # shape is (batch, steps, features)

        system = BuildingSystem(sorted_nodes)