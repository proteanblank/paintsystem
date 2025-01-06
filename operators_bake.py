import bpy
from bpy.types import Operator, Context
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem


def get_baking_steps(node_tree):
    """Get all nodes that are part of the baking process

    Args:
        node_tree (bpy.types.NodeTree): The node tree to check

    Returns: 
        list: A list of nodes that are part of the baking process
    """
    unsupported_nodes = []
    for node in node_tree.nodes:
        print(node.bl_idname)
        # if node.bl_idname in SUPPORTED_NODES:
        #     unsupported_nodes.append(node)
    return unsupported_nodes


def is_bakeable_material(mat):
    """Check if the material is bakeable

    Args:
        mat (bpy.types.Material): The material to check

    Returns:
        bool: True if the material is bakeable
    """
    if not mat:
        return False
    # TODO: Check if the material is bakeable

    return True


class PAINTSYSTEM_OT_BakeGroup(Operator):
    bl_idname = "paint_system.bake_group"
    bl_label = "Bake Group"
    bl_description = "Bake the selected group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        if not mat:
            return {'CANCELLED'}
        get_baking_steps(mat.node_tree)
        pass


classes = (
    PAINTSYSTEM_OT_BakeGroup,
)

register, unregister = register_classes_factory(classes)
