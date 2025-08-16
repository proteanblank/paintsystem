import bpy
from bpy.props import EnumProperty, BoolProperty
from bpy.types import NodeTree, Node, NodeSocket
from .list_manager import ListManager
from bpy.utils import register_classes_factory
from .common import PSContextMixin, scale_content, MultiMaterialOperator, get_icon
from mathutils import Vector
from typing import Union


TEMPLATE_ENUM = [
    ('BASIC', "Basic", "Basic painting setup", "IMAGE", 0),
    ('PAINT_OVER', "Paint Over", "Paint over the existing material", get_icon('paintbrush'), 1),
    ('PBR', "PBR", "PBR painting setup", "MATERIAL", 2),
    ('NORMAL', "Normals Painting", "Start off with a normal painting setup", "NORMALS_VERTEX_FACE", 3),
    ('NONE', "None", "Just add node group to material", "NONE", 4),
]

def get_material_output(mat_node_tree: NodeTree) -> Node:
    node = None
    for node in mat_node_tree.nodes:
        if node.type == 'ShaderNodeOutputMaterial' and node.is_active_output:
            return node
    if node is None:
        node = mat_node_tree.nodes.new(type='ShaderNodeOutputMaterial')
        node.is_active_output = True
    return node

def traverse_connected_nodes(node: Node) -> set[Node]:
    nodes = set()
    for input_socket in node.inputs:
        for link in input_socket.links:
            nodes.append(link.from_node)
            nodes.update(traverse_connected_nodes(link.from_node))
    return nodes

def transfer_connection(source_socket: NodeSocket, target_socket: NodeSocket):
    if source_socket.is_linked:
        original_socket = source_socket.links[0].from_socket
        target_socket.links.new(original_socket)
        source_socket.links.clear()

class PAINTSYSTEM_OT_NewGroup(PSContextMixin, MultiMaterialOperator):
    """Create a new group in the Paint System"""
    bl_idname = "paint_system.new_group"
    bl_label = "New Group"
    bl_options = {'REGISTER', 'UNDO'}
    
    template: EnumProperty(
        name="Template",
        items=TEMPLATE_ENUM,
        default='BASIC'
    )

    group_name: bpy.props.StringProperty(
        name="Group Name",
        description="Name of the new group",
        default="New Group",
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
    
    set_view_transform: BoolProperty(
        name="Use Standard View Transform",
        description="Use the standard view transform",
        default=True
    )
    
    pbr_add_color: BoolProperty(
        name="Add Color",
        description="Add a color to the PBR setup",
        default=True
    )
    
    pbr_add_roughness: BoolProperty(
        name="Add Roughness",
        description="Add a roughness to the PBR setup",
        default=False
    )
    
    pbr_add_metallic: BoolProperty(
        name="Add Metallic",
        description="Add a metallic to the PBR setup",
        default=False
    )
    
    pbr_add_normal: BoolProperty(
        name="Add Normal",
        description="Add a normal to the PBR setup",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def process_material(self, context):
        # See if there is any material slot on the active object
        if not context.active_object.active_material:
            bpy.data.materials.new(name="New Material")
            context.active_object.active_material = bpy.data.materials[-1]
        
        ps_ctx = self.ensure_context(context)
        mat = ps_ctx.active_material
        mat.use_nodes = True
        
        if self.use_alpha_blend:
            mat.blend_method = 'BLEND'
        if self.disable_show_backface:
            mat.show_transparent_back = False
            mat.use_backface_culling = True
        if self.set_view_transform:
            context.scene.view_settings.view_transform = 'Standard'
        
        node_tree = bpy.data.node_groups.new(name=f"Paint System ({self.group_name})", type='ShaderNodeTree')
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        new_group = lm.add_item()
        new_group.name = self.group_name
        new_group.node_tree = node_tree
        new_group.update_node_tree(context)
        mat_node_tree = mat.node_tree
        
        # Create Channels and layers and setup the group
        match self.template:
            case 'BASIC':
                bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Color', channel_type='COLOR', use_alpha=True)
                bpy.ops.paint_system.new_solid_color_layer('INVOKE_DEFAULT')
                
                right_most_node = None
                for node in mat_node_tree.nodes:
                    if right_most_node is None:
                        right_most_node = node
                    elif node.location.x > right_most_node.location.x:
                        right_most_node = node
                node_group = mat_node_tree.nodes.new(type='ShaderNodeGroup')
                node_group.node_tree = node_tree
                node_group.location = right_most_node.location + Vector((200, 0))
                mix_shader = mat_node_tree.nodes.new(type='ShaderNodeMixShader')
                mix_shader.location = node_group.location + Vector((200, 0))
                transparent_node = mat_node_tree.nodes.new(type='ShaderNodeBsdfTransparent')
                transparent_node.location = node_group.location + Vector((0, 100))
                mat_output = mat_node_tree.nodes.new(type='ShaderNodeOutputMaterial')
                mat_output.location = mix_shader.location + Vector((200, 0))
                mat_output.is_active_output = True
                mat_node_tree.links.new(node_group.outputs[0], mix_shader.inputs[2])
                mat_node_tree.links.new(node_group.outputs[1], mix_shader.inputs[0])
                mat_node_tree.links.new(transparent_node.outputs[0], mix_shader.inputs[1])
                mat_node_tree.links.new(mix_shader.outputs[0], mat_output.inputs[0])
            case 'PBR':
                material_output = get_material_output(mat_node_tree)
                def find_principled_node(node_list: list[Node]) -> Node | None:
                    for node in node_list:
                        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
                            return node
                        for input_socket in node.inputs:
                            nodes = [link.from_node for link in input_socket.links]
                            if len(nodes) > 0:
                                return find_principled_node(nodes)
                    return None
                principled_node = find_principled_node([material_output])
                if principled_node is None:
                    principled_node = mat_node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
                    principled_node.location = material_output.location + Vector((-200, 0))
                node_group = mat_node_tree.nodes.new(type='ShaderNodeGroup')
                node_group.node_tree = node_tree
                node_group.location = principled_node.location + Vector((-200, 0))
                mat_node_tree.links.new(principled_node.outputs[0], material_output.inputs[0])

                if self.pbr_add_color:
                    bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Color', channel_type='COLOR', use_alpha=True)
                    bpy.ops.paint_system.new_solid_color_layer('INVOKE_DEFAULT')
                    transfer_connection(principled_node.inputs['Base Color'], node_group.inputs['Color'])
                    transfer_connection(principled_node.inputs['Alpha'], node_group.inputs['Color Alpha'])
                    mat_node_tree.links.new(node_group.outputs['Color'], principled_node.inputs['Base Color'])
                    mat_node_tree.links.new(node_group.outputs['Color Alpha'], principled_node.inputs['Alpha'])

                if self.pbr_add_metallic:
                    bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Metallic', channel_type='FLOAT', use_alpha=False, use_factor=True)
                    mat_node_tree.links.new(node_group.outputs['Metallic'], principled_node.inputs['Metallic'])
                if self.pbr_add_roughness:
                    bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Roughness', channel_type='FLOAT', use_alpha=False, use_factor=True)
                    mat_node_tree.links.new(node_group.outputs['Roughness'], principled_node.inputs['Roughness'])
                if self.pbr_add_normal:
                    bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Normal', channel_type='VECTOR', use_alpha=False, normalize=True)
                    mat_node_tree.links.new(node_group.outputs['Normal'], principled_node.inputs['Normal'])
                    tex_coord = mat_node_tree.nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = node_group.location + Vector((-200, 0))
                    mat_node_tree.links.new(tex_coord.outputs['Normal'], node_group.inputs['Normal'])
                    norm_map_node = mat_node_tree.nodes.new(type='ShaderNodeNormalMap')
                    norm_map_node.location = node_group.location + Vector((0, -300))
                    norm_map_node.space = 'OBJECT'
                    mat_node_tree.links.new(node_group.outputs['Normal'], norm_map_node.inputs[1])
                    mat_node_tree.links.new(norm_map_node.outputs[0], principled_node.inputs['Normal'])
                ps_ctx = self.ensure_context(context)
                ps_ctx.active_group.active_index = 0

                nodes = traverse_connected_nodes(principled_node)
                for node in nodes:
                    node.location = node.location + Vector((0, -200))

            case 'PAINT_OVER':
                bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Color', channel_type='COLOR', use_alpha=True)
                bpy.ops.paint_system.new_solid_color_layer('INVOKE_DEFAULT')
            case 'NORMAL':
                bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Normal', channel_type='VECTOR', use_alpha=True)
            case _:
                bpy.ops.paint_system.add_channel('EXEC_DEFAULT', channel_name='Color', channel_type='COLOR', use_alpha=True)
                bpy.ops.paint_system.new_solid_color_layer('INVOKE_DEFAULT')
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)
    
    def draw(self, context):
        layout = self.layout
        self.multiple_objects_ui(layout, context)
        row = layout.row()
        scale_content(context, row, 1.5, 1.5)
        row.prop(self, "template", text="Template")
        
        if self.template in ['PBR']:
            box = layout.box()
            row = box.row()
            row.alignment = "CENTER"
            row.label(text="PBR Channels:", icon="MATERIAL")
            col = box.column(align=True)
            col.prop(self, "pbr_add_color", text="Color", icon_value=get_icon('color_socket'))
            col.prop(self, "pbr_add_metallic", text="Metallic", icon_value=get_icon('float_socket'))
            col.prop(self, "pbr_add_roughness", text="Roughness", icon_value=get_icon('float_socket'))
            col.prop(self, "pbr_add_normal", text="Normal", icon_value=get_icon('vector_socket'))
        
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Advanced Settings:", icon="TOOL_SETTINGS")
        split = box.split(factor=0.4)
        split.label(text="Group Name:")
        split.prop(self, "group_name", text="", icon='NODETREE')
        if self.template in ['BASIC']:
            box.prop(self, "use_alpha_blend", text="Use Alpha Blend")
            box.prop(self, "disable_show_backface",
                     text="Use Backface Culling")
        if context.scene.view_settings.view_transform != 'Standard':
            box.prop(self, "set_view_transform",
                     text="Use Standard View Transform")


class PAINTSYSTEM_OT_DeleteGroup(PSContextMixin, MultiMaterialOperator):
    """Delete the selected group in the Paint System"""
    bl_idname = "paint_system.delete_group"
    bl_label = "Delete Group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_group is not None

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        lm.remove_active_item()
        return {'FINISHED'}


class PAINTSYSTEM_OT_MoveGroup(PSContextMixin, MultiMaterialOperator):
    """Move the selected group in the Paint System"""
    bl_idname = "paint_system.move_group"
    bl_label = "Move Group"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", "Move group up"),
            ('DOWN', "Down", "Move group down")
        ],
        default='UP'
    )

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return bool(ps_ctx.ps_mat_data and ps_ctx.ps_mat_data.active_index >= 0)

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        lm.move_active_down() if self.direction == 'DOWN' else lm.move_active_up()
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_NewGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_MoveGroup,
)

register, unregister = register_classes_factory(classes)    