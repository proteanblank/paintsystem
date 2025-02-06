import bpy
from bpy.types import Context
from typing import List
from mathutils import Vector

icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys(
)


def icon_parser(icon: str, default="NONE") -> str:
    if icon in icons:
        return icon
    return default


def is_online():
    return not bpy.app.version >= (4, 2, 0) or bpy.app.online_access


def is_newer_than(major, minor=0, patch=0):
    return bpy.app.version >= (major, minor, patch)


STRING_CACHE = {}


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()


def map_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))

# Fixes UnicodeDecodeError bug


def intern_enum_items(items):
    def intern_string(s):
        if not isinstance(s, str):
            return s
        global STRING_CACHE
        if s not in STRING_CACHE:
            STRING_CACHE[s] = s
        return STRING_CACHE[s]
    return [tuple(intern_string(s) for s in item) for item in items]


class NodeOrganizer:
    created_nodes_names: List[str]

    def __init__(self, material: bpy.types.Material):
        self.node_tree = material.node_tree
        self.nodes = self.node_tree.nodes
        self.links = self.node_tree.links
        self.rightmost = max(
            self.nodes, key=lambda node: node.location.x).location
        self.created_nodes_names = []

    def value_set(self, obj, path, value):
        if '.' in path:
            path_prop, path_attr = path.rsplit('.', 1)
            prop = obj.path_resolve(path_prop)
        else:
            prop = obj
            path_attr = path
        setattr(prop, path_attr, value)

    def create_node(self, node_type, attrs):
        node = self.nodes.new(node_type)
        for attr in attrs:
            self.value_set(node, attr, attrs[attr])
        self.created_nodes_names.append(node.name)
        return node

    def create_link(self, output_node_name: str, input_node_name: str, output_name, input_name):
        output_node = self.nodes[output_node_name]
        input_node = self.nodes[input_node_name]
        self.links.new(input_node.inputs[input_name],
                       output_node.outputs[output_name])

    def move_nodes_offset(self, offset: Vector):
        created_nodes = [self.nodes[name] for name in self.created_nodes_names]
        for node in created_nodes:
            if node.type != 'FRAME':
                node.location += offset

    def move_nodes_to_end(self):
        created_nodes = [self.nodes[name] for name in self.created_nodes_names]
        created_nodes_leftmost = min(
            created_nodes, key=lambda node: node.location.x).location
        offset = self.rightmost - created_nodes_leftmost + Vector((200, 0))
        self.move_nodes_offset(offset)


def get_object_uv_maps(self, context: Context):
    items = [
        (uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers
    ]
    return intern_enum_items(items)
