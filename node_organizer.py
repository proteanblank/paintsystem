import math
from collections import defaultdict, deque
from bpy.types import Operator, Panel
import bpy


class NODE_OT_organize(Operator):
    """Organize Shader Nodes Using a Sugiyama-like layered layout."""
    bl_idname = "node.organize"
    bl_label = "Organize Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.space_data.tree_type != 'ShaderNodeTree':
            self.report({'WARNING'}, "Not in a Shader Node Tree.")
            return {'CANCELLED'}

        node_tree = context.space_data.edit_tree
        nodes = list(node_tree.nodes)

        # Get active node output
        output_nodes = []
        for node in nodes:
            if len(node.outputs) == 0 or node.type == 'OUTPUT_MATERIAL':
                output_nodes.append(node)

        return {'FINISHED'}


class NODE_PT_organizer_panel(Panel):
    """Panel for the Sugiyama layout"""
    bl_label = "Node Organizer"
    bl_idname = "NODE_PT_organizer_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Node Organizer'

    def draw(self, context):
        layout = self.layout

        op = layout.operator("node.organize", text="Organize")


def register():
    bpy.utils.register_class(NODE_PT_organizer_panel)
    bpy.utils.register_class(NODE_PT_organizer_panel)


def unregister():
    bpy.utils.unregister_class(NODE_PT_organizer_panel)
    bpy.utils.unregister_class(NODE_PT_organizer_panel)


if __name__ == "__main__":
    register()
