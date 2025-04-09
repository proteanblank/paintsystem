import bpy
from bpy.types import NodeTree, Node, NodeSocket

class NodeTreeBuilder:
    def __init__(self, node_tree: NodeTree):
        """
        Initialize the NodeTreeBuilder with a given node tree.
        :param node_tree: The node tree to be built.
        """
        if not isinstance(node_tree, NodeTree):
            raise TypeError("node_tree must be of type NodeTree")
        self.node_tree = node_tree

    def create_node(self, type: str, attrs: dict = None) -> Node:
        """
        Create a node of the specified type with optional attributes.
        """
        node = self.node_tree.nodes.new(type)
        if attrs:
            for key, value in attrs.items():
                setattr(node, key, value)
        return node.name
    
    def create_link(self, from_node_name: str, from_socket: str, to_node_name: str, to_socket: str):
        """
        Create a link between two nodes.
        """
        from_node = self.node_tree.nodes.get(from_node_name)
        if not from_node:
            raise ValueError("From node not found")
        
        to_node = self.node_tree.nodes.get(to_node_name)
        if not to_node:
            raise ValueError("To node not found")

        from_socket = from_node.outputs.get(from_socket)
        to_socket = to_node.inputs.get(to_socket)

        if not from_socket or not to_socket:
            raise ValueError("One or both sockets not found")

        self.node_tree.links.new(to_socket, from_socket)
        
    def delete_node(self, node_name: str):
        """
        Delete a node by its name.
        """
        node = self.node_tree.nodes.get(node_name)
        if not node:
            raise ValueError("Node not found")
        self.node_tree.nodes.remove(node)