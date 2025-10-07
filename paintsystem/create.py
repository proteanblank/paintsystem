import bpy
from uuid import uuid4
from .data import Channel, GlobalLayer, Layer

def add_global_layer(layer_type: str, layer_name: str = "New Layer") -> GlobalLayer:
    """Add a new layer of the specified type."""
    
    if not layer_name:
        raise ValueError("Layer name cannot be empty")
    if not isinstance(layer_name, str):
        raise TypeError("layer_name must be a string")
    
    node_tree = bpy.data.node_groups.new(name=f"PS_Layer ({layer_name})", type='ShaderNodeTree')
    node_tree.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="OUTPUT", socket_type="NodeSocketFloat")
    node_tree.interface.new_socket("Clip", in_out="INPUT", socket_type="NodeSocketBool")
    node_tree.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    if layer_type == "FOLDER":
        node_tree.interface.new_socket("Over Color", in_out="INPUT", socket_type="NodeSocketColor")
        node_tree.interface.new_socket("Over Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    global_layer = bpy.context.scene.ps_scene_data.layers.add()
    global_layer.name = str(uuid4())
    global_layer.type = layer_type
    global_layer.node_tree = node_tree
    return global_layer