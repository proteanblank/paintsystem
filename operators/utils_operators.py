import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty
from .common import PSContextMixin, MultiMaterialOperator
from bpy.utils import register_classes_factory
from .brushes import get_brushes_from_library
from ..utils.nodes import find_node, get_material_output
from bpy_extras.node_utils import connect_sockets
from mathutils import Vector
import pathlib
import math




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
        
        if ps_ctx.ps_mat_data.preview_channel and context.object.mode == 'TEXTURE_PAINT':
            bpy.ops.paint_system.preview_active_channel('EXEC_DEFAULT')

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


class PAINTSYSTEM_OT_PreviewActiveChannel(PSContextMixin, Operator):
    bl_idname = "paint_system.preview_active_channel"
    bl_label = "Preview Active Channel"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Preview the active channel"
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_object is not None and ps_ctx.active_material is not None and ps_ctx.active_channel is not None
    
    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_group = ps_ctx.active_group
        active_channel = ps_ctx.active_channel
        ps_mat_data = ps_ctx.ps_mat_data
        mat = ps_ctx.active_material
        mat_output = get_material_output(mat.node_tree)
        if not ps_mat_data.preview_channel:
            ps_mat_data.preview_channel = True
            # Store the node connected to material output
            connected_link = mat_output.inputs[0].links[0]
            ps_ctx.ps_mat_data.original_node_name = connected_link.from_node.name
            ps_ctx.ps_mat_data.original_socket_name = connected_link.from_socket.name
            
            # Find channel node tree
            node = find_node(mat.node_tree, {'bl_idname': 'ShaderNodeGroup', 'node_tree': active_group.node_tree})
            if node:
                # Connect node tree to material output
                connect_sockets(mat_output.inputs[0], node.outputs[active_channel.name])
            
            # Force toggle paint mode
            if bpy.context.object.mode != 'TEXTURE_PAINT':
                bpy.ops.paint_system.toggle_paint_mode('EXEC_DEFAULT')
        else:
            ps_mat_data.preview_channel = False
            # Find node by name
            node = mat.node_tree.nodes.get(ps_mat_data.original_node_name)
            if node:
                connect_sockets(node.outputs[ps_mat_data.original_socket_name], mat_output.inputs[0])
        return {'FINISHED'}


class PAINTSYSTEM_OT_CreatePaintSystemUVMap(Operator):
    bl_idname = "paint_system.create_paint_system_uv_map"
    bl_label = "Create Paint System UV Map"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new UV Map"

    def execute(self, context):
        # Get all objects in selection
        selection = context.selected_objects

        # Get the active object
        active_object = context.active_object
        
        if active_object.data.uv_layers.get("PS_UVMap"):
            return {'FINISHED'}

        # Deselect all objects
        for obj in selection:
            if obj != active_object:
                obj.select_set(False)
        # Make it active
        context.view_layer.objects.active = active_object
        original_mode = str(active_object.mode)
        bpy.ops.object.mode_set(mode='EDIT')
        obj.update_from_editmode()
        bpy.ops.mesh.select_all(action='SELECT')
        # Apply to only the active object
        bpy.ops.uv.smart_project(angle_limit=30/180*math.pi, island_margin=0.005)
        uv_layers = active_object.data.uv_layers
        uvmap = uv_layers.new(name="PS_UVMap")
        # Set active UV Map
        uv_layers.active = uv_layers.get(uvmap.name)
        bpy.ops.object.mode_set(mode=original_mode)
        # Deselect the object
        active_object.select_set(False)
        # Restore the selection
        for obj in selection:
            obj.select_set(True)
        context.view_layer.objects.active = active_object
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_AddPresetBrushes,
    PAINTSYSTEM_OT_SelectMaterialIndex,
    PAINTSYSTEM_OT_NewMaterial,
    PAINTSYSTEM_OT_PreviewActiveChannel,
    PAINTSYSTEM_OT_CreatePaintSystemUVMap,
)
register, unregister = register_classes_factory(classes)