import bpy
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
from .nested_list_manager import BaseNLM_UL_List
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
        return context.active_object

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        mat = ob.active_material

        if not mat:
            layout.label(text="No active material")
            return
        layout.template_ID(ob, "active_material", new="material.new")

        if not hasattr(mat, "paint_system"):
            layout.operator("paint_system.add_paint_system")
            return
        # Add Group button and selector
        row = layout.row()
        row.scale_y = 2.0
        row.operator("paint_system.add_group",
                     text="Add New Group", icon='ADD')

        if len(mat.paint_system.groups) > 0:
            layout.label(text="Active Group:")
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.prop(mat.paint_system, "active_group", text="")
            row.menu("MAT_MT_PaintSystemGroup", text="", icon='COLLAPSEMENU')


class MAT_MT_PaintSystemGroup(Menu):
    bl_label = "Group Menu"
    bl_idname = "MAT_MT_PaintSystemGroup"

    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.rename_group",
                        text="Rename Group", icon='GREASEPENCIL')
        layout.operator("paint_system.delete_group",
                        text="Delete Group", icon='TRASH')

# -------------------------------------------------------------------
# Layers Panels
# -------------------------------------------------------------------


class MAT_PT_UL_PaintSystemLayerList(BaseNLM_UL_List):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        active_group = get_active_group(self, context)
        flattened = active_group.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            row = layout.row(align=True)
            for _ in range(level):
                row.label(icon='BLANK1')
            if display_item.type == 'IMAGE':
                if display_item.image.preview:
                    row.label(icon_value=display_item.image.preview.icon_id)
                else:
                    display_item.image.asset_generate_preview()
                    row.label(icon='BLANK1')
            else:
                row.label(icon='FILE_FOLDER')
            row.prop(display_item, "name", text="", emboss=False)
            # row.label(text=f"Order: {display_item.order}")
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
        active_group = get_active_group(self, context)
        if not active_group:
            layout.label(text="No active group")
            return

        mat = context.active_object.active_material
        contains_mat_setup = any([node.type == 'GROUP' and node.node_tree ==
                                 active_group.node_tree for node in mat.node_tree.nodes])

        flattened = active_group.flatten_hierarchy()

        # Toggle paint mode (switch between object and texture paint mode)
        current_mode = context.mode
        row = layout.row()
        row.scale_y = 1.5
        if contains_mat_setup:
            row.operator("paint_system.toggle_paint_mode",
                         text="Toggle Paint Mode", icon="BRUSHES_ALL")
        else:
            row.alert = True
            row.operator("paint_system.create_template_setup",
                         text="Setup Material")
            row.alert = False

        has_dirty_images = any(
            [layer.image and layer.image.is_dirty for layer, _ in flattened if layer.type == 'IMAGE'])
        layout.operator("wm.save_mainfile",
                        text="Save Images*" if has_dirty_images else "Save Images")

        row = layout.row()
        row.scale_y = 1.5

        row.template_list(
            "MAT_PT_UL_PaintSystemLayerList", "", active_group, "items", active_group, "active_index",
            rows=max(5, len(flattened))
        )

        col = row.column(align=True)
        col.menu("MAT_MT_PaintSystemAddImage", icon='IMAGE', text="")
        col.operator("paint_system.add_folder", icon='NEWFOLDER', text="")
        col.separator()
        col.operator("paint_system.delete_item", icon="TRASH", text="")
        col.separator()
        col.operator("paint_system.move_up", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")

        # Settings
        active_layer = get_active_layer(self, context)

        if not active_layer:
            return

        # Loop over every nodes in the active layer node tree
        layer_node = None
        for node in active_group.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree and node.node_tree.name == active_layer.node_tree.name:
                layer_node = node
        # layer_node = active_group.node_tree.nodes.get(
        #     active_layer.node_tree.name)

        layout.label(text=f"{active_layer.name} Settings")

        color_mix_node = None
        for node in active_layer.node_tree.nodes:
            if node.type == 'MIX' and node.data_type == 'RGBA':
                color_mix_node = node

        row = layout.row()
        row.scale_y = 1.5
        # Let user set opacity and blend mode:
        row.prop(color_mix_node, "blend_type", text="Blend")

        row = layout.row()
        row.scale_y = 1.5
        row.prop(layer_node.inputs[1], "default_value",
                 text="Clip", icon="CLIPUV_HLT", icon_only=True)
        row.prop(layer_node.inputs[0], "default_value",
                 text="Opacity")

        if active_layer.type == 'IMAGE':

            # # Create row for image selection
            # row = layout.row(align=True)
            # # Image property with dropdown
            # row.template_ID(active_layer, "image",
            #                 new="image.new", open="image.open")
            # print(dir(active_layer.image))
            image = active_layer.image
            # layout.prop(active_layer, "interpolation", text="Interpolation")
        # If an image is selected, show additional properties
        # if active_layer.image:
        #     layout.template_image(active_layer, "image",
        #                           active_layer.image.colorspace_settings)

# -------------------------------------------------------------------
# Images Panels
# -------------------------------------------------------------------


class MAT_MT_PaintSystemAddImage(Menu):
    bl_label = "Add Image"
    bl_idname = "MAT_MT_PaintSystemAddImage"

    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.new_image",
                        text="New Image", icon="IMAGE")
        layout.operator("paint_system.open_image",
                        text="Open Image", icon="FILE")


# -------------------------------------------------------------------
# For testing
# -------------------------------------------------------------------

class MAT_PT_PaintSystemTest(Panel):
    bl_idname = 'MAT_PT_PaintSystemTest'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System Test"
    bl_category = 'Paint System'

    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.test", text="Test")


classes = (
    MAT_PT_PaintSystemGroups,
    MAT_MT_PaintSystemGroup,
    MAT_PT_UL_PaintSystemLayerList,
    MAT_PT_PaintSystemLayers,
    MAT_MT_PaintSystemAddImage,
    # MAT_PT_PaintSystemTest,
)

register, unregister = register_classes_factory(classes)
