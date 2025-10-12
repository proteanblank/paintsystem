import bpy
import bmesh
import os
import numpy as np
from bpy.types import Operator
from bpy.props import StringProperty
from .brush_painter_core import BrushPainterCore

class BRUSH_OT_apply_brushes(Operator):
    """Apply brush painting effects to the selected image"""
    bl_idname = "brush_painter.apply_brushes"
    bl_label = "Apply Brush Effects"
    bl_description = "Apply artistic brush strokes to the selected image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.brush_painter_props
        
        # Check if target image is selected
        if props.target_image is None:
            self.report({'ERROR'}, "No target image selected!")
            return {'CANCELLED'}
        
        # Initialize brush painter core
        painter = BrushPainterCore()
        
        # Set parameters from UI
        painter.brush_coverage_density = props.brush_coverage_density
        painter.min_brush_scale = props.min_brush_scale
        painter.max_brush_scale = props.max_brush_scale
        painter.start_opacity = props.start_opacity
        painter.end_opacity = props.end_opacity
        painter.steps = props.steps
        painter.gradient_threshold = props.gradient_threshold
        painter.gaussian_sigma = props.gaussian_sigma
        
        # Set brush paths based on mode
        brush_folder_path = None
        brush_texture_path = None
        
        if props.brush_mode == 'FOLDER' and props.brush_folder_path:
            if os.path.exists(props.brush_folder_path):
                brush_folder_path = props.brush_folder_path
            else:
                self.report({'WARNING'}, f"Brush folder not found: {props.brush_folder_path}")
        elif props.brush_mode == 'SINGLE' and props.brush_texture_path:
            if os.path.exists(props.brush_texture_path):
                brush_texture_path = props.brush_texture_path
            else:
                self.report({'WARNING'}, f"Brush texture not found: {props.brush_texture_path}")
        
        try:
            # Apply brush painting
            self.report({'INFO'}, "Starting brush painting process...")
            
            result_image = painter.apply_brush_painting(
                props.target_image,
                brush_folder_path=brush_folder_path,
                brush_texture_path=brush_texture_path
            )
            
            if result_image is None:
                self.report({'ERROR'}, "Failed to apply brush effects!")
                return {'CANCELLED'}
            
            # Handle result based on user preference
            if props.create_new_image:
                # Create new image in Blender
                # bpy.data.images.append(result_image)
                self.report({'INFO'}, f"Created new image: {result_image.name}")
            else:
                # Replace original image data
                original_image = props.target_image
                original_image.pixels = result_image.pixels
                original_image.update()
                self.report({'INFO'}, f"Updated original image: {original_image.name}")
            
            self.report({'INFO'}, "Brush painting completed successfully!")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error during brush painting: {str(e)}")
            return {'CANCELLED'}

class BRUSH_OT_refresh_images(Operator):
    """Refresh the list of available images"""
    bl_idname = "brush_painter.refresh_images"
    bl_label = "Refresh Images"
    bl_description = "Refresh the list of available images in Blender"

    def execute(self, context):
        # This operator doesn't need to do anything special
        # The image list is automatically updated by Blender
        self.report({'INFO'}, "Image list refreshed")
        return {'FINISHED'}

class BRUSH_OT_test_brushes(Operator):
    """Test brush loading and display information"""
    bl_idname = "brush_painter.test_brushes"
    bl_label = "Test Brushes"
    bl_description = "Test brush loading and display information"

    def execute(self, context):
        props = context.scene.brush_painter_props
        painter = BrushPainterCore()
        
        brush_list = []
        brush_info = []
        
        try:
            if props.brush_mode == 'FOLDER' and props.brush_folder_path:
                if os.path.exists(props.brush_folder_path):
                    brush_list = painter.load_multiple_brushes(props.brush_folder_path)
                    brush_info.append(f"Loaded {len(brush_list)} brushes from folder")
                else:
                    brush_info.append("Brush folder not found")
            elif props.brush_mode == 'SINGLE' and props.brush_texture_path:
                if os.path.exists(props.brush_texture_path):
                    brush_list = [painter.load_brush_texture(props.brush_texture_path)]
                    brush_info.append("Loaded single brush texture")
                else:
                    brush_info.append("Brush texture not found")
            else:
                brush_list = [painter.create_circular_brush(50)]
                brush_info.append("Using default circular brush")
            
            # Display brush information
            for info in brush_info:
                self.report({'INFO'}, info)
            
            if brush_list:
                total_area = sum(np.sum(brush > 0) for brush in brush_list)
                avg_area = total_area / len(brush_list)
                self.report({'INFO'}, f"Average brush area: {avg_area:.1f} pixels")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error testing brushes: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(BRUSH_OT_apply_brushes)
    bpy.utils.register_class(BRUSH_OT_refresh_images)
    bpy.utils.register_class(BRUSH_OT_test_brushes)

def unregister():
    bpy.utils.unregister_class(BRUSH_OT_test_brushes)
    bpy.utils.unregister_class(BRUSH_OT_refresh_images)
    bpy.utils.unregister_class(BRUSH_OT_apply_brushes)
