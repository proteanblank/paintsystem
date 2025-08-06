import bpy
from bpy.props import StringProperty, CollectionProperty
from bpy.types import PropertyGroup
from bpy.utils import register_submodule_factory
from .settings import PaintSystemData

submodules = [
    "base_layer",
    "settings",
]

_register, _unregister = register_submodule_factory(__name__, submodules)

def register():
    _register()
    bpy.types.Scene.paint_system = bpy.props.PointerProperty(
        type=PaintSystemData,
        name="Paint System Data",
        description="Data for the Paint System"
    )

def unregister():
    del bpy.types.Scene.paint_system
    _unregister()