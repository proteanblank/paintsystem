import bpy

bl_info = {
    "name": "Header Label Add-on",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Header",
    "description": "Adds a custom label to the 3D View header.",
    "category": "User Interface",
}

# 1. Define a Property Group to store the text.


class MyAddonProperties(bpy.types.PropertyGroup):
    header_text: bpy.props.StringProperty(
        name="Header Text",
        default="Hello Header!",
        description="Text to display in the 3D View header.",
    )


# 2. Define a Panel to add the text in the Header
class VIEW3D_HT_my_header(bpy.types.Header):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    def draw(self, context):
        layout = self.layout
        props = context.scene.my_addon

        layout.label(text=props.header_text)


def register():
    bpy.utils.register_class(MyAddonProperties)
    bpy.utils.register_class(VIEW3D_HT_my_header)
    bpy.types.Scene.my_addon = bpy.props.PointerProperty(
        type=MyAddonProperties)


def unregister():
    del bpy.types.Scene.my_addon
    bpy.utils.unregister_class(VIEW3D_HT_my_header)
    bpy.utils.unregister_class(MyAddonProperties)


if __name__ == '__main__':
    register()
