import bpy

from bpy.props import (IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (PropertyGroup, Context,
                       NodeTreeInterface, Nodes, NodeTree, NodeLinks, NodeSocket)
from .nested_list_manager import BaseNestedListItem, BaseNestedListManager
from mathutils import Vector
from .paint_system import PaintSystem, get_nodetree_from_library
from dataclasses import dataclass
from typing import Dict


def get_all_group_names(self, context):
    mat = context.active_object.active_material
    if not mat or not hasattr(mat, "paint_system"):
        return []
    return [(str(i), group.name, f"Group {i}") for i, group in enumerate(mat.paint_system.groups)]


def update_active_image(self=None, context: Context = None):
    context = context or bpy.context
    ps = PaintSystem(context)
    image_paint = context.tool_settings.image_paint
    mat = ps.get_active_material()
    active_layer = ps.get_active_layer()
    update_brush_settings(self, context)
    if not active_layer:
        return
    if active_layer.type != 'IMAGE' or active_layer.lock_layer:
        if image_paint.mode == 'MATERIAL':
            image_paint.mode = 'IMAGE'
        image_paint.canvas = None
        # Unable to paint
        return
    if image_paint.mode == 'IMAGE':
        image_paint.mode = 'MATERIAL'
    for i, image in enumerate(mat.texture_paint_images):
        if image == active_layer.image:
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


def update_paintsystem_image_name(self, context):
    ps = PaintSystem(context)
    active_group = ps.get_active_group()
    mat = ps.get_active_material()
    for layer in active_group.items:
        if layer.image:
            layer.image.name = f"PS {mat.name} {active_group.name} {layer.name}"


class PaintSystemLayer(BaseNestedListItem):

    def update_node_tree(self, context):
        PaintSystem(context).get_active_group().update_node_tree()

    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer",
        update=update_paintsystem_image_name
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True,
        update=update_node_tree
    )
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image
    )
    type: EnumProperty(
        items=[
            ('FOLDER', "Folder", "Folder layer"),
            ('IMAGE', "Image", "Image layer"),
            ('SOLID_COLOR', "Solid Color", "Solid Color layer"),
            ('ADJUSTMENT', "Adjustment", "Adjustment layer"),
        ],
        default='IMAGE'
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


@dataclass
class NodeEntry:
    color_input: NodeSocket
    alpha_input: NodeSocket
    location: Vector
    is_clip: bool
    clip_color_input: NodeSocket
    clip_alpha_input: NodeSocket


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
        for node in self.node_tree.nodes:
            self.node_tree.nodes.remove(node)

        # Check inputs and outputs
        if not self.node_tree.interface.items_tree:
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
            ng_output.inputs['Color'], ng_output.inputs['Alpha'], ng_output.location, False, None, None)

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
            group_node = nodes.new('ShaderNodeGroup')
            group_node.node_tree = item.node_tree
            group_node.location = node_entry.location + \
                Vector((-200, 0))
            group_node.mute = not item.enabled

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
                    group_node.location + Vector((0, -250)),
                    False,
                    None,
                    None)

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

        links.new(node_entry.color_input, ng_input.outputs['Color'])
        links.new(node_entry.alpha_input, ng_input.outputs['Alpha'])
        ng_input.location = node_entry.location + Vector((-200, 0))

    # Define the collection property directly in the class
    items: CollectionProperty(type=PaintSystemLayer)
    name: StringProperty(
        name="Name",
        description="Group name",
        default="Group",
        update=update_paintsystem_image_name
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
        type=bpy.types.Image
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
        update=update_active_image
    )


class PaintSystemSettings(PropertyGroup):
    brush_color: FloatVectorProperty(
        name="Brush Color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0)
    )
    brush_xray: BoolProperty(
        name="Brush X-Ray",
        description="Brush X-Ray",
        default=False
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
