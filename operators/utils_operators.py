import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty
from .common import PSContextMixin, get_icon
from bpy.utils import register_classes_factory
from .brushes import get_brushes_from_library
from bpy_extras.node_utils import find_node_input


TEMPLATE_ENUM = [
    ('BASIC', "Basic", "Basic material setup", "IMAGE", 0),
    ('PAINT_OVER', "Paint Over", "Paint over the existing material", get_icon('over'), 1),
    ('EXISTING', "Convert Existing Material", "Add to existing material setup", "FILE_REFRESH", 2),
    ('NORMAL', "Normals Painting", "Start off with a normal painting setup", "NORMALS_VERTEX_FACE", 3),
    ('NONE', "Manual", "Just add node group to material", "NONE", 4),
    # ('STANDARD', "Standard", "Replace the existing material and start off with a basic setup", "IMAGE", 0),
    # ('EXISTING', "Convert Existing Material", "Add to existing material setup", "FILE_REFRESH", 1),
    # ('NORMAL', "Normals Painting", "Start off with a normal painting setup", "NORMALS_VERTEX_FACE", 2),
    # ('TRANSPARENT', "Transparent", "Start off with a transparent setup" , "FILE", 3),
    # ('NONE', "Manual", "Just add node group to material", "NONE", 4),
]

class PAINTSYSTEM_OT_TogglePaintMode(PSContextMixin, Operator):
    bl_idname = "paint_system.toggle_paint_mode"
    bl_label = "Toggle Paint Mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Toggle between texture paint and object mode"

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT', toggle=True)
        is_cycles = bpy.context.scene.render.engine == 'CYCLES'
        if bpy.context.object.mode == 'TEXTURE_PAINT':
            # Change shading mode
            if bpy.context.space_data.shading.type != ('RENDERED' if not is_cycles else 'MATERIAL'):
                bpy.context.space_data.shading.type = ('RENDERED' if not is_cycles else 'MATERIAL')

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
        get_brushes_from_library()

        return {'FINISHED'}


class PAINTSYSTEM_OT_AddPaintSystemToMaterial(Operator):
    bl_idname = "paint_system.add_paint_system_to_material"
    bl_label = "Add Paint System to Material"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Add Paint System to the active material"

    template: EnumProperty(
        name="Template",
        items=TEMPLATE_ENUM,
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

    # @classmethod
    # def poll(cls, context):
    #     ps = PaintSystem(context)
    #     return ps.get_active_group()

    def execute(self, context):
        bpy.ops.paint_system.new_group()
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        mat.use_nodes = True

        self.set_uv_mode(context)

        if self.template in ('STANDARD', 'NONE'):
            bpy.ops.paint_system.new_solid_color(
                'INVOKE_DEFAULT', disable_popup=True)
        if self.template != "TRANSPARENT":
            bpy.ops.paint_system.new_image('INVOKE_DEFAULT', disable_popup=True,
                                        uv_map_mode=self.uv_map_mode,
                                        uv_map_name=self.uv_map_name)

        node_organizer = NodeOrganizer(mat)
        if self.template == 'NONE':
            node_group = node_organizer.create_node(
                'ShaderNodeGroup', {'node_tree': active_group.node_tree})
            node_organizer.move_nodes_to_end()
            return {'FINISHED'}

        if self.template == 'EXISTING':
            # Use existing connected node to surface
            material_output = find_node_input(mat.node_tree, 'OUTPUT_MATERIAL')
            link = material_output.inputs['Surface'].links[0]
            linked_node = link.from_node
            socket = link.from_socket
            is_shader = socket.type == 'SHADER'
            if is_shader:
                shader_to_rgb_node = node_organizer.create_node(
                    'ShaderNodeShaderToRGB', {'location': linked_node.location + Vector((200, 0))})
                node_organizer.create_link(
                    linked_node.name, shader_to_rgb_node.name, socket.name, 'Shader')
                linked_node = shader_to_rgb_node
                socket = shader_to_rgb_node.outputs['Color']
            node_group = node_organizer.create_node(
                'ShaderNodeGroup', {'node_tree': active_group.node_tree, 'location': linked_node.location + Vector((200, 0))})
            node_group.inputs['Alpha'].default_value = 1
            node_organizer.create_link(
                linked_node.name, node_group.name, socket.name, 'Color')
            if is_shader:
                node_organizer.create_link(
                    linked_node.name, node_group.name, linked_node.outputs['Alpha'].name, 'Alpha')
            emission_node = node_organizer.create_node(
                'ShaderNodeEmission', {'location': node_group.location + Vector((200, -100))})
            transparent_node = node_organizer.create_node(
                'ShaderNodeBsdfTransparent', {'location': node_group.location + Vector((200, 100))})
            shader_mix_node = node_organizer.create_node(
                'ShaderNodeMixShader', {'location': node_group.location + Vector((400, 0))})
            node_organizer.create_link(
                node_group.name, emission_node.name, 'Color', 'Color')
            node_organizer.create_link(
                node_group.name, shader_mix_node.name, 'Alpha', 0)
            node_organizer.create_link(
                transparent_node.name, shader_mix_node.name, 'BSDF', 1)
            node_organizer.create_link(
                emission_node.name, shader_mix_node.name, 'Emission', 2)
            node_organizer.create_link(
                shader_mix_node.name, material_output.name, 'Shader', 'Surface')
            material_output.location = shader_mix_node.location + \
                Vector((200, 0))

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

        return {'FINISHED'}

classes = (
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_AddPresetBrushes,
)
register, unregister = register_classes_factory(classes)