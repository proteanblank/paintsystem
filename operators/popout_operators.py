import bpy
from .ui_widgets.bl_ui_draw_op import BL_UI_OT_draw_operator

class TestPopoutOperator(BL_UI_OT_draw_operator):
    bl_idname = "paint_system.test_popout_operator"
    bl_label = "Test Popout Operator"
    bl_description = "A test operator to demonstrate popout functionality"
    bl_options = {"REGISTER"}

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ui_scale = bpy.context.preferences.view.ui_scale

        text_size = int(14 * ui_scale)
        margin = int(10 * ui_scale)
        area_margin = int(50 * ui_scale)