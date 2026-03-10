from neuromancer.hvac.building_components import RTU, VAVBox, Envelope, SolarGains
from neuromancer.hvac.building import BuildingNode
from node_connection import Connection

class BuildingModel():
    def __init__(self, name):
        self.name = name
        self.nodes = []
        self.connections = []

    def addNode(self, node):
        self.nodes.append(node)
    
    def removeNode(self, node):
        # removes any connections associated with that node
        for connection in self.connections:
            if (connection.srcNode == node) or (connection.dstNode == node):
                self.removeConnection(connection)
        # removes the node itself
        self.nodes.remove(node)

    def addConnection(self, connection):
        # Will connect srcNode output to some part of dstNode input. To be implemented
        self.connections.append(connection)

    def removeConnection(self, connection):
        self.connections.remove(connection)

    def runSimulation(self):
        # Will use self.nodes and self.connections to run the simulation
        print("Running simulation")
        print("Current nodes in model:", [node.name for node in self.nodes])
