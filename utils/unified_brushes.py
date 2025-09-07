import bpy
from bl_ui.properties_paint_common import (
    UnifiedPaintPanel,
)

from ..utils.version import is_newer_than

def paint_settings(context):
    tool_settings = context.tool_settings

    mode = context.mode

    # 3D paint settings
    if mode == 'PAINT_TEXTURE':
        return tool_settings.image_paint
    # Grease Pencil settings
    elif mode == 'PAINT_GPENCIL':
        return tool_settings.gpencil_paint
    elif mode == 'SCULPT_GPENCIL':
        return tool_settings.gpencil_sculpt_paint
    elif mode == 'WEIGHT_GPENCIL':
        return tool_settings.gpencil_weight_paint
    elif mode == 'VERTEX_GPENCIL':
        return tool_settings.gpencil_vertex_paint
    elif mode == 'PAINT_GREASE_PENCIL':
        return tool_settings.gpencil_paint
    elif mode == 'SCULPT_CURVES':
        return tool_settings.curves_sculpt
    elif mode == 'PAINT_GREASE_PENCIL':
        return tool_settings.gpencil_paint
    elif mode == 'SCULPT_GREASE_PENCIL':
        return tool_settings.gpencil_sculpt_paint
    elif mode == 'WEIGHT_GREASE_PENCIL':
        return tool_settings.gpencil_weight_paint
    elif mode == 'VERTEX_GREASE_PENCIL':
        return tool_settings.gpencil_vertex_paint
    return None

def get_unified_settings(context: bpy.types.Context, unified_name: str):
    tool_settings = UnifiedPaintPanel.paint_settings(context)
    if is_newer_than(4,4):
        ups = tool_settings.unified_paint_settings
    else:
        ups = context.tool_settings.unified_paint_settings
    brush = tool_settings.brush
    prop_owner = brush
    if unified_name and getattr(ups, unified_name):
        prop_owner = ups
    return prop_owner