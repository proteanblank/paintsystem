import bpy
from bpy.types import Panel
from bpy.utils import register_classes_factory

class MAT_PT_PaintSystemMainPanel(Panel):
    bl_idname = 'MAT_PT_PaintSystemMainPanel'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System"
    bl_category = 'Paint System'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Welcome to the Paint System!")
        layout.operator("paint_system.new_image_layer", text="Create New Image Layer")
        # ps = PaintSystem(context)
        # obj = ps.active_object

        # if not obj:
        #     layout.label(text="No active object found.")
        #     return

        # # Add your custom UI elements here
        # layout.label(text=f"Active Object: {obj.name}")
        # layout.operator("paintsystem.some_operator", text="Some Operator")


classes = (
    MAT_PT_PaintSystemMainPanel,
)

register, unregister = register_classes_factory(classes)