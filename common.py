from typing import Tuple, Optional
from bpy.types import Context, Image, Material, PropertyGroup, NodeTree, Node
import bpy
import re
import os


LIBRARY_FILE_NAME = "library.blend"
NODE_GROUP_PREFIX = "_PS"


def get_addon_filepath():
    return os.path.dirname(bpy.path.abspath(__file__)) + os.sep


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


def cleanup_duplicate_nodegroups(node_tree: NodeTree):
    """
    Cleanup duplicate node groups by using Blender's remap_users feature.
    This automatically handles all node links and nested node groups.

    Args:
        node_group_name (str): Name of the main node group to clean up
    """
    def find_original_nodegroup(name):
        # Get the base name by removing the .001, .002 etc. if present
        # This gets the part before the first dot
        base_name = name.split('.')[0]

        # Find all matching node groups
        matching_groups = [ng for ng in bpy.data.node_groups
                           if ng.name == base_name or ng.name.split('.')[0] == base_name]

        if not matching_groups:
            return None

        # The original is likely the one without a number suffix
        # or the one with the lowest number if all have suffixes
        for ng in matching_groups:
            if ng.name == base_name:  # Exact match without any suffix
                return ng

        # If we didn't find an exact match, return the one with lowest suffix number
        return sorted(matching_groups, key=lambda x: x.name)[0]

    # Process each node group
    for node in node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            ng = node.node_tree

            # Find the original node group
            original_group = find_original_nodegroup(ng.name)

            # If this is a duplicate (not the original) and we found the original
            if original_group and ng != original_group:
                # Remap all users of this node group to the original
                ng.user_remap(original_group)
                # Remove the now-unused node group
                bpy.data.node_groups.remove(ng)


def get_node_from_library(tree_name, force_reload=False):
    # Check if the node group already exists
    ng = bpy.data.node_groups.get(tree_name)
    if ng:
        if force_reload:
            bpy.data.node_groups.remove(ng)
        else:
            return ng

    # Load the library file
    filepath = get_addon_filepath() + LIBRARY_FILE_NAME
    with bpy.data.libraries.load(filepath) as (lib_file, current_file):
        lib_node_group_names = lib_file.node_groups
        current_node_groups_names = current_file.node_groups
        for node_group_name in lib_node_group_names:
            if node_group_name == tree_name:
                current_node_groups_names.append(node_group_name)

    # Getting the node group
    ng = bpy.data.node_groups.get(tree_name)
    if not ng:
        return None
    cleanup_duplicate_nodegroups(ng)
    return ng


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


def get_uv_maps_names(self, context: Context):
    return [(uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers]
