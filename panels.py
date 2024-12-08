from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList,
                       UILayout,
                       Menu)
from bpy.utils import register_classes_factory
from .nestedListManager import BaseNLM_UL_List
from .common import get_active_group, get_active_layer

# -------------------------------------------------------------------
# Group Panels
# -------------------------------------------------------------------


class MAT_PT_PaintSystemGroups(Panel):
    bl_idname = 'MAT_PT_PaintSystemGroups'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System"
    bl_category = 'Paint System'

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system")

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material

        if not mat:
            layout.label(text="No active material")
            return

        if not hasattr(mat, "paint_system"):
            layout.operator("paint_system.add_paint_system")
            return
        # Add Group button and selector
        row = layout.row()
        row.scale_y = 2.0
        row.operator("paint_system.add_group",
                     text="Add New Group", icon='ADD')
        row = layout.row()
        row.operator(
            "paint_system.delete_group", text="Delete Current Group", icon='TRASH')

        if len(mat.paint_system.groups) > 0:
            layout.label(text="Active Group:")
            row = layout.row()
            row.scale_y = 1.5
            row.prop(mat.paint_system, "active_group", text="")

# -------------------------------------------------------------------
# Layers Panels
# -------------------------------------------------------------------


class MAT_PT_UL_PaintSystemLayerList(BaseNLM_UL_List):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        nested_list_manager = self.get_list_manager(context)
        flattened = nested_list_manager.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            # indent = " " * (level * 4)
            icon = 'FILE_FOLDER' if display_item.type == 'FOLDER' else 'IMAGE_DATA'
            row = layout.row(align=True)
            for _ in range(level):
                row.label(icon='BLANK1')
            row.prop(display_item, "name", text="", emboss=False, icon=icon)
            self.draw_custom_properties(row, display_item)

    def draw_custom_properties(self, layout, item):
        if hasattr(item, 'custom_int'):
            layout.label(text=str(item.order))

    def get_list_manager(self, context):
        return get_active_group(self, context)


class MAT_PT_PaintSystemLayers(Panel):
    bl_idname = 'MAT_PT_PaintSystemLayers'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layers"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemGroups'

    def draw(self, context):
        layout = self.layout
        manager = get_active_group(self, context)
        if not manager:
            layout.label(text="No active group")
            return

        flattened = manager.flatten_hierarchy()

        row = layout.row()
        row.template_list(
            "MAT_PT_UL_PaintSystemLayerList", "", manager, "items", manager, "active_index",
            rows=max(5, len(flattened))
        )

        col = row.column(align=True)
        col.operator("paint_system.add_item", text="",
                     icon='IMAGE_DATA').item_type = 'IMAGE'
        col.operator("paint_system.add_item", text="",
                     icon='NEWFOLDER').item_type = 'FOLDER'
        col.separator()
        col.operator("paint_system.remove_item", icon="TRASH", text="")
        col.separator()
        col.operator("paint_system.move_up", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")

        # Settings
        layout.separator()
        active_layer = get_active_layer(self, context)
        layout.label(text=f"{active_layer.name} Settings")
        row = layout.row()
        row.scale_y = 1.5
        row.prop(active_layer, "opacity", slider=True)
        row.prop(active_layer, "blend_mode", text="")

        # Create row for image selection
        row = layout.row(align=True)
        # Image property with dropdown
        row.template_ID(active_layer, "image",
                        new="image.new", open="image.open")
        # If an image is selected, show additional properties
        if active_layer.image:
            layout.template_image(active_layer, "image",
                                  active_layer.image.colorspace_settings)


classes = (
    MAT_PT_PaintSystemGroups,
    MAT_PT_UL_PaintSystemLayerList,
    MAT_PT_PaintSystemLayers,
)

register, unregister = register_classes_factory(classes)
