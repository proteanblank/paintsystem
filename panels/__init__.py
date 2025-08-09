import bpy
from bpy.utils import register_submodule_factory

submodules = [
    # "custom_icons",
    "main_panels",
    "preferences_panels",
    "channels_panels",
    "layers_panels",
]

register, unregister = register_submodule_factory(__name__, submodules)