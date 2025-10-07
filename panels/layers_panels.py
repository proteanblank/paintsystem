import bpy
from bpy.types import UIList, Menu, Context, Image, ImagePreview, Panel, NodeTree
from bpy.utils import register_classes_factory

from ..utils.version import is_newer_than
from .common import (
    PSContextMixin,
    scale_content,
    get_global_layer,
    icon_parser,
    get_icon,
    get_icon_from_channel,
    check_group_multiuser
)

from ..utils.nodes import find_node, traverse_connected_nodes, get_material_output
from ..paintsystem.data import (
    GlobalLayer,
    ADJUSTMENT_TYPE_ENUM, 
    GRADIENT_TYPE_ENUM, 
    is_global_layer_linked,
    sort_actions
)

if is_newer_than(4,3):
    from bl_ui.properties_data_grease_pencil import (
        GreasePencil_LayerMaskPanel,
        DATA_PT_grease_pencil_onion_skinning,
    )


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


def draw_global_layer_icon(global_item: GlobalLayer, layout: bpy.types.UILayout):
    match global_item.type:
        case 'IMAGE':
            if not global_item.image.preview:
                global_item.image.asset_generate_preview()
            if global_item.image.preview and is_image_painted(global_item.image.preview):
                layout.label(
                    icon_value=global_item.image.preview.icon_id)
            else:
                layout.label(icon_value=get_icon('image'))
        case 'FOLDER':
            layout.prop(global_item, "is_expanded", text="", icon_only=True, icon_value=get_icon(
                'folder_open') if global_item.is_expanded else get_icon('folder'), emboss=False)
        case 'SOLID_COLOR':
            rgb_node = global_item.find_node("rgb")
            if rgb_node:
                layout.prop(
                    rgb_node.outputs[0], "default_value", text="", icon='IMAGE_RGB_ALPHA')
        case 'ADJUSTMENT':
            layout.label(icon='SHADERFX')
        case 'SHADER':
            layout.label(icon='SHADING_RENDERED')
        case 'NODE_GROUP':
            layout.label(icon='NODETREE')
        case 'ATTRIBUTE':
            layout.label(icon='MESH_DATA')
        case 'GRADIENT':
            layout.label(icon='COLOR')
        case 'RANDOM':
            layout.label(icon='SEQ_HISTOGRAM')
        case _:
            layout.label(icon='BLANK1')
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
            global_parent_item = get_global_layer(parent_item)
            if global_parent_item and not global_parent_item.enabled:
                main_row.enabled = False

            row = main_row.row(align=True)
            for _ in range(level):
                row.label(icon='BLANK1')
            draw_global_layer_icon(global_item, row)

            row = main_row.row(align=True)
            row.prop(item, "name", text="", emboss=False)
            # if global_item.mask_image:
            #     row.prop(global_item, "enable_mask",
            #              icon='MOD_MASK' if global_item.enable_mask else 'MATPLANE', text="", emboss=False)
            if global_item.is_clip:
                row.label(icon="SELECT_INTERSECT")
            if global_item.lock_layer:
                row.label(icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
            if len(global_item.actions) > 0:
                row.label(icon="KEYTYPE_KEYFRAME_VEC")
            if is_global_layer_linked(global_item):
                if global_item.attached_to_camera_plane:
                    row.label(icon="VIEW_CAMERA")
                else:
                    row.label(icon="LINKED")
            row.prop(global_item, "enabled", text="",
                     icon="HIDE_OFF" if global_item.enabled else "HIDE_ON", emboss=False)
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

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        if ps_ctx.active_group and check_group_multiuser(ps_ctx.active_group.node_tree):
            return False
        return (ps_ctx.active_channel is not None or ps_ctx.ps_object.type == 'GREASEPENCIL')

    def draw_header_preset(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        if context.mode != 'TEXTURE_PAINT':
            return
        if ps_ctx.active_channel:
            layout.popover(
                panel="MAT_PT_ChannelsSelect",
                text=ps_ctx.active_channel.name if ps_ctx.active_channel else "No Channel",
                icon_value=get_icon_from_channel(ps_ctx.active_channel)
            )

    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps_ctx = self.parse_context(context)
    #     active_channel = ps_ctx.active_channel
    #     global_layers = [get_global_layer(layer) for layer, _ in active_channel.flatten_hierarchy()]
    #     has_dirty_images = any(
    #         [layer.image and layer.image.is_dirty for layer in global_layers if layer.type == 'IMAGE'])
    #     if has_dirty_images:
    #         row = layout.row(align=True)
    #         row.operator("wm.save_mainfile",
    #                      text="Click to Save!", icon="FUND")

    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(icon="IMAGE_RGB")
    def draw(self, context):
        ps_ctx = self.parse_context(context)

        layout = self.layout
        current_mode = context.mode
        box = layout.box()
        col = box.column()
        row = col.row(align=True)
        row.scale_y = 1.7
        row.scale_x = 1.7
        # if contains_mat_setup:
        row.operator("paint_system.toggle_paint_mode",
                    text="Toggle Paint Mode", depress=current_mode != 'OBJECT', icon_value=get_icon('paintbrush'))
        if ps_ctx.ps_object.type == 'GREASEPENCIL':
            grease_pencil = context.grease_pencil
            layers = grease_pencil.layers
            is_layer_active = layers.active is not None
            is_group_active = grease_pencil.layer_groups.active is not None
            row.operator("wm.save_mainfile",
                text="", icon="FILE_TICK")
            row = box.row()
            scale_content(context, row, scale_x=1, scale_y=1.2)
            row.template_grease_pencil_layer_tree()
            col = row.column()
            sub = col.column(align=True)
            sub.operator_context = 'EXEC_DEFAULT'
            sub.operator("grease_pencil.layer_add", icon='ADD', text="")
            sub.operator("grease_pencil.layer_group_add", icon='NEWFOLDER', text="")
            sub.separator()

            if is_layer_active:
                sub.operator("grease_pencil.layer_remove", icon='REMOVE', text="")
            if is_group_active:
                sub.operator("grease_pencil.layer_group_remove", icon='REMOVE', text="").keep_children = True

            sub.separator()

            sub.menu("GREASE_PENCIL_MT_grease_pencil_add_layer_extra", icon='DOWNARROW_HLT', text="")

            col.separator()

            sub = col.column(align=True)
            sub.operator("grease_pencil.layer_move", icon='TRIA_UP', text="").direction = 'UP'
            sub.operator("grease_pencil.layer_move", icon='TRIA_DOWN', text="").direction = 'DOWN'
        elif ps_ctx.ps_object.type == 'MESH':
            active_group = ps_ctx.active_group
            active_channel = ps_ctx.active_channel
            active_layer = ps_ctx.active_global_layer
            mat = ps_ctx.active_material
            # contains_mat_setup = any([node.type == 'GROUP' and node.node_tree ==
            #                           active_channel.node_tree for node in mat.node_tree.nodes])

            layers = active_channel.layers

            # Toggle paint mode (switch between object and texture paint mode)
            group_node = find_node(mat.node_tree, {
                                'bl_idname': 'ShaderNodeGroup', 'node_tree': active_group.node_tree})
            if not group_node:
                warning_box = box.box()
                warning_box.alert = True
                col = warning_box.column(align=True)
                col.label(text="Paint System not connected", icon='ERROR')
                col.label(text="to material output!", icon='BLANK1')
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
            if ps_ctx.ps_settings.show_tooltips and not active_group.hide_norm_paint_tips and active_group.template in {'NORMAL', 'PBR'} and any(channel.name == 'Normal' for channel in active_group.channels) and active_channel.name == 'Normal':
                tip_box = col.box()
                tip_box.scale_x = 1.4
                tip_row = tip_box.row()
                tip_col = tip_row.column(align=True)
                tip_col.label(text="The button above will")
                tip_col.label(text="show object normal")
                tip_row.label(icon_value=get_icon('arrow_up'))
                tip_row.operator("paint_system.hide_normal_painting_tips",
                            text="", icon='X')

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
                rows=max(5, len(layers))
            )

            col = row.column(align=True)
            col.scale_x = 1.2
            col.menu("MAT_MT_AddLayer", icon_value=get_icon('layer_add'), text="")
            col.menu("MAT_MT_LayerMenu",
                    text="", icon='COLLAPSEMENU')
            col.separator()
            col.operator("paint_system.delete_item",
                            text="", icon="TRASH")
            col.separator()
            # col.operator("paint_system.delete_item", icon="TRASH", text="")
            # col.separator()
            col.operator("paint_system.move_up", icon="TRIA_UP", text="")
            col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")
            # col.separator()
            # col.popover(
            #     panel="MAT_PT_Actions",
            #     text="",
            #     icon='KEYTYPE_KEYFRAME_VEC',
            # )

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
        ps_ctx = cls.parse_context(context)
        if ps_ctx.ps_object.type == 'MESH':
            active_layer = ps_ctx.active_layer
            return active_layer is not None
        elif ps_ctx.ps_object.type == 'GREASEPENCIL':
            grease_pencil = context.grease_pencil
            active_layer = grease_pencil.layers.active
            return active_layer is not None
        else:
            return False

    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(icon="SETTINGS")
        
    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps_ctx = self.parse_context(context)
    #     global_layer = ps_ctx.active_global_layer
    #     layout.popover(
    #         panel="MAT_PT_Actions",
    #         text=f"Actions ({len(global_layer.actions)})" if global_layer.actions else "Actions",
    #         icon="KEYTYPE_KEYFRAME_VEC"
    #     )

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        if ps_ctx.ps_object.type == 'GREASEPENCIL':
            active_layer = context.grease_pencil.layers.active
            active_group = context.grease_pencil.layer_groups.active
            if active_layer:
                box = layout.box()
                col = box.column(align=True)
                row = col.row(align=True)
                row.scale_y = 1.2
                row.scale_x = 1.2
                scale_content(context, row, 1.7, 1.5)
                options_row = row.row(align=True)
                options_row.enabled = not active_layer.lock
                options_row.prop(active_layer, "use_masks", text="")
                # options_row.prop(active_layer, "use_lights", text="", icon='LIGHT')
                # options_row.prop(active_layer, "use_onion_skinning", text="")
                lock_row = row.row(align=True)
                lock_row.prop(active_layer, "lock", text="")
                blend_row = row.row(align=True)
                blend_row.enabled = not active_layer.lock
                blend_row.prop(active_layer, "blend_mode", text="")
                opacity_row = col.row(align=True)
                opacity_row.enabled = not active_layer.lock
                scale_content(context, opacity_row, 1.7, 1.5)
                opacity_row.prop(active_layer, "opacity")
                
                col = box.column()
                col.enabled = not active_layer.lock
                col.prop(active_layer, "use_lights", text="Use Lights", icon='LIGHT')
                # box.prop(active_layer, "use_onion_skinning", text="Use Onion Skinning")
            
        elif ps_ctx.ps_object.type == 'MESH':
            active_layer = ps_ctx.active_layer
            global_layer = get_global_layer(active_layer)
            if not active_layer:
                return
                # Settings
            row = layout.row(align=True)
            scale_content(context, row)
            row.popover(
                panel="MAT_PT_Actions",
                text=f"{len(global_layer.actions)} Active Actions" if global_layer.actions else "Add Layer Actions",
                icon="KEYTYPE_KEYFRAME_VEC"
            )
            box = layout.box()
            if global_layer.image:
                row = box.row(align=True)
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
            col = box.column(align=True)
            row = col.row(align=True)
            row.scale_y = 1.2
            row.scale_x = 1.2
            scale_content(context, row, 1.7, 1.5)
            clip_row = row.row(align=True)
            clip_row.enabled = not global_layer.lock_layer
            clip_row.prop(global_layer, "is_clip", text="",
                    icon="SELECT_INTERSECT")
            if global_layer.type == 'IMAGE':
                clip_row.prop(global_layer, "lock_alpha",
                        text="", icon='TEXTURE')
            lock_row = row.row(align=True)
            lock_row.prop(global_layer, "lock_layer",
                    text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
            blend_type_row = row.row(align=True)
            blend_type_row.enabled = not global_layer.lock_layer
            blend_type_row.prop(color_mix_node, "blend_type", text="")
            row = col.row(align=True)
            scale_content(context, row, scale_x=1.2, scale_y=1.5)
            row.enabled = not global_layer.lock_layer
            row.prop(global_layer.pre_mix_node.inputs['Opacity'], "default_value",
                    text="Opacity", slider=True)
            col = box.column()
            match global_layer.type:
                case 'IMAGE':
                    pass
                case 'ADJUSTMENT':
                    adjustment_node = global_layer.find_node("adjustment")
                    if adjustment_node:
                        col.enabled = not global_layer.lock_layer
                        col.label(text="Adjustment Settings:", icon='SHADERFX')
                        col.template_node_inputs(adjustment_node)
                case 'NODE_GROUP':
                    custom_node_tree = global_layer.custom_node_tree
                    node_group = global_layer.find_node('custom_node_tree')
                    inputs = [i for i in node_group.inputs if not i.is_linked and i.name not in (
                        'Color', 'Alpha')]
                    if not inputs:
                        return
                    col.enabled = not global_layer.lock_layer
                    col.label(text="Node Group Settings:", icon='NODETREE')
                    for socket in inputs:
                        col.prop(socket, "default_value",
                                text=socket.name)

                case 'ATTRIBUTE':
                    attribute_node = global_layer.find_node("attribute")
                    if attribute_node:
                        col.enabled = not global_layer.lock_layer
                        col.label(text="Attribute Settings:", icon='MESH_DATA')
                        col.template_node_inputs(attribute_node)
                case 'GRADIENT':
                    gradient_node = global_layer.find_node("gradient")
                    map_range_node = global_layer.find_node("map_range")
                    if gradient_node and map_range_node:
                        col.use_property_split = True
                        col.use_property_decorate = False
                        col.enabled = not global_layer.lock_layer
                        if global_layer.gradient_type in ('LINEAR', 'RADIAL'):
                            if global_layer.empty_object and global_layer.empty_object.name in context.view_layer.objects:
                                col.operator("paint_system.select_gradient_empty", text="Select Gradient Empty", icon='OBJECT_ORIGIN')
                            else:
                                err_box = col.box()
                                err_box.alert = True
                                err_col = err_box.column(align=True)
                                err_col.label(text="Gradient Empty not found", icon='ERROR')
                                err_col.operator("paint_system.fix_missing_gradient_empty", text="Fix Missing Gradient Empty")
                        col.separator()
                        col.label(text="Gradient Settings:", icon='SHADERFX')
                        col.template_node_inputs(gradient_node)
                        col.separator()
                        col.prop(map_range_node, "interpolation_type", text="Interpolation")
                        if map_range_node.interpolation_type in ('STEPPED'):
                            col.prop(map_range_node.inputs[5], "default_value", text="Steps")
                        col.prop(map_range_node.inputs[1], "default_value", text="Start Distance")
                        col.prop(map_range_node.inputs[2], "default_value", text="End Distance")
                case 'SOLID_COLOR':
                    rgb_node = global_layer.find_node("rgb")
                    if rgb_node:
                        col.enabled = not global_layer.lock_layer
                        col.prop(rgb_node.outputs[0], "default_value", text="Color",
                                icon='IMAGE_RGB_ALPHA')

                case 'ADJUSTMENT':
                    adjustment_node = global_layer.find_node("adjustment")
                    if adjustment_node:
                        col.enabled = not global_layer.lock_layer
                        col.label(text="Adjustment Settings:", icon='SHADERFX')
                        col.template_node_inputs(adjustment_node)

                case 'RANDOM':
                    random_node = global_layer.find_node("add_2")
                    if random_node:
                        col.enabled = not global_layer.lock_layer
                        col.label(text="Random Settings:", icon='SHADERFX')
                        col.prop(
                            random_node.inputs[1], "default_value", text="Random Seed")
                case _:
                    pass


class MAT_PT_UL_CameraPlaneLayerList(PSContextMixin, UIList):
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
            global_parent_item = get_global_layer(parent_item)
            if global_parent_item and not global_parent_item.enabled:
                main_row.enabled = False

            # row = main_row.row(align=True)
            # draw_global_layer_icon(global_item, row)

            row = main_row.row(align=True)
            # row.label(text=global_item.name)
            # row.label(text=f"Order: {item.order}")
            if self.parse_context(context).active_global_layer == global_item:
                row.label(text=f"Camera Plane {item.order} (Current)", icon="SOLO_ON")
            else:
                row.label(text=f"Camera Plane {item.order}")
                row.enabled = False
    
    def filter_items(self, context, data, propname):
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

class MAT_PT_LayerCameraPlaneSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_LayerCameraPlaneSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Camera Plane"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_LayerSettings'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.ps_object.type == 'MESH'
    
    def draw_header_preset(self, context):
        ps_ctx = self.parse_context(context)
        layout = self.layout
        global_layer = ps_ctx.active_global_layer
        attached_to_camera_plane = global_layer.attached_to_camera_plane
        layout.prop(global_layer, "attached_to_camera_plane", text="Remove" if attached_to_camera_plane else "Attach", icon="NONE" if attached_to_camera_plane else "ADD", toggle = 1)
    
    def draw(self, context):
        ps_ctx = self.parse_context(context)
        layout = self.layout
        global_layer = ps_ctx.active_global_layer
        # layout.prop(global_layer, "attached_to_camera_plane", text="Remove from Camera Plane" if global_layer.attached_to_camera_plane else "Attach to Camera Plane", icon="VIEW_CAMERA")
        
        box = layout.box()
        box.enabled = global_layer.attached_to_camera_plane
        row = box.row()
        row.alignment = 'CENTER'
        row.label(text="Layers in Camera Plane:", icon="VIEW_CAMERA")
        row = box.row()
        col = row.column()
        col.template_list(
            "MAT_PT_UL_CameraPlaneLayerList", "", ps_ctx.camera_plane_channel, "layers", ps_ctx.camera_plane_channel, "active_index",
            rows=max(5, len(ps_ctx.camera_plane_channel.layers))
        )
        col = row.column(align=True)
        col.operator("paint_system.move_up_camera_plane", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down_camera_plane", icon="TRIA_DOWN", text="")
        

# Grease Pencil Layer Settings

def disable_if_lock(self, context):
    active_layer = context.grease_pencil.layers.active
    layout = self.layout
    layout.enabled = not active_layer.lock

class MAT_PT_GreasePencilMaskSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_GreasePencilMaskSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Mask"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_LayerSettings'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.ps_object.type == 'GREASEPENCIL' and is_newer_than(4,3)

    def draw_header(self, context):
        GreasePencil_LayerMaskPanel.draw_header(self, context)
        disable_if_lock(self, context)
    
    def draw(self, context):
        GreasePencil_LayerMaskPanel.draw(self, context)
        disable_if_lock(self, context)

class MAT_PT_GreasePencilOnionSkinningSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_GreasePencilOnionSkinningSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Onion Skinning"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_LayerSettings'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.ps_object.type == 'GREASEPENCIL' and is_newer_than(4,3)
    
    def draw(self, context):
        DATA_PT_grease_pencil_onion_skinning.draw(self, context)
        disable_if_lock(self, context)
    
    def draw_header(self, context):
        layout = self.layout
        active_layer = context.grease_pencil.layers.active
        layout.prop(active_layer, "use_onion_skinning", text="", toggle=0)
        disable_if_lock(self, context)


# Paint System Layer Settings Advanced
class MAT_PT_LayerSettingsAdvanced(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_PaintSystemLayerSettingsAdvanced'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Advanced Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_LayerSettings'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        global_layer = ps_ctx.active_global_layer
        return global_layer and global_layer.type == 'IMAGE'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        ps_ctx = self.parse_context(context)
        global_layer = ps_ctx.active_global_layer
        layout.enabled = not global_layer.lock_layer
        box = layout.box()
        box.label(text="Coordinate Type:")
        box.prop(global_layer, "coord_type", text="")
        if global_layer.attached_to_camera_plane:
            box.label(text="This layer is attached to the camera plane", icon='ERROR')
            
        if global_layer.coord_type == 'UV':
            layout.prop_search(global_layer, "uv_map_name", text="UV Map",
                                search_data=context.object.data, search_property="uv_layers", icon='GROUP_UVS')

        image_node = global_layer.find_node("image")
        if image_node:
            box = layout.box()
            box.label(text="Image Settings:")
            box.template_node_inputs(image_node)
            box.prop(image_node, "interpolation",
                     text="")
            box.prop(image_node, "projection",
                     text="")
            box.prop(image_node, "extension",
                     text="")
            box.prop(global_layer.image, "source",
                     text="")

class MAT_MT_LayerMenu(PSContextMixin, Menu):
    bl_label = "Layer Menu"
    bl_idname = "MAT_MT_LayerMenu"

    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.copy_layer",
                        text="Copy Layer", icon="COPYDOWN")
        layout.operator("paint_system.copy_all_layers",
                        text="Copy All Layers", icon="COPYDOWN")
        layout.operator("paint_system.paste_layer",
                        text="Paste Layer(s)", icon="PASTEDOWN").linked = False
        layout.operator("paint_system.paste_layer",
                        text="Paste Linked Layer(s)", icon="LINKED").linked = True


class MAT_MT_AddImageLayerMenu(Menu):
    bl_label = "Add Image"
    bl_idname = "MAT_MT_AddImageLayerMenu"
    
    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.new_image_layer", text="New Image Layer", icon='IMAGE_RGB_ALPHA')
        layout.operator("paint_system.new_image_layer", text="Import Image Layer", icon='IMPORT')
        layout.operator("paint_system.new_image_layer", text="Use Existing Image Layer", icon='IMAGE')


class MAT_MT_AddGradientLayerMenu(Menu):
    bl_label = "Add Gradient"
    bl_idname = "MAT_MT_AddGradientLayerMenu"
    
    def draw(self, context):
        layout = self.layout
        for idx, (node_type, name, description) in enumerate(GRADIENT_TYPE_ENUM):
            layout.operator("paint_system.new_gradient_layer",
                text=name, icon='COLOR' if idx == 0 else 'NONE').gradient_type = node_type


class MAT_MT_AddAdjustmentLayerMenu(Menu):
    bl_label = "Add Adjustment"
    bl_idname = "MAT_MT_AddAdjustmentLayerMenu"
    
    def draw(self, context):
        layout = self.layout
        for idx, (node_type, name, description) in enumerate(ADJUSTMENT_TYPE_ENUM):
            layout.operator("paint_system.new_adjustment_layer",
                text=name, icon='SHADERFX' if idx == 0 else 'NONE').adjustment_type = node_type
class MAT_MT_AddLayerMenu(Menu):
    bl_label = "Add Layer"
    bl_idname = "MAT_MT_AddLayer"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator("paint_system.new_folder_layer",
                     icon_value=get_icon('folder'), text="Folder")
        col.separator()
        # col.label(text="Basic:")
        col.operator("paint_system.new_solid_color_layer", text="Solid Color",
                     icon=icon_parser('STRIP_COLOR_03', "SEQUENCE_COLOR_03"))
        col.menu("MAT_MT_AddImageLayerMenu", text="Image", icon='IMAGE_RGB_ALPHA')
        col.menu("MAT_MT_AddGradientLayerMenu", text="Gradient", icon='COLOR')
        col.menu("MAT_MT_AddAdjustmentLayerMenu", text="Adjustment", icon='SHADERFX')
        col.separator()
        # col.label(text="Advanced:")
        col.operator("paint_system.new_attribute_layer",
                     text="Attribute Color", icon='MESH_DATA')
        col.operator("paint_system.new_random_color_layer",
                     text="Random Color", icon='SEQ_HISTOGRAM')

        col.operator("paint_system.new_custom_node_group_layer",
                     text="Custom Node Tree", icon='NODETREE')


class PAINTSYSTEM_UL_Actions(PSContextMixin, UIList):
    bl_idname = "PAINTSYSTEM_UL_Actions"
    bl_label = "Actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_LayerSettings'

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        layout.prop(item, "action_bind", text="", icon_only=True, emboss=False)
        bind_to = 'Marker' if item.action_bind == 'MARKER' else 'Frame'
        bind_name = (item.marker_name if item.marker_name else "None") if item.action_bind == 'MARKER' else str(item.frame)
        layout.label(text=f"{bind_to} {bind_name} Action")
    
    def filter_items(self, context, data, propname):
        actions = getattr(data, propname).values()
        flt_flags = [self.bitflag_filter_item] * len(data.actions)
        flt_neworder = []
        sorted_actions = sort_actions(context, data)
        for action in actions:
            flt_neworder.append(sorted_actions.index(action))
        return flt_flags, flt_neworder


class MAT_PT_Actions(PSContextMixin, Panel):
    bl_idname = "MAT_PT_Actions"
    bl_label = "Actions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_category = 'Paint System'
    # bl_parent_id = 'MAT_PT_LayerSettings'
    # bl_options = {'DEFAULT_CLOSED'}
    bl_ui_units_x = 12

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        active_layer = ps_ctx.active_layer
        return active_layer is not None

    def draw(self, context):
        ps_ctx = self.parse_context(context)
        global_layer = ps_ctx.active_global_layer
        layout = self.layout
        layout.use_property_split = True
        layout.alignment = 'LEFT'
        layout.use_property_decorate = False
        layout.label(text="Layer Actions")
        if ps_ctx.ps_settings.show_tooltips and not global_layer.actions:
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Actions can control layer visibility", icon='INFO')
            col.label(text="with frame number or marker", icon='BLANK1')
        row = layout.row()
        # row.template_list("PAINTSYSTEM_UL_Actions", "", global_layer,
        #                   "actions", global_layer, "active_action_index")
        actions_col = row.column()
        scale_content(context, actions_col)
        actions_col.template_list("PAINTSYSTEM_UL_Actions", "", global_layer,
                          "actions", global_layer, "active_action_index", rows=5)
        # if global_layer.actions:
        #     sorted_actions = sort_actions(context, global_layer)
        #     for action in sorted_actions:
        #         action_row = box.row()
        #         action_row.prop(action, "action_bind", text="", icon_only=True)
        #         split = action_row.split(factor=0.5)
        #         split.prop(action, "action_type", text="")
        #         if action.action_bind == 'FRAME':
        #             split.prop(action, "frame", text="")
        #         elif action.action_bind == 'MARKER':
        #             split.prop_search(action, "marker_name", context.scene, "timeline_markers", text="", icon="MARKER_HLT")
        # else:
        #     action_row = box.row()
        #     action_row.label(icon='INFO')
        #     col = action_row.column(align=True)
        #     col.label(text="Control the visibility of the layer based on")
        #     col.label(text="frame or marker")
        col = row.column(align=True)
        col.operator("paint_system.add_action", icon="ADD", text="")
        col.operator("paint_system.delete_action", icon="REMOVE", text="")
        if not global_layer.actions:
            # col.label(text="Add Actions to control the layer visibility", icon='INFO')
            return
        active_action = global_layer.actions[global_layer.active_action_index]
        if not active_action:
            return
        actions_col.separator()
        actions_col.prop(active_action, "action_bind", text="Bind to")
        if active_action.action_bind == 'FRAME':
            actions_col.prop(active_action, "frame", text="Frame")
        elif active_action.action_bind == 'MARKER':
            actions_col.prop_search(active_action, "marker_name", context.scene, "timeline_markers", text="Once reach", icon="MARKER_HLT")
        actions_col.prop(active_action, "action_type", text="Action")


classes = (
    MAT_PT_UL_LayerList,
    MAT_MT_AddLayerMenu,
    MAT_MT_AddImageLayerMenu,
    MAT_MT_AddGradientLayerMenu,
    MAT_MT_AddAdjustmentLayerMenu,
    MAT_MT_LayerMenu,
    MAT_PT_Layers,
    MAT_PT_LayerSettings,
    MAT_PT_UL_CameraPlaneLayerList,
    MAT_PT_LayerCameraPlaneSettings,
    MAT_PT_GreasePencilMaskSettings,
    MAT_PT_GreasePencilOnionSkinningSettings,
    MAT_PT_LayerSettingsAdvanced,
    MAT_PT_Actions,
    PAINTSYSTEM_UL_Actions,
)

register, unregister = register_classes_factory(classes)
