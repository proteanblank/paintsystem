import bpy
from bpy.types import Context, Material, Image, NodeTree, Node, PropertyGroup
from typing import Optional, Tuple
from dataclasses import dataclass
import os


LIBRARY_FILE_NAME = "library.blend"
NODE_GROUP_PREFIX = "_PS"
BRUSH_PREFIX = "PS_"


def get_addon_filepath():
    return os.path.dirname(bpy.path.abspath(__file__)) + os.sep


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


def get_brushes_from_library():
    # Load the library file
    filepath = get_addon_filepath() + LIBRARY_FILE_NAME
    with bpy.data.libraries.load(filepath) as (lib_file, current_file):
        lib_brushes = lib_file.brushes
        current_brushes = current_file.brushes
        for brush in lib_brushes:
            if brush.startswith(BRUSH_PREFIX) and brush not in bpy.data.brushes:
                current_brushes.append(brush)


@dataclass
class PaintSystemPreferences:
    # unified_brush_color: bool
    # unified_brush_size: bool
    pass


class PaintSystem:
    def __init__(self, context: Context):
        self.preferences: PaintSystemPreferences = bpy.context.preferences.addons[
            __package__].preferences
        self.context = context
        self.active_object = context.active_object
        self.settings = self._get_paint_system_settings()
        self.active_material = self._get_active_material()
        self.groups = self._get_groups()
        self.active_group = self._get_active_group()
        self.active_layer = self._get_active_layer()
        self.layer_node_tree = self._get_layer_node_tree()
        self.layer_node_group = self._get_layer_node_group()
        self.color_mix_node = self._find_color_mix_node()
        self.uv_map_node = self._find_uv_map_node()
        self.opacity_mix_node = self._find_opacity_mix_node()
        self.clip_mix_node = self._find_clip_mix_node()
        self.rgb_node = self._find_rgb_node()

    def add_group(self, name: str) -> PropertyGroup:
        """Creates a new group in the active material's paint system.

        Args:
            name (str): The name of the new group.

        Returns:
            PropertyGroup: The newly created group.
        """
        new_group = self.active_material.paint_system.groups.add()
        new_group.name = name
        node_tree = bpy.data.node_groups.new(
            name=f"PS_GRP {name} (MAT: {self.active_material.name})", type='ShaderNodeTree')
        new_group.node_tree = node_tree
        new_group.update_node_tree()
        # Set the active group to the newly created one
        self.active_material.paint_system.active_group = str(
            len(self.active_material.paint_system.groups) - 1)

        return new_group

    def delete_active_group(self):
        """
        Deletes the currently active group along with all its items and children.
        Returns:
            bool: True if the active group and its items were successfully deleted, False otherwise.
        """
        use_node_tree = False
        for node in self.active_material.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree == self.active_group.node_tree:
                use_node_tree = True
                break

        # 2 users: 1 for the material node tree, 1 for the datablock
        if self.active_group.node_tree and self.active_group.node_tree.users <= 1 + use_node_tree:
            bpy.data.node_groups.remove(self.active_group.node_tree)

        for item, _ in self.active_group.flatten_hierarchy():
            self._on_item_delete(item)

        active_group_idx = int(self.active_material.paint_system.active_group)
        self.active_material.paint_system.groups.remove(active_group_idx)

        if self.active_material.paint_system.active_group:
            self.active_material.paint_system.active_group = str(
                min(active_group_idx, len(self.active_material.paint_system.groups) - 1))

        return True

    def delete_active_item(self):
        """
        Deletes the currently active item in the active group along with its children.
        Returns:
            bool: True if the active item and its children were successfully deleted, False otherwise.
        """

        item_id = self.active_group.get_id_from_flattened_index(
            self.active_group.active_index)

        if item_id != -1 and self.active_group.remove_item_and_children(item_id, self._on_item_delete):
            # Update active_index
            flattened = self.active_group.flatten_hierarchy()
            self.active_group.active_index = min(
                self.active_group.active_index, len(flattened) - 1)

            self.active_group.update_node_tree()

            return True
        return False

    def create_image_layer(self, name: str, image: Image, uv_map_name: str = None) -> PropertyGroup:
        """Creates a new image layer in the active group.

        Args:
            image (Image): The image to be used in the layer.
            uv_map_name (str, optional): The name of the UV map to be used. Defaults to None.

        Returns:
            PropertyGroup: The newly created image layer.
        """

        # Get insertion position
        parent_id, insert_order = self.active_group.get_insertion_data()
        # Adjust existing items' order
        self.active_group.adjust_sibling_orders(parent_id, insert_order)

        node_tree = self._create_layer_node_tree(name, image, uv_map_name)

        # Create the new item
        new_id = self.active_group.add_item(
            name=name,
            item_type='IMAGE',
            parent_id=parent_id,
            order=insert_order,
            image=image,
            node_tree=node_tree,
        )

        # Update active index
        if new_id != -1:
            flattened = self.active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    self.active_group.active_index = i
                    break

        self.active_group.update_node_tree()

        return self.active_group.get_item_by_id(new_id)

    def create_solid_color_layer(self, name: str, color: Tuple[float, float, float, float]) -> PropertyGroup:
        """Creates a new solid color layer in the active group.

        Args:
            color (Tuple[float, float, float, float]): The color to be used in the layer.

        Returns:
            PropertyGroup: The newly created solid color layer.
        """
        # Get insertion position
        parent_id, insert_order = self.active_group.get_insertion_data()
        # Adjust existing items' order
        self.active_group.adjust_sibling_orders(parent_id, insert_order)

        solid_color_template = get_node_from_library(
            '_PS_Solid_Color_Template', False)
        solid_color_nt = solid_color_template.copy()
        solid_color_nt.name = f"PS {name} (MAT: {self.active_material.name})"
        solid_color_nt.nodes['RGB'].outputs[0].default_value = color

        # Create the new item
        new_id = self.active_group.add_item(
            name=name,
            item_type='SOLID_COLOR',
            parent_id=parent_id,
            order=insert_order,
            node_tree=solid_color_nt,
        )

        # Update active index
        if new_id != -1:
            flattened = self.active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    self.active_group.active_index = i
                    break

        self.active_group.update_node_tree()

        return self.active_group.get_item_by_id(new_id)

    def create_folder(self, name: str) -> PropertyGroup:
        """Creates a new folder in the active group.

        Args:
            name (str): The name of the new folder.

        Returns:
            PropertyGroup: The newly created folder.
        """
        # Get insertion position
        parent_id, insert_order = self.active_group.get_insertion_data()

        # Adjust existing items' order
        self.active_group.adjust_sibling_orders(parent_id, insert_order)

        folder_template = get_node_from_library(
            '_PS_Folder_Template', False)
        folder_nt = folder_template.copy()
        folder_nt.name = f"PS {name} (MAT: {self.active_material.name})"

        # Create the new item
        new_id = self.active_group.add_item(
            name=name,
            item_type='FOLDER',
            parent_id=parent_id,
            order=insert_order,
            node_tree=folder_nt
        )

        # Update active index
        if new_id != -1:
            flattened = self.active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    self.active_group.active_index = i
                    break

        self.active_group.update_node_tree()

    def _get_paint_system_settings(self) -> Optional[PropertyGroup]:
        return bpy.context.scene.paint_system_settings

    def _get_active_material(self) -> Optional[Material]:
        if not self.active_object or self.active_object.type != 'MESH':
            return None

        return self.active_object.active_material

    def _get_groups(self) -> Optional[PropertyGroup]:
        if not self.active_material or not hasattr(self.active_material, "paint_system"):
            return None
        paint_system = self.active_material.paint_system
        return paint_system.groups

    def _get_active_group(self) -> Optional[PropertyGroup]:
        if not self.groups:
            return None
        paint_system = self.active_material.paint_system

        active_group_idx = int(paint_system.active_group)
        if active_group_idx >= len(paint_system.groups):
            return None  # handle cases where active index is invalid
        return paint_system.groups[active_group_idx]

    def _get_active_layer(self) -> Optional[PropertyGroup]:
        if not self.active_group:
            return None
        flattened = self.active_group.flatten_hierarchy()
        if not flattened:
            return None

        if self.active_group.active_index >= len(flattened):
            return None  # handle cases where active index is invalid

        return flattened[self.active_group.active_index][0]

    def _get_layer_node_tree(self) -> Optional[NodeTree]:
        if not self.active_layer:
            return None
        return self.active_layer.node_tree

    def _get_layer_node_group(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        node = self.__find_node_group(
            self.active_group.node_tree, self.active_layer.node_tree.name)
        return node

    def _find_color_mix_node(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        for node in self.layer_node_tree.nodes:
            if node.type == 'MIX' and node.data_type == 'RGBA':
                return node
        return None

    def _find_uv_map_node(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        for node in self.layer_node_tree.nodes:
            if node.type == 'UVMAP':
                return node
        return None

    def _find_opacity_mix_node(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        for node in self.layer_node_tree.nodes:
            if node.type == 'MIX' and node.name == 'Opacity':
                # print("Found opacity mix node")
                return node
        return None

    def _find_clip_mix_node(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        for node in self.layer_node_tree.nodes:
            if node.type == 'MIX' and node.name == 'Clip':
                # print("Found clip mix node")
                return node
        return None

    def _find_rgb_node(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        for node in self.layer_node_tree.nodes:
            if node.name == 'RGB':
                return node
        return None

    def _create_folder_node_tree(self, folder_name: str, force_reload=False) -> NodeTree:
        folder_template = get_node_from_library(
            '_PS_Folder_Template', force_reload)
        folder_nt = folder_template.copy()
        folder_nt.name = f"PS {folder_name} (MAT: {self.active_material.name})"
        return folder_nt

    def _create_layer_node_tree(self, layer_name: str, image: Image, uv_map_name: str = None, force_reload=True) -> NodeTree:
        layer_template = get_node_from_library(
            '_PS_Layer_Template', force_reload)
        layer_nt = layer_template.copy()
        layer_nt.name = f"PS {layer_name} (MAT: {self.active_material.name})"
        # Find the image texture node
        image_texture_node = None
        for node in layer_nt.nodes:
            if node.type == 'TEX_IMAGE':
                image_texture_node = node
                break
        uv_map_node = None
        # Find UV Map node
        for node in layer_nt.nodes:
            if node.type == 'UVMAP':
                uv_map_node = node
                break
        # use uv_map_name or default to first uv map
        if uv_map_name:
            uv_map_node.uv_map = uv_map_name
        else:
            uv_map_node.uv_map = bpy.context.object.data.uv_layers[0].name
        image_texture_node.image = image
        return layer_nt

    def _on_item_delete(self, item):
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

    def __find_node_group(self, node_tree: NodeTree, name: str) -> Optional[Node]:
        for node in node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree and node.node_tree.name == name:
                return node
        return None
