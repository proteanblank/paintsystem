from bpy.types import Context


def get_active_group(self, context: Context):
    active_object = context.active_object
    if not active_object:
        return None
    mat = active_object.active_material
    if not mat or not hasattr(mat, "paint_system"):
        return None
    active_group_idx = int(mat.paint_system.active_group)
    return mat.paint_system.groups[active_group_idx]


def get_active_layer(self, context: Context):
    active_group = get_active_group(self, context)
    if not active_group:
        return None
    active_layer_idx = active_group.active_index
    flattened = active_group.flatten_hierarchy()
    active_layer = flattened[active_group.active_index][0]
    return active_layer


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()
