import bpy
from bpy.utils import register_submodule_factory

submodules = [
    "paintsystem_panels"
]

register, unregister = register_submodule_factory(__name__, submodules)