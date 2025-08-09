import bpy
from ..paintsystem.data import PSContextMixin, get_global_layer
from ..custom_icons import get_icon
from ..paintsystem.common import get_preferences

def scale_content(context, layout, scale_x=1.2, scale_y=1.2):
    """Scale the content of the panel."""
    prefs = get_preferences(context)
    if prefs.use_compact_design:
        layout.scale_x = scale_x
        layout.scale_y = scale_y
    return layout