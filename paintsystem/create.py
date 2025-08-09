import bpy
from bpy.types import Context
from .data import Channel, GlobalLayer, Layer
from uuid import uuid4
# from ..graph import NodeTreeBuilder

def add_global_layer(channel: Channel, layer_type: str, layer_name: str = "New Layer") -> GlobalLayer:
    """Add a new layer of the specified type."""
    
    if not layer_name:
        raise ValueError("Layer name cannot be empty")
    if not isinstance(layer_name, str):
        raise TypeError("layer_name must be a string")
    
    global_layer = bpy.context.scene.ps_scene_data.layers.add()
    global_layer.id = str(uuid4())
    global_layer.type = layer_type
    global_layer.layer_name = layer_name
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
    global_layer = add_global_layer(channel, "IMAGE", layer_name)
    global_layer.image = img
    layer = add_global_layer_to_channel(channel, global_layer)
    # return new_layer