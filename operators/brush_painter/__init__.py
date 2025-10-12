import bpy
from . import brush_painter_panel
from . import brush_painter_operator

def register():
    brush_painter_panel.register()
    brush_painter_operator.register()

def unregister():
    brush_painter_operator.unregister()
    brush_painter_panel.unregister()

if __name__ == "__main__":
    register()
