import bpy
from .common import get_addon_filepath, LIBRARY_FILE_NAME


def cleanup_duplicate_nodegroups(node_tree: bpy.types.NodeTree):
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


def get_node_from_library(tree_name):
    # Check if the node group already exists
    ng = bpy.data.node_groups.get(tree_name)
    if ng:
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


class NodeTreeManager:
    def __init__(self, node_tree: bpy.types.NodeTree):
        self.node_tree = node_tree

    def add_node(self, node_name: str, location: tuple):
        ng = get_node_from_library(node_name)
        if not ng:
            return None

        node = self.node_tree.nodes.new('ShaderNodeGroup')
        node.node_tree = ng
        node.location = location

        return node

    def add_node_link(self, output_node, output_socket, input_node, input_socket):
        return self.node_tree.links.new(output_node.outputs[output_socket], input_node.inputs[input_socket])
