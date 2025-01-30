from PIL import Image  # Pillow
import numpy as np
import bpy
bl_info = {
    "name": "UV Image Blender",
    "author": "Tawan Sunflower",
    "version": (1, 0),
    "blender": (4, 1, 0),  # Minimum Blender version
    "location": "Image Editor > UV Image Blender",
    "description": "Blends two images based on input UV maps.",
    "warning": "",
    "doc_url": "",
    "category": "Image",
}


# Utility function for bilinear interpolation

def bilinear_interpolation(image_np, u, v):
    width, height, channels = image_np.shape
    u_norm = u * (width - 1)
    v_norm = v * (height - 1)

    x = int(u_norm)
    y = int(v_norm)

    u_frac = u_norm - x
    v_frac = v_norm - y

    x0 = max(0, min(x, width - 1))
    x1 = max(0, min(x + 1, width - 1))
    y0 = max(0, min(y, height - 1))
    y1 = max(0, min(y + 1, height - 1))

    p00 = image_np[x0, y0]
    p01 = image_np[x0, y1]
    p10 = image_np[x1, y0]
    p11 = image_np[x1, y1]

    interp_top = p00 * (1 - u_frac) + p10 * u_frac
    interp_bottom = p01 * (1 - u_frac) + p11 * u_frac

    return interp_top * (1 - v_frac) + interp_bottom * v_frac


class UVImageBlendOperator(bpy.types.Operator):
    """Blends two images based on UV maps."""
    bl_idname = "image.uv_blend_images"
    bl_label = "Blend Images with UVs"
    bl_options = {'REGISTER', 'UNDO'}

    image1_name: bpy.props.StringProperty(name="Image 1")
    image2_name: bpy.props.StringProperty(name="Image 2")
    output_image_name: bpy.props.StringProperty(
        name="Output Image Name", default="BlendedImage")
    blend_factor: bpy.props.FloatProperty(
        name="Blend Factor", default=0.5, min=0.0, max=1.0)

    def execute(self, context):
        image1 = bpy.data.images.get(self.image1_name)
        image2 = bpy.data.images.get(self.image2_name)

        if not image1 or not image2:
            self.report({'ERROR_INVALID_INPUT'},
                        "Please select both Image 1 and Image 2.")
            return {'CANCELLED'}

        # Convert Blender images to NumPy arrays (RGBA for simplicity)
        image1_np = np.array(image1.pixels[:], dtype=np.float32).reshape(
            (image1.size[1], image1.size[0], 4)).copy()
        image2_np = np.array(image2.pixels[:], dtype=np.float32).reshape(
            (image2.size[1], image2.size[0], 4)).copy()

        # Or let user define target size?
        output_width = max(image1.size[0], image2.size[0])
        # Or let user define target size?
        output_height = max(image1.size[1], image2.size[1])
        output_pixels = []

        # Iterate through target UV space (we'll use pixel coordinates as UVs for now, normalized 0-1)
        for y in range(output_height):
            for x in range(output_width):
                u = x / output_width
                v = y / output_height

                # Sample pixels from both images using the *same* UV coordinates (simplified approach)
                color1 = bilinear_interpolation(image1_np, u, v)
                color2 = bilinear_interpolation(image2_np, u, v)

                # Alpha blending
                blended_color = (1 - self.blend_factor) * \
                    color1 + self.blend_factor * color2

                # Convert numpy array to list
                output_pixels.extend(blended_color.tolist())

        # Create new Blender image for output
        output_image = bpy.data.images.new(
            self.output_image_name, width=output_width, height=output_height)
        output_image.pixels[:] = output_pixels

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "image1_name", bpy.data,
                           "images", text="Image 1")
        layout.prop_search(self, "image2_name", bpy.data,
                           "images", text="Image 2")
        layout.prop(self, "output_image_name")
        layout.prop(self, "blend_factor")


class IMAGE_PT_uv_blend_panel(bpy.types.Panel):
    """Creates a Panel in the Image editor properties window"""
    bl_label = "UV Image Blender"
    bl_idname = "IMAGE_PT_uv_blend"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, layout):
        layout.operator(UVImageBlendOperator.bl_idname)


def register():
    bpy.utils.register_class(UVImageBlendOperator)
    bpy.utils.register_class(IMAGE_PT_uv_blend_panel)


def unregister():
    bpy.utils.unregister_class(UVImageBlendOperator)
    bpy.utils.unregister_class(IMAGE_PT_uv_blend_panel)


if __name__ == "__main__":
    register()
