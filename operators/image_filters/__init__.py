from .basic_filters import *
import os
from pathlib import Path


def resolve_brush_preset_path():
    """Resolve the path to the brush preset. A folder containing folders of brush images."""
    return os.path.join(Path(__file__).resolve().parent, "brush_painter", "brush_presets")


def list_brush_presets():
    """List the brush presets."""
    return os.listdir(resolve_brush_preset_path())