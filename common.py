import bpy
from bpy.types import Context, Node, NodeTree, Image
from typing import List
from mathutils import Vector
from typing import List, Tuple
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


def import_legacy_updater():
    try:
        from . import addon_updater_ops
        return addon_updater_ops
    except ImportError:
        return None


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()


def map_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


# Fixes UnicodeDecodeError bug
STRING_CACHE = {}


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

    def create_node(self, node_type, attrs = {}):
        node = self.nodes.new(node_type)
        for attr in attrs:
            self.value_set(node, attr, attrs[attr])
        self.created_nodes_names.append(node.name)
        return node

    def create_link(self, from_node_name: str, to_node_name: str, from_socket_name, to_socket_name):
        output_node = self.nodes[from_node_name]
        input_node = self.nodes[to_node_name]
        self.links.new(input_node.inputs[to_socket_name],
                       output_node.outputs[from_socket_name])

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
        (uv_map.name, uv_map.name, "") for uv_map in context.active_object.data.uv_layers
    ]
    return intern_enum_items(items)


def find_keymap(keymap_name):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km in kc.keymaps:
            if km:
                kmi = km.keymap_items.get(keymap_name)
                if kmi:
                    return kmi
    return None


def get_event_icons(kmi):
    """Return a list of icons for a keymap item, including modifiers

    Args:
        kmi: KeyMapItem object

    Returns:
        list: List of Blender icon identifiers
    """
    # Create a list to store all icons
    icons = []

    # Add modifier icons first (in standard order)
    if kmi.ctrl:
        icons.append('EVENT_CTRL')
    if kmi.alt:
        icons.append('EVENT_ALT')
    if kmi.shift:
        icons.append('EVENT_SHIFT')
    if kmi.oskey:
        icons.append('EVENT_OS')

    # Dictionary mapping key types to icons
    key_icons = {
        # Mouse
        'LEFTMOUSE': 'MOUSE_LMB',
        'RIGHTMOUSE': 'MOUSE_RMB',
        'MIDDLEMOUSE': 'MOUSE_MMB',
        'WHEELUPMOUSE': 'MOUSE_LMB_DRAG',
        'WHEELDOWNMOUSE': 'MOUSE_LMB_DRAG',

        # Special keys
        'ESC': 'EVENT_ESC',
        'RET': 'EVENT_RETURN',
        'SPACE': 'EVENT_SPACEKEY',
        'TAB': 'EVENT_TAB',
        'DEL': 'EVENT_DELETEKEY',
        'BACK_SPACE': 'EVENT_BACKSPACEKEY',
        'COMMA': 'EVENT_COMMA',
        'PERIOD': 'EVENT_PERIOD',
        'SEMI_COLON': 'EVENT_SEMI_COLON',
        'QUOTE': 'EVENT_QUOTE',

        # Numbers
        '0': 'EVENT_0',
        '1': 'EVENT_1',
        '2': 'EVENT_2',
        '3': 'EVENT_3',
        '4': 'EVENT_4',
        '5': 'EVENT_5',
        '6': 'EVENT_6',
        '7': 'EVENT_7',
        '8': 'EVENT_8',
        '9': 'EVENT_9',

        # Letters
        'A': 'EVENT_A',
        'B': 'EVENT_B',
        'C': 'EVENT_C',
        'D': 'EVENT_D',
        'E': 'EVENT_E',
        'F': 'EVENT_F',
        'G': 'EVENT_G',
        'H': 'EVENT_H',
        'I': 'EVENT_I',
        'J': 'EVENT_J',
        'K': 'EVENT_K',
        'L': 'EVENT_L',
        'M': 'EVENT_M',
        'N': 'EVENT_N',
        'O': 'EVENT_O',
        'P': 'EVENT_P',
        'Q': 'EVENT_Q',
        'R': 'EVENT_R',
        'S': 'EVENT_S',
        'T': 'EVENT_T',
        'U': 'EVENT_U',
        'V': 'EVENT_V',
        'W': 'EVENT_W',
        'X': 'EVENT_X',
        'Y': 'EVENT_Y',
        'Z': 'EVENT_Z',

        # Function keys
        'F1': 'EVENT_F1',
        'F2': 'EVENT_F2',
        'F3': 'EVENT_F3',
        'F4': 'EVENT_F4',
        'F5': 'EVENT_F5',
        'F6': 'EVENT_F6',
        'F7': 'EVENT_F7',
        'F8': 'EVENT_F8',
        'F9': 'EVENT_F9',
        'F10': 'EVENT_F10',
        'F11': 'EVENT_F11',
        'F12': 'EVENT_F12',

        # Arrows
        'LEFT_ARROW': 'EVENT_LEFT_ARROW',
        'RIGHT_ARROW': 'EVENT_RIGHT_ARROW',
        'UP_ARROW': 'EVENT_UP_ARROW',
        'DOWN_ARROW': 'EVENT_DOWN_ARROW',

        # Numpad
        'NUMPAD_0': 'EVENT_0',
        'NUMPAD_1': 'EVENT_1',
        'NUMPAD_2': 'EVENT_2',
        'NUMPAD_3': 'EVENT_3',
        'NUMPAD_4': 'EVENT_4',
        'NUMPAD_5': 'EVENT_5',
        'NUMPAD_6': 'EVENT_6',
        'NUMPAD_7': 'EVENT_7',
        'NUMPAD_8': 'EVENT_8',
        'NUMPAD_9': 'EVENT_9',
        'NUMPAD_PLUS': 'EVENT_PLUS',
        'NUMPAD_MINUS': 'EVENT_MINUS',
        'NUMPAD_ASTERIX': 'EVENT_ASTERISK',
        'NUMPAD_SLASH': 'EVENT_SLASH',
        'NUMPAD_PERIOD': 'EVENT_PERIOD',
        'NUMPAD_ENTER': 'EVENT_RETURN',
    }

    # Add the key icon if it exists in our mapping
    if kmi.type in key_icons:
        icons.append(key_icons[kmi.type])
    else:
        # Fall back to a generic keyboard icon for unknown keys
        icons.append('KEYINGSET')

    return icons


def get_connected_nodes(output_node: Node) -> List[Tuple[Node, int]]:
    """
    Gets all nodes connected to the given output_node with their search depth,
    maintaining the order in which they were found and removing duplicates.

    Args:
        output_node: The output node.

    Returns:
        A list of tuples (Node, depth), preserving the order of discovery and removing duplicates.
    """
    nodes = []
    visited = set()  # Track visited nodes to avoid duplicates

    def traverse(node: Node, depth: int = 0):
        if node not in visited:  # Check if the node has been visited
            visited.add(node)  # Add the node to the visited set
            if not node.mute:
                nodes.append((node, depth))
                if hasattr(node, 'node_tree') and node.node_tree:
                    for sub_node in node.node_tree.nodes:
                        traverse(sub_node, depth + 1)
            for input in node.inputs:
                for link in input.links:
                    traverse(link.from_node, depth)

    traverse(output_node)
    return nodes


def get_active_material_output(node_tree: NodeTree) -> Node:
    """Get the active material output node

    Args:
        node_tree (bpy.types.NodeTree): The node tree to check

    Returns:
        bpy.types.Node: The active material output node
    """
    for node in node_tree.nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial" and node.is_active_output:
            return node
    return None
