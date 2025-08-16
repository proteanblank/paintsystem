import bpy
from bpy.utils import register_submodule_factory

submodules = [
    # "custom_icons",
    "preferences_panels",
    "main_panels",
    "channels_panels",
    "layers_panels",
]

register, unregister = register_submodule_factory(__name__, submodules)