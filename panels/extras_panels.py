import bpy
from bpy.types import Panel, Menu
from bpy.utils import register_classes_factory
from ..utils.unified_brushes import get_unified_settings
from .common import PSContextMixin, get_event_icons, find_keymap, find_keymap_by_name
from ..utils.version import is_newer_than

def prop_unified(
    layout,
    context,
    prop_name,
    unified_name=None,
    icon='EMPTY',
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
        row.prop(ups, unified_name, text="", icon='WORLD')

    return row

class MAT_PT_BrushTooltips(Panel):
    bl_label = "Brush Tooltips"
    bl_description = "Brush Tooltips"
    bl_idname = "MAT_PT_BrushTooltips"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_ui_units_x = 8

    def draw_shortcut(self, layout, kmi, text):
        row = layout.row(align=True)
        icons = get_event_icons(kmi)
        for idx, icon in enumerate(icons):
            row.label(icon=icon, text=text if idx == len(icons)-1 else "")

    def draw(self, context):
        layout = self.layout
        # split = layout.split(factor=0.1)
        col = layout.column()
        kmi = find_keymap("paint_system.toggle_brush_erase_alpha")
        self.draw_shortcut(col, kmi, "Toggle Erase Alpha")
        kmi = find_keymap("paint_system.color_sampler")
        self.draw_shortcut(col, kmi, "Eyedropper")
        # kmi = find_keymap("object.transfer_mode")
        # self.draw_shortcut(col, kmi, "Switch Object")
        kmi = find_keymap_by_name("Radial Control")
        if kmi:
            self.draw_shortcut(col, kmi, "Scale Brush Size")
        # col.label(text="Scale Brush Size", icon='EVENT_F')
        layout.separator()
        layout.operator('paint_system.open_paint_system_preferences', text="Preferences", icon='PREFERENCES')
        layout.operator('wm.url_open', text="Suggest more!",
                        icon='URL').url = "https://github.com/natapol2547/paintsystem/issues"
        # layout.operator("paint_system.disable_tool_tips",
        #                 text="Disable Tooltips", icon='CANCEL')

class MAT_PT_Brush(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_Brush'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Brush"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        obj = ps_ctx.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="BRUSHES_ALL")

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()
        prop_unified(row, context, "size",
                    "use_unified_size", icon="WORLD", text="Size", slider=True, header=True)
            
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        tool_settings = context.tool_settings.image_paint
        # Check blender version
        if not is_newer_than(4, 3):
            layout.template_ID_preview(tool_settings, "brush",
                                       new="brush.add", rows=3, cols=8, hide_buttons=False)
        box = layout.box()
        row = box.row()
        row.label(text="Settings:", icon="SETTINGS")
        if ps_ctx.ps_settings.show_tooltips:
            row.popover(
                panel="MAT_PT_BrushTooltips",
                text='Shortcuts!',
                icon='INFO_LARGE'
            )
        # row.operator("paint_system.set_active_panel",
        #              text="More", icon="RIGHTARROW").category = "Tool"
        col = box.column(align=True)
        if not ps_ctx.ps_settings.use_compact_design:
            col.scale_y = 1.5
        prop_unified(col, context, "size",
                     "use_unified_size", icon="WORLD", text="Size", slider=True)
        prop_unified(col, context, "strength",
                     "use_unified_strength", icon="WORLD", text="Strength")
        # row.label(text="Brush Shortcuts")
        
        brush = tool_settings.brush
        if brush:
            row = box.row()
            if not ps_ctx.ps_settings.use_compact_design:
                row.scale_y = 1.2
                row.scale_x = 1.2
            # if global_layer and global_layer.mask_image and global_layer.edit_mask:
            #     row.operator("paint_system.toggle_mask_erase", text="Toggle Mask Erase", depress=brush.blend == 'ERASE_ALPHA', icon="BRUSHES_ALL")
            # else:
            row.operator("paint_system.toggle_brush_erase_alpha", text="Toggle Erase Alpha", depress=brush.blend == 'ERASE_ALPHA', icon="BRUSHES_ALL")
        
        brush_imported = False
        for brush in bpy.data.brushes:
            if brush.name.startswith("PS_"):
                brush_imported = True
                break
        if not brush_imported:
            layout.operator("paint_system.add_preset_brushes",
                            text="Add Preset Brushes", icon="IMPORT")

class MAT_PT_BrushSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_BrushSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_Brush'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        obj = ps_ctx.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw(self, context):
        layout = self.layout
        tool_settings = context.tool_settings.image_paint
        brush = tool_settings.brush
        prop_unified(layout, context, "strength",
                     "use_unified_strength", icon="WORLD", text="Strength")
        prop_unified(layout, context, "size",
                     "use_unified_size", icon="WORLD", text="Size", slider=True)


class MAT_PT_BrushAdvanced(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_BrushAdvanced'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Advacnced Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_Brush'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        image_paint = context.tool_settings.image_paint
        layout.prop(image_paint, "use_occlude", text="Occlude Faces")
        layout.prop(image_paint, "use_backface_culling", text="Backface Culling")
        
        layout.prop(image_paint, "use_normal_falloff", text="Normal Falloff")
        col = layout.column(align=True)
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(image_paint, "normal_angle", text="Angle")
        layout.prop(ps_ctx.ps_settings, "allow_image_overwrite",
                 text="Auto Image Select", icon='FILE_IMAGE')


class MAT_PT_BrushColor(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_BrushColor'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Color"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        obj = ps_ctx.active_object
        return hasattr(obj, "mode") and obj.mode == 'TEXTURE_PAINT'

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="COLOR")

    def draw_header_preset(self, context):
        layout = self.layout
        ups = context.tool_settings.unified_paint_settings
        row = layout.row(align=True)
        row.prop(get_unified_settings(context, "use_unified_color"), "color",
                 text="", icon='IMAGE_RGB_ALPHA')
        row.prop(ups, "use_unified_color",
                 text="", icon='WORLD')
        # prop_unified(layout, context, "color", "use_unified_color",
        #              icon="IMAGE_RGB_ALPHA", text="Color")
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

classes = (
    MAT_PT_BrushTooltips,
    MAT_PT_Brush,
    MAT_PT_BrushAdvanced,
    MAT_PT_BrushColor,
)

register, unregister = register_classes_factory(classes)