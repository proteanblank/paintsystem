import bpy

def is_newer_than(major, minor=0, patch=0):
    return bpy.app.version >= (major, minor, patch)