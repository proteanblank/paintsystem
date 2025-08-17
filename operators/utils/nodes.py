import bpy
from bpy.types import Node, NodeTree, NodeSocket

def find_node(node_list: list[Node], properties: dict) -> Node | None:
    for node in node_list:
        print(f"Find node {node.bl_idname}")
        has_all_properties_and_values = all(
            hasattr(node, prop) and getattr(node, prop) == value
            for prop, value in properties.items()
        )
        if has_all_properties_and_values:
            return node
        for input_socket in node.inputs:
            nodes = [link.from_node for link in input_socket.links]
            if len(nodes) > 0:
                return find_node(nodes, properties)
    return None

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
    if node is None:
        node = mat_node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        node.is_active_output = True
    return node

def transfer_connection(node_tree: NodeTree, source_socket: NodeSocket, target_socket: NodeSocket):
    if source_socket.is_linked:
        original_socket = source_socket.links[0].from_socket
        node_tree.links.new(original_socket, target_socket)