import bpy
from .list_manager import ListManager
from bpy.utils import register_classes_factory
from .common import PSContextMixin, scale_content


class PAINTSYSTEM_OT_NewGroup(PSContextMixin, bpy.types.Operator):
    """Create a new group in the Paint System"""
    bl_idname = "paint_system.new_group"
    bl_label = "New Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: bpy.props.StringProperty(
        name="Group Name",
        description="Name of the new group",
        default="New Group",
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        # See if there is any material slot on the active object
        if not context.active_object.active_material:
            bpy.data.materials.new(name="New Material")
            context.active_object.active_material = bpy.data.materials[-1]
        
        ps_ctx = self.ensure_context(context)
        node_tree = bpy.data.node_groups.new(name=f"Paint System ({self.group_name})", type='ShaderNodeTree')
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        new_group = lm.add_item()
        new_group.name = self.group_name
        new_group.node_tree = node_tree
        new_group.update_node_tree(context)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        scale_content(context, self.layout)
        row.prop(self, "group_name", text="Name")


class PAINTSYSTEM_OT_DeleteGroup(PSContextMixin, bpy.types.Operator):
    """Delete the selected group in the Paint System"""
    bl_idname = "paint_system.delete_group"
    bl_label = "Delete Group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_group is not None

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        lm.remove_active_item()
        return {'FINISHED'}


class PAINTSYSTEM_OT_MoveGroup(PSContextMixin, bpy.types.Operator):
    """Move the selected group in the Paint System"""
    bl_idname = "paint_system.move_group"
    bl_label = "Move Group"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('UP', "Up", "Move group up"),
            ('DOWN', "Down", "Move group down")
        ],
        default='UP'
    )

    @classmethod
    def _poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return bool(ps_ctx.ps_mat_data and ps_ctx.ps_mat_data.active_index >= 0)

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        ps_mat_data = ps_ctx.ps_mat_data
        lm = ListManager(ps_mat_data, 'groups', ps_mat_data, 'active_index')
        lm.move_active_down() if self.direction == 'DOWN' else lm.move_active_up()
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_NewGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_MoveGroup,
)

register, unregister = register_classes_factory(classes)    