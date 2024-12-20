import bpy
from bpy.types import Context, Material, Image, NodeTree, Node, PropertyGroup
from typing import Optional, Tuple
from .common import on_item_delete, get_node_from_library
from mathutils import Vector


class PaintSystem:
    def __init__(self, context: Context):
        self.context = context
        self.active_object = context.active_object
        self.active_material = self._get_active_material()

        self.active_group = self._get_active_group()
        self.active_layer = self._get_active_layer()
        self.layer_node_tree = self._get_layer_node_tree()
        self.layer_node_group = self._get_layer_node_group()
        self.layer_mix_node, self.layer_uvmap_node = self._get_layer_node_info()

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
            on_item_delete(item)

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

        if item_id != -1 and self.active_group.remove_item_and_children(item_id, on_item_delete):
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

        node_tree = self._create_folder_node_tree(name)

        # Create the new item
        new_id = self.active_group.add_item(
            name=name,
            item_type='FOLDER',
            parent_id=parent_id,
            order=insert_order,
            node_tree=node_tree
        )

        # Update active index
        if new_id != -1:
            flattened = self.active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    self.active_group.active_index = i
                    break

        self.active_group.update_node_tree()

    def _get_active_material(self) -> Optional[Material]:
        if not self.active_object or self.active_object.type != 'MESH':
            return None

        return self.active_object.active_material

    def _get_active_group(self) -> Optional[PropertyGroup]:
        if not self.active_material or not hasattr(self.active_material, "paint_system"):
            return None
        paint_system = self.active_material.paint_system
        if not paint_system.groups:
            return None

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

        # if not self.active_layer.node_tree:
        #     if self.active_layer.type == 'FOLDER':
        #         layer_node_tree = self._create_folder_node_tree(
        #             self.active_layer.name)
        #     elif self.active_layer.type == 'IMAGE':
        #         layer_node_tree = self._create_layer_node_tree(
        #             self.active_layer.name, self.active_layer.image, self.active_layer.uv_map)

        #     self.active_layer.node_tree = layer_node_tree

        return self.active_layer.node_tree

    def _get_layer_node_group(self) -> Optional[Node]:
        if not self.layer_node_tree:
            return None
        node = self.__find_node_group(
            self.active_group.node_tree, self.active_layer.node_tree.name)
        return node
        # if node:
        #     return node
        # print("Node not found")
        # try:
        #     # Try to update the node group
        #     self.active_group.update_node_tree()
        #     node = self.__find_node_group(
        #         self.active_group.node_tree, self.active_layer.name)
        #     if node:
        #         return node
        # except AttributeError:
        #     # print("AttributeError")
        #     pass
        # return None  # (Should be impossible to reach here)

    def _get_layer_node_info(self) -> Tuple[Optional[Node], Optional[Node]]:
        if not self.layer_node_group:
            return None, None

        layer_mix_node = self._find_mix_node()

        # if not layer_mix_node:
        # if self.active_layer.type == 'FOLDER':
        #     layer_node_tree = self._create_folder_node_tree(
        #         self.active_layer.name, True)
        # elif self.active_layer.type == 'IMAGE':
        #     layer_node_tree = self._create_layer_node_tree(
        #         self.active_layer.name, self.active_layer.image, self.active_layer.get("uv_map"), True)
        # self.active_layer.node_tree = layer_node_tree
        # layer_mix_node = self._find_mix_node()

        layer_uvmap_node = self._find_uv_map_node()
        # if not layer_uvmap_node and self.active_layer.type == 'IMAGE':
        #     layer_node_tree = self._create_layer_node_tree(
        #         self.active_layer.name, self.active_layer.image, self.active_layer.get("uv_map"), True)
        #     self.active_layer.node_tree = layer_node_tree
        #     layer_uvmap_node = self._find_uv_map_node()

        return layer_mix_node, layer_uvmap_node

    def _find_mix_node(self) -> Optional[Node]:
        for node in self.layer_node_tree.nodes:
            if node.type == 'MIX' and node.data_type == 'RGBA':
                return node
        return None

    def _find_uv_map_node(self) -> Optional[Node]:
        for node in self.layer_node_tree.nodes:
            if node.type == 'UVMAP':
                return node
        return None

    def _create_folder_node_tree(self, folder_name: str, force_reload=False) -> NodeTree:
        folder_template = get_node_from_library(
            '_PS_Folder_Template', force_reload)
        folder_nt = folder_template.copy()
        folder_nt.name = f"PS {folder_name} (MAT: {self.active_material.name})"
        return folder_nt

    def _create_layer_node_tree(self, layer_name: str, image: Image, uv_map_name: str = None, force_reload=False) -> NodeTree:
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

    def __find_node_group(self, node_tree: NodeTree, name: str) -> Optional[Node]:
        for node in node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree and node.node_tree.name == name:
                return node
        return None
