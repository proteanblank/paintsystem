from .paintsystem.common import PaintSystemPreferences

def addon_package() -> str:
    """Get the addon package name"""
    return __package__

def get_preferences(context) -> PaintSystemPreferences:
    """Get the Paint System preferences"""
    ps = addon_package()
    prefs:PaintSystemPreferences = context.preferences.addons[ps].preferences
    return prefs