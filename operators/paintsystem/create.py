import bpy
from bpy.types import Context
from .base_layer import PaintSystemLayer
# from ..graph import NodeTreeBuilder

def add_layer(layer_type: str, layer_name: str = "New Layer") -> PaintSystemLayer:
    """Add a new layer of the specified type."""
    
    if not layer_name:
        raise ValueError("Layer name cannot be empty")
    if not isinstance(layer_name, str):
        raise TypeError("layer_name must be a string")
    
    bpy.context.scene.paint_system.layers.add()
    new_layer = bpy.context.scene.paint_system.layers[-1]
    new_layer.type = layer_type
    new_layer.layer_name = layer_name
    return new_layer

def create_image_layer(img: bpy.types.Image, layer_name="New Image Layer"):
    """Create a new image layer."""
    if not img:
        raise ValueError("Image cannot be None")
    if not isinstance(img, bpy.types.Image):
        raise TypeError("img must be of type bpy.types.Image")
    
    # Create a new ImageLayer instance
    new_layer = add_layer('IMAGE', layer_name)
    new_layer.layer_name = layer_name
    new_layer.image = img
    return new_layer