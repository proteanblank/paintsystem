import bpy
from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (Panel,
                       Menu,
                       AddonPreferences,
                       Context)
from bpy.utils import register_classes_factory
from .nested_list_manager import BaseNLM_UL_List
from .paint_system import PaintSystem, ADJUSTMENT_ENUM
from . import addon_updater_ops
from .common import is_online, is_newer_than, icon_parser
from .operators_bake import is_bakeable
# from .. import __package__ as base_package

# -------------------------------------------------------------------
# Addon Preferences
# -------------------------------------------------------------------


@addon_updater_ops.make_annotations
class PaintSystemPreferences(AddonPreferences):
    """Demo bare-bones preferences"""
    bl_idname = __package__

    # Addon updater preferences.

    auto_check_update = BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True if bpy.app.version < (4, 2) else is_online())

    updater_interval_months = IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0)

    updater_interval_days = IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=1,
        min=0,
        max=31)

    updater_interval_hours = IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23)

    updater_interval_minutes = IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59)

    show_tooltips = BoolProperty(
        name="Show Tooltips",
        description="Show tooltips in the UI",
        default=True
    )

    use_compact_design = BoolProperty(
        name="Use Compact Design",
        description="Use a more compact design for the UI",
        default=False
    )

    name_layers_group = BoolProperty(
        name="Name Layers According to Group Name",
        default=False
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "show_tooltips", text="Show Tooltips")
        layout.prop(self, "use_compact_design", text="Use Compact Design")
        layout.prop(self, "name_layers_group",
                    text="Name Layers According to Group Name")

        if is_online():
            # Updater draw function, could also pass in col as third arg.
            addon_updater_ops.update_settings_ui(self, context)
        else:
            self.auto_check_update = False
            layout.label(
                text="Please allow online access in user preferences to use the updater")


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
        addon_updater_ops.check_for_update_background()
        return (context.active_object and context.active_object.type == 'MESH' and context.active_object.mode != 'TEXTURE_PAINT') or addon_updater_ops.updater.update_ready

    def draw_header(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        layout.label(icon="KEYTYPE_KEYFRAME_VEC")

    def draw(self, context):
        layout = self.layout

        addon_updater_ops.update_notice_box_ui(self, context)

        ps = PaintSystem(context)
        ob = ps.active_object
        mat = ps.get_active_material()

        layout.label(text="Selected Material:")

        col = layout.column(align=True)
        if not ps.preferences.use_compact_design:
            col.scale_y = 1.2
        col.template_ID(ob, "active_material", new="material.new")

        if not mat:
            layout.label(text="No active material")
            return

        col.prop(mat, "surface_render_method", text="")

        row = layout.row()

        if not ps.preferences.use_compact_design:
            row.scale_y = 2.0

        if hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0:
            row = layout.row(align=True)
            if not ps.preferences.use_compact_design:
                row.scale_y = 1.5
                row.scale_x = 1.5
            row.prop(mat.paint_system, "active_group", text="")
            row.operator("paint_system.new_group",
                         text="", icon='ADD')
            col = row.column(align=True)
            col.menu("MAT_MT_PaintSystemGroup", text="", icon='COLLAPSEMENU')
        else:
            row = layout.row(align=True)
            if not ps.preferences.use_compact_design:
                row.scale_y = 1.5
            row.operator("paint_system.new_group",
                         text="Add Group", icon='ADD')


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
# Brush Settings Panels
# -------------------------------------------------------------------


def set_active_panel(context: Context, panel_name):
    context.region.active_panel_category = panel_name


def get_unified_settings(context: Context, unified_name=None):
    ups = context.tool_settings.unified_paint_settings
    tool_settings = context.tool_settings.image_paint
    brush = tool_settings.brush
    prop_owner = brush
    if unified_name and getattr(ups, unified_name):
        prop_owner = ups
    return prop_owner


def prop_unified(
    layout,
    context,
    prop_name,
    unified_name=None,
    icon='NONE',
    text=None,
    slider=False,
    header=False,
):
    """ Generalized way of adding brush options to the UI,
        along with their pen pressure setting and global toggle, if they exist. """
    row = layout.row(align=True)
    ups = context.tool_settings.unified_paint_settings
    prop_owner = get_unified_settings(context, unified_name)

    row.prop(prop_owner, prop_name, icon=icon, text=text, slider=slider)

    if unified_name and not header:
        # NOTE: We don't draw UnifiedPaintSettings in the header to reduce clutter. D5928#136281
        row.prop(ups, unified_name, text="", icon='BRUSHES_ALL')

    return row


class MAT_PT_Brush(Panel):
    bl_idname = 'MAT_PT_Brush'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Brush"
    bl_category = 'Paint System'

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        obj = ps.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw_header(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        layout.label(icon="BRUSHES_ALL")

    def draw_header_preset(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        if ps.preferences.show_tooltips:
            row = layout.row()
            row.menu("MAT_MT_BrushTooltips",
                     text='View Shortcuts!')

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        obj = ps.active_object
        # row = layout.row()
        # if not ps.preferences.use_compact_design:
        #     row.scale_y = 1.5
        # row.operator("paint_system.set_active_panel",
        #              text="Advanced Settings", icon="PREFERENCES").category = "Tool"

        brush_imported = False
        for brush in bpy.data.brushes:
            if brush.name.startswith("PS_"):
                brush_imported = True
                break
        if not brush_imported:
            layout.operator("paint_system.add_preset_brushes",
                            text="Add Preset Brushes", icon="IMPORT")

        tool_settings = context.tool_settings.image_paint
        # Check blender version
        if not is_newer_than(4, 3):
            layout.template_ID_preview(tool_settings, "brush",
                                       new="brush.add", rows=3, cols=8, hide_buttons=False)
        # else:
        #     col = layout.column(align=True)
        #     shelf_name = "VIEW3D_AST_brush_texture_paint"
        #     brush = tool_settings.brush
        #     display_name = brush.name if brush else None
        #     if display_name and brush.has_unsaved_changes:
        #         display_name = display_name + "*"
        #     preview_icon_id = brush.preview.icon_id if brush and brush.preview else 0
        #     col.template_asset_shelf_popover(
        #         shelf_name,
        #         icon='BRUSH_DATA' if not preview_icon_id else 'NONE',
        #         icon_value=preview_icon_id,
        #     )
        #     if brush:
        #         col.prop(brush, "name", text="")

        box = layout.box()
        row = box.row()
        row.label(text="Settings:", icon="SETTINGS")
        row.operator("paint_system.set_active_panel",
                     text="More", icon="RIGHTARROW").category = "Tool"
        col = box.column(align=True)
        if not ps.preferences.use_compact_design:
            col.scale_y = 1.5
        prop_unified(col, context, "size",
                     "use_unified_size", icon="WORLD", text="Size", slider=True)
        prop_unified(col, context, "strength",
                     "use_unified_strength", icon="WORLD", text="Strength")
        if obj and obj.mode == 'TEXTURE_PAINT':
            box.prop(ps.settings, "allow_image_overwrite",
                     text="Auto Image Select", icon='CHECKBOX_HLT' if ps.settings.allow_image_overwrite else 'CHECKBOX_DEHLT')
        # row.label(text="Brush Shortcuts")


class MAT_MT_BrushTooltips(Menu):
    bl_label = "Brush Tooltips"
    bl_description = "Brush Tooltips"
    bl_idname = "MAT_MT_BrushTooltips"

    def draw(self, context):
        layout = self.layout
        # split = layout.split(factor=0.1)
        col = layout.column()
        col.label(text="Switch to Eraser", icon='EVENT_E')
        col.label(text="Eyedrop Screen Color", icon='EVENT_I')
        row = col.row(align=True)
        row.label(icon='EVENT_SHIFT', text="")
        row.label(text="Eyedrop Layer Color", icon='EVENT_X')
        col.label(text="Scale Brush Size", icon='EVENT_F')
        layout.separator()
        layout.operator('wm.url_open', text="Suggest more shortcuts on Github!",
                        icon='URL').url = "https://github.com/natapol2547/paintsystem/issues"
        layout.operator("paint_system.disable_tool_tips",
                        text="Disable Tooltips", icon='CANCEL')


class MAT_PT_BrushColor(Panel):
    bl_idname = 'MAT_PT_BrushColor'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Color"
    bl_category = 'Paint System'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        obj = ps.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw_header(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        layout.label(icon="COLOR")

    def draw_header_preset(self, context):
        layout = self.layout
        layout.prop(get_unified_settings(context, "use_unified_color"), "color",
                    text="", icon='IMAGE_RGB_ALPHA')
        # layout.label(text="", icon="INFO")

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(context.preferences.view, "color_picker_type", text="")
        tool_settings = bpy.context.scene.tool_settings
        unified_settings = tool_settings.unified_paint_settings
        brush_settings = tool_settings.image_paint.brush
        col.template_color_picker(
            unified_settings if unified_settings.use_unified_color else brush_settings, "color", value_slider=True)


class MAT_PT_BrushColorPalette(Panel):
    bl_idname = 'MAT_PT_BrushColorPalette'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Color Palette"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_BrushColor'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        obj = ps.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT' and is_newer_than(4, 3)

    def draw(self, context):
        layout = self.layout
        settings = context.tool_settings.image_paint
        layout.template_ID(settings, "palette", new="palette.new")
        if settings.palette:
            layout.template_palette(settings, "palette", color=True)


class MAT_PT_BrushSettings(Panel):
    bl_idname = 'MAT_PT_BrushSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_Brush'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        obj = ps.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings.image_paint
        brush = tool_settings.brush
        prop_unified(layout, context, brush, "strength",
                     "use_unified_strength", icon="WORLD", text="Strength")
        prop_unified(layout, context, brush, "size",
                     "use_unified_strength", icon="WORLD", text="Size", slider=True)

# -------------------------------------------------------------------
# Layers Panels
# -------------------------------------------------------------------


class MAT_PT_UL_PaintSystemLayerList(BaseNLM_UL_List):
    def draw_item(self, context: Context, layout, data, item, icon, active_data, active_property, index):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        flattened = active_group.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            row = layout.row(align=True)
            # Check if parent of the current item is enabled
            parent_item = ps.get_active_group().get_item_by_id(
                display_item.parent_id)
            if parent_item and not parent_item.enabled:
                row.enabled = False

            for _ in range(level):
                row.label(icon='BLANK1')
            # if display_item.clip:
            #     row.separator()
            match display_item.type:
                case 'IMAGE':
                    if display_item.image.preview:
                        row.label(
                            icon_value=display_item.image.preview.icon_id)
                    # elif not display_item.image.is_dirty:
                    #     row.label(icon='IMAGE_DATA')
                    else:
                        display_item.image.asset_generate_preview()
                        row.label(icon='BLANK1')
                case 'FOLDER':
                    row.label(icon='FILE_FOLDER')
                case 'SOLID_COLOR':
                    rgb_node = None
                    for node in display_item.node_tree.nodes:
                        if node.name == 'RGB':
                            rgb_node = node
                    if rgb_node:
                        row.prop(
                            rgb_node.outputs[0], "default_value", text="", icon='IMAGE_RGB_ALPHA')
                case 'ADJUSTMENT':
                    row.label(icon='SHADERFX')
            row.prop(display_item, "name", text="", emboss=False)
            if display_item.clip:
                row.label(icon="SELECT_INTERSECT")
            # if display_item.lock_alpha:
            #     row.label(icon="TEXTURE")
            if display_item.lock_layer:
                row.label(icon="VIEW_LOCKED")
            row.prop(display_item, "enabled", text="",
                     icon="HIDE_OFF" if display_item.enabled else "HIDE_ON", emboss=False)
            # row.label(text=f"Order: {display_item.order}")
            self.draw_custom_properties(row, display_item)

    def draw_custom_properties(self, layout, item):
        if hasattr(item, 'custom_int'):
            layout.label(text=str(item.order))

    def get_list_manager(self, context):
        return PaintSystem(context).group


class MAT_MT_LayersSettingsTooltips(Menu):
    bl_label = "Layer Settings Tooltips"
    bl_description = "Layer Settings Tooltips"
    bl_idname = "MAT_MT_LayersSettingsTooltips"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Layer Settings Tips!")
        layout.separator()
        layout.label(text="Clip to Layer Below", icon='SELECT_INTERSECT')
        layout.label(text="Lock Layer Alpha", icon='TEXTURE')
        layout.label(text="Lock Layer Settings",
                     icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
        layout.separator()
        layout.operator('wm.url_open', text="Suggest more settings on Github!",
                        icon='URL').url = "https://github.com/natapol2547/paintsystem/issues"
        layout.operator("paint_system.disable_tool_tips",
                        text="Disable Tooltips", icon='CANCEL')


class MAT_PT_PaintSystemLayers(Panel):
    bl_idname = 'MAT_PT_PaintSystemLayers'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layers"
    bl_category = 'Paint System'
    # bl_parent_id = 'MAT_PT_PaintSystemGroups'

    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps = PaintSystem(context)
    #     obj = ps.active_object

    #     if obj and obj.mode == 'TEXTURE_PAINT':
    #         layout.prop(ps.settings, "allow_image_overwrite",
    #                     text="Auto Select", icon='CHECKBOX_HLT' if ps.settings.allow_image_overwrite else 'CHECKBOX_DEHLT')

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        return active_group

    def draw_header(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        layout.label(icon="IMAGE_RGB")

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        contains_mat_setup = any([node.type == 'GROUP' and node.node_tree ==
                                 active_group.node_tree for node in mat.node_tree.nodes])

        flattened = active_group.flatten_hierarchy()

        # Toggle paint mode (switch between object and texture paint mode)
        current_mode = context.mode
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.5
        # row.menu("MAT_MT_PaintSystemGroup", text="", icon='BRUSHES_ALL')
        if contains_mat_setup:
            row.operator("paint_system.toggle_paint_mode",
                         text="Toggle Paint Mode", depress=current_mode == 'PAINT_TEXTURE')
        else:
            row.alert = True
            row.operator("paint_system.create_template_setup",
                         text="Setup Material", icon="ERROR")
            row.alert = False
        row.operator("wm.save_mainfile",
                     text="", icon="FILE_TICK")
        # Baking and Exporting
        row = col.row(align=True)
        row.scale_y = 1.5
        row.scale_x = 1.5

        if not active_group.bake_image:
            row.menu("MAT_MT_PaintSystemMergeAndExport",
                     icon='EXPORT', text="Merge and Export")
        has_dirty_images = any(
            [layer.image and layer.image.is_dirty for layer, _ in flattened if layer.type == 'IMAGE'])
        if has_dirty_images:
            col.label(text="Don't forget to save!", icon="FUND")

        if not any([item.image for (item, _) in flattened]):
            col.label(text="Add an image layer first!",
                      icon="ERROR")

        if active_group.bake_image:
            box = layout.box()
            row = box.row(align=True)
            if not ps.preferences.use_compact_design:
                row.scale_x = 1.5
                row.scale_y = 1.5
            row.prop(active_group, "use_bake_image",
                     text="Use Merged Image", icon='CHECKBOX_HLT' if active_group.use_bake_image else 'CHECKBOX_DEHLT')
            row.operator("paint_system.export_baked_image",
                         icon='EXPORT', text="")
            col = row.column(align=True)
            col.menu("MAT_MT_PaintSystemMergeOptimize",
                     icon='COLLAPSEMENU', text="")
            if active_group.use_bake_image:
                box.label(
                    text="Merged Image Used. It's faster!", icon='SOLO_ON')
                return

        row = layout.row()
        if not ps.preferences.use_compact_design:
            row.scale_y = 1.5
        row.template_list(
            "MAT_PT_UL_PaintSystemLayerList", "", active_group, "items", active_group, "active_index",
            rows=max(5, len(flattened))
        )

        col = row.column(align=True)
        col.menu("MAT_MT_PaintSystemAddLayer", icon='IMAGE_DATA', text="")
        col.operator("paint_system.new_folder", icon='NEWFOLDER', text="")
        col.separator()
        col.operator("paint_system.delete_item", icon="TRASH", text="")
        col.separator()
        col.operator("paint_system.move_up", icon="TRIA_UP", text="")
        col.operator("paint_system.move_down", icon="TRIA_DOWN", text="")

        active_layer = ps.get_active_layer()
        if not active_layer:
            return

        # Settings
        box = layout.box()
        row = box.row()
        row.label(text="Layer Settings:", icon='SETTINGS')
        if ps.preferences.show_tooltips:
            row.menu("MAT_MT_LayersSettingsTooltips", text='', icon='QUESTION')

        # Let user set opacity and blend mode:
        color_mix_node = ps.find_color_mix_node()
        match active_layer.type:
            case 'IMAGE':
                row = box.row(align=True)
                if not ps.preferences.use_compact_design:
                    row.scale_y = 1.5
                    row.scale_x = 1.5
                row.prop(active_layer, "clip", text="",
                         icon="SELECT_INTERSECT")
                row.prop(active_layer, "lock_alpha",
                         text="", icon='TEXTURE')
                row.prop(active_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = box.row()
                row.enabled = not active_layer.lock_layer
                if not ps.preferences.use_compact_design:
                    row.scale_y = 1.5
                row.prop(ps.find_opacity_mix_node().inputs[0], "default_value",
                         text="Opacity", slider=True)

            case 'ADJUSTMENT':
                row = box.row(align=True)
                if not ps.preferences.use_compact_design:
                    row.scale_y = 1.5
                    row.scale_x = 1.5
                row.prop(active_layer, "clip", text="",
                         icon="SELECT_INTERSECT")
                row.prop(active_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(ps.find_opacity_mix_node().inputs[0], "default_value",
                         text="Opacity", slider=True)
            case _:
                row = box.row(align=True)
                if not ps.preferences.use_compact_design:
                    row.scale_y = 1.5
                    row.scale_x = 1.5
                row.prop(active_layer, "clip", text="",
                         icon="SELECT_INTERSECT")
                row.prop(active_layer, "lock_layer",
                         text="", icon=icon_parser('VIEW_LOCKED', 'LOCKED'))
                row.prop(color_mix_node, "blend_type", text="")
                row = box.row()
                row.enabled = not active_layer.lock_layer
                if not ps.preferences.use_compact_design:
                    row.scale_y = 1.5
                row.prop(ps.find_opacity_mix_node().inputs[0], "default_value",
                         text="Opacity", slider=True)

        rgb_node = ps.find_rgb_node()
        col = box.column()
        col.enabled = not active_layer.lock_layer
        if rgb_node:
            col.prop(rgb_node.outputs[0], "default_value", text="Color",
                     icon='IMAGE_RGB_ALPHA')

        adjustment_node = ps.find_adjustment_node()
        if adjustment_node:
            col.label(text="Adjustment Settings:", icon='SHADERFX')
            col.template_node_inputs(adjustment_node)


# class MAT_MT_PaintSystemLayerMenu(Menu):


class MAT_PT_PaintSystemLayersAdvanced(Panel):
    bl_idname = 'MAT_PT_PaintSystemLayersAdvanced'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Advanced Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemLayers'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        return active_group and ps.get_active_layer() and ps.get_active_layer().type == 'IMAGE' and not active_group.use_bake_image

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        color_mix_node = ps.find_color_mix_node()
        active_layer = ps.get_active_layer()
        if color_mix_node:
            layout.prop(color_mix_node, "clamp_result", text="Clamp Result")

        uv_map_node = ps.find_uv_map_node()
        if uv_map_node:
            layout.prop_search(uv_map_node, "uv_map", text="UV Map",
                               search_data=context.object.data, search_property="uv_layers", icon='GROUP_UVS')

        image_texture_node = ps.find_image_texture_node()
        if image_texture_node:
            layout.prop(image_texture_node, "interpolation",
                        text="Interpolation")
            layout.prop(active_layer.image, "alpha_mode", text="Alpha Mode")

# -------------------------------------------------------------------
# Images Panels
# -------------------------------------------------------------------


class MAT_MT_PaintSystemAddLayer(Menu):
    bl_label = "Add Image"
    bl_idname = "MAT_MT_PaintSystemAddLayer"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()
        col.label(text="Image Layer:")
        col.operator("paint_system.new_image",
                     text="New Image Layer", icon="FILE")
        col.operator("paint_system.open_image",
                     text="Open External Image")
        col.operator("paint_system.open_existing_image",
                     text="Use Existing Image")
        col.separator()
        col.label(text="Color:")
        col.operator("paint_system.new_solid_color", text="Solid Color",
                     icon=icon_parser('STRIP_COLOR_03', "SEQUENCE_COLOR_03"))

        col.separator()
        col.label(text="Shader:")

        col = row.column()
        col.label(text="Adjustment Layer:")
        for idx, (node_type, name, description) in enumerate(ADJUSTMENT_ENUM):
            col.operator("paint_system.new_adjustment_layer",
                         text=name, icon='SHADERFX' if idx == 0 else 'NONE').adjustment_type = node_type
        # col = row.column()
        # col.label(text="Folder:")
        # col.operator("paint_system.new_folder", text="Folder",
        #              icon="FILE_FOLDER")


class MAT_MT_PaintSystemMergeAndExport(Menu):
    bl_label = "Merge and Export"
    bl_idname = "MAT_MT_PaintSystemMergeAndExport"

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        bakeable, error_message, nodes = is_bakeable(context)
        if not bakeable:
            col = layout.column()
            col.alert = True
            col.label(text=error_message, icon='ERROR')

            for node in nodes:
                col.operator("paint_system.focus_node",
                             text=node.name).node_name = node.name
        else:
            col = layout.column()
            col.label(text="This is Experimental!", icon='ERROR')
            col.label(text="Be sure to save regularly!")
            col.separator()
            col.label(text="Merge:")
            col.operator("paint_system.merge_group",
                         text="Merge as New Layer", icon="FILE").as_new_layer = True
            col.operator("paint_system.merge_group",
                         text="Merge All Layers (Bake)").as_new_layer = False
            col.separator()
            col.label(text="Export:")
            col.operator("paint_system.merge_and_export_group",
                         text="Export Merged Image", icon='EXPORT')
            # if not active_group.bake_image:
            #     col.label(text="Bake first!", icon='ERROR')


class MAT_MT_PaintSystemMergeOptimize(Menu):
    bl_label = "Merge and Export"
    bl_idname = "MAT_MT_PaintSystemMergeOptimize"

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.operator("paint_system.merge_group",
                     text="Update Merged Layer", icon="FILE_REFRESH").as_new_layer = False
        col.operator("paint_system.delete_bake_image",
                     text="Delete Merged Image", icon='TRASH')
        col.operator("paint_system.export_baked_image",
                     text="Export Merged Image", icon='EXPORT')
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
    PaintSystemPreferences,
    MAT_PT_PaintSystemGroups,
    MAT_MT_PaintSystemGroup,
    MAT_PT_Brush,
    MAT_PT_BrushColor,
    MAT_PT_BrushColorPalette,
    # MAT_PT_BrushSettings,
    MAT_PT_UL_PaintSystemLayerList,
    MAT_MT_LayersSettingsTooltips,
    MAT_PT_PaintSystemLayers,
    MAT_PT_PaintSystemLayersAdvanced,
    MAT_MT_PaintSystemAddLayer,
    MAT_MT_BrushTooltips,
    MAT_MT_PaintSystemMergeAndExport,
    MAT_MT_PaintSystemMergeOptimize,
    # MAT_PT_PaintSystemTest,
)

register, unregister = register_classes_factory(classes)
