import bpy
from bpy.types import Node, NodeTree, NodeSocket

def traverse_connected_nodes(node: Node, input: bool = True, output: bool = False) -> set[Node]:
    nodes = set()
    if input:
        for input_socket in node.inputs:
            for link in input_socket.links:
                nodes.add(link.from_node)
                nodes.update(traverse_connected_nodes(link.from_node))
    if output:
        for output_socket in node.outputs:
            for link in output_socket.links:
                nodes.add(link.to_node)
                nodes.update(traverse_connected_nodes(link.to_node))
    return nodes

def get_material_output(mat_node_tree: NodeTree) -> Node:
    node = None
    for node in mat_node_tree.nodes:
        if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output:
            return node
    # Try to find Group Output node instead
    for node in mat_node_tree.nodes:
        if node.bl_idname == 'NodeGroupOutput':
            return node
    if node is None:
        node = mat_node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        node.is_active_output = True
    return node

def transfer_connection(node_tree: NodeTree, source_socket: NodeSocket, target_socket: NodeSocket):
    if source_socket.is_linked:
        original_socket = source_socket.links[0].from_socket
        node_tree.links.new(original_socket, target_socket)
        return True
    else:
        # Copy the value from source socket to target socket
        target_socket.default_value = source_socket.default_value
    return False

def find_nodes(node_tree: NodeTree, properties: dict) -> list[Node]:
    node = get_material_output(node_tree)
    nodes = traverse_connected_nodes(node)
    return [node for node in nodes if all(hasattr(node, prop) and getattr(node, prop) == value for prop, value in properties.items())]

def find_node(node_tree: NodeTree, properties: dict) -> Node | None:
    nodes = find_nodes(node_tree, properties)
    return nodes[0] if nodes else None