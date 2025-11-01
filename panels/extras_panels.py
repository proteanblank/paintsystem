import bpy
from bpy.types import Panel, Menu
from bpy.utils import register_classes_factory

from .common import PSContextMixin, get_event_icons, find_keymap, find_keymap_by_name, scale_content, get_icon
from ..utils.version import is_newer_than
from ..utils.unified_brushes import get_unified_settings

from bl_ui.properties_paint_common import (
    UnifiedPaintPanel,
    brush_settings,
    draw_color_settings,
)

class MAT_PT_BrushTooltips(Panel):
    bl_label = "Brush Tooltips"
    bl_description = "Brush Tooltips"
    bl_idname = "MAT_PT_BrushTooltips"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"INSTANCED"}
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
        layout.label(icon_value=get_icon('brush'))

    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     ps_ctx = self.parse_context(context)
    #     settings = self.paint_settings(context)
    #     brush = settings.brush
    #     obj = ps_ctx.ps_object
    #     row = layout.row()
    #     match obj.type:
    #         case 'GREASEPENCIL':
    #             row.label(text="Grease Pencil", icon="GREASEPENCIL")
    #         case 'MESH':
    #             self.prop_unified(row, context, brush, "size",
    #                 "use_unified_size", icon="WORLD", text="Size", slider=True, header=True)
    #         case _:
    #             pass
            
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
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
                icon='INFO_LARGE' if is_newer_than(4,3) else 'INFO'
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
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.ps_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
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


class MAT_PT_BrushColorSettings(PSContextMixin, Panel):
    bl_idname = "MAT_PT_BrushColorSettings"
    bl_label = "Color Picker Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"INSTANCED"}
    bl_ui_units_x = 10
    
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        layout.prop(context.preferences.view, "color_picker_type", text="")
        layout.prop(ps_ctx.ps_settings, "color_picker_scale", text="Color Picker Scale", slider=True)
        layout.prop(ps_ctx.ps_settings, "show_hex_color", text="Show Hex Color")
        layout.prop(ps_ctx.ps_settings, "show_more_color_picker_settings", text="Show HSV Sliders")

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
        ps_ctx = cls.parse_context(context)
        settings = cls.paint_settings(context)
        if not settings:
            return False
        brush = settings.brush
        if ps_ctx.ps_object is None or brush is None:
            return False

        if ps_ctx.ps_object.type == 'MESH':
            if context.image_paint_object:
                capabilities = brush.image_paint_capabilities
                return capabilities.has_color
        elif ps_ctx.ps_object.type == 'GREASEPENCIL':
            from bl_ui.space_toolsystem_common import ToolSelectPanelHelper
            tool = ToolSelectPanelHelper.tool_active_from_context(context)
            if is_newer_than(5,0):
                gpencil_brush_type = brush.gpencil_brush_type
            else:
                gpencil_brush_type = brush.gpencil_tool
            if tool and tool.idname in {"builtin.cutter", "builtin.eyedropper", "builtin.interpolate"}:
                return False
            if gpencil_brush_type == 'TINT':
                return True
            if gpencil_brush_type not in {'DRAW', 'FILL'}:
                return False
            return True
        return False

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon_value=get_icon('color'))

    def draw_header_preset(self, context):
        ps_ctx = self.parse_context(context)
        layout = self.layout
        settings = self.paint_settings(context)
        brush = settings.brush
        if ps_ctx.ps_object.type == 'MESH':
            self.prop_unified_color(layout, context, brush, "color", text="")
        elif ps_ctx.ps_object.type == 'GREASEPENCIL':
            layout.prop(brush, "color", text="")
            

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        col = layout.column()
        settings = self.paint_settings(context)
        brush = settings.brush
        if ps_ctx.ps_object.type == 'MESH':
            row = col.row(align=True)
            row.scale_y = 1.2
            row.popover(
                panel="MAT_PT_BrushColorSettings",
                icon="SETTINGS"
            )
            prop_owner = get_unified_settings(context, "use_unified_color")
            row = col.row()
            row.scale_y = ps_ctx.ps_settings.color_picker_scale
            self.prop_unified_color_picker(row, context, brush, "color", value_slider=True)
            if ps_ctx.ps_settings.show_more_color_picker_settings:
                if not context.preferences.view.color_picker_type == "SQUARE_SV":
                    col.prop(ps_ctx.ps_scene_data, "hue", text="Hue")
                col.prop(ps_ctx.ps_scene_data, "saturation", text="Saturation")
                col.prop(ps_ctx.ps_scene_data, "value", text="Value")
            if ps_ctx.ps_settings.show_hex_color:
                row = col.row()
                row.prop(ps_ctx.ps_scene_data, "hex_color", text="Hex")
            if is_newer_than(4,5):
                from bl_ui.properties_paint_common import color_jitter_panel
                color_jitter_panel(col, context, brush)
            # draw_color_settings(context, col, brush)
        if ps_ctx.ps_object.type == 'GREASEPENCIL':
            row = col.row()
            row.prop(settings, "color_mode", expand=True)
            use_unified_paint = (context.object.mode != 'PAINT_GREASE_PENCIL')
            ups = context.tool_settings.unified_paint_settings
            prop_owner = ups if use_unified_paint and ups.use_unified_color else brush
            enable_color_picker = settings.color_mode == 'VERTEXCOLOR'
            if not enable_color_picker:
                ma = ps_ctx.ps_object.active_material
                icon_id = 0
                txt_ma = ""
                if ma:
                    ma.id_data.preview_ensure()
                    if ma.id_data.preview:
                        icon_id = ma.id_data.preview.icon_id
                        txt_ma = ma.name
                        maxw = 25
                        if len(txt_ma) > maxw:
                            txt_ma = txt_ma[:maxw - 5] + '..' + txt_ma[-3:]
                col.popover(
                    panel="TOPBAR_PT_grease_pencil_materials",
                    text=txt_ma,
                    icon_value=icon_id,
                )
                return
            # This panel is only used for Draw mode, which does not use unified paint settings.
            row = col.row(align=True)
            row.scale_y = 1.2
            row.prop(context.preferences.view, "color_picker_type", text="")
            row = col.row()
            row.scale_y = ps_ctx.ps_settings.color_picker_scale
            row.template_color_picker(prop_owner, "color", value_slider=True)

            sub_row = col.row(align=True)
            if use_unified_paint:
                self.prop_unified_color(sub_row, context, brush, "color", text="")
                self.prop_unified_color(sub_row, context, brush, "secondary_color", text="")
            else:
                sub_row.prop(brush, "color", text="")
                sub_row.prop(brush, "secondary_color", text="")

            sub_row.operator("paint.brush_colors_flip", icon='FILE_REFRESH', text="")

classes = (
    MAT_PT_BrushTooltips,
    MAT_PT_Brush,
    MAT_PT_BrushAdvanced,
    MAT_PT_BrushColorSettings,
    MAT_PT_BrushColor,
)

register, unregister = register_classes_factory(classes)