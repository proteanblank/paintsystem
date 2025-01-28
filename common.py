import bpy
from bpy.types import Context


def is_online():
    return not bpy.app.version >= (4, 2, 0) or bpy.app.online_access


STRING_CACHE = {}


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()


def map_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))

# Fixes UnicodeDecodeError bug


def intern_enum_items(items):
    def intern_string(s):
        if not isinstance(s, str):
            return s
        global STRING_CACHE
        if s not in STRING_CACHE:
            STRING_CACHE[s] = s
        return STRING_CACHE[s]
    return [tuple(intern_string(s) for s in item) for item in items]


def get_object_uv_maps(self, context: Context):
    items = [
        (uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers
    ]
    return intern_enum_items(items)
