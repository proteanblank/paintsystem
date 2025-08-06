import bpy
from bpy.props import PointerProperty, CollectionProperty
from bpy.types import PropertyGroup
from .base_layer import PaintSystemLayer
from bpy.utils import register_classes_factory

class PaintSystemData(PropertyGroup):
    """Custom data for the Paint System"""
    layers: CollectionProperty(
        type=PaintSystemLayer,
        name="Paint System Layers",
        description="Collection of layers in the Paint System"
    )

classes = (PaintSystemData,)

register, unregister = register_classes_factory(classes)