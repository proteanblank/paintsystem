import bpy
from ..paintsystem.data import PSContextMixin, get_global_layer
from ..custom_icons import get_icon
from ..preferences import get_preferences
from ..utils.unified_brushes import get_unified_settings
from bpy.types import Operator, Context
from bpy.props import BoolProperty

icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()

def icon_parser(icon: str, default="NONE") -> str:
    if icon in icons:
        return icon
    return default

def scale_content(context, layout, scale_x=1.2, scale_y=1.2):
    """Scale the content of the panel."""
    prefs = get_preferences(context)
    if not prefs.use_compact_design:
        layout.scale_x = scale_x
        layout.scale_y = scale_y
    return layout

class MultiMaterialOperator(Operator):
    multiple_objects: BoolProperty(
        name="Multiple Objects",
        description="Run the operator on multiple objects",
        default=True,
    )
    multiple_materials: BoolProperty(
        name="Multiple Materials",
        description="Run the operator on multiple materials",
        default=False,
    )
    def execute(self, context: Context):
        error_count = 0
        ps_ctx = PSContextMixin.ensure_context(context)
        objects = set()
        objects.add(ps_ctx.ps_object)
        if self.multiple_objects:
            objects.update(context.selected_objects)
        
        seen_materials = set()
        for object in objects:
            if object.type != 'MESH':
                continue
            object_mats = object.data.materials
            if object_mats:
                if self.multiple_materials:
                    for mat in object_mats:
                        if mat in seen_materials:
                            continue
                        with context.temp_override(object=object, active_object=object, selected_objects=[object], active_material=mat):
                            error_count += not bool(self.process_material(bpy.context))
                        seen_materials.add(mat)
                else:
                    if object.active_material in seen_materials:
                        continue
                    with context.temp_override(object=object, active_object=object, selected_objects=[object], active_material=object.active_material):
                        error_count += not bool(self.process_material(bpy.context))
                    seen_materials.add(object.active_material)
            else:
                with context.temp_override(object=object, active_object=object, selected_objects=[object]):
                    error_count += not bool(self.process_material(bpy.context))
        
        if error_count > 0:
            self.report({'WARNING'}, f"Completed with {error_count} error{'s' if error_count > 1 else ''}")
        
        return {'FINISHED'}
    
    def process_material(self, context: Context):
        """Override this method in subclasses to process the material."""
        raise NotImplementedError("Subclasses must implement this method.")
        
    def multiple_objects_ui(self, layout, context: Context):
        if len(context.selected_objects) > 1:
            box = layout.box()
            box.label(text="Applying to all selected objects", icon='INFO')