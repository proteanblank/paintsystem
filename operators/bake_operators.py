import bpy
from bpy.types import Operator
from bpy.utils import register_classes_factory
from bpy.props import StringProperty

from .common import PSContextMixin, PSImageCreateMixin, PSUVOptionsMixin

from ..paintsystem.data import get_global_layer
from ..utils.nodes import get_material_output

class PAINTSYSTEM_OT_BakeChannel(PSContextMixin, PSUVOptionsMixin, PSImageCreateMixin, Operator):
    """Bake the active channel"""
    bl_idname = "paint_system.bake_channel"
    bl_label = "Bake Channel"
    bl_description = "Bake the active channel"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}
    
    uv_map: StringProperty(
        name= "UV Map",
        default= "UVMap",
        options={'SKIP_SAVE'}
    )
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.active_channel
    
    def invoke(self, context, event):
        """Invoke the operator to create a new channel."""
        ps_ctx = self.parse_context(context)
        self.get_coord_type(context)
        if self.coord_type == 'AUTO':
            self.uv_map = "PS_UVMap"
        else:
            self.uv_map = self.uv_map_name
        self.image_name = f"Bake Image ({ps_ctx.active_channel.name})"
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        self.image_create_ui(layout, context)
        box = layout.box()
        box.label(text="UV Map", icon='UV')
        box.prop_search(self, "uv_map", context.object.data, "uv_layers", text="")
    
    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_channel = ps_ctx.active_channel
        mat = ps_ctx.active_material
        bake_image = active_channel.bake_image
        
        if not bake_image:
            self.image_name = f"Bake Image ({ps_ctx.active_channel.name})"
            bake_image = self.create_image()
            bake_image.colorspace_settings.name = 'sRGB'
            active_channel.bake_image = bake_image
        elif bake_image.size[0] != self.image_width or bake_image.size[1] != self.image_height:
            bake_image.scale(self.image_width, self.image_height)
            
        active_channel.bake_channel(context, mat, bake_image, self.uv_map)
        # Return to object mode
        bpy.ops.object.mode_set(mode="OBJECT")
        return {'FINISHED'}


class PAINTSYSTEM_OT_BakeAllChannels(PSContextMixin, PSUVOptionsMixin, PSImageCreateMixin, Operator):
    bl_idname = "paint_system.bake_all_channels"
    bl_label = "Bake All Channels"
    bl_description = "Bake all channels"
    bl_options = {'INTERNAL', 'REGISTER', 'UNDO'}
    
    uv_map: StringProperty(
        name= "UV Map",
        default= "UVMap",
        options={'SKIP_SAVE'}
    )
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.active_channel
    
    def invoke(self, context, event):
        """Invoke the operator to create a new channel."""
        ps_ctx = self.parse_context(context)
        self.get_coord_type(context)
        if self.coord_type == 'AUTO':
            self.uv_map = "PS_UVMap"
        else:
            self.uv_map = self.uv_map_name
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "uv_map", context.object.data, "uv_layers", text="")
    
    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_group = ps_ctx.active_group
        if not active_group:
            return {'CANCELLED'}
        
        for channel in active_group.channels:
            mat = ps_ctx.active_material
            bake_image = channel.bake_image
            
            if not bake_image:
                self.image_name = f"Bake Image ({channel.name})"
                bake_image = self.create_image()
                bake_image.colorspace_settings.name = 'sRGB'
                channel.bake_image = bake_image
            elif bake_image.size[0] != self.image_width or bake_image.size[1] != self.image_height:
                bake_image.scale(self.image_width, self.image_height)
                
            channel.bake_channel(context, mat, bake_image, self.uv_map)
        return {'FINISHED'}


class PAINTSYSTEM_OT_ExportBakedImage(PSContextMixin, Operator):
    bl_idname = "paint_system.export_baked_image"
    bl_label = "Export Baked Image"
    bl_description = "Export the baked image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        image = active_channel.bake_image
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.save_as('INVOKE_DEFAULT', copy=True)
        return {'FINISHED'}


class PAINTSYSTEM_OT_DeleteBakedImage(PSContextMixin, Operator):
    bl_idname = "paint_system.delete_bake_image"
    bl_label = "Delete Baked Image"
    bl_description = "Delete the baked image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        image = active_channel.bake_image
        if not image:
            self.report({'ERROR'}, "No baked image found.")
            return {'CANCELLED'}

        bpy.data.images.remove(image)
        active_channel.bake_image = None
        active_channel.use_bake_image = False
        active_channel.bake_uv_map = ""

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text="Click OK to delete the baked image.")


class PAINTSYSTEM_OT_TransferImageLayerUV(PSContextMixin, Operator):
    bl_idname = "paint_system.transfer_image_layer_uv"
    bl_label = "Transfer Image Layer UV"
    bl_description = "Transfer the UV of the image layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    uv_map: StringProperty(
        name= "UV Map",
        options={'SKIP_SAVE'},
    )
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.active_channel and ps_ctx.active_global_layer.type == 'IMAGE' and ps_ctx.active_global_layer.image
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "uv_map", context.object.data, "uv_layers", text="")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="This cannot be undone!", icon='ERROR')

    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_channel = ps_ctx.active_channel
        active_global_layer = ps_ctx.active_global_layer
        if not active_channel:
            return {'CANCELLED'}
        
        to_be_enabled_layers = []
        # Ensure all layers are disabled except the active layer
        for layer in active_channel.layers:
            global_layer = get_global_layer(layer)
            if global_layer.enabled:
                to_be_enabled_layers.append(global_layer)
                global_layer.enabled = False
        active_channel.bake_channel(context, ps_ctx.active_material, active_global_layer.image, self.uv_map, use_group_tree=False)
        # Restore the layers
        for layer in to_be_enabled_layers:
            layer.enabled = True
        
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_BakeChannel,
    PAINTSYSTEM_OT_BakeAllChannels,
    PAINTSYSTEM_OT_TransferImageLayerUV,
    PAINTSYSTEM_OT_ExportBakedImage,
    PAINTSYSTEM_OT_DeleteBakedImage,
)

register, unregister = register_classes_factory(classes)