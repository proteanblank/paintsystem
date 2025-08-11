import bpy
from bpy.utils import register_classes_factory
from bpy.types import Panel
from .common import PSContextMixin, get_icon

class MAT_PT_PaintSystemMainPanel(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_PaintSystemMainPanel'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System"
    bl_category = 'Paint System'
    
    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("paint_system.new_group", text="", icon="ADD")
        row.operator("paint_system.delete_group", text="", icon="REMOVE")
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon_value=get_icon("sunflower"))

    def draw(self, context):
        layout = self.layout
        # ps_ctx = self.ensure_context(context)  # not strictly necessary here
        layout.label(text="Welcome to the Paint System!")
        layout.operator("paint_system.new_image_layer", text="Create New Image Layer")


classes = (
    MAT_PT_PaintSystemMainPanel,
)

register, unregister = register_classes_factory(classes)