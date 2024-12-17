from bpy.types import (Panel,
                       Operator,
                       PropertyGroup)
from bpy.props import (StringProperty,
                       CollectionProperty,
                       PointerProperty,
                       IntProperty,
                       EnumProperty)
import bpy
bl_info = {
    "name": "Material Image Collection",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Properties > Material > Image Collection",
    "description": "Manages images in material collections",
    "category": "Material"
}


class MaterialImage(PropertyGroup):
    """Group of properties representing an image in the collection."""
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image,
    )


class IMAGE_UL_material_images(bpy.types.UIList):
    """UI List for displaying images in the material."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.image:
                layout.prop(item.image, "name", text="",
                            emboss=False, icon='IMAGE_DATA')
            else:
                layout.label(text="Empty Slot", icon='IMAGE_DATA')


class CreateNewImage(Operator):
    """Create a new image and add it to the material collection"""
    bl_idname = "material.create_image"
    bl_label = "Create New Image"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(
        name="Name",
        description="Name of the new image",
        default="New Image"
    )

    width: IntProperty(
        name="Width",
        description="Image width in pixels",
        default=1024,
        min=1,
        max=16384
    )

    height: IntProperty(
        name="Height",
        description="Image height in pixels",
        default=1024,
        min=1,
        max=16384
    )

    color_type: EnumProperty(
        name="Color",
        description="Image color type",
        items=[
            ('COLOR', "Color", "RGB color image"),
            ('BW', "Black & White", "Grayscale image"),
            ('ALPHA', "Alpha", "Alpha channel only")
        ],
        default='COLOR'
    )

    alpha: EnumProperty(
        name="Alpha",
        description="Alpha channel setting",
        items=[
            ('NONE', "None", "No alpha channel"),
            ('STRAIGHT', "Straight", "Straight alpha channel"),
            ('PREMUL', "Premultiplied", "Premultiplied alpha channel")
        ],
        default='STRAIGHT'
    )

    def execute(self, context):
        material = context.material

        # Create new image
        image = bpy.data.images.new(
            name=self.name,
            width=self.width,
            height=self.height,
            alpha=(self.alpha != 'NONE'),
            is_data=False
        )

        # Set image color mode
        if self.color_type == 'BW':
            image.colorspace_settings.name = 'Non-Color'

        # Add to material's collection
        item = material.image_collection.add()
        item.image = image

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "width")
        layout.prop(self, "height")
        layout.prop(self, "color_type")
        if self.color_type == 'COLOR':
            layout.prop(self, "alpha")


class AddImageToMaterial(Operator):
    """Add a new image to the material collection"""
    bl_idname = "material.add_image"
    bl_label = "Add Image"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        name="Image Path",
        description="Path to image file",
        maxlen=1024,
        subtype='FILE_PATH',
    )

    def execute(self, context):
        material = context.material

        # Load the image
        image = bpy.data.images.load(self.filepath)

        # Add to material's collection
        item = material.image_collection.add()
        item.image = image

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class RemoveImageFromMaterial(Operator):
    """Remove the selected image from the material collection"""
    bl_idname = "material.remove_image"
    bl_label = "Remove Image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        material = context.material
        index = material.active_image_index

        material.image_collection.remove(index)
        material.active_image_index = min(
            max(0, index - 1), len(material.image_collection) - 1)

        return {'FINISHED'}


class MATERIAL_PT_image_collection(Panel):
    """Panel for managing material images"""
    bl_label = "Image Collection"
    bl_idname = "MATERIAL_PT_image_collection"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        layout = self.layout
        material = context.material

        if material:
            row = layout.row()
            row.template_list("IMAGE_UL_material_images", "", material, "image_collection",
                              material, "active_image_index")

            col = row.column(align=True)
            col.operator("material.add_image", icon='FILE_FOLDER', text="")
            col.operator("material.create_image", icon='IMAGE_DATA', text="")
            col.operator("material.remove_image", icon='REMOVE', text="")


def register():
    # Register property group for material images
    bpy.utils.register_class(MaterialImage)

    # Add collection property to materials
    bpy.types.Material.image_collection = CollectionProperty(
        type=MaterialImage)
    bpy.types.Material.active_image_index = bpy.props.IntProperty()

    # Register all classes
    bpy.utils.register_class(IMAGE_UL_material_images)
    bpy.utils.register_class(CreateNewImage)
    bpy.utils.register_class(AddImageToMaterial)
    bpy.utils.register_class(RemoveImageFromMaterial)
    bpy.utils.register_class(MATERIAL_PT_image_collection)


def unregister():
    # Unregister all classes
    bpy.utils.unregister_class(MATERIAL_PT_image_collection)
    bpy.utils.unregister_class(RemoveImageFromMaterial)
    bpy.utils.unregister_class(AddImageToMaterial)
    bpy.utils.unregister_class(CreateNewImage)
    bpy.utils.unregister_class(IMAGE_UL_material_images)
    bpy.utils.unregister_class(MaterialImage)

    # Remove properties
    del bpy.types.Material.image_collection
    del bpy.types.Material.active_image_index


if __name__ == "__main__":
    register()
