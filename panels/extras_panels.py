import bpy
from bpy.types import Panel, Menu
from bpy.utils import register_classes_factory
# from ..utils.unified_brushes import get_unified_settings, paint_settings
from .common import PSContextMixin, get_event_icons, find_keymap, find_keymap_by_name, scale_content
from ..utils.version import is_newer_than

from bl_ui.properties_grease_pencil_common import (
    GreasePencilSculptAdvancedPanel,
    GreasePencilDisplayPanel,
    GreasePencilBrushFalloff,
)
from bl_ui.properties_paint_common import (
    UnifiedPaintPanel,
    BrushSelectPanel,
    ClonePanel,
    TextureMaskPanel,
    ColorPalettePanel,
    StrokePanel,
    SmoothStrokePanel,
    FalloffPanel,
    DisplayPanel,
    brush_texture_settings,
    brush_mask_texture_settings,
    brush_settings,
    brush_settings_advanced,
    draw_color_settings,
)

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

class MAT_PT_Brush(PSContextMixin, Panel, UnifiedPaintPanel):
    bl_idname = 'MAT_PT_Brush'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Brush"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        mode = cls.get_brush_mode(context)
        return mode in ['PAINT_TEXTURE', 'PAINT_GREASE_PENCIL', 'VERTEX_GREASE_PENCIL', 'WEIGHT_GREASE_PENCIL', 'SCULPT_GREASE_PENCIL']

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="BRUSHES_ALL")

    def draw_header_preset(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        settings = self.paint_settings(context)
        brush = settings.brush
        obj = ps_ctx.ps_object
        row = layout.row()
        match obj.type:
            case 'GREASEPENCIL':
                row.label(text="Grease Pencil", icon="GREASEPENCIL")
            case 'MESH':
                self.prop_unified(row, context, brush, "size",
                    "use_unified_size", icon="WORLD", text="Size", slider=True, header=True)
            case _:
                pass
            
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        settings = self.paint_settings(context)
        brush = settings.brush
        mode = self.get_brush_mode(context)
        # Check blender version
        if not is_newer_than(4, 3):
            layout.template_ID_preview(settings, "brush",
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
        col = box.column(align=True)
        scale_content(context, col, scale_x=1, scale_y=1.2)
        brush_settings(col, context, brush, popover=self.is_popover)
        
        brush_imported = False
        for brush in bpy.data.brushes:
            if brush.name.startswith("PS_"):
                brush_imported = True
                break
        if not brush_imported:
            layout.operator("paint_system.add_preset_brushes",
                            text="Add Preset Brushes", icon="IMPORT")

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


class MAT_PT_BrushColor(PSContextMixin, Panel, UnifiedPaintPanel):
    bl_idname = 'MAT_PT_BrushColor'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Color"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    # bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        settings = cls.paint_settings(context)
        if not settings:
            return False
        brush = settings.brush

        if context.image_paint_object:
            capabilities = brush.image_paint_capabilities
            return capabilities.has_color

        return False

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="COLOR")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = self.paint_settings(context)
        brush = settings.brush
        self.prop_unified_color(layout, context, brush, "color", text="")

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.scale_y = 1.2
        row.prop(context.preferences.view, "color_picker_type", text="")
        settings = self.paint_settings(context)
        brush = settings.brush
        draw_color_settings(context, col, brush)
        # tool_settings = bpy.context.scene.tool_settings
        # unified_settings = tool_settings.unified_paint_settings
        # brush_settings = tool_settings.image_paint.brush
        # col.template_color_picker(
        #     unified_settings if unified_settings.use_unified_color else brush_settings, "color", value_slider=True)

classes = (
    MAT_PT_BrushTooltips,
    MAT_PT_Brush,
    MAT_PT_BrushAdvanced,
    MAT_PT_BrushColor,
)

register, unregister = register_classes_factory(classes)