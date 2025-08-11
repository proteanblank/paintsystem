from __future__ import annotations

from pathlib import Path
from typing import Optional

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
    existing_tree: Optional[bpy.types.NodeTree] = bpy.data.node_groups.get(tree_name)
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


__all__ = ["get_library_nodetree"]


