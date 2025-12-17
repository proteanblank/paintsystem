import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from bpy.utils import register_classes_factory
import os


from ..custom_icons import get_icon, get_image_editor_icon

from ..paintsystem.data import EDIT_EXTERNAL_MODE_ENUM
from ..paintsystem.image import save_image
from .common import PSContextMixin, scale_content
import numpy as np
import pathlib


def image_needs_save(image) -> bool:
    """Check if an image needs to be saved to disk before external editing."""
    if not image:
        return False
    # If no filepath, it needs to be saved
    if not image.filepath:
        return True
    # Check if the file actually exists on disk
    abs_path = bpy.path.abspath(image.filepath)
    return not os.path.exists(abs_path)

# https://projects.blender.org/blender/blender/src/branch/main/scripts/startup/bl_operators/image.py#L54
class PAINTSYSTEM_OT_ProjectEdit(PSContextMixin, Operator):
    """Edit a snapshot of the 3D Viewport in an external image editor"""
    bl_idname = "paint_system.project_edit"
    bl_label = "Project Edit"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import os

        ps_ctx = self.parse_context(context)
        active_layer = ps_ctx.active_layer
        if not active_layer.image:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}

        EXT = "png"  # could be made an option but for now ok

        for image in bpy.data.images:
            image.tag = True

        # opengl buffer may fail, we can't help this, but best report it.
        try:
            bpy.ops.paint.image_from_view()
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}

        image_new = None
        for image in bpy.data.images:
            if not image.tag:
                image_new = image
                break

        if not image_new:
            self.report({'ERROR'}, "Could not make new image")
            return {'CANCELLED'}

        filepath = os.path.basename(bpy.data.filepath)
        filepath = os.path.splitext(filepath)[0]
        # fixes <memory> rubbish, needs checking
        # filepath = bpy.path.clean_name(filepath)

        if bpy.data.is_saved:
            filepath = "//" + filepath
        else:
            filepath = os.path.join(bpy.app.tempdir, "project_edit")

        obj = context.object

        if obj:
            filepath += "_" + bpy.path.clean_name(obj.name)

        filepath_final = filepath + "." + EXT
        i = 0

        while os.path.exists(bpy.path.abspath(filepath_final)):
            filepath_final = filepath + "{:03d}.{:s}".format(i, EXT)
            i += 1

        image_new.name = bpy.path.basename(filepath_final)
        active_layer.external_image = image_new

        image_new.filepath_raw = filepath_final  # TODO, filepath raw is crummy
        image_new.file_format = 'PNG'
        image_new.save()

        filepath_final = bpy.path.abspath(filepath_final)

        try:
            bpy.ops.image.external_edit(filepath=filepath_final)
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex))

        return {'FINISHED'}


def set_rgb_to_zero_if_alpha_zero(image):
    """
    Checks each pixel in the input Blender Image. If a pixel's alpha
    channel is 0.0, it sets the Red, Green, and Blue channels of that
    pixel to 0.0 as well.

    Args:
        image (bpy.types.Image): The Blender Image data-block to process.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    if not image:
        print("Error: No image provided.")
        return False

    if not isinstance(image, bpy.types.Image):
        print(f"Error: Input '{image.name}' is not a bpy.types.Image.")
        return False

    # if not image.has_data:
    #     print(f"Error: Image '{image.name}' has no pixel data loaded.")
    #     # You might want to pack the image or ensure the file path is correct
    #     # before calling this function if this happens.
    #     return False

    # --- Method 1: Using Numpy (Generally Faster for large images) ---
    width = image.size[0]
    height = image.size[1]
    channels = image.channels  # Usually 4 (RGBA)

    if channels != 4:
        print(
            f"Error: Image '{image.name}' does not have 4 channels (RGBA). Found {channels}.")
        # Or handle images with 3 channels differently if needed
        return False

    # Copy pixel data to a numpy array for easier manipulation
    # The `.pixels` attribute is a flat list [R1, G1, B1, A1, R2, G2, B2, A2, ...]
    # Reshape it into a (height, width, channels) array
    # Note: Blender's pixel storage order might seem inverted height-wise
    # when directly reshaping. Accessing pixels[:] gets the flat list correctly.
    pixel_data = np.array(image.pixels[:])  # Make a copy
    pixel_data = pixel_data.reshape((height, width, channels))

    # Find pixels where alpha (channel index 3) is 0.0
    # alpha_zero_mask will be a boolean array of shape (height, width)
    alpha_zero_mask = (pixel_data[:, :, 3] == 0.0)

    # Set RGB channels (indices 0, 1, 2) to 0.0 where the mask is True
    pixel_data[alpha_zero_mask, 0:3] = 0.0

    # Flatten the array back and update the image pixels
    image.pixels = pixel_data.ravel()  # Update with modified data

    # --- Method 2: Direct Pixel Iteration (Simpler, potentially slower) ---
    # Uncomment this section and comment out Method 1 if you prefer
    # or if numpy is unavailable (though it ships with Blender).
    #
    # if image.channels != 4:
    #     print(f"Error: Image '{image.name}' does not have 4 channels (RGBA). Found {image.channels}.")
    #     return False
    #
    # pixels = image.pixels # Get a reference (can be modified directly)
    # num_pixels = len(pixels) // 4 # Calculate total number of pixels
    #
    # modified = False
    # for i in range(num_pixels):
    #     idx_alpha = i * 4 + 3
    #
    #     if pixels[idx_alpha] == 0.0:
    #         idx_r = i * 4
    #         idx_g = i * 4 + 1
    #         idx_b = i * 4 + 2
    #
    #         # Check if modification is needed (avoids unnecessary writes)
    #         if pixels[idx_r] != 0.0 or pixels[idx_g] != 0.0 or pixels[idx_b] != 0.0:
    #             pixels[idx_r] = 0.0
    #             pixels[idx_g] = 0.0
    #             pixels[idx_b] = 0.0
    #             modified = True

    # --- Final Step ---
    # Mark the image as updated so Blender recognizes the changes
    return True


class PAINTSYSTEM_OT_ProjectApply(PSContextMixin, Operator):
    """Project edited image back onto the object"""
    bl_idname = "paint_system.project_apply"
    bl_label = "Project Apply"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        active_layer = ps_ctx.active_layer
        return active_layer and active_layer.external_image

    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_layer = ps_ctx.active_layer

        current_image_editor = context.preferences.filepaths.image_editor
        editor_path = pathlib.Path(current_image_editor)
        app_name = editor_path.name
        external_image = active_layer.external_image
        external_image_name = str(active_layer.external_image.name)

        # external_image_name = str(external_image.name)
        # print(external_image_name)

        external_image.reload()
        if app_name == "CLIPStudioPaint.exe":
            set_rgb_to_zero_if_alpha_zero(external_image)
            external_image.update_tag()

        # if image is None:
        #     self.report({'ERROR'}, rpt_(
        #         "Could not find image '{:s}'").format(external_image_name))
        #     return {'CANCELLED'}

        with bpy.context.temp_override(**{'mode': 'IMAGE_PAINT'}):
            bpy.ops.paint.project_image(image=external_image_name)

        active_layer.external_image = None

        return {'FINISHED'}


class PAINTSYSTEM_OT_QuickEdit(PSContextMixin, Operator):
    bl_idname = "paint_system.quick_edit"
    bl_label = "Quick Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Quickly edit the active image"
    
    edit_external_mode: EnumProperty(
        items=EDIT_EXTERNAL_MODE_ENUM,
        name="Edit External Mode",
        description="Edit external mode",
        default='IMAGE_EDIT'
    )
    
    save_directory: StringProperty(
        name="Save Directory",
        description="Directory to save unsaved images",
        subtype='DIR_PATH',
        default=""
    )

    def execute(self, context):
        current_image_editor = context.preferences.filepaths.image_editor
        if not current_image_editor:
            self.report({'ERROR'}, "No image editor set")
            return {'CANCELLED'}
        
        ps_ctx = self.parse_context(context)
        active_layer = ps_ctx.active_layer
        
        if self.edit_external_mode == 'VIEW_CAPTURE':
            active_layer.edit_external_mode = 'VIEW_CAPTURE'
            bpy.ops.paint_system.project_edit('INVOKE_DEFAULT')
            return {'FINISHED'}
        
        # IMAGE_EDIT mode
        if not active_layer:
            self.report({'ERROR'}, "No active layer selected")
            return {'CANCELLED'}
        
        if not active_layer.image:
            self.report({'ERROR'}, "Active layer does not have an image")
            return {'CANCELLED'}
        
        image = active_layer.image
        active_layer.edit_external_mode = 'IMAGE_EDIT'
        
        # Check if image needs to be saved
        if image_needs_save(image):
            if not self.save_directory:
                self.report({'ERROR'}, "Please select a directory to save the image")
                return {'CANCELLED'}
            
            # Build filepath
            image_name = bpy.path.clean_name(image.name)
            if not image_name.lower().endswith('.png'):
                image_name += '.png'
            filepath = os.path.join(bpy.path.abspath(self.save_directory), image_name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the image
            image.filepath_raw = filepath
            image.file_format = 'PNG'
        save_image(image)
        
        # Get the absolute filepath
        filepath = bpy.path.abspath(image.filepath)
        
        # Store as external image for apply operation
        active_layer.external_image = image
        
        # Open in external editor
        try:
            bpy.ops.image.external_edit(filepath=filepath)
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}
        
        return {'FINISHED'}

    def invoke(self, context, event):
        # Set default save directory based on blend file location or temp dir
        if bpy.data.is_saved:
            self.save_directory = os.path.dirname(bpy.data.filepath)
        else:
            self.save_directory = bpy.app.tempdir
        
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        
        # Mode selector
        row = layout.row()
        scale_content(context, row, 1.5, 1.5)
        row.prop(self, "edit_external_mode", expand=True)
        
        if ps_ctx.ps_settings.show_tooltips:
            if self.edit_external_mode == 'IMAGE_EDIT':
                box = layout.box()
                col = box.column(align=True)
                col.label(text="Edit the layer's image directly in the", icon="INFO")
                col.label(text="external image editor", icon="BLANK1")
            elif self.edit_external_mode == 'VIEW_CAPTURE':
                box = layout.box()
                col = box.column(align=True)
                col.label(text="Capture the current view and edit it in the", icon="INFO")
                col.label(text="external image editor", icon="BLANK1")
        
        current_image_editor = context.preferences.filepaths.image_editor
        image_paint = context.scene.tool_settings.image_paint
        
        # Show editor path
        if not current_image_editor:
            layout.prop(context.preferences.filepaths, "image_editor")
        else:
            editor_path = pathlib.Path(current_image_editor)
            app_name = editor_path.name
            row = layout.row()
            row.template_icon(get_image_editor_icon(current_image_editor), scale=1.5)
            col = row.column()
            col.scale_y = 1.5
            col.label(text=f"{app_name.replace('.exe', '')}")
        
        if self.edit_external_mode == 'IMAGE_EDIT':
            # IMAGE_EDIT specific UI
            active_layer = ps_ctx.active_layer
            
            if not active_layer or not active_layer.image:
                box = layout.box()
                box.alert = True
                box.label(text="No image on active layer!", icon="ERROR")
            else:
                # image = active_layer.image
                box = layout.box()
                box.label(text=f"Save Directory:", icon="IMAGE_DATA")
                box.prop(self, "save_directory", text="")
                # Check if image needs to be saved
                # if image_needs_save(image):
                #     box = layout.box()
                #     col = box.column(align=True)
                #     col.label(text="Image will be saved in:", icon="INFO")
                #     col.label(text=f"{self.save_directory}", icon="BLANK1")
        else:
            
            box = layout.box()
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="External Settings:", icon="TOOL_SETTINGS")
            row = box.row()
            row.prop(image_paint, "seam_bleed", text="Bleed")
            row.prop(image_paint, "dither", text="Dither")
            split = box.split()
            split.label(text="Screen Grab Size:")
            split.prop(image_paint, "screen_grab_size", text="")
        
            # Warning about closing editor
            box = layout.box()
            box.alert = True
            row = box.row()
            row.alignment = "CENTER"
            row.label(icon="ERROR")
            col = row.column(align=True)
            col.label(text="Make sure to close the image editor")
            col.label(text=" before applying the edit.")


class PAINTSYSTEM_OT_ReloadImage(PSContextMixin, Operator):
    bl_idname = "paint_system.reload_image"
    bl_label = "Reload Image"
    bl_options = {'REGISTER'}
    bl_description = "Reload the image"

    def execute(self, context):
        ps_ctx = self.parse_context(context)
        active_layer = ps_ctx.active_layer
        if not active_layer.external_image:
            self.report({'ERROR'}, "No external image found")
            return {'CANCELLED'}
        active_layer.external_image.reload()
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_ProjectEdit,
    PAINTSYSTEM_OT_ProjectApply,
    PAINTSYSTEM_OT_QuickEdit,
    PAINTSYSTEM_OT_ReloadImage,
)

register, unregister = register_classes_factory(classes)