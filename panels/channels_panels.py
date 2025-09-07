import bpy
from bpy.types import UIList
from bpy.utils import register_classes_factory
from bpy.types import Panel
from .common import (
    PSContextMixin,
    get_icon_from_channel,
    get_group_node,
    check_group_multiuser
)

class PAINTSYSTEM_UL_channels(PSContextMixin, UIList):
    """UIList for displaying paint channels."""

    def draw_item(self, context, layout: bpy.types.UILayout, data, item, icon, active_data, active_propname, index):
        channel = item
        ps_ctx = self.parse_context(context)
        split = layout.split(factor=0.6)
        group_node = get_group_node(context)
        icon_row = split.row(align=True)
        icon_row.prop(channel, "type", text="", icon_only=True, emboss=False)
        icon_row.prop(channel, "name", text="", emboss=False)
        if group_node and channel.type == "FLOAT":
            split.prop(group_node.inputs[channel.name], "default_value", text="", slider=channel.use_factor)

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
    bl_ui_units_x = 10
    
    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        col = layout.column(align=True)
        col.label(text="Channels")
        row = col.row()
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
        ps_ctx = cls.parse_context(context)
        ob = context.object
        if ps_ctx.active_group and check_group_multiuser(ps_ctx.active_group.node_tree):
            return False
        return ps_ctx.ps_mat_data and ps_ctx.active_group is not None and ob.mode == 'OBJECT'
    
    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(icon_value=get_icon('channel'))
        
    def draw_header_preset(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        if ps_ctx.active_channel:
            layout.popover(
                panel="MAT_PT_ChannelsSelect",
                text=ps_ctx.active_channel.name if ps_ctx.active_channel else "No Channel",
                icon_value=get_icon_from_channel(ps_ctx.active_channel)
            )

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
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
    bl_parent_id = 'MAT_PT_ChannelsPanel'
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.active_channel is not None and len(ps_ctx.active_group.channels) > 0
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(icon="BLANK1")
        ps_ctx = self.parse_context(context)
        active_channel = ps_ctx.active_channel
        col = row.column(align=True)
        col.prop(active_channel, "use_alpha")
        if active_channel.type == "VECTOR":
            col.prop(active_channel, "use_normalize")


classes = (
    PAINTSYSTEM_UL_channels,
    MAT_PT_ChannelsSelect,
    MAT_PT_ChannelsPanel,
    MAT_PT_ChannelsSettings,
)

register, unregister = register_classes_factory(classes)