import bpy
from bpy.types import Operator
from ..utils import get_next_unique_name
from ..paintsystem import parse_context
from ..paintsystem.data import CHANNEL_TYPE_ENUM
from .utils import redraw_panel
from .common import PSContextMixin

class PAINTSYSTEM_OT_AddChannel(PSContextMixin, Operator):
    """Create a new channel in the Paint System"""
    bl_idname = "paint_system.add_channel"
    bl_label = "Add Channel"
    bl_options = {'REGISTER', 'UNDO'}
    
    def get_unique_channel_name(self, context):
        """Set a unique name for the new channel."""
        parsed_context = parse_context(context)
        active_group = parsed_context.get("active_group")
        return get_next_unique_name(self.channel_name, [channel.name for channel in active_group.channels])

    channel_name: bpy.props.StringProperty(
        name="Channel Name",
        description="Name of the new channel",
        default="New Channel",
    )
    channel_type: bpy.props.EnumProperty(
        name="Channel Type",
        description="Type of the new channel",
        items=CHANNEL_TYPE_ENUM,
        default='COLOR'
    )
    
    def execute(self, context):
        channels = self.active_group.channels
        new_channel = channels.add()
        unique_name = self.get_unique_channel_name(context)
        new_channel.name = unique_name
        new_channel.type = self.channel_type
        redraw_panel(context)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        """Invoke the operator to create a new channel."""
        self.channel_name = self.get_unique_channel_name(context)
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "channel_name", text="Name")
        layout.prop(self, "channel_type", text="Type")
        unique_name = self.get_unique_channel_name(context)
        if unique_name != self.channel_name:
            box = layout.box()
            box.alert = True
            box.alignment = 'CENTER'
            box.label(text=f"Name will be changed to '{unique_name}'", icon='ERROR')

class PAINTSYSTEM_OT_DeleteChannel(PSContextMixin, Operator):
    """Delete the selected channel in the Paint System"""
    bl_idname = "paint_system.delete_channel"
    bl_label = "Delete Channel"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def _poll(self, context):
        return self.ps_mat_data and self.ps_mat_data.active_index >= 0

    def execute(self, context):
        
        active_index = self.ps_mat_data.active_index
        if active_index < 0 or active_index >= len(self.active_group.channels):
            self.report({'ERROR'}, "No valid channel selected")
            return {'CANCELLED'}
        
        self.active_group.channels.remove(active_index)
        self.ps_mat_data.active_index = max(0, active_index - 1)
        redraw_panel(context)
        return {'FINISHED'}

classes = (
    PAINTSYSTEM_OT_AddChannel,
    PAINTSYSTEM_OT_DeleteChannel,
)

register, unregister = bpy.utils.register_classes_factory(classes)