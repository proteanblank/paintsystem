import bpy
from bpy.types import Menu, Operator
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty, FloatProperty
from bpy.utils import register_classes_factory
from .common import PSImageFilterMixin, get_unified_settings
from .image_filters import (
    blender_image_to_numpy,
    numpy_to_blender_image,
    switch_image_content,
    gaussian_blur,
    )
import numpy


class PAINTSYSTEM_OT_InvertColors(PSImageFilterMixin, Operator):
    bl_idname = "paint_system.invert_colors"
    bl_label = "Invert Colors"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Invert the colors of the active image"

    invert_r: BoolProperty(default=True)
    invert_g: BoolProperty(default=True)
    invert_b: BoolProperty(default=True)
    invert_a: BoolProperty(default=False)

    def execute(self, context):
        image: bpy.types.Image = self.get_image(context)
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.invert('INVOKE_DEFAULT', invert_r=self.invert_r,
                                 invert_g=self.invert_g, invert_b=self.invert_b, invert_a=self.invert_a)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "invert_r", text="Red")
        layout.prop(self, "invert_g", text="Green")
        layout.prop(self, "invert_b", text="Blue")
        layout.prop(self, "invert_a", text="Alpha")


class PAINTSYSTEM_OT_ResizeImage(PSImageFilterMixin, Operator):
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

    width: IntProperty(name="Width", default=1024, subtype='PIXEL')
    height: IntProperty(name="Height", default=1024, subtype='PIXEL')
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
    base_width: IntProperty()
    base_height: IntProperty()

    def execute(self, context):
        image = self.get_image(context)
        image.scale(self.width, self.height)
        return {'FINISHED'}

    def invoke(self, context, event):
        image = self.get_image(context)
        self.base_width, self.base_height = image.size
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


class PAINTSYSTEM_OT_ClearImage(PSImageFilterMixin, Operator):
    bl_idname = "paint_system.clear_image"
    bl_label = "Clear Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Clear the active image"

    def execute(self, context):
        image = self.get_image(context)
        # Replace every pixel with a transparent pixel
        pixels = numpy.empty(len(image.pixels), dtype=numpy.float32)
        pixels[::4] = 0.0
        image.pixels.foreach_set(pixels)
        image.update()
        image.update_tag()
        return {'FINISHED'}
    
class PAINTSYSTEM_OT_FillImage(PSImageFilterMixin, Operator):
    bl_idname = "paint_system.fill_image"
    bl_label = "Fill Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Fill the active image with current color"
    
    def execute(self, context):
        image = self.get_image(context)
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


class PAINTSYSTEM_OT_GaussianBlur(PSImageFilterMixin, Operator):
    bl_idname = "paint_system.gaussian_blur"
    bl_label = "Gaussian Blur"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Apply a Gaussian blur to the active image"
    
    gaussian_sigma: FloatProperty(name="Gaussian Sigma", default=3.0, min=0.1, max=10.0, step=0.1)
    
    def execute(self, context):
        image = self.get_image(context)
        np_image = blender_image_to_numpy(image)
        np_image = gaussian_blur(np_image, self.gaussian_sigma)
        new_image = numpy_to_blender_image(np_image, image.name)
        switch_image_content(image, new_image)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "gaussian_sigma")


classes = (
    PAINTSYSTEM_OT_InvertColors,
    PAINTSYSTEM_OT_ResizeImage,
    PAINTSYSTEM_OT_ClearImage,
    PAINTSYSTEM_OT_FillImage,
    PAINTSYSTEM_OT_GaussianBlur,
)
register, unregister = register_classes_factory(classes)