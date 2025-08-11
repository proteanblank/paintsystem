import bpy
from bpy.types import UIList, Menu, Context, Image, ImagePreview, Panel
from bpy.utils import register_classes_factory
from .common import PSContextMixin, scale_content, get_global_layer


def is_image_painted(image: Image | ImagePreview) -> bool:
    """Check if the image is painted

    Args:
        image (bpy.types.Image): The image to check

    Returns:
        bool: True if the image is painted, False otherwise
    """
    if not image:
        return False
    if isinstance(image, Image):
        return image.pixels and len(image.pixels) > 0 and any(image.pixels)
    elif isinstance(image, ImagePreview):
        # print("ImagePreview", image.image_pixels, image.image_size[0], image.image_size[1], len(list(image.icon_pixels)[3::4]))
        return any([pixel > 0 for pixel in list(image.image_pixels_float)[3::4]])
    return False


class MAT_PT_UL_PaintSystemLayerList(PSContextMixin, UIList):
    def draw_item(self, context: Context, layout, data, item, icon, active_data, active_property, index):
        # The UIList passes channel as 'data'
        active_channel = data
        flattened = active_channel.flatten_hierarchy()
        if index < len(flattened):
            global_item = get_global_layer(item)
            level = active_channel.get_item_level_from_id(global_item.id)
            row = layout.row(align=True)
            # Check if parent of the current item is enabled
            parent_item = active_channel.get_item_by_id(
                item.parent_id)
            if parent_item and not parent_item.enabled:
                row.enabled = False

            for _ in range(level):
                row.label(icon='BLANK1')
            match global_item.type:
                case 'IMAGE':
                    if not global_item.image.preview:
                        global_item.image.asset_generate_preview()
                    if global_item.image.preview and is_image_painted(global_item.image.preview):
                        row.label(
                            icon_value=global_item.image.preview.icon_id)
                    else:
                        row.label(icon='IMAGE_DATA')
                case 'FOLDER':
                    row.prop(global_item, "expanded", text="", icon='TRIA_DOWN' if global_item.expanded else 'TRIA_RIGHT', emboss=False)
                case 'SOLID_COLOR':
                    rgb_node = None
                    for node in global_item.node_tree.nodes:
                        if node.name == 'RGB':
                            rgb_node = node
                    if rgb_node:
                        row.prop(
                            rgb_node.outputs[0], "default_value", text="", icon='IMAGE_RGB_ALPHA')
                case 'ADJUSTMENT':
                    row.label(icon='SHADERFX')
                case 'SHADER':
                    row.label(icon='SHADING_RENDERED')
                case 'NODE_GROUP':
                    row.label(icon='NODETREE')
                case 'ATTRIBUTE':
                    row.label(icon='MESH_DATA')
                case 'GRADIENT':
                    row.label(icon='COLOR')
                case _:
                    row.label(icon='BLANK1')
            row.prop(global_item, "name", text="", emboss=False)

            if global_item.mask_image:
                row.prop(global_item, "enable_mask",
                         icon='MOD_MASK' if global_item.enable_mask else 'MATPLANE', text="", emboss=False)
            if item.clip:
                row.label(icon="SELECT_INTERSECT")
            if global_item.lock_layer:
                row.label(icon="VIEW_LOCKED")
            row.prop(item, "enabled", text="",
                     icon="HIDE_OFF" if item.enabled else "HIDE_ON", emboss=False)
            self.draw_custom_properties(row, global_item)

    def filter_items(self, context, data, propname):
        # This function gets the collection property (as the usual tuple (data, propname)), and must return two lists:
        # * The first one is for filtering, it must contain 32bit integers were self.bitflag_filter_item marks the
        #   matching item as filtered (i.e. to be shown). The upper 16 bits (including self.bitflag_filter_item) are
        #   reserved for internal use, the lower 16 bits are free for custom use. Here we use the first bit to mark
        #   VGROUP_EMPTY.
        # * The second one is for reordering, it must return a list containing the new indices of the items (which
        #   gives us a mapping org_idx -> new_idx).
        # Please note that the default UI_UL_list defines helper functions for common tasks (see its doc for more info).
        # If you do not make filtering and/or ordering, return empty list(s) (this will be more efficient than
        # returning full lists doing nothing!).
        layers = getattr(data, propname).values()
        helper_funcs = bpy.types.UI_UL_list
        flattened_layers = [v[0] for v in data.flatten_hierarchy()]

        # Default return values.
        flt_flags = []
        flt_neworder = []

        # Filtering by name
        flt_flags = [self.bitflag_filter_item] * len(layers)
        for idx, layer in enumerate(layers):
            flt_neworder.append(flattened_layers.index(layer))
            while layer.parent_id != -1:
                layer = data.get_item_by_id(layer.parent_id)
                if layer and not layer.expanded:
                    flt_flags[idx] &= ~self.bitflag_filter_item
                    break

        return flt_flags, flt_neworder

    def draw_custom_properties(self, layout, item):
        if hasattr(item, 'custom_int'):
            layout.label(text=str(item.order))

class MAT_PT_PaintSystemLayers(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_PaintSystemLayers'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layers"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'

    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps = PaintSystem(context)
    #     obj = ps.active_object

    #     if obj and obj.mode == 'TEXTURE_PAINT':
    #         layout.prop(ps.settings, "allow_image_overwrite",
    #                     text="Auto Select", icon='CHECKBOX_HLT' if ps.settings.allow_image_overwrite else 'CHECKBOX_DEHLT')

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    def draw_header_preset(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        flattened = active_channel.flatten_hierarchy()
        has_dirty_images = any(
            [layer.image and layer.image.is_dirty for layer, _ in flattened if layer.type == 'IMAGE'])
        if has_dirty_images:
            row = layout.row(align=True)
            row.operator("wm.save_mainfile",
                         text="Click to Save!", icon="FUND")

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="IMAGE_RGB")

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        obj = ps_ctx.active_object
        active_channel = ps_ctx.active_channel
        active_layer = ps_ctx.active_global_layer
        mat = ps_ctx.active_material
        # contains_mat_setup = any([node.type == 'GROUP' and node.node_tree ==
        #                           active_channel.node_tree for node in mat.node_tree.nodes])

        flattened = active_channel.flatten_hierarchy()

        # Toggle paint mode (switch between object and texture paint mode)
        current_mode = context.mode
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.5
        # if contains_mat_setup:
        row.operator("paint_system.toggle_paint_mode",
                        text="Toggle Paint Mode", depress=current_mode == 'PAINT_TEXTURE')
        # else:
        #     row.alert = True
        #     row.operator("paint_system.create_template_setup",
        #                  text="Setup Material", icon="ERROR")
        #     row.alert = False
        row.operator("wm.save_mainfile",
                     text="", icon="FILE_TICK")
        # Baking and Exporting
        row = col.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.5

        # TODO: Bake and Export options
        # if not active_channel.bake_image:
        #     row.menu("MAT_MT_PaintSystemMergeAndExport",
        #              icon='EXPORT', text="Merge and Bake")

        if active_channel.bake_image:
            row = box.row(align=True)
            scale_content(context, row)
            row.prop(active_channel, "use_bake_image",
                     text="Use Merged Image", icon='CHECKBOX_HLT' if active_channel.use_bake_image else 'CHECKBOX_DEHLT')
            row.operator("paint_system.export_baked_image",
                         icon='EXPORT', text="")
            col = row.column(align=True)
            col.menu("MAT_MT_PaintSystemMergeOptimize",
                     icon='COLLAPSEMENU', text="")
            if active_channel.use_bake_image:
                box.label(
                    text="Merged Image Used. It's faster!", icon='SOLO_ON')
                return

        # if active_layer.mask_image:
        #     row = box.row(align=True)
        #     if not ps.preferences.use_compact_design:
        #         row.scale_x = 1.2
        #         row.scale_y = 1.2
        #     row.prop(active_layer, "edit_mask", text="Editing Mask" if active_layer.edit_mask else "Click to Edit Mask", icon='MOD_MASK')

        if active_layer and active_layer.edit_mask and obj.mode == 'TEXTURE_PAINT':
            mask_box = box.box()
            split = mask_box.split(factor=0.6)
            split.alert = True
            split.label(text="Editing Mask!", icon="INFO")
            split.prop(active_layer, "edit_mask", text="Disable", icon='X', emboss=False)
        
        row = box.row()
        scale_content(context, row, scale_x=1, scale_y=1.5)
        row.template_list(
            "MAT_PT_UL_PaintSystemLayerList", "", active_channel, "layers", active_channel, "active_index",
            rows=max(5, len(flattened))
        )

        col = row.column(align=True)
        # col.menu("MAT_MT_PaintSystemAddLayer", icon='IMAGE_DATA', text="")
        # col.operator("paint_system.new_folder", icon='NEWFOLDER', text="")
        col.separator()
        col.operator("paint_system.delete_item", icon="TRASH", text="")
        col.separator()
        col.operator("paint_system.move_up", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")

        active_layer = ps_ctx.active_layer
        if not active_layer:
            return

classes = (
    MAT_PT_UL_PaintSystemLayerList,
    MAT_PT_PaintSystemLayers,
)

register, unregister = register_classes_factory(classes)