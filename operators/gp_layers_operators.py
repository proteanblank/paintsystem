import bpy
from bpy.types import Operator
from .common import PSContextMixin, scale_content, get_icon

class PAINTSYSTEM_OT_GPClipLayer(PSContextMixin, Operator):
    """Clip the active layer"""
    bl_idname = "paint_system.gp_clip_layer"
    bl_label = "Clip Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        return context.grease_pencil.layers.active is not None or context.grease_pencil.layer_groups.active is not None
    
    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layers = context.grease_pencil.layers
        active_layer = context.grease_pencil.layers.active
        clip_layer = None
        for 
        if active_layer.use_masks:
        return {'FINISHED'}