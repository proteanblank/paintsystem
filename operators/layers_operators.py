import bpy
from bpy.utils import register_classes_factory
from .paintsystem.create import create_image_layer

class PAINTSYSTEM_OT_NewImage(bpy.types.Operator):
    """Create a new image layer"""
    bl_idname = "paint_system.new_image_layer"
    bl_label = "New Image Layer"
    bl_options = {'REGISTER', 'UNDO'}

    layer_name: bpy.props.StringProperty(
        name="Layer Name",
        description="Name of the new image layer",
        default="New Image Layer"
    )

    def execute(self, context):
        img = bpy.data.images.new(name=self.layer_name, width=1024, height=1024)
        new_layer = create_image_layer(img, self.layer_name)
        return {'FINISHED'}
    
classes = (PAINTSYSTEM_OT_NewImage,)

register, unregister = register_classes_factory(classes)