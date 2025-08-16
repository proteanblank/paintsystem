import bpy
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty, IntProperty
from .common import PSContextMixin, get_icon, MultiMaterialOperator
from bpy.utils import register_classes_factory
from .brushes import get_brushes_from_library
from bpy_extras.node_utils import find_node_input
from mathutils import Vector
import pathlib




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


class PAINTSYSTEM_OT_SelectMaterialIndex(PSContextMixin, Operator):
    """Select the item in the UI list"""
    bl_idname = "paint_system.select_material_index"
    bl_label = "Select Material Index"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Select the material index in the UI list"

    index: IntProperty()

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        ob = ps_ctx.active_object
        if not ob:
            return {'CANCELLED'}
        if ob.type != 'MESH':
            return {'CANCELLED'}
        ob.active_material_index = self.index
        return {'FINISHED'}

# class PAINTSYSTEM_OT_AddPaintSystemToMaterial(PSContextMixin, MultiMaterialOperator):
#     bl_idname = "paint_system.add_paint_system_to_material"
#     bl_label = "Add Paint System to Material"
#     bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
#     bl_description = "Add Paint System to the active material"

#     template: EnumProperty(
#         name="Template",
#         items=TEMPLATE_ENUM,
#         default='STANDARD'
#     )

#     use_alpha_blend: BoolProperty(
#         name="Use Alpha Blend",
#         description="Use alpha blend instead of alpha clip",
#         default=False
#     )

#     disable_show_backface: BoolProperty(
#         name="Disable Show Backface",
#         description="Disable Show Backface",
#         default=True
#     )

#     # use_paintsystem_uv: BoolProperty(
#     #     name="Use Paint System UV",
#     #     description="Use Paint System UV",
#     #     default=True
#     # )

#     @classmethod
#     def poll(cls, context):
#         ps_ctx = cls.ensure_context(context)
#         return ps_ctx.active_group is not None

#     def process_material(self, context):
#         bpy.ops.paint_system.new_group()
#         ps_ctx = self.ensure_context(context)
#         active_group = ps_ctx.active_group
#         mat = ps_ctx.active_material
#         mat.use_nodes = True

#         self.set_uv_mode(context)

#         if self.template in ('BASIC'):
#             bpy.ops.paint_system.new_solid_color_layer(
#                 'EXEC_DEFAULT')
#         # if self.template != "TRANSPARENT":
#         #     bpy.ops.paint_system.new_image_layer('EXECUTE_DEFAULT')

#         node_organizer = NodeOrganizer(mat)
#         if self.template == 'NONE':
#             node_group = node_organizer.create_node(
#                 'ShaderNodeGroup', {'node_tree': active_group.node_tree})
#             node_organizer.move_nodes_to_end()
#             return {'FINISHED'}

#         if self.template == 'PAINT_OVER':
#             # Use existing connected node to surface
#             material_output = find_node_input(mat.node_tree, 'OUTPUT_MATERIAL')
#             link = material_output.inputs['Surface'].links[0]
#             linked_node = link.from_node
#             socket = link.from_socket
#             is_shader = socket.type == 'SHADER'
#             if is_shader:
#                 shader_to_rgb_node = node_organizer.create_node(
#                     'ShaderNodeShaderToRGB', {'location': linked_node.location + Vector((200, 0))})
#                 node_organizer.create_link(
#                     linked_node.name, shader_to_rgb_node.name, socket.name, 'Shader')
#                 linked_node = shader_to_rgb_node
#                 socket = shader_to_rgb_node.outputs['Color']
#             node_group = node_organizer.create_node(
#                 'ShaderNodeGroup', {'node_tree': active_group.node_tree, 'location': linked_node.location + Vector((200, 0))})
#             node_group.inputs['Alpha'].default_value = 1
#             node_organizer.create_link(
#                 linked_node.name, node_group.name, socket.name, 'Color')
#             if is_shader:
#                 node_organizer.create_link(
#                     linked_node.name, node_group.name, linked_node.outputs['Alpha'].name, 'Alpha')
#             emission_node = node_organizer.create_node(
#                 'ShaderNodeEmission', {'location': node_group.location + Vector((200, -100))})
#             transparent_node = node_organizer.create_node(
#                 'ShaderNodeBsdfTransparent', {'location': node_group.location + Vector((200, 100))})
#             shader_mix_node = node_organizer.create_node(
#                 'ShaderNodeMixShader', {'location': node_group.location + Vector((400, 0))})
#             node_organizer.create_link(
#                 node_group.name, emission_node.name, 'Color', 'Color')
#             node_organizer.create_link(
#                 node_group.name, shader_mix_node.name, 'Alpha', 0)
#             node_organizer.create_link(
#                 transparent_node.name, shader_mix_node.name, 'BSDF', 1)
#             node_organizer.create_link(
#                 emission_node.name, shader_mix_node.name, 'Emission', 2)
#             node_organizer.create_link(
#                 shader_mix_node.name, material_output.name, 'Shader', 'Surface')
#             material_output.location = shader_mix_node.location + \
#                 Vector((200, 0))

#             return {'FINISHED'}

#         if self.use_alpha_blend:
#             mat.blend_method = 'BLEND'
#         if self.disable_show_backface:
#             mat.show_transparent_back = False
#             mat.use_backface_culling = True

#         if self.template in ['BASIC']:
#             node_group = node_organizer.create_node(
#                 'ShaderNodeGroup', {'location': Vector((-600, 0)), 'node_tree': active_group.node_tree})
#             emission_node = node_organizer.create_node(
#                 'ShaderNodeEmission', {'location': Vector((-400, -100))})
#             transparent_node = node_organizer.create_node(
#                 'ShaderNodeBsdfTransparent', {'location': Vector((-400, 100))})
#             shader_mix_node = node_organizer.create_node(
#                 'ShaderNodeMixShader', {'location': Vector((-200, 0))})
#             output_node = node_organizer.create_node(
#                 'ShaderNodeOutputMaterial', {'location': Vector((0, 0)), 'is_active_output': True})
#             node_organizer.create_link(
#                 node_group.name, emission_node.name, 'Color', 'Color')
#             node_organizer.create_link(
#                 node_group.name, shader_mix_node.name, 'Alpha', 0)
#             node_organizer.create_link(
#                 transparent_node.name, shader_mix_node.name, 'BSDF', 1)
#             node_organizer.create_link(
#                 emission_node.name, shader_mix_node.name, 'Emission', 2)
#             node_organizer.create_link(
#                 shader_mix_node.name, output_node.name, 'Shader', 'Surface')

#         elif self.template == 'NORMAL':
#             tex_coord_node = node_organizer.create_node(
#                 'ShaderNodeTexCoord', {'location': Vector((-1000, 0))})
#             vector_math_node1 = node_organizer.create_node(
#                 'ShaderNodeVectorMath', {'location': Vector((-800, 0)),
#                                          'operation': 'MULTIPLY_ADD',
#                                          'inputs[1].default_value': (0.5, 0.5, 0.5),
#                                          'inputs[2].default_value': (0.5, 0.5, 0.5)})
#             node_group = node_organizer.create_node(
#                 'ShaderNodeGroup', {'location': Vector((-600, 0)),
#                                     'node_tree': active_group.node_tree,
#                                     'inputs["Alpha"].default_value': 1})
#             frame = node_organizer.create_node(
#                 'NodeFrame', {'label': "Plug this when you are done painting"})
#             vector_math_node2 = node_organizer.create_node(
#                 'ShaderNodeVectorMath', {'location': Vector((-400, -200)),
#                                          'parent': frame,
#                                          'operation': 'MULTIPLY_ADD',
#                                          'inputs[1].default_value': (2, 2, 2),
#                                          'inputs[2].default_value': (-1, -1, -1)})
#             vector_transform_node = node_organizer.create_node(
#                 'ShaderNodeVectorTransform', {'location': Vector((-200, -200)),
#                                               'parent': frame,
#                                               'vector_type': 'NORMAL',
#                                               'convert_from': 'OBJECT',
#                                               'convert_to': 'WORLD'})
#             output_node = node_organizer.create_node(
#                 'ShaderNodeOutputMaterial', {'location': Vector((0, 0)), 'is_active_output': True})
#             node_organizer.create_link(
#                 tex_coord_node.name, vector_math_node1.name, 'Normal', 'Vector')
#             node_organizer.create_link(
#                 vector_math_node1.name, node_group.name, 'Vector', 'Color')
#             node_organizer.create_link(
#                 node_group.name, output_node.name, 'Color', 'Surface')
#             node_organizer.create_link(
#                 vector_math_node2.name, vector_transform_node.name, 'Vector', 'Vector')

#         node_organizer.move_nodes_to_end()

#         return {'FINISHED'}
    
#     def invoke(self, context, event):
#         ps_ctx = self.ensure_context(context)
#         groups = ps_ctx.ps_mat_data.groups
#         self.group_name = self.get_next_group_name(context)
#         if groups:
#             self.material_template = "NONE"
#         # if ps.get_active_material():
#         #     self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
#         #     ).use_paintsystem_uv else 'OPEN'
#         return context.window_manager.invoke_props_dialog(self)

#     def draw(self, context):
#         ps_ctx = self.ensure_context(context)
#         layout = self.layout
#         mat = ps_ctx.active_material
#         obj = ps_ctx.active_object
        
#         if len(context.selected_objects) == 1:
#             split = layout.split(factor=0.4)
#             split.scale_y = 1.5
#             if not mat:
#                 split.label(text="New Material Name:")
#                 split.prop(self, "material_name", text="", icon='MATERIAL')
#             else:
#                 split.label(text="Selected Material:")
#                 row = split.row(align=True)
#                 row.prop(obj, "active_material", text="")
#                 # row.operator("material.new", text="", icon='ADD')
#         else:
#             self.multiple_objects_ui(layout, context)
#             # row = box.row(align=True)
#             # row.prop(self, "multiple_objects", text="Selected Objects", icon='CHECKBOX_HLT' if self.multiple_objects else 'CHECKBOX_DEHLT')
#             # row.prop(self, "multiple_materials", text="All Materials", icon='CHECKBOX_HLT' if self.multiple_materials else 'CHECKBOX_DEHLT')
            
#         if not self.hide_template:
#             # row = layout.row(align=True)
#             # row.scale_y = 1.5
#             split = layout.split(factor=0.4)
#             split.scale_y = 1.5
#             split.label(text="Template:")
#             split.prop(self, "material_template", text="")
#             # row.prop(self, "create_material_setup",
#             #         text="Setup Material", icon='CHECKBOX_HLT' if self.create_material_setup else 'CHECKBOX_DEHLT')
#             # row.prop(self, "material_template", text="Template")
#         row = layout.row()
#         row.scale_y = 1.2
#         layout.separator()
#         box = layout.box()
#         row = box.row()
#         row.alignment = "CENTER"
#         row.label(text="Advanced Settings:", icon="TOOL_SETTINGS")
#         split = box.split(factor=0.4)
#         split.label(text="Group Name:")
#         split.prop(self, "group_name", text="", icon='NODETREE')
#         if self.material_template in ['STANDARD', 'TRANSPARENT']:
#             box.prop(self, "use_alpha_blend", text="Use Alpha Blend")
#             box.prop(self, "use_backface_culling",
#                      text="Use Backface Culling")
#         if context.scene.view_settings.view_transform != 'Standard':
#             box.prop(self, "set_view_transform",
#                      text="Set View Transform to Standard")


class PAINTSYSTEM_OT_QuickEdit(Operator):
    bl_idname = "paint_system.quick_edit"
    bl_label = "Quick Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Quickly edit the active image"

    def execute(self, context):
        current_image_editor = context.preferences.filepaths.image_editor
        if not current_image_editor:
            self.report({'ERROR'}, "No image editor set")
            return {'CANCELLED'}
        bpy.ops.paint_system.project_edit('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        current_image_editor = context.preferences.filepaths.image_editor
        image_paint = context.scene.tool_settings.image_paint
        if not current_image_editor:
            layout.prop(context.preferences.filepaths, "image_editor")
        else:
            editor_path = pathlib.Path(current_image_editor)
            app_name = editor_path.name
            layout.label(text=f"Open {app_name}", icon="EXPORT")
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


class PAINTSYSTEM_OT_ApplyEdit(Operator):
    bl_idname = "paint_system.apply_edit"
    bl_label = "Apply Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Apply the edit to the active image"

    def execute(self, context):
        bpy.ops.image.project_apply('INVOKE_DEFAULT')
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewMaterial(MultiMaterialOperator):
    bl_idname = "paint_system.new_material"
    bl_label = "New Material"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new material"
    
    def process_material(self, context):
        bpy.ops.object.material_slot_add()
        bpy.data.materials.new(name="New Material")
        context.active_object.active_material = bpy.data.materials[-1]
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_AddPresetBrushes,
    PAINTSYSTEM_OT_SelectMaterialIndex,
    PAINTSYSTEM_OT_QuickEdit,
    PAINTSYSTEM_OT_ApplyEdit,
    PAINTSYSTEM_OT_NewMaterial,
)
register, unregister = register_classes_factory(classes)