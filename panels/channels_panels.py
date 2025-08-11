import bpy
from bpy.types import UIList
from bpy.utils import register_classes_factory
from bpy.types import Panel
from .common import PSContextMixin, get_icon

class PAINTSYSTEM_UL_channels(UIList):
    """UIList for displaying paint channels."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        channel = item
        row = layout.row(align=True)
        row.prop(channel, "type", text="", icon_only=True, emboss=False)
        row.prop(channel, "name", text="", emboss=False)

    # def filter_items(self, context, data, propname):
    #     channels = getattr(data, propname)
    #     flt_flags = [self.bitflag_filter_item] * len(channels)
    #     flt_neworder = list(range(len(channels)))
    #     return flt_flags, flt_neworder

class MAT_PT_ChannelsSelect(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_ChannelsSelect'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Channels"
    bl_ui_units_x = 8
    
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        layout.template_list(
            "PAINTSYSTEM_UL_channels", 
            "",
            ps_ctx.active_group,
            "channels", 
            ps_ctx.active_group,
            "active_index",
            rows=max(len(ps_ctx.active_group.channels), 4),
        )

class MAT_PT_ChannelsPanel(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_ChannelsPanel'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Channels"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.ps_mat_data and ps_ctx.active_group is not None
    
    # def draw_header(self, context):
    #     layout = self.layout
    #     type_to_icon = {
    #         'COLOR': 'color_socket',
    #         'VECTOR': 'vector_socket',
    #         'VALUE': 'value_socket',
    #     }
    #     layout.label(icon_value=get_icon(type_to_icon.get(self.active_channel.type, 'color_socket')))
        
    def draw_header_preset(self, context):
        layout = self.layout
        type_to_icon = {
            'COLOR': 'color_socket',
            'VECTOR': 'vector_socket',
            'FLOAT': 'float_socket',
        }
        ps_ctx = self.ensure_context(context)
        if ps_ctx.active_channel:
            layout.popover(
                panel="MAT_PT_ChannelsSelect",
                text=ps_ctx.active_channel.name if ps_ctx.active_channel else "No Channel",
                icon_value=get_icon(type_to_icon.get(ps_ctx.active_channel.type, 'color_socket'))
            )

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        row = layout.row()
        row.template_list(
            "PAINTSYSTEM_UL_channels", 
            "",
            ps_ctx.active_group,
            "channels", 
            ps_ctx.active_group,
            "active_index",
            rows=max(len(ps_ctx.active_group.channels), 4),
        )
        col = row.column(align=True)
        col.operator("paint_system.add_channel", icon='ADD', text="")
        col.operator("paint_system.delete_channel", icon='REMOVE', text="")
        col.operator("paint_system.move_channel_up", icon='TRIA_UP', text="")
        col.operator("paint_system.move_channel_down", icon='TRIA_DOWN', text="")


class MAT_PT_ChannelsSettings(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_ChannelsSettings'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Channels Settings"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_PaintSystemMainPanel'
    
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        layout.prop(ps_ctx.active_channel, "use_alpha")


classes = (
    PAINTSYSTEM_UL_channels,
    MAT_PT_ChannelsSelect,
    MAT_PT_ChannelsPanel,
    MAT_PT_ChannelsSettings,
)

register, unregister = register_classes_factory(classes)