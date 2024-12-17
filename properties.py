import bpy
from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (PropertyGroup, Context,
                       NodeTreeInterface, Nodes, NodeTree, NodeLinks)
from .nested_list_manager import BaseNestedListItem, BaseNestedListManager
from mathutils import Vector


def get_groups(self, context):
    mat = context.active_object.active_material
    if not mat or not hasattr(mat, "paint_system"):
        return []
    return [(str(i), group.name, f"Group {i}") for i, group in enumerate(mat.paint_system.groups)]


class PaintSystemLayer(BaseNestedListItem):

    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True
    )
    # opacity: FloatProperty(
    #     name="Opacity",
    #     description="Layer opacity",
    #     min=0.0,
    #     max=1.0,
    #     default=1.0
    # )
    # clip_below: BoolProperty(
    #     name="Clip Below",
    #     description="Clip layers below this one",
    #     default=False
    # )
    # blend_mode: EnumProperty(
    #     name="Blend Mode",
    #     items=[
    #         ('NORMAL', "Normal", "Normal blend mode"),
    #         ('MULTIPLY', "Multiply", "Multiply blend mode"),
    #         ('SCREEN', "Screen", "Screen blend mode"),
    #         ('OVERLAY', "Overlay", "Overlay blend mode"),
    #         ('DARKEN', "Darken", "Darken blend mode"),
    #         ('LIGHTEN', "Lighten", "Lighten blend mode"),
    #         ('COLOR_DODGE', "Color Dodge", "Color Dodge blend mode"),
    #         ('COLOR_BURN', "Color Burn", "Color Burn blend mode"),
    #         ('HARD_LIGHT', "Hard Light", "Hard Light blend mode"),
    #         ('SOFT_LIGHT', "Soft Light", "Soft Light blend mode"),
    #         ('DIFFERENCE', "Difference", "Difference blend mode"),
    #         ('EXCLUSION', "Exclusion", "Exclusion blend mode"),
    #         ('HUE', "Hue", "Hue blend mode"),
    #         ('SATURATION', "Saturation", "Saturation blend mode"),
    #         ('COLOR', "Color", "Color blend mode"),
    #         ('LUMINOSITY', "Luminosity", "Luminosity blend mode"),
    #     ],
    #     default='NORMAL'
    # )
    # interpolation: EnumProperty(
    #     name="Interpolation",
    #     items=[
    #         ('NEAREST', "Nearest", "Nearest interpolation"),
    #         ('LINEAR', "Linear", "Linear interpolation"),
    #         ('CUBIC', "Cubic", "Cubic interpolation"),
    #         ('SMART', "Smart", "Smart interpolation")
    #     ],
    #     default='NEAREST',
    #     description="Interpolation method"
    # )
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image
    )
    type: EnumProperty(
        items=[
            ('FOLDER', "Folder", "Folder layer"),
            ('IMAGE', "Image", "Image layer"),
        ],
        default='IMAGE'
    )
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
    )


class PaintSystemGroup(BaseNestedListManager):
    def test(self):
        print("test")

    def update_active_image(self, context: Context):
        image_paint = context.tool_settings.image_paint
        flattened = self.flatten_hierarchy()
        if not flattened:
            return None
        active_layer = flattened[self.active_index][0]
        if not active_layer:
            return

        image_paint.canvas = active_layer.image
        if image_paint.mode == 'MATERIAL':
            image_paint.mode = 'IMAGE'

    def update_node_tree(self):
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
        depth_inputs = {}

        # Add group input and output nodes
        ng_input = nodes.new('NodeGroupInput')
        ng_output = nodes.new('NodeGroupOutput')
        depth_inputs[-1] = (ng_output.inputs['Color'],
                            ng_output.inputs['Alpha'], ng_output.location)

        for item, _ in flattened:
            group_node = nodes.new('ShaderNodeGroup')
            group_node.node_tree = item.node_tree
            inputs = depth_inputs[item.parent_id]
            group_node.location = inputs[2] + Vector((-200, 0))
            links.new(inputs[0], group_node.outputs['Color'])
            links.new(inputs[1], group_node.outputs['Alpha'])
            if item.type == 'IMAGE':
                depth_inputs[item.parent_id] = (
                    group_node.inputs['Color'], group_node.inputs['Alpha'], group_node.location)
            elif item.type == 'FOLDER':
                depth_inputs[item.parent_id] = (
                    group_node.inputs['Under Color'], group_node.inputs['Under Alpha'], group_node.location)
                depth_inputs[item.id] = (
                    group_node.inputs['Over Color'], group_node.inputs['Over Alpha'], group_node.location + Vector((0, 250)))

        inputs = depth_inputs[-1]
        links.new(inputs[0], ng_input.outputs['Color'])
        links.new(inputs[1], ng_input.outputs['Alpha'])
        ng_input.location = inputs[2] + Vector((-200, 0))

    # Define the collection property directly in the class
    items: CollectionProperty(type=PaintSystemLayer)
    active_index: IntProperty(
        name="Active Index",
        description="Active layer index",
        update=update_active_image
    )
    node_tree: PointerProperty(
        name="Node Tree",
        type=bpy.types.NodeTree
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
        items=get_groups
    )


classes = (
    PaintSystemLayer,
    PaintSystemGroup,
    PaintSystemGroups
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Material.paint_system = PointerProperty(type=PaintSystemGroups)


def unregister():
    del bpy.types.Material.paint_system
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
