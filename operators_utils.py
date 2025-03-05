import bpy

from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty
)
import gpu
from bpy.types import Operator, Context
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem, get_brushes_from_library
from mathutils import Vector
from .common import redraw_panel, NodeOrganizer
from typing import List

# bpy.types.Image.pack
# -------------------------------------------------------------------
# Group Operators
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_SaveFileAndImages(Operator):
    """Save all images in the active group"""
    bl_idname = "paint_system.save_file_and_images"
    bl_label = "Save File and Images"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save all images and the blend file"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.get_active_group() and ps.get_active_group().flatten_hierarchy()

    def execute(self, context):
        # ps = PaintSystem(context)
        # flattened = ps.get_active_group().flatten_hierarchy()
        # for item, _ in flattened:
        #     if item.image:
        #         item.image.pack()
        bpy.ops.wm.save_mainfile()
        return {'FINISHED'}


class PAINTSYSTEM_OT_TogglePaintMode(Operator):
    bl_idname = "paint_system.toggle_paint_mode"
    bl_label = "Toggle Paint Mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Toggle between texture paint and object mode"

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT', toggle=True)

        if bpy.context.object.mode == 'TEXTURE_PAINT':
            # Change shading mode
            if bpy.context.space_data.shading.type != 'RENDERED':
                bpy.context.space_data.shading.type = 'RENDERED'

            # if ps.preferences.unified_brush_color:
            #     bpy.context.scene.tool_settings.unified_paint_settings.use_unified_color = True
            # if ps.preferences.unified_brush_size:
            #     bpy.context.scene.tool_settings.unified_paint_settings.use_unified_size = True

        return {'FINISHED'}


class PAINTSYSTEM_OT_AddPresetBrushes(Operator):
    bl_idname = "paint_system.add_preset_brushes"
    bl_label = "Import Paint System Brushes"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add preset brushes to the active group"

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        get_brushes_from_library()

        return {'FINISHED'}


def set_active_panel_category(category, area_type):
    areas = (
        area for win in bpy.context.window_manager.windows for area in win.screen.areas if area.type == area_type)
    for a in areas:
        for r in a.regions:
            if r.type == 'UI':
                if r.width == 1:
                    with bpy.context.temp_override(area=a):
                        bpy.ops.wm.context_toggle(
                            data_path='space_data.show_region_ui')
                try:
                    if r.active_panel_category != category:
                        r.active_panel_category = category
                        a.tag_redraw()
                except NameError as e:
                    raise e


class PAINTSYSTEM_OT_SetActivePanel(Operator):
    bl_idname = "paint_system.set_active_panel"
    bl_label = "Set Active Panel"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Set active panel"
    bl_options = {'INTERNAL'}

    category: StringProperty()

    area_type: StringProperty(
        default='VIEW_3D',
    )

    def execute(self, context: Context):
        set_active_panel_category(self.category, self.area_type)
        return {'FINISHED'}


class PAINTSYSTEM_OT_PaintModeSettings(Operator):
    bl_label = "Paint Mode Settings"
    bl_idname = "paint_system.paint_mode_menu"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Paint mode settings"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()
        unified_settings = bpy.context.scene.tool_settings.unified_paint_settings
        col.prop(unified_settings, "use_unified_color", text="Unified Color")
        col.prop(unified_settings, "use_unified_size", text="Unified Size")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_popup(self, width=200)
        return {'FINISHED'}


# def get_uv_maps_names(self, context: Context):
#     return [(uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers]

# -------------------------------------------------------------------
# Template Material Creation
# -------------------------------------------------------------------
class PAINTSYSTEM_OT_CreateTemplateSetup(Operator):
    bl_idname = "paint_system.create_template_setup"
    bl_label = "Create Template Setup"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Create a template material setup for painting"

    template: EnumProperty(
        name="Template",
        items=[
            ('NONE', "Use Existing Material", "Just add node group to material"),
            ('STANDARD', "Standard", "Start off with a standard setup"),
            ('TRANSPARENT', "Transparent", "Start off with a transparent setup"),
            ('NORMAL', "Normal", "Start off with a normal painting setup"),
        ],
        default='STANDARD'
    )

    disable_popup: BoolProperty(
        name="Disable Popup",
        description="Disable popup",
        default=False
    )

    use_alpha_blend: BoolProperty(
        name="Use Alpha Blend",
        description="Use alpha blend instead of alpha clip",
        default=False
    )

    disable_show_backface: BoolProperty(
        name="Disable Show Backface",
        description="Disable Show Backface",
        default=True
    )

    use_paintsystem_uv: BoolProperty(
        name="Use Paint System UV",
        description="Use Paint System UV",
        default=True
    )

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.get_active_group()

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        mat.use_nodes = True

        if self.template in ('STANDARD', 'NONE'):
            bpy.ops.paint_system.new_solid_color(
                'INVOKE_DEFAULT', disable_popup=True)
        bpy.ops.paint_system.new_image('INVOKE_DEFAULT', disable_popup=True,
                                       uv_map_mode='PAINT_SYSTEM' if self.use_paintsystem_uv else 'OPEN')

        node_organizer = NodeOrganizer(mat)
        if self.template == 'NONE':
            node_group = node_organizer.create_node(
                'ShaderNodeGroup', {'node_tree': active_group.node_tree})
            node_organizer.move_nodes_to_end()
            return {'FINISHED'}

        if self.use_alpha_blend:
            mat.blend_method = 'BLEND'
        if self.disable_show_backface:
            mat.show_transparent_back = False
            mat.use_backface_culling = True

        if self.template in ['STANDARD', 'TRANSPARENT']:
            node_group = node_organizer.create_node(
                'ShaderNodeGroup', {'location': Vector((-600, 0)), 'node_tree': active_group.node_tree})
            emission_node = node_organizer.create_node(
                'ShaderNodeEmission', {'location': Vector((-400, -100))})
            transparent_node = node_organizer.create_node(
                'ShaderNodeBsdfTransparent', {'location': Vector((-400, 100))})
            shader_mix_node = node_organizer.create_node(
                'ShaderNodeMixShader', {'location': Vector((-200, 0))})
            output_node = node_organizer.create_node(
                'ShaderNodeOutputMaterial', {'location': Vector((0, 0)), 'is_active_output': True})
            node_organizer.create_link(
                node_group.name, emission_node.name, 'Color', 'Color')
            node_organizer.create_link(
                node_group.name, shader_mix_node.name, 'Alpha', 0)
            node_organizer.create_link(
                transparent_node.name, shader_mix_node.name, 'BSDF', 1)
            node_organizer.create_link(
                emission_node.name, shader_mix_node.name, 'Emission', 2)
            node_organizer.create_link(
                shader_mix_node.name, output_node.name, 'Shader', 'Surface')

        elif self.template == 'NORMAL':
            tex_coord_node = node_organizer.create_node(
                'ShaderNodeTexCoord', {'location': Vector((-1000, 0))})
            vector_math_node1 = node_organizer.create_node(
                'ShaderNodeVectorMath', {'location': Vector((-800, 0)),
                                         'operation': 'MULTIPLY_ADD',
                                         'inputs[1].default_value': (0.5, 0.5, 0.5),
                                         'inputs[2].default_value': (0.5, 0.5, 0.5)})
            node_group = node_organizer.create_node(
                'ShaderNodeGroup', {'location': Vector((-600, 0)),
                                    'node_tree': active_group.node_tree,
                                    'inputs["Alpha"].default_value': 1})
            frame = node_organizer.create_node(
                'NodeFrame', {'label': "Plug this when you are done painting"})
            vector_math_node2 = node_organizer.create_node(
                'ShaderNodeVectorMath', {'location': Vector((-400, -200)),
                                         'parent': frame,
                                         'operation': 'MULTIPLY_ADD',
                                         'inputs[1].default_value': (2, 2, 2),
                                         'inputs[2].default_value': (-1, -1, -1)})
            vector_transform_node = node_organizer.create_node(
                'ShaderNodeVectorTransform', {'location': Vector((-200, -200)),
                                              'parent': frame,
                                              'vector_type': 'NORMAL',
                                              'convert_from': 'OBJECT',
                                              'convert_to': 'WORLD'})
            output_node = node_organizer.create_node(
                'ShaderNodeOutputMaterial', {'location': Vector((0, 0)), 'is_active_output': True})
            node_organizer.create_link(
                tex_coord_node.name, vector_math_node1.name, 'Normal', 'Vector')
            node_organizer.create_link(
                vector_math_node1.name, node_group.name, 'Vector', 'Color')
            node_organizer.create_link(
                node_group.name, output_node.name, 'Color', 'Surface')
            node_organizer.create_link(
                vector_math_node2.name, vector_transform_node.name, 'Vector', 'Vector')

        node_organizer.move_nodes_to_end()

        # match self.template:
        #     case 'NONE':
        #         node_group = nodes.new('ShaderNodeGroup')
        #         node_group.node_tree = active_group.node_tree
        #         node_group.location = position + Vector((200, 0))

        # case 'COLOR':
        #     node_group = nodes.new('ShaderNodeGroup')
        #     node_group.node_tree = active_group.node_tree
        #     node_group.location = position + Vector((200, 0))
        #     vector_scale_node = nodes.new('ShaderNodeVectorMath')
        #     vector_scale_node.operation = 'SCALE'
        #     vector_scale_node.location = position + Vector((400, 0))
        #     output_node = nodes.new('ShaderNodeOutputMaterial')
        #     output_node.location = position + Vector((600, 0))
        #     output_node.is_active_output = True
        #     links.new(
        #         vector_scale_node.inputs['Vector'], node_group.outputs['Color'])
        #     links.new(
        #         vector_scale_node.inputs['Scale'], node_group.outputs['Alpha'])
        #     links.new(output_node.inputs['Surface'],
        #               vector_scale_node.outputs['Vector'])

        # case 'STANDARD':
        #     node_group = nodes.new('ShaderNodeGroup')
        #     node_group.node_tree = active_group.node_tree
        #     node_group.location = position + Vector((200, 0))
        #     emission_node = nodes.new('ShaderNodeEmission')
        #     emission_node.location = position + Vector((400, -100))
        #     transparent_node = nodes.new('ShaderNodeBsdfTransparent')
        #     transparent_node.location = position + Vector((400, 100))
        #     shader_mix_node = nodes.new('ShaderNodeMixShader')
        #     shader_mix_node.location = position + Vector((600, 0))
        #     output_node = nodes.new('ShaderNodeOutputMaterial')
        #     output_node.location = position + Vector((800, 0))
        #     output_node.is_active_output = True
        #     links.new(
        #         emission_node.inputs['Color'], node_group.outputs['Color'])
        #     links.new(shader_mix_node.inputs[0],
        #               node_group.outputs['Alpha'])
        #     links.new(shader_mix_node.inputs[1],
        #               transparent_node.outputs['BSDF'])
        #     links.new(shader_mix_node.inputs[2],
        #               emission_node.outputs['Emission'])
        #     links.new(output_node.inputs['Surface'],
        #               shader_mix_node.outputs['Shader'])
        #     if self.use_alpha_blend:
        #         mat.blend_method = 'BLEND'
        #     if self.disable_show_backface:
        #         mat.show_transparent_back = False

        # case 'TRANSPARENT':

        return {'FINISHED'}

    def invoke(self, context, event):
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "template")
        if self.template == 'COLORALPHA':
            layout.prop(self, "use_alpha_blend")
            layout.prop(self, "disable_show_backface")

# -------------------------------------------------------------------
# Image Sampler
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_ColorSampler(Operator):
    """Sample the color under the mouse cursor"""
    bl_idname = "paint_system.color_sampler"
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

        tool_settings = bpy.context.scene.tool_settings
        unified_settings = tool_settings.unified_paint_settings
        brush_settings = tool_settings.image_paint.brush
        unified_settings.color = pix_value
        brush_settings.color = pix_value

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.active_object.mode == 'TEXTURE_PAINT'

    def invoke(self, context, event):
        self.x = event.mouse_x
        self.y = event.mouse_y
        return self.execute(context)


class PAINTSYSTEM_OT_ToggleBrushEraseAlpha(Operator):
    bl_idname = "paint_system.toggle_brush_erase_alpha"
    bl_label = "Toggle Brush Erase Alpha"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Toggle between brush and erase alpha"

    def execute(self, context):
        tool_settings = context.tool_settings
        paint = tool_settings.image_paint

        if paint is not None:
            brush = paint.brush
            if brush is not None:
                if brush.blend == 'ERASE_ALPHA':
                    brush.blend = 'MIX'  # Switch back to normal blending
                else:
                    brush.blend = 'ERASE_ALPHA'  # Switch to Erase Alpha mode
        return {'FINISHED'}

# -------------------------------------------------------------------
# For changing preferences
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_DisableTooltips(Operator):
    bl_idname = "paint_system.disable_tool_tips"
    bl_label = "Disable Tool Tips"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Disable Tool Tips"

    def execute(self, context):
        ps = PaintSystem(context)
        preferences = ps.preferences
        preferences.show_tooltips = False

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Disable Tool Tips?")
        layout.label(text="You can enable them again in the preferences")

# -------------------------------------------------------------------
# For testing
# -------------------------------------------------------------------


# class PAINTSYSTEM_OT_Test(Operator):
#     """Test importing node groups from library"""
#     bl_idname = "paint_system.test"
#     bl_label = "Test"

#     node_name: StringProperty()

#     def execute(self, context):
#         return {'FINISHED'}

#     def invoke(self, context, event):
#         return context.window_manager.invoke_props_dialog(self)

#     def draw(self, context):
#         layout = self.layout
#         layout.prop(self, "node_name")


classes = (
    PAINTSYSTEM_OT_SaveFileAndImages,
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_AddPresetBrushes,
    PAINTSYSTEM_OT_SetActivePanel,
    PAINTSYSTEM_OT_PaintModeSettings,
    PAINTSYSTEM_OT_CreateTemplateSetup,
    PAINTSYSTEM_OT_ColorSampler,
    PAINTSYSTEM_OT_ToggleBrushEraseAlpha,
    PAINTSYSTEM_OT_DisableTooltips,
    # PAINTSYSTEM_OT_Test,
)

_register, _unregister = register_classes_factory(classes)

addon_keymaps = []


def register():
    _register()
    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            PAINTSYSTEM_OT_ColorSampler.bl_idname, 'I', 'PRESS', repeat=True)
        kmi = km.keymap_items.new(
            PAINTSYSTEM_OT_ToggleBrushEraseAlpha.bl_idname, type='E', value='PRESS')
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    _unregister()
