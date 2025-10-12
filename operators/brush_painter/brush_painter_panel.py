import bpy
from bpy.types import Panel, PropertyGroup
from bpy.props import (
    StringProperty,
    FloatProperty,
    IntProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty
)

class BrushPainterProperties(PropertyGroup):
    """Properties for the Brush Painter addon."""
    
    # Brush settings
    brush_coverage_density: FloatProperty(
        name="Coverage Density",
        description="Target coverage: fraction of image area covered by brushes",
        default=0.7,
        min=0.1,
        max=1.0,
        step=0.1
    )
    
    min_brush_scale: FloatProperty(
        name="Min Brush Scale",
        description="Minimum scale of the brush (0.0 to 1.0)",
        default=0.03,
        min=0.01,
        max=0.5,
        step=0.01
    )
    
    max_brush_scale: FloatProperty(
        name="Max Brush Scale",
        description="Maximum scale of the brush (0.0 to 1.0)",
        default=0.1,
        min=0.01,
        max=0.5,
        step=0.01
    )
    
    start_opacity: FloatProperty(
        name="Start Opacity",
        description="Starting opacity for brush strokes",
        default=0.4,
        min=0.0,
        max=1.0,
        step=0.1
    )
    
    end_opacity: FloatProperty(
        name="End Opacity",
        description="Ending opacity for brush strokes",
        default=1.0,
        min=0.0,
        max=1.0,
        step=0.1
    )
    
    steps: IntProperty(
        name="Steps",
        description="Number of different brush scales to apply",
        default=7,
        min=1,
        max=20
    )
    
    gradient_threshold: FloatProperty(
        name="Gradient Threshold",
        description="Minimum edge strength to place a brush",
        default=0.0,
        min=0.0,
        max=1.0,
        step=0.01
    )
    
    gaussian_sigma: FloatProperty(
        name="Gaussian Sigma",
        description="Blur strength for preprocessing",
        default=3.0,
        min=0.1,
        max=10.0,
        step=0.1
    )
    
    # Brush texture settings
    brush_folder_path: StringProperty(
        name="Brush Folder",
        description="Path to folder containing brush textures",
        default="",
        subtype='DIR_PATH'
    )
    
    brush_texture_path: StringProperty(
        name="Single Brush Texture",
        description="Path to a single brush texture file",
        default="",
        subtype='FILE_PATH'
    )
    
    brush_mode: EnumProperty(
        name="Brush Mode",
        description="Choose brush texture source",
        items=[
            ('FOLDER', "Brush Folder", "Use multiple brushes from a folder"),
            ('SINGLE', "Single Brush", "Use a single brush texture"),
            ('DEFAULT', "Default Circular", "Use default circular brush")
        ],
        default='DEFAULT'
    )
    
    # Image selection
    target_image: PointerProperty(
        name="Target Image",
        description="Image to apply brush effects to",
        type=bpy.types.Image
    )
    
    create_new_image: BoolProperty(
        name="Create New Image",
        description="Create a new image instead of modifying the original",
        default=True
    )

class BRUSH_PT_painter_panel(Panel):
    """Creates a Panel in the 3D Viewport N-panel"""
    bl_label = "Brush Painter"
    bl_idname = "BRUSH_PT_painter_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Brush Painter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.brush_painter_props
        
        # Image selection
        box = layout.box()
        box.label(text="Image Selection", icon='IMAGE_DATA')
        box.prop(props, "target_image", text="Target Image")
        box.prop(props, "create_new_image", text="Create New Image")
        
        # Brush texture settings
        box = layout.box()
        box.label(text="Brush Textures", icon='BRUSH_DATA')
        box.prop(props, "brush_mode", text="Mode")
        
        if props.brush_mode == 'FOLDER':
            box.prop(props, "brush_folder_path", text="Brush Folder")
        elif props.brush_mode == 'SINGLE':
            box.prop(props, "brush_texture_path", text="Brush Texture")
        
        # Brush parameters
        box = layout.box()
        box.label(text="Brush Parameters")
        
        col = box.column(align=True)
        col.prop(props, "brush_coverage_density", text="Coverage Density")
        col.prop(props, "min_brush_scale", text="Min Scale")
        col.prop(props, "max_brush_scale", text="Max Scale")
        
        col = box.column(align=True)
        col.prop(props, "start_opacity", text="Start Opacity")
        col.prop(props, "end_opacity", text="End Opacity")
        col.prop(props, "steps", text="Steps")
        
        # Advanced settings
        box = layout.box()
        box.label(text="Advanced Settings", icon='SETTINGS')
        box.prop(props, "gradient_threshold", text="Gradient Threshold")
        box.prop(props, "gaussian_sigma", text="Gaussian Sigma")
        
        # Apply button
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        row.operator("brush_painter.apply_brushes", text="Apply Brush Effects", icon='BRUSH_DATA')

def register():
    bpy.utils.register_class(BrushPainterProperties)
    bpy.utils.register_class(BRUSH_PT_painter_panel)
    bpy.types.Scene.brush_painter_props = PointerProperty(type=BrushPainterProperties)

def unregister():
    del bpy.types.Scene.brush_painter_props
    bpy.utils.unregister_class(BRUSH_PT_painter_panel)
    bpy.utils.unregister_class(BrushPainterProperties)
