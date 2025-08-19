import bpy

def get_unified_settings(context: bpy.types.Context, unified_name=None):
    ups = context.tool_settings.unified_paint_settings
    tool_settings = context.tool_settings.image_paint
    brush = tool_settings.brush
    prop_owner = brush
    if unified_name and getattr(ups, unified_name):
        prop_owner = ups
    return prop_owner