import bpy
from bpy.types import Context
from .data import Channel, GlobalLayer, Layer
from uuid import uuid4
# from ..graph import NodeTreeBuilder

def add_global_layer(layer_type: str, layer_name: str = "New Layer") -> GlobalLayer:
    """Add a new layer of the specified type."""
    
    if not layer_name:
        raise ValueError("Layer name cannot be empty")
    if not isinstance(layer_name, str):
        raise TypeError("layer_name must be a string")
    
    node_tree = bpy.data.node_groups.new(name=layer_name, type='ShaderNodeTree')
    node_tree.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="OUTPUT", socket_type="NodeSocketFloat")
    node_tree.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    if layer_type == "FOLDER":
        node_tree.interface.new_socket("Over Color", in_out="OUTPUT", socket_type="NodeSocketColor")
        node_tree.interface.new_socket("Over Alpha", in_out="OUTPUT", socket_type="NodeSocketFloat")
        node_tree.interface.new_socket("Over Color", in_out="INPUT", socket_type="NodeSocketColor")
        node_tree.interface.new_socket("Over Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    global_layer = bpy.context.scene.ps_scene_data.layers.add()
    global_layer.id = str(uuid4())
    global_layer.type = layer_type
    global_layer.node_tree = node_tree
    # Ensure we set the declared property name
    global_layer.name = layer_name
    return global_layer

def add_global_layer_to_channel(channel: Channel, global_layer: GlobalLayer) -> Layer:
    layer = channel.add_item(global_layer.name, "ITEM" if global_layer.type != 'FOLDER' else "FOLDER")
    layer.ref_layer_id = global_layer.id
    return layer

def create_image_layer(channel: Channel, img: bpy.types.Image, layer_name="New Image Layer"):
    """Create a new image layer."""
    if not img:
        raise ValueError("Image cannot be None")
    if not isinstance(img, bpy.types.Image):
        raise TypeError("img must be of type bpy.types.Image")
    
    # Create a new ImageLayer instance
    global_layer = add_global_layer("IMAGE", layer_name)
    global_layer.image = img
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_folder_layer(channel: Channel, layer_name: str = "New Folder") -> Layer:
    """Create a new folder layer (dummy)."""
    global_layer = add_global_layer("FOLDER", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_solid_color_layer(channel: Channel, layer_name: str = "New Solid Color Layer") -> Layer:
    """Create a new solid color layer (dummy)."""
    global_layer = add_global_layer("SOLID_COLOR", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_attribute_layer(channel: Channel, layer_name: str = "New Attribute Layer") -> Layer:
    """Create a new attribute layer (dummy)."""
    global_layer = add_global_layer("ATTRIBUTE", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_adjustment_layer(channel: Channel, layer_name: str = "New Adjustment Layer") -> Layer:
    """Create a new adjustment layer (dummy)."""
    global_layer = add_global_layer("ADJUSTMENT", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_shader_layer(channel: Channel, layer_name: str = "New Shader Layer") -> Layer:
    """Create a new shader layer (dummy)."""
    global_layer = add_global_layer("SHADER", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_node_group_layer(channel: Channel, layer_name: str = "New Node Group Layer") -> Layer:
    """Create a new node group layer (dummy)."""
    global_layer = add_global_layer("NODE_GROUP", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer


def create_gradient_layer(channel: Channel, layer_name: str = "New Gradient Layer") -> Layer:
    """Create a new gradient layer (dummy)."""
    global_layer = add_global_layer("GRADIENT", layer_name)
    layer = add_global_layer_to_channel(channel, global_layer)
    return layer