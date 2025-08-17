from __future__ import annotations

from pathlib import Path
from typing import Optional

import bpy

BRUSH_PREFIX = "PS_"

def _resolve_library_path(filename: str = "brushes.blend") -> Path:
    """
    Resolve the absolute path to the given library filename.

    `brushes.blend` resides with this file.
    """
    folder_root = Path(__file__).resolve().parent
    return folder_root / filename


def get_brushes_from_library():
    # Load the library file
    filepath = _resolve_library_path()
    if not filepath.exists():
        raise FileNotFoundError(f"Library file not found: {filepath}")

    # 3) Inspect the library for the node tree, then append it
    library_path_str = str(filepath)
    with bpy.data.libraries.load(library_path_str) as (lib_file, current_file):
        lib_brushes = lib_file.brushes
        current_brushes = current_file.brushes
        for brush in lib_brushes:
            if brush.startswith(BRUSH_PREFIX) and brush not in bpy.data.brushes:
                current_brushes.append(brush)

    # For blender 4.3
    if bpy.app.version >= (4, 3, 0):
        for brush in bpy.data.brushes:
            if brush.name.startswith(BRUSH_PREFIX):
                brush.asset_mark()

__all__ = ["get_brushes_from_library"]


