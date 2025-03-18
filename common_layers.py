import bpy
from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty,
)
from bpy.types import Operator, Context
from .common import get_object_uv_maps
from .paint_system import PaintSystem

class UVLayerHandler(Operator):
    uv_map_mode: EnumProperty(
        name="UV Map",
        items=[
            ('PAINT_SYSTEM', "Paint System UV", "Use the Paint System UV Map"),
            ('OPEN', "Use Existing", "Open an existing UV Map"),
        ]
    )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )
    
    def set_uv_mode(self, context: Context):
        ps = PaintSystem(context)
        mat_settings = ps.get_material_settings()
        if mat_settings:
            ps.get_material_settings().use_paintsystem_uv = self.uv_map_mode == "PAINT_SYSTEM"
    
    def save_uv_mode(self, context: Context):
        ps = PaintSystem(context)
        mat_settings = ps.get_material_settings()
        if mat_settings:
            self.uv_map_mode = 'PAINT_SYSTEM' if mat_settings.use_paintsystem_uv else 'OPEN'
            
    def select_uv_ui(self, layout):
        layout.label(text="UV Map", icon='UV')
        row = layout.row(align=True)
        row.prop(self, "uv_map_mode", expand=True)
        if self.uv_map_mode == 'OPEN':
            layout.prop(self, "uv_map_name", text="")
