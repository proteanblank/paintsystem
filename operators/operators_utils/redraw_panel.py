from bpy.types import Context

def redraw_panel(context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()