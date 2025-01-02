import bpy


def is_online():
    return not bpy.app.version >= (4, 2, 0) or bpy.app.online_access
