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
    global_layer.uid = str(uuid4())
    global_layer.type = layer_type
    global_layer.node_tree = node_tree
    # Ensure we set the declared property name
    # global_layer.name = layer_name
    return global_layer

def add_global_layer_to_channel(channel: Channel, global_layer: GlobalLayer, layer_name: str) -> Layer:
    parent_id, insert_order = channel.get_insertion_data()
    # Adjust existing items' order
    channel.adjust_sibling_orders(parent_id, insert_order)
    layer = channel.add_item(
            global_layer.name,
            "ITEM" if global_layer.type != 'FOLDER' else "FOLDER",
            parent_id=parent_id,
            order=insert_order
        )
    layer.ref_layer_id = global_layer.uid
    layer.name = layer_name
    # Update active index
    new_id = layer.id
    if new_id != -1:
        for i, item in enumerate(channel.layers):
            if item.id == new_id:
                channel.active_index = i
                break
    return layer

# def create_image_layer(channel: Channel, global_layer: GlobalLayer, img: bpy.types.Image):
#     """Create a new image layer."""
#     if not img:
#         raise ValueError("Image cannot be None")
#     if not isinstance(img, bpy.types.Image):
#         raise TypeError("img must be of type bpy.types.Image")
    
#     # Create a new ImageLayer instance
#     global_layer.image = img
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_folder_layer(channel: Channel, global_layer: GlobalLayer, layer_name: str = "New Folder") -> Layer:
#     """Create a new folder layer (dummy)."""
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_solid_color_layer(channel: Channel, global_layer: GlobalLayer) -> Layer:
#     """Create a new solid color layer (dummy)."""
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_attribute_layer(channel: Channel, global_layer: GlobalLayer, ) -> Layer:
#     """Create a new attribute layer (dummy)."""
#     global_layer = add_global_layer("ATTRIBUTE", layer_name)
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_adjustment_layer(channel: Channel, global_layer: GlobalLayer, ) -> Layer:
#     """Create a new adjustment layer (dummy)."""
#     global_layer = add_global_layer("ADJUSTMENT", layer_name)
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_shader_layer(channel: Channel, global_layer: GlobalLayer, ) -> Layer:
#     """Create a new shader layer (dummy)."""
#     global_layer = add_global_layer("SHADER", layer_name)
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_node_group_layer(channel: Channel, global_layer: GlobalLayer) -> Layer:
#     """Create a new node group layer (dummy)."""
#     global_layer = add_global_layer("NODE_GROUP", layer_name)
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer


# def create_gradient_layer(channel: Channel, global_layer: GlobalLayer, ) -> Layer:
#     """Create a new gradient layer (dummy)."""
#     global_layer = add_global_layer("GRADIENT", layer_name)
#     layer = add_global_layer_to_channel(channel, global_layer)
#     return layer