import bpy
from bpy.types import Context


icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys(
)


def icon_parser(icon: str, default="NONE") -> str:
    if icon in icons:
        return icon
    return default


def is_online():
    return not bpy.app.version >= (4, 2, 0) or bpy.app.online_access


def is_newer_than(major, minor=0, patch=0):
    return bpy.app.version >= (major, minor, patch)


STRING_CACHE = {}


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()


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
