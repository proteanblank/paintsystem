import bpy
from dataclasses import dataclass
from .. import __package__ as ps

@dataclass
class PaintSystemPreferences:
    show_tooltips: bool
    use_compact_design: bool
    name_layers_group: bool

def get_preferences(context) -> PaintSystemPreferences:
    """Get the Paint System preferences"""
    # print("Package", ps)
    prefs:PaintSystemPreferences = context.preferences.addons[ps].preferences
    return prefs