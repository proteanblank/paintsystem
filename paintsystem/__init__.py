import bpy
from bpy.utils import register_submodule_factory
from .data import PaintSystemGlobalData, MaterialData, get_global_layer

submodules = [
    "data",
    "handlers",
    # "graph",
    # "nested_list_manager",
    # "move",
]

register, unregister = register_submodule_factory(__name__, submodules)