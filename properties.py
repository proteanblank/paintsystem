import bpy

from bpy.props import (IntProperty,
                       FloatVectorProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (PropertyGroup, Context,
                       NodeTreeInterface, Nodes, NodeTree, NodeLinks, NodeSocket, Image)
from .nested_list_manager import BaseNestedListItem, BaseNestedListManager
from mathutils import Vector
from .paint_system import PaintSystem, get_nodetree_from_library, LAYER_ENUM, TEMPLATE_ENUM
from dataclasses import dataclass
from typing import Dict


def get_all_group_names(self, context):
    ps = PaintSystem(context)
    mat = ps.active_object.active_material
    if not mat or not hasattr(mat, "paint_system"):
        return []
    return [(str(i), group.name, f"Group {i}") for i, group in enumerate(mat.paint_system.groups)]


def update_active_image(self=None, context: Context = None):
    context = context or bpy.context
    ps = PaintSystem(context)
    if not ps.settings.allow_image_overwrite:
        return
    image_paint = context.tool_settings.image_paint
    mat = ps.get_active_material()
    active_group = ps.get_active_group()
    if not mat or not active_group:
        return
    active_layer = ps.get_active_layer()
    update_brush_settings(self, context)
    if not active_layer:
        return
    if active_layer.type != 'IMAGE' or active_layer.lock_layer or active_group.use_bake_image:
        if image_paint.mode == 'MATERIAL':
            image_paint.mode = 'IMAGE'
        image_paint.canvas = None
        # Unable to paint
        return
    if image_paint.mode == 'IMAGE':
        image_paint.mode = 'MATERIAL'
    for i, image in enumerate(mat.texture_paint_images):
        if image == (active_layer.mask_image if active_layer.edit_mask else active_layer.image):
            mat.paint_active_slot = i
            # Get uv map name
            uv_map_node = ps.find_uv_map_node()
            if uv_map_node:
                ps.active_object.data.uv_layers[uv_map_node.uv_map].active = True
            break


def update_brush_settings(self=None, context: Context = bpy.context):
    if context.mode != 'PAINT_TEXTURE':
        return
    ps = PaintSystem(context)
    active_layer = ps.get_active_layer()
    brush = context.tool_settings.image_paint.brush
    if not brush:
        return
    brush.use_alpha = not active_layer.lock_alpha


def update_paintsystem_data(self, context):
    ps = PaintSystem(context)
    ps._update_paintsystem_data()


class PaintSystemLayer(BaseNestedListItem):

    def update_node_tree(self, context):
        PaintSystem(context).get_active_group().update_node_tree()

    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer",
        update=update_paintsystem_data
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True,
        update=update_node_tree
    )
    image: PointerProperty(
        name="Image",
        type=Image
    )
    type: EnumProperty(
        items=LAYER_ENUM,
        default='IMAGE'
    )
    sub_type: StringProperty(
        name="Sub Type",
        default="",
    )
    clip: BoolProperty(
        name="Clip to Below",
        description="Clip the layer to the one below",
        default=False,
        update=update_node_tree
    )
    lock_alpha: BoolProperty(
        name="Lock Alpha",
        description="Lock the alpha channel",
        default=False,
        update=update_brush_settings
    )
    lock_layer: BoolProperty(
        name="Lock Layer",
        description="Lock the layer",
        default=False,
        update=update_active_image
    )
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
    )
    edit_mask: BoolProperty(
        name="Edit Mask",
        description="Edit mask",
        default=False,
    )
    mask_image: PointerProperty(
        name="Mask Image",
        type=Image,
        update=update_node_tree
    )
    enable_mask: BoolProperty(
        name="Enabled Mask",
        description="Toggle mask visibility",
        default=False,
        update=update_node_tree
    )
    mask_uv_map: StringProperty(
        name="Mask UV Map",
        default="",
        update=update_node_tree
    )
    edit_external_image: PointerProperty(
        name="Edit External Image",
        type=Image,
    )


@dataclass
class NodeEntry:
    color_input: NodeSocket
    alpha_input: NodeSocket
    location: Vector
    is_clip: bool = False
    clip_color_input: NodeSocket | None = None
    clip_alpha_input: NodeSocket | None = None
    mask_color_input: NodeSocket | None = None
    mask_alpha_input: NodeSocket | None = None


# class PaintSystemNodesStore:
#     def __init__(self):
#         self.data: Dict[int, NodeEntry] = {}

#     def add_entry(self, entry_id: int, entry: NodeEntry):
#         """Add a new entry to the datastore."""
#         self.data[entry_id] = entry

#     def get_entry(self, entry_id: int) -> NodeEntry:
#         """Retrieve an entry by its ID."""
#         return self.data.get(entry_id, None)

#     def remove_entry(self, entry_id: int):
#         """Remove an entry by its ID."""
#         if entry_id in self.data:
#             del self.data[entry_id]

#     def list_ids(self):
#         """List all entry IDs."""
#         return list(self.data.keys())


class PaintSystemGroup(BaseNestedListManager):

    def update_node_tree(self, context=bpy.context):
        self.normalize_orders()
        flattened = self.flatten_hierarchy()
        interface: NodeTreeInterface = self.node_tree.interface
        nodes: Nodes = self.node_tree.nodes
        links: NodeLinks = self.node_tree.links

        # Delete every node
        # for node in self.node_tree.nodes:
        #     self.node_tree.nodes.remove(node)

        # Create new node group
        def ensure_node_group(item):
            node_group = None
            for node in nodes:
                if node.type == 'GROUP' and node.node_tree == item.node_tree:
                    node_group = node
                    break
            if not node_group:
                node_group = nodes.new('ShaderNodeGroup')
                node_group.node_tree = item.node_tree
            return node_group

        # Remode every links
        links.clear()

        # Remove unused node groups
        for node in nodes:
            if node.type == 'GROUP':
                if node.node_tree not in [item.node_tree for item, _ in flattened]:
                    nodes.remove(node)
            else:
                nodes.remove(node)

        # Check inputs and outputs
        if not interface.items_tree:
            interface.new_socket(
                name="Color", in_out='INPUT', socket_type="NodeSocketColor")
            new_socket = interface.new_socket(
                name="Alpha", in_out='INPUT', socket_type="NodeSocketFloat")
            new_socket.subtype = 'FACTOR'
            new_socket.min_value = 0.0
            new_socket.max_value = 1.0
            interface.new_socket(
                name="Color", in_out='OUTPUT', socket_type="NodeSocketColor")
            new_socket = interface.new_socket(
                name="Alpha", in_out='OUTPUT', socket_type="NodeSocketFloat")
            new_socket.subtype = 'FACTOR'
            new_socket.min_value = 0.0
            new_socket.max_value = 1.0

        # Check if any node uses the normal input
        special_inputs = ['Normal']
        # special_sockets: list[NodeSocket] = []
        for input_name in special_inputs:
            interface_socket = interface.items_tree.get(input_name)

            special_socket_type = []
            for item, _ in flattened:
                if item.node_tree:
                    socket = item.node_tree.interface.items_tree.get(
                        input_name)
                    if socket:
                        special_socket_type.append(socket)
            if any(special_socket_type) != bool(interface_socket):
                if interface_socket:
                    interface.remove(interface_socket)
                else:
                    new_socket = interface.new_socket(
                        name=input_name, in_out='INPUT', socket_type=special_socket_type[0].socket_type)
                    new_socket.hide_value = special_socket_type[0].hide_value

        # use_normal = any([item.node_tree.inputs['Normal']
        #                  if item.node_tree else False for item, _ in flattened])
        # if use_normal:
        #     print("Use Normal")

        # Contains the inputs for each depth level and position in the hierarchy
        # depth_inputs = {}
        # temp_clip_inputs = []
        ps_nodes_store: Dict[int, NodeEntry] = {}

        # Add group input and output nodes
        ng_input = nodes.new('NodeGroupInput')
        ng_output = nodes.new('NodeGroupOutput')
        # depth_inputs[-1] = (ng_output.inputs['Color'],
        #                     ng_output.inputs['Alpha'], ng_output.location)
        ps_nodes_store[-1] = NodeEntry(
            ng_output.inputs['Color'], ng_output.inputs['Alpha'], ng_output.location)

        for item, _ in flattened:
            is_clip = item.clip
            node_entry = ps_nodes_store[item.parent_id]
            if is_clip and not node_entry.is_clip:
                alpha_over_nt = get_nodetree_from_library(
                    '_PS_Alpha_Over')
                group_node = nodes.new('ShaderNodeGroup')
                group_node.node_tree = alpha_over_nt
                group_node.location = node_entry.location + \
                    Vector((-200, 0))
                links.new(node_entry.color_input,
                          group_node.outputs['Color'])
                links.new(node_entry.alpha_input,
                          group_node.outputs['Alpha'])
                node_entry.color_input = group_node.inputs['Under Color']
                node_entry.alpha_input = group_node.inputs['Under Alpha']
                node_entry.location = group_node.location
                node_entry.clip_color_input = group_node.inputs['Over Color']
                node_entry.clip_alpha_input = group_node.inputs['Over Alpha']

            # Connect layer node group
            group_node = ensure_node_group(item)
            # group_node = reset_node_properties(group_node)
            group_node.inputs['Alpha'].default_value = 0.0
            # group_node = nodes.new('ShaderNodeGroup')
            # group_node.node_tree = item.node_tree
            group_node.location = node_entry.location + \
                Vector((-200, 0))
            group_node.mute = not item.enabled
            
            if node_entry.mask_color_input and node_entry.mask_alpha_input:
                links.new(node_entry.mask_color_input,
                          group_node.outputs['Color'])
                links.new(node_entry.mask_alpha_input,
                          group_node.outputs['Alpha'])
                node_entry.mask_color_input = None
                node_entry.mask_alpha_input = None
            
            if item.enable_mask:
                mask_nt = get_nodetree_from_library(
                    '_PS_Mask')
                mask_node = nodes.new('ShaderNodeGroup')
                mask_node.node_tree = mask_nt
                mask_node.location = group_node.location
                group_node.location += Vector((-200, 0))
                
                mask_image_node = nodes.new('ShaderNodeTexImage')
                mask_image_node.image = item.mask_image
                mask_image_node.location = mask_node.location + Vector((-200, -200))
                mask_image_node.width = 140
                mask_image_node.hide = True
                
                mask_uvmap_node = nodes.new('ShaderNodeUVMap')
                mask_uvmap_node.uv_map = item.mask_uv_map
                mask_uvmap_node.location = mask_image_node.location + Vector((0, -50))
                mask_uvmap_node.hide = True
                
                if item.image:
                    image_texture_node = item.node_tree.nodes['Image Texture']
                    mask_image_node.interpolation = image_texture_node.interpolation
                    mask_image_node.extension = image_texture_node.extension
                
                node_entry.location = mask_node.location
                node_entry.mask_color_input = mask_node.inputs['Original Color']
                node_entry.mask_alpha_input = mask_node.inputs['Original Alpha']
                links.new(node_entry.color_input,
                          mask_node.outputs['Color'])
                links.new(node_entry.alpha_input,
                          mask_node.outputs['Alpha'])
                links.new(mask_image_node.outputs['Color'],
                          mask_node.inputs['Mask Alpha'])
                links.new(mask_uvmap_node.outputs['UV'],
                            mask_image_node.inputs['Vector'])
                node_entry.color_input = mask_node.inputs['Color']
                node_entry.alpha_input = mask_node.inputs['Alpha']

            if is_clip or node_entry.is_clip:
                links.new(node_entry.clip_color_input,
                          group_node.outputs['Color'])
                node_entry.clip_color_input = group_node.inputs['Color']
                if not is_clip:
                    links.new(node_entry.clip_alpha_input,
                              group_node.outputs['Alpha'])
                    node_entry.clip_alpha_input = group_node.inputs['Alpha']
                else:
                    group_node.inputs['Alpha'].default_value = 1.0
            else:
                links.new(node_entry.color_input,
                          group_node.outputs['Color'])
                links.new(node_entry.alpha_input,
                          group_node.outputs['Alpha'])
                node_entry.color_input = group_node.inputs['Color']
                node_entry.alpha_input = group_node.inputs['Alpha']
            node_entry.location = group_node.location
            node_entry.is_clip = is_clip

            if item.type == 'FOLDER':
                ps_nodes_store[item.id] = NodeEntry(
                    group_node.inputs['Over Color'],
                    group_node.inputs['Over Alpha'],
                    group_node.location + Vector((0, -250)))

        node_entry = ps_nodes_store[-1]
        if self.bake_image and self.use_bake_image:
            bake_image_node = nodes.new('ShaderNodeTexImage')
            bake_image_node.image = self.bake_image
            bake_image_node.location = ng_output.location + Vector((-300, 300))
            bake_image_node.interpolation = 'Closest'
            uvmap_node = nodes.new('ShaderNodeUVMap')
            uvmap_node.uv_map = self.bake_uv_map
            uvmap_node.location = bake_image_node.location + Vector((-200, 0))
            links.new(uvmap_node.outputs['UV'],
                      bake_image_node.inputs['Vector'])
            links.new(ng_output.inputs['Color'],
                      bake_image_node.outputs['Color'])
            links.new(ng_output.inputs['Alpha'],
                      bake_image_node.outputs['Alpha'])

        # Connect special inputs
        for input_name in special_inputs:
            for node in nodes:
                if node.type == 'GROUP':
                    socket = node.inputs.get(
                        input_name)
                    if socket:
                        links.new(socket, ng_input.outputs[socket.name])

        links.new(node_entry.color_input, ng_input.outputs['Color'])
        links.new(node_entry.alpha_input, ng_input.outputs['Alpha'])
        if node_entry.mask_color_input and node_entry.mask_alpha_input:
            links.new(node_entry.mask_color_input,
                        ng_input.outputs['Color'])
            links.new(node_entry.mask_alpha_input,
                        ng_input.outputs['Alpha'])
            node_entry.mask_color_input = None
            node_entry.mask_alpha_input = None
        ng_input.location = node_entry.location + Vector((-200, 0))

    # Define the collection property directly in the class
    items: CollectionProperty(type=PaintSystemLayer)
    name: StringProperty(
        name="Name",
        description="Group name",
        default="Group",
        update=update_paintsystem_data
    )
    active_index: IntProperty(
        name="Active Index",
        description="Active layer index",
        update=update_active_image,
    )
    node_tree: PointerProperty(
        name="Node Tree",
        type=bpy.types.NodeTree
    )
    bake_image: PointerProperty(
        name="Bake Image",
        type=Image
    )
    bake_uv_map: StringProperty(
        name="Bake Image UV Map",
        default="UVMap",
        update=update_node_tree
    )
    use_bake_image: BoolProperty(
        name="Use Bake Image",
        default=False,
        update=update_node_tree
    )

    @property
    def item_type(self):
        return PaintSystemLayer

    def get_movement_menu_items(self, item_id, direction):
        """
        Get menu items for movement options.
        Returns list of tuples (identifier, label, description)
        """
        options = self.get_movement_options(item_id, direction)
        menu_items = []

        # Map option identifiers to their operators
        operator_map = {
            'UP': 'paint_system.move_up',
            'DOWN': 'paint_system.move_down'
        }

        for identifier, description in options:
            menu_items.append((
                operator_map[direction],
                description,
                {'action': identifier}
            ))

        return menu_items


class PaintSystemGroups(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Paint system name",
        default="Paint System"
    )
    groups: CollectionProperty(type=PaintSystemGroup)
    active_group: EnumProperty(
        name="Active Group",
        description="Select active group",
        items=get_all_group_names,
        update=update_active_image,
    )
    use_paintsystem_uv: BoolProperty(
        name="Use Paint System UV",
        description="Use the Paint System UV Map",
        default=True
    )


class PaintSystemSettings(PropertyGroup):
    brush_xray: BoolProperty(
        name="Brush X-Ray",
        description="Brush X-Ray",
        default=False
    )
    allow_image_overwrite: BoolProperty(
        name="Allow Image Overwrite",
        description="Make Image in 3D Viewport the same as the active layer",
        default=True
    )

    template: EnumProperty(
        name="Template",
        items=TEMPLATE_ENUM,
        default='STANDARD',
    )


classes = (
    PaintSystemLayer,
    PaintSystemGroup,
    PaintSystemGroups,
    PaintSystemSettings
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.paint_system_settings = PointerProperty(
        type=PaintSystemSettings)
    bpy.types.Material.paint_system = PointerProperty(type=PaintSystemGroups)


def unregister():
    del bpy.types.Material.paint_system
    del bpy.types.Scene.paint_system_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
