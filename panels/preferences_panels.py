import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, IntProperty
from bpy.utils import register_classes_factory
from .. import __package__ as ps

class PaintSystemPreferences(AddonPreferences):
    """Demo bare-bones preferences"""
    bl_idname = ps

    show_tooltips = BoolProperty(
        name="Show Tooltips",
        description="Show tooltips in the UI",
        default=True
    )

    use_compact_design = BoolProperty(
        name="Use Compact Design",
        description="Use a more compact design for the UI",
        default=False
    )

    name_layers_group = BoolProperty(
        name="Name Layers According to Group Name",
        default=False
    )

    def draw_shortcut(self, layout, kmi, text):
        row = layout.row(align=True)
        row.prop(kmi, "active",
                 text="", emboss=False)
        row.label(text=text)
        row.prop(kmi, "type", text="", full_event=True)

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "show_tooltips", text="Show Tooltips")
        layout.prop(self, "use_compact_design", text="Use Compact Design")
        layout.prop(self, "name_layers_group",
                    text="Name Layers According to Group Name")

        box = layout.box()
        box.label(text="Paint System Shortcuts:")

classes = (
    PaintSystemPreferences,
)

register, unregister = register_classes_factory(classes)