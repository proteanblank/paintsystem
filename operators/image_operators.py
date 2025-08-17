import bpy
from bpy.types import Menu, Operator
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty
from bpy.utils import register_classes_factory
from .common import PSContextMixin, get_unified_settings
import numpy


class MAT_MT_ImageMenu(PSContextMixin, Menu):
    bl_label = "Image Menu"
    bl_idname = "MAT_MT_ImageMenu"

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        global_layer = ps_ctx.active_global_layer
        return global_layer and global_layer.image

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.ensure_context(context)
        global_layer = ps_ctx.active_global_layer
        image_name = global_layer.image.name
        layout.operator("paint_system.export_active_layer",
                        text="Export Layer", icon='EXPORT')
        layout.separator()
        layout.operator("paint_system.fill_image", 
                        text="Fill Image", icon='SNAP_FACE').image_name = image_name
        layout.operator("paint_system.invert_colors",
                        icon="MOD_MASK").image_name = image_name
        layout.operator("paint_system.resize_image",
                        icon="CON_SIZELIMIT").image_name = image_name
        layout.operator("paint_system.clear_image",
                        icon="X").image_name = image_name


class PAINTSYSTEM_OT_InvertColors(Operator):
    bl_idname = "paint_system.invert_colors"
    bl_label = "Invert Colors"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Invert the colors of the active image"

    invert_r: BoolProperty(default=True)
    invert_g: BoolProperty(default=True)
    invert_b: BoolProperty(default=True)
    invert_a: BoolProperty(default=False)

    image_name: StringProperty()

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.invert('INVOKE_DEFAULT', invert_r=self.invert_r,
                                 invert_g=self.invert_g, invert_b=self.invert_b, invert_a=self.invert_a)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        # Check if image have alpha channel
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        if not image:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        layout.prop(self, "invert_r", text="Red")
        layout.prop(self, "invert_g", text="Green")
        layout.prop(self, "invert_b", text="Blue")
        layout.prop(self, "invert_a", text="Alpha")


class PAINTSYSTEM_OT_ExportActiveLayer(PSContextMixin, Operator):
    bl_idname = "paint_system.export_active_layer"
    bl_label = "Save Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save the active image"

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_layer = ps_ctx.active_layer
        image = active_layer.image
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.save_as('INVOKE_DEFAULT', copy=True)
        return {'FINISHED'}


class PAINTSYSTEM_OT_ResizeImage(Operator):
    bl_idname = "paint_system.resize_image"
    bl_label = "Resize Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Resize the active image"

    def update_width_height(self, context):
        relative_width = self.width / self.base_width
        relative_height = self.height / self.base_height
        if self.relative_scale != 'CUSTOM' and (relative_width != relative_height or relative_width != self.relative_scale or relative_height != self.relative_scale):
            scale = float(self.relative_scale)
            self.width = int(scale * self.base_width)
            self.height = int(scale * self.base_height)

    width: IntProperty(name="Width", default=1024)
    height: IntProperty(name="Height", default=1024)
    relative_scale: EnumProperty(
        name="Relative Scale",
        description="Scale the image by a factor",
        items=[
            ('0.5', "0.5x", "Half the size"),
            ('1.0', "1x", "Original size"),
            ('2.0', "2x", "Double the size"),
            ('3.0', "3x", "Triple the size"),
            ('4.0', "4x", "Quadruple the size"),
            ('CUSTOM', "Custom", "Custom Size"),
        ],
        default='1.0',
        update=update_width_height,
    )
    image_name: StringProperty()
    base_width: IntProperty()
    base_height: IntProperty()
    image: bpy.types.Image

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image = bpy.data.images.get(self.image_name)
        image.scale(self.width, self.height)
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        self.image: bpy.types.Image = bpy.data.images.get(self.image_name)
        if not self.image:
            self.report({'ERROR'}, "Image not found")
            return {'CANCELLED'}
        self.base_width, self.base_height = self.image.size
        self.relative_scale = '1.0'
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Scale", icon='IMAGE_DATA')
        row = box.row()
        row.prop(self, "relative_scale", expand=True)
        if self.relative_scale == 'CUSTOM':
            col = box.column(align=True)
            col.prop(self, "width")
            col.prop(self, "height")
        else:
            box.label(text=f"{self.width} x {self.height}")


class PAINTSYSTEM_OT_ClearImage(Operator):
    bl_idname = "paint_system.clear_image"
    bl_label = "Clear Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Clear the active image"

    image_name: StringProperty()

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        # Replace every pixel with a transparent pixel
        pixels = numpy.empty(len(image.pixels), dtype=numpy.float32)
        pixels[::4] = 0.0
        image.pixels.foreach_set(pixels)
        image.update()
        image.update_tag()
        return {'FINISHED'}
    
class PAINTSYSTEM_OT_FillImage(Operator):
    bl_idname = "paint_system.fill_image"
    bl_label = "Fill Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Fill the active image with current color"

    image_name: StringProperty()

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        # Replace every pixel with a transparent pixel
        pixels = numpy.empty(len(image.pixels), dtype=numpy.float32)
        prop_owner = get_unified_settings(context, "use_unified_color")
        color = prop_owner.color
        
        # Fill the image with the current brush color
        pixels[::4] = color[0]  # R
        pixels[1::4] = color[1]  # G
        pixels[2::4] = color[2]  # B
        pixels[3::4] = 1.0  # A - full opacity
        
        image.pixels.foreach_set(pixels)
        image.update()
        image.update_tag()
        return {'FINISHED'}


classes = (
    MAT_MT_ImageMenu,
    PAINTSYSTEM_OT_InvertColors,
    PAINTSYSTEM_OT_ExportActiveLayer,
    PAINTSYSTEM_OT_ResizeImage,
    PAINTSYSTEM_OT_ClearImage,
    PAINTSYSTEM_OT_FillImage,
)
register, unregister = register_classes_factory(classes)