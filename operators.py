import bpy

from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)

from bpy.types import Operator

from bpy.utils import register_classes_factory
from .common import get_active_group, get_active_layer, redraw_panel

# -------------------------------------------------------------------
# Group Operators
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_DuplicateGroupWarning(Operator):
    """Warning for duplicate group name"""
    bl_idname = "paint_system.duplicate_group_warning"
    bl_label = "Warning"
    bl_options = {'INTERNAL'}

    group_name: StringProperty()

    def execute(self, context):
        mat = context.active_object.active_material
        new_group = mat.paint_system.groups.add()
        new_group.name = self.group_name

        # Force the UI to update
        if context.area:
            context.area.tag_redraw()

        # Set the active group to the newly created one
        mat.paint_system.active_group = str(len(mat.paint_system.groups) - 1)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text=f"Group name '{self.group_name}' already exists!", icon='ERROR')
        layout.label(
            text="Click OK to create anyway, or cancel to choose a different name")


class PAINTSYSTEM_OT_AddGroup(Operator):
    """Add a new group"""
    bl_idname = "paint_system.add_group"
    bl_label = "Add Group"
    bl_description = "Add a new group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    group_name: StringProperty(
        name="Group Name",
        description="Name for the new group",
        default="New Group"
    )

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        # Check for duplicate names
        for group in mat.paint_system.groups:
            if group.name == self.group_name:
                bpy.ops.paint_system.duplicate_group_warning(
                    'INVOKE_DEFAULT', group_name=self.group_name)
                return {'CANCELLED'}

        new_group = mat.paint_system.groups.add()
        new_group.name = self.group_name

        # Force the UI to update
        redraw_panel(self, context)

        # Set the active group to the newly created one
        mat.paint_system.active_group = str(len(mat.paint_system.groups) - 1)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "group_name")


class PAINTSYSTEM_OT_DeleteGroup(Operator):
    """Delete the active group"""
    bl_idname = "paint_system.delete_group"
    bl_label = "Delete Group"
    bl_description = "Delete the active group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        active_group_idx = int(mat.paint_system.active_group)
        mat.paint_system.groups.remove(active_group_idx)

        if mat.paint_system.active_group:
            mat.paint_system.active_group = str(
                min(active_group_idx, len(mat.paint_system.groups) - 1))

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        layout = self.layout
        layout.label(
            text=f"Delete '{mat.paint_system.groups[active_group_idx].name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the group")


# -------------------------------------------------------------------
# Layers Operators
# -------------------------------------------------------------------
class PAINTSYSTEM_OT_AddItem(Operator):
    """Add a new item"""
    bl_idname = "paint_system.add_item"
    bl_label = "Add Item"
    bl_options = {'REGISTER', 'UNDO'}

    item_type: EnumProperty(
        items=[
            ('FOLDER', "Folder", "Add a folder"),
            ('IMAGE', "Image", "Add an image")
        ],
        default='IMAGE'
    )

    def execute(self, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        # Get insertion position
        parent_id, insert_order = manager.get_insertion_data()

        # Adjust existing items' order
        manager.adjust_sibling_orders(parent_id, insert_order)

        # Get next number based on type
        flattened = manager.flatten_hierarchy()
        for i, (item, _) in enumerate(flattened):
            if item.order >= insert_order:
                insert_order += 1

        # Create the new item
        new_id = manager.add_item(
            name=f"{'Folder' if self.item_type == 'FOLDER' else 'Image'} {manager.next_id}",
            item_type=self.item_type,
            parent_id=parent_id,
            order=insert_order
        )

        # Update active index
        if new_id != -1:
            flattened = manager.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    manager.active_index = i
                    break

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}


class PAINTSYSTEM_OT_RemoveItem(Operator):
    """Remove the active item"""
    bl_idname = "paint_system.remove_item"
    bl_label = "Remove Item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        item_id = manager.get_id_from_flattened_index(manager.active_index)

        if item_id != -1 and manager.remove_item_and_children(item_id):
            # Update active_index
            flattened = manager.flatten_hierarchy()
            manager.active_index = min(
                manager.active_index, len(flattened) - 1)
            # Run normalize orders to fix any gaps
            manager.normalize_orders()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        active_layer = get_active_layer(self, context)
        if not active_layer:
            return {'CANCELLED'}
        layout.label(
            text=f"Delete '{active_layer.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the layer")


class PAINTSYSTEM_OT_MoveUp(Operator):
    """Move the active item up"""
    bl_idname = "paint_system.move_up"
    bl_label = "Move Item Up"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: EnumProperty(
        items=[
            ('MOVE_INTO', "Move Into", "Move into folder"),
            ('MOVE_ADJACENT', "Move Adjacent", "Move as sibling"),
            ('MOVE_OUT', "Move Out", "Move out of folder"),
            ('SKIP', "Skip", "Skip over item"),
        ]
    )

    def invoke(self, context, event):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        item_id = manager.get_id_from_flattened_index(manager.active_index)

        options = manager.get_movement_options(item_id, 'UP')
        if not options:
            return {'CANCELLED'}

        if len(options) == 1 and options[0][0] == 'SKIP':
            self.action = 'SKIP'
            return self.execute(context)

        context.window_manager.popup_menu(
            self.draw_menu,
            title="Move Options"
        )
        return {'FINISHED'}

    def draw_menu(self, self_menu, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}
        item_id = manager.get_id_from_flattened_index(manager.active_index)

        for op_id, label, props in manager.get_movement_menu_items(item_id, 'UP'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}
        item_id = manager.get_id_from_flattened_index(manager.active_index)

        if manager.execute_movement(item_id, 'UP', self.action):
            # Update active_index to follow the moved item
            flattened = manager.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == item_id:
                    manager.active_index = i
                    break
            manager.normalize_orders()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}


class PAINTSYSTEM_OT_MoveDown(Operator):
    """Move the active item down"""
    bl_idname = "paint_system.move_down"
    bl_label = "Move Item Down"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    action: EnumProperty(
        items=[
            ('MOVE_OUT_BOTTOM', "Move Out Bottom", "Move out of folder"),
            ('MOVE_INTO_TOP', "Move Into Top", "Move to top of folder"),
            ('MOVE_ADJACENT', "Move Adjacent", "Move as sibling"),
            ('SKIP', "Skip", "Skip over item"),
        ]
    )

    def invoke(self, context, event):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        item_id = manager.get_id_from_flattened_index(manager.active_index)

        options = manager.get_movement_options(item_id, 'DOWN')
        if not options:
            return {'CANCELLED'}

        if len(options) == 1 and options[0][0] == 'SKIP':
            self.action = 'SKIP'
            return self.execute(context)

        context.window_manager.popup_menu(
            self.draw_menu,
            title="Move Options"
        )
        return {'FINISHED'}

    def draw_menu(self, self_menu, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        item_id = manager.get_id_from_flattened_index(manager.active_index)

        for op_id, label, props in manager.get_movement_menu_items(item_id, 'DOWN'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        manager = get_active_group(self, context)
        if not manager:
            return {'CANCELLED'}

        item_id = manager.get_id_from_flattened_index(manager.active_index)

        if manager.execute_movement(item_id, 'DOWN', self.action):
            # Update active_index to follow the moved item
            flattened = manager.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == item_id:
                    manager.active_index = i
                    break
            manager.normalize_orders()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}


classes = (
    PAINTSYSTEM_OT_DuplicateGroupWarning,
    PAINTSYSTEM_OT_AddGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_AddItem,
    PAINTSYSTEM_OT_RemoveItem,
    PAINTSYSTEM_OT_MoveUp,
    PAINTSYSTEM_OT_MoveDown,
)

register, unregister = register_classes_factory(classes)
