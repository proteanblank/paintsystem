from __future__ import annotations

from pathlib import Path
from typing import Optional
from ..nodetree_builder import NodeTreeBuilder

import bpy


def _resolve_library_path(filename: str = "library2.blend") -> Path:
    """
    Resolve the absolute path to the given library filename.

    `library2.blend` resides with this file.
    """
    folder_root = Path(__file__).resolve().parent
    return folder_root / filename


def get_library_nodetree(tree_name: str, library_filename: str = "library2.blend") -> bpy.types.NodeTree:
    """
    Return a `bpy.types.NodeTree` by name, appending it from the given library if needed.

    - First checks the current .blend for an existing node tree with `tree_name` and returns it if found.
    - Otherwise, appends the node tree from `library_filename` and returns the appended datablock.

    Args:
        tree_name: Name of the node tree (node group) to retrieve.
        library_filename: Blend file to append from. Defaults to "library2.blend".

    Returns:
        The resolved `bpy.types.NodeTree` instance.

    Raises:
        FileNotFoundError: If the library file cannot be found.
        ValueError: If the requested node tree name does not exist in the library.
    """
    # 1) Check if the node tree already exists in the current .blend
    existing_tree = bpy.data.node_groups.get(tree_name)
    if existing_tree is not None:
        return existing_tree

    # 2) Resolve path to the library file
    library_path = _resolve_library_path(library_filename)
    if not library_path.exists():
        raise FileNotFoundError(f"Library file not found: {library_path}")

    # 3) Inspect the library for the node tree, then append it
    library_path_str = str(library_path)
    with bpy.data.libraries.load(library_path_str, link=False) as (data_from, data_to):
        if tree_name not in data_from.node_groups:
            raise ValueError(
                f"Node tree '{tree_name}' not found in '{library_filename}'.\n"
                f"Available: {list(data_from.node_groups)}"
            )
        data_to.node_groups = [tree_name]

    # 4) Return the newly appended node tree (now present in bpy.data.node_groups)
    appended_tree: Optional[bpy.types.NodeTree] = bpy.data.node_groups.get(tree_name)
    if appended_tree is None:
        # Safety: In case Blender renames on conflict (shouldn't happen because we early-return if exists)
        # fallback to the last appended group if present
        if len(bpy.data.node_groups) > 0:
            appended_tree = bpy.data.node_groups[-1]
        else:
            raise RuntimeError(
                f"Unexpected error: Node tree '{tree_name}' was not appended from '{library_filename}'."
            )
    return appended_tree

def create_mixing_graph(builder: NodeTreeBuilder, color_node_name: str, color_socket: str, alpha_node_name: str = None, alpha_socket: str = None) -> NodeTreeBuilder:
    pre_mix = get_library_nodetree(".PS Pre Mix")
    post_mix = get_library_nodetree(".PS Post Mix")
    builder.add_node("group_input", "NodeGroupInput")
    builder.add_node("group_output", "NodeGroupOutput")
    builder.add_node("pre_mix", "ShaderNodeGroup", {"node_tree": pre_mix}, {"Over Alpha": 1.0})
    builder.add_node("post_mix", "ShaderNodeGroup", {"node_tree": post_mix})
    builder.add_node("mix_rgb", "ShaderNodeMix", {"blend_type": "MIX", "data_type": "RGBA"})
    if alpha_node_name is not None and alpha_socket is not None:
        builder.link(alpha_node_name, "pre_mix", alpha_socket, "Over Alpha")
    builder.link("group_input", "pre_mix", "Color", "Color")
    builder.link("group_input", "pre_mix", "Alpha", "Alpha")
    builder.link("pre_mix", "mix_rgb", "Color", "A")
    builder.link("pre_mix", "mix_rgb", "Over Alpha", "Factor")
    builder.link(color_node_name, "mix_rgb", color_socket, "B")
    builder.link("mix_rgb", "post_mix", "Result", "Color")
    builder.link("pre_mix", "post_mix", "Over Alpha", "Over Alpha")
    builder.link("group_input", "post_mix", "Alpha", "Alpha")
    builder.link("post_mix", "group_output", "Color", "Color")
    builder.link("post_mix", "group_output", "Alpha", "Alpha")
    return builder


def create_coord_graph(builder: NodeTreeBuilder, coord_type: str, uv_map_name: str, node_name: str, socket_name: str) -> NodeTreeBuilder:
    if coord_type == "AUTO":
        builder.add_node("uvmap", "ShaderNodeUVMap", {"uv_map": "PS_UVMap"})
        builder.link("uvmap", node_name, "UV", socket_name)
    elif coord_type == "UV":
        builder.add_node("uvmap", "ShaderNodeUVMap", {"uv_map": uv_map_name})
        builder.link("uvmap", node_name, "UV", socket_name)
    elif coord_type in ["OBJECT", "CAMERA", "WINDOW", "REFLECTION"]:
        builder.add_node("tex_coord", "ShaderNodeTexCoord")
        builder.link("tex_coord", node_name, coord_type.title(), socket_name)
    elif coord_type == "POSITION":
        builder.add_node("geometry", "ShaderNodeGeometry")
        builder.link("geometry", node_name, "Position", socket_name)
    return builder


