import bpy
from bpy.utils import register_submodule_factory
from .data import PaintSystemGlobalData, MaterialData, parse_context, get_global_layer
from .common import get_preferences

submodules = [
    "data",
    "graph",
    # "move",
]

_register, _unregister = register_submodule_factory(__name__, submodules)

def register():
    _register()
    bpy.types.Scene.ps_scene_data = bpy.props.PointerProperty(
        type=PaintSystemGlobalData,
        name="Paint System Data",
        description="Data for the Paint System"
    )
    bpy.types.Material.ps_mat_data = bpy.props.PointerProperty(
        type=MaterialData,
        name="Paint System Material data",
        description="Material Data for the Paint System"
    )

def unregister():
    """Unregister the Paint System module."""
    del bpy.types.Material.ps_mat_data
    del bpy.types.Scene.ps_scene_data
    _unregister()