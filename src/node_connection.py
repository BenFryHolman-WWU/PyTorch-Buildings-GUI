class Connection():
    # Initializes with a source node, the output property, the destination node, and the destination nodes input property
    # This class just stores the connection details and acts as a new type
    def __init__(self, srcNode, srcOutput, dstNode, dstInput):
        self.srcNode = srcNode
        self.srcOutput = srcOutput
        self.dstNode = dstNode
        self.dstInput = dstInput