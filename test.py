from bpy.props import IntProperty
from bpy.types import Operator
from gpu_extras.presets import draw_texture_2d
import gpu
import bgl
import bpy
bl_info = {
    "name": "Screen Color Sampler",
    "blender": (3, 0, 0),
    "category": "Utility",
    "description": "Sample a color from the Blender screen and print it."
}


class PAINTSYSTEM_OT_ColorSampler(Operator):
    """Sample the color under the mouse cursor"""
    bl_idname = "screen.color_sampler"
    bl_label = "Color Sampler"

    x: IntProperty()
    y: IntProperty()

    def execute(self, context):
        # Get the screen dimensions
        x, y = self.x, self.y

        buffer = gpu.state.active_framebuffer_get()
        pixel = buffer.read_color(x, y, 1, 1, 3, 0, 'FLOAT')
        pixel.dimensions = 1 * 1 * 3
        pix_value = [float(item) for item in pixel]
        print(f"Sampled Color: {pix_value}")

        tool_settings = bpy.context.scene.tool_settings
        unified_settings = tool_settings.unified_paint_settings
        brush_settings = tool_settings.image_paint.brush
        brush_color = unified_settings.color if unified_settings.use_unified_color else brush_settings.color
        brush_color = [round(c, 2) for c in brush_color]

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.active_object.mode == 'TEXTURE_PAINT'

    def invoke(self, context, event):
        self.x = event.mouse_x
        self.y = event.mouse_y
        return self.execute(context)


addon_keymaps = []


def register():
    bpy.utils.register_class(SCREEN_OT_color_sampler)

    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Screen', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            SCREEN_OT_color_sampler.bl_idname, 'E', 'PRESS')
        addon_keymaps.append((km, kmi))


def unregister():
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(SCREEN_OT_color_sampler)


if __name__ == "__main__":
    register()
