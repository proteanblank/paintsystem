from bpy.types import Context, Image
import bpy
import re
import os


LIBRARY_FILE_NAME = "library.blend"
NODE_GROUP_PREFIX = "_PS"


def get_addon_filepath():
    return os.path.dirname(bpy.path.abspath(__file__)) + os.sep


def get_active_material(self, context: Context):
    active_object = context.active_object
    if not active_object:
        return None
    if active_object.type != 'MESH':
        return None
    return active_object.active_material


def get_active_group(self, context: Context):
    mat = get_active_material(self, context)
    if not mat or not hasattr(mat, "paint_system"):
        return None
    if not mat.paint_system.groups:
        return None
    active_group_idx = int(mat.paint_system.active_group)
    return mat.paint_system.groups[active_group_idx]


def get_active_layer(self, context: Context):
    active_group = get_active_group(self, context)
    if not active_group:
        return None
    flattened = active_group.flatten_hierarchy()
    if not flattened:
        return None
    active_layer = flattened[active_group.active_index][0]
    return active_layer


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()


def get_highest_number_with_prefix(prefix, string_list):
    highest_number = 0
    for string in string_list:
        if string.startswith(prefix):
            # Extract numbers from the string using regex
            match = re.search(r'\d+', string)
            if match:
                number = int(match.group())
                if number > highest_number:
                    highest_number = number
    return highest_number


def update_group_node_tree(self, context: Context):
    active_group = get_active_group(self, context)
    if not active_group:
        return

    node_tree = active_group.node_tree

    # Delete all nodes
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)

    # Rebuild the node tree
    for layer in active_group.layers:
        layer.add_nodes(node_tree)


def on_item_delete(item):
    if item.node_tree:
        # 2 users: 1 for the node tree, 1 for the datablock
        if item.node_tree.users <= 2:
            # print("Removing node tree")
            bpy.data.node_groups.remove(item.node_tree)

    if item.image:
        # 2 users: 1 for the image datablock, 1 for the panel
        if item.image and item.image.users <= 2:
            # print("Removing image")
            bpy.data.images.remove(item.image)
