import bpy
from bpy.types import UIList, Menu, Context, Image, ImagePreview, Panel, NodeTree
from bpy.utils import register_classes_factory
from .common import PSContextMixin, scale_content, get_global_layer, icon_parser, get_icon, get_icon_from_channel
from ..utils.nodes import find_node, traverse_connected_nodes, get_material_output
from ..paintsystem.data import is_valid_ps_nodetree, GlobalLayer, ADJUSTMENT_TYPE_ENUM, GRADIENT_TYPE_ENUM, is_global_layer_linked


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


def is_basic_setup(node_tree: NodeTree) -> bool:
    material_output = get_material_output(node_tree)
    nodes = traverse_connected_nodes(material_output)
    is_basic_setup = True
    # Only first 3 nodes
    for check in ('ShaderNodeGroup', 'ShaderNodeMixShader', 'ShaderNodeBsdfTransparent'):
        if not any(node.bl_idname == check for node in nodes):
            is_basic_setup = False
            break
    return is_basic_setup




class MAT_PT_UL_LayerList(PSContextMixin, UIList):
    def draw_item(self, context: Context, layout, data, item, icon, active_data, active_property, index):
        # The UIList passes channel as 'data'
        active_channel = data
        flattened = active_channel.flatten_hierarchy()
        if index < len(flattened):
            global_item = get_global_layer(item)
            level = active_channel.get_item_level_from_id(item.id)
            main_row = layout.row()
            # Check if parent of the current item is enabled
            parent_item = active_channel.get_item_by_id(
                item.parent_id)
            if parent_item and not parent_item.enabled:
                main_row.enabled = False

            row = main_row.row(align=True)
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
                        row.label(icon_value=get_icon('image'))
                case 'FOLDER':
                    row.prop(global_item, "is_expanded", text="", icon_only=True, icon_value=get_icon('folder_open') if global_item.is_expanded else get_icon('folder'), emboss=False)
                case 'SOLID_COLOR':
                    rgb_node = global_item.find_node("rgb")
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
            
            row = main_row.row(align=True)
            row.prop(item, "name", text="", emboss=False)
            # if global_item.mask_image:
            #     row.prop(global_item, "enable_mask",
            #              icon='MOD_MASK' if global_item.enable_mask else 'MATPLANE', text="", emboss=False)
            if global_item.is_clip:
                row.label(icon="SELECT_INTERSECT")
            if global_item.lock_layer:
                row.label(icon="VIEW_LOCKED")
            if is_global_layer_linked(global_item):
                row.label(icon="LINKED")
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
                global_layer = get_global_layer(layer)
                if global_layer and not global_layer.is_expanded:
                    flt_flags[idx] &= ~self.bitflag_filter_item
                    break

        return flt_flags, flt_neworder

    def draw_custom_properties(self, layout, item):
        if hasattr(item, 'custom_int'):
            layout.label(text=str(item.order))

class MAT_PT_Layers(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_Layers'
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
        if ps_ctx.active_object.mode != 'TEXTURE_PAINT':
            return
        if ps_ctx.active_channel:
            layout.popover(
                panel="MAT_PT_ChannelsSelect",
                text=ps_ctx.active_channel.name if ps_ctx.active_channel else "No Channel",
                icon_value=get_icon_from_channel(ps_ctx.active_channel)
            )

    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps_ctx = self.ensure_context(context)
    #     active_channel = ps_ctx.active_channel
    #     global_layers = [get_global_layer(layer) for layer, _ in active_channel.flatten_hierarchy()]
    #     has_dirty_images = any(
    #         [layer.image and layer.image.is_dirty for layer in global_layers if layer.type == 'IMAGE'])
    #     if has_dirty_images:
    #         row = layout.row(align=True)
    #         row.operator("wm.save_mainfile",
    #                      text="Click to Save!", icon="FUND")

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
        group_node = find_node(mat.node_tree, {'bl_idname': 'ShaderNodeGroup', 'node_tree': ps_ctx.active_group.node_tree})
        if not group_node:
            warning_box = box.box()
            warning_box.alert = True
            col = warning_box.column(align=True)
            col.label(text="Paint System not connected", icon='ERROR')
            col.label(text="to material output!", icon='BLANK1')
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.7
        row.scale_x = 1.7
        # if contains_mat_setup:
        row.operator("paint_system.toggle_paint_mode",
                        text="Toggle Paint Mode", depress=current_mode == 'PAINT_TEXTURE', icon_value=get_icon('paintbrush'))
        # else:
        #     row.alert = True
        #     row.operator("paint_system.create_template_setup",
        #                  text="Setup Material", icon="ERROR")
        #     row.alert = False
        if not is_basic_setup(mat.node_tree) or len(ps_ctx.active_group.channels) > 1:
            row.operator("paint_system.preview_active_channel",
                            text="", depress=ps_ctx.ps_mat_data.preview_channel, icon_value=get_icon_from_channel(ps_ctx.active_channel) if ps_ctx.ps_mat_data.preview_channel else get_icon('channel'))
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

        # if active_layer and active_layer.edit_mask and obj.mode == 'TEXTURE_PAINT':
        #     mask_box = box.box()
        #     split = mask_box.split(factor=0.6)
        #     split.alert = True
        #     split.label(text="Editing Mask!", icon="INFO")
        #     split.prop(active_layer, "edit_mask", text="Disable", icon='X', emboss=False)
        
        row = box.row()
        scale_content(context, row, scale_x=1, scale_y=1.5)
        row.template_list(
            "MAT_PT_UL_LayerList", "", active_channel, "layers", active_channel, "active_index",
            rows=max(5, len(flattened))
        )

        col = row.column(align=True)
        col.scale_x = 1.2
        col.menu("MAT_MT_AddLayer", icon_value=get_icon('layer_add'), text="")
        col.menu("MAT_MT_LayerMenu",
                     text="", icon='COLLAPSEMENU')
        col.separator()
        # col.operator("paint_system.delete_item", icon="TRASH", text="")
        # col.separator()
        col.operator("paint_system.move_up", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")

        active_layer = ps_ctx.active_layer
        if not active_layer:
            return
        
class MAT_PT_LayerSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_LayerSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layer Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_Layers'
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        active_layer = ps_ctx.active_layer
        return active_layer is not None

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="SETTINGS")

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        active_layer = ps_ctx.active_layer
        global_layer = get_global_layer(active_layer)
        if not active_layer:
            return
            # Settings
        box = layout.box()
        row = box.row(align=True)
        if global_layer.image:
            if not global_layer.external_image:
                row.operator("paint_system.quick_edit", text="Edit Externally")
            else:
                row.operator("paint_system.project_apply",
                             text="Apply")
            row.menu("MAT_MT_ImageMenu",
                     text="", icon='COLLAPSEMENU')

        # if ps.preferences.show_tooltips:
        #     row.menu("MAT_MT_LayersSettingsTooltips", text='', icon='QUESTION')

        # Let user set opacity and blend mode:
        color_mix_node = global_layer.mix_node
        match global_layer.type:
            case 'IMAGE':
                col = box.column(align=True)
                row = col.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="",
                         icon="SELECT_INTERSECT")
                row.prop(active_layer, "lock_alpha",
                         text="", icon='TEXTURE')
                row.prop(global_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = col.row()
                scale_content(context, row, scale_x=1.2, scale_y=1.5)
                row.prop(global_layer.pre_mix_node.inputs[0], "default_value",
                         text="Opacity", slider=True)

            case 'ADJUSTMENT':
                row = box.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="",
                         icon="SELECT_INTERSECT")
                row.prop(global_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(global_layer.pre_mix_node.inputs[0], "default_value",
                         text="Opacity", slider=True)
                adjustment_node = global_layer.find_node("adjustment")
                if adjustment_node:
                    col = box.column()
                    col.label(text="Adjustment Settings:", icon='SHADERFX')
                    col.template_node_inputs(adjustment_node)
            case 'NODE_GROUP':
                row = box.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="Clip Layer",
                         icon="SELECT_INTERSECT")
                if not is_valid_ps_nodetree(global_layer.node_tree):
                    col = box.column(align=True)
                    col.label(text="Invalid Node Tree!", icon='ERROR')
                    col.label(text="Please check the input/output sockets.")
                    return
                node_group = global_layer.node_group
                inputs = [i for i in node_group.inputs if not i.is_linked and i.name not in (
                    'Color', 'Alpha')]
                if not inputs:
                    return
                box.label(text="Node Group Settings:", icon='NODETREE')
                for socket in inputs:
                    col = box.column()
                    col.prop(socket, "default_value",
                             text=socket.name)
                    
            case 'ATTRIBUTE':
                col = box.column(align=True)
                row = col.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="",
                         icon="SELECT_INTERSECT")
                row.prop(global_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = col.row()
                scale_content(context, row, 1, 1.5)
                row.prop(global_layer.pre_mix_node.inputs[0], "default_value",
                         text="Opacity", slider=True)
                attribute_node = global_layer.find_node("attribute")
                if attribute_node:
                    box.label(text="Attribute Settings:", icon='MESH_DATA')
                    box.template_node_inputs(attribute_node)
            case 'GRADIENT':
                col = box.column(align=True)
                row = col.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="",
                         icon="SELECT_INTERSECT")
                row.prop(global_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = col.row()
                row.scale_y = 1.2
                scale_content(context, row, 1, 1.5)
                row.prop(global_layer.pre_mix_node.inputs[0], "default_value",
                         text="Opacity", slider=True)
                # color_ramp_node = global_layer.find_node("color_ramp")
                #             "label": "Gradient Color Ramp"})
                # box.template_color_ramp(
                #     color_ramp_node, "color_ramp")
                # box.prop(layer_node_group.inputs['Use Steps'], "default_value",
                #          text="Use Steps")
                # box.prop(layer_node_group.inputs['Steps'], "default_value", text="Steps")
            case 'GRADIENT':
                gradient_node = global_layer.find_node("gradient")
                if gradient_node:
                    col = box.column()
                    col.label(text="Gradient Settings:", icon='SHADERFX')
                    col.template_node_inputs(gradient_node)
            case _:
                col = box.column(align=True)
                row = col.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.5, 1.5)
                row.prop(global_layer.post_mix_node.inputs["Clip"], "default_value", text="",
                         icon="SELECT_INTERSECT")
                row.prop(global_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = col.row()
                row.enabled = not global_layer.lock_layer
                row.scale_y = 1.2
                scale_content(context, row, 1, 1.5)
                row.prop(global_layer.pre_mix_node.inputs[0], "default_value",
                         text="Opacity", slider=True)

                if global_layer.type == 'SOLID_COLOR':
                    rgb_node = global_layer.find_node("rgb")
                    col = box.column()
                    col.enabled = not global_layer.lock_layer
                    if rgb_node:
                        col.prop(rgb_node.outputs[0], "default_value", text="Color",
                                icon='IMAGE_RGB_ALPHA')

                if global_layer.type == 'ADJUSTMENT':
                    adjustment_node = global_layer.find_node("adjustment")
                    if adjustment_node:
                        col.label(text="Adjustment Settings:", icon='SHADERFX')
                        col.template_node_inputs(adjustment_node)

        # if active_layer.type == 'SHADER':
        #     box = layout.box()
        #     row = box.row()
        #     row.label(text="Shader Settings:", icon='SHADING_RENDERED')
        #     col = box.column()
        #     match active_layer.sub_type:
        #         case "_PS_Toon_Shader":
        #             layer_node_group = ps.get_active_layer_node_group()
        #             use_color_ramp = layer_node_group.inputs['Use Color Ramp']
        #             row = col.row()
        #             row.label(text="Colors:", icon='COLOR')
        #             row.prop(
        #                 use_color_ramp, "default_value", text="Color Ramp", icon='CHECKBOX_HLT' if use_color_ramp.default_value else 'CHECKBOX_DEHLT')
        #             box = col.box()
        #             colors_col = box.column()
        #             row = colors_col.row()
        #             row.label(text="Shadow:")
        #             if use_color_ramp.default_value:
        #                 color_ramp_node = ps.find_node(active_layer.node_tree, {
        #                     "label": "Shading Color Ramp"})
        #                 if color_ramp_node:
        #                     colors_col.template_node_inputs(color_ramp_node)
        #             else:

        #                 colors_col.prop(layer_node_group.inputs['Shadow Color'], "default_value",
        #                                 text="", icon='IMAGE_RGB_ALPHA')
        #                 colors_col.separator()
        #                 row = colors_col.row()
        #                 row.label(text="Light:")
        #                 use_clamp_value = layer_node_group.inputs['Clamp Value']
        #                 intensity_multiplier = layer_node_group.inputs['Intensity Multiplier']
        #                 light_col_influence = layer_node_group.inputs['Light Color Influence']
        #                 row.prop(
        #                     use_clamp_value, "default_value", text="Clamp Value", icon='CHECKBOX_HLT' if use_clamp_value.default_value else 'CHECKBOX_DEHLT')
        #                 colors_col.prop(layer_node_group.inputs['Light Color'], "default_value",
        #                                 text="", icon='IMAGE_RGB_ALPHA')
        #                 colors_col.prop(intensity_multiplier, "default_value",
        #                                 text="Intensity Multiplier")
        #                 colors_col.prop(light_col_influence, "default_value",
        #                                 text="Light Color Influence")
        #             use_cell_shaded = layer_node_group.inputs['Cel-Shaded']
        #             col.prop(
        #                 use_cell_shaded, "default_value", text="Cel-Shaded")
        #             col = col.column()
        #             col.enabled = use_cell_shaded.default_value
        #             col.prop(
        #                 layer_node_group.inputs['Steps'], "default_value", text="Cel-Shaded Steps")
        #         case "_PS_Light":
        #             layer_node_group = ps.get_active_layer_node_group()
        #             row = col.row()
        #             row.label(text="Colors:", icon='COLOR')
        #             box = col.box()
        #             colors_col = box.column()
        #             row = colors_col.row()
        #             row.label(text="Light:")
        #             use_clamp_value = layer_node_group.inputs['Clamp Value']
        #             intensity_multiplier = layer_node_group.inputs['Intensity Multiplier']
        #             light_col_influence = layer_node_group.inputs['Light Color Influence']
        #             row.prop(
        #                 use_clamp_value, "default_value", text="Clamp Value", icon='CHECKBOX_HLT' if use_clamp_value.default_value else 'CHECKBOX_DEHLT')
        #             colors_col.prop(layer_node_group.inputs['Light Color'], "default_value",
        #                             text="", icon='IMAGE_RGB_ALPHA')
        #             colors_col.prop(intensity_multiplier, "default_value",
        #                             text="Intensity Multiplier")
        #             colors_col.prop(light_col_influence, "default_value",
        #                             text="Light Color Influence")
        #             use_cell_shaded = layer_node_group.inputs['Cel-Shaded']
        #             col.prop(
        #                 use_cell_shaded, "default_value", text="Cel-Shaded")
        #             col = col.column()
        #             col.enabled = use_cell_shaded.default_value
        #             col.prop(
        #                 layer_node_group.inputs['Steps'], "default_value", text="Cel-Shaded Steps")
        #         case _:
        #             layer_node_group = ps.get_active_layer_node_group()
        #             inputs = []
        #             for input in layer_node_group.inputs:
        #                 if not input.is_linked:
        #                     inputs.append(input)
        #             for input in inputs:
        #                 node_input_prop(col, layer_node_group,
        #                                 input.name, text=input.name)


class MAT_MT_LayerMenu(PSContextMixin, Menu):
    bl_label = "Layer Menu"
    bl_idname = "MAT_MT_LayerMenu"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.copy_layer", text="Copy Layer", icon="COPYDOWN")
        layout.operator("paint_system.copy_all_layers", text="Copy All Layers", icon="COPYDOWN")
        layout.operator("paint_system.paste_layer", text="Paste Layer(s)", icon="PASTEDOWN").linked = False
        layout.operator("paint_system.paste_layer", text="Paste Linked Layer(s)", icon="LINKED").linked = True
        layout.separator()
        layout.operator("paint_system.delete_item", text="Delete Layer", icon="TRASH")

class MAT_MT_AddLayerMenu(Menu):
    bl_label = "Add Layer"
    bl_idname = "MAT_MT_AddLayer"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()
        # col.label(text="--- IMAGE ---")
        col.operator("paint_system.new_folder_layer", icon_value=get_icon('folder'), text="Folder")
        col.separator()
        col.operator("paint_system.new_image_layer",
                     text="New Image Layer", icon_value=get_icon('image_plus')).image_add_type = "NEW"
        col.operator("paint_system.new_image_layer",
                     text="Import Image Layer", icon_value=get_icon('import')).image_add_type = "IMPORT"
        col.operator("paint_system.new_image_layer",
                     text="Use Existing Image Layer", icon_value=get_icon('image')).image_add_type = "EXISTING"
        # col.operator("paint_system.open_image",
        #              text="Open External Image")
        # col.operator("paint_system.open_existing_image",
        #              text="Use Existing Image")
        col.separator()
        # col.label(text="--- COLOR ---")
        col.operator("paint_system.new_solid_color_layer", text="Solid Color",
                     icon=icon_parser('STRIP_COLOR_03', "SEQUENCE_COLOR_03"))
        col.operator("paint_system.new_attribute_layer",
                     text="Attribute Color", icon='MESH_DATA')
        col.separator()
        col.label(text="--- GRADIENT ---")
        for idx, (node_type, name, description) in enumerate(GRADIENT_TYPE_ENUM):
            col.operator("paint_system.new_gradient_layer",
                         text=name, icon='COLOR' if idx == 0 else 'NONE').gradient_type = node_type

        # col.separator()
        # col.label(text="--- SHADER ---")
        # for idx, (node_type, name, description) in enumerate(SHADER_ENUM):
        #     col.operator("paint_system.new_shader_layer",
        #                  text=name, icon='SHADING_RENDERED' if idx == 0 else 'NONE').shader_type = node_type

        col = row.column()
        # col.label(text="--- ADJUSTMENT ---")
        for idx, (node_type, name, description) in enumerate(ADJUSTMENT_TYPE_ENUM):
            col.operator("paint_system.new_adjustment_layer",
                         text=name, icon='SHADERFX' if idx == 0 else 'NONE').adjustment_type = node_type
        col.separator()
        col.label(text="--- CUSTOM ---")
        col.operator("paint_system.new_node_group_layer",
                     text="Custom Node Tree", icon='NODETREE')

classes = (
    MAT_PT_UL_LayerList,
    MAT_MT_AddLayerMenu,
    MAT_MT_LayerMenu,
    MAT_PT_Layers,
    MAT_PT_LayerSettings,
)

register, unregister = register_classes_factory(classes)