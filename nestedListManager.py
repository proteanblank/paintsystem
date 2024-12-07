import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, PointerProperty
from typing import cast


class NestedListItem(bpy.types.PropertyGroup):
    """Represents a single item in the nested list."""
    id: IntProperty()  # Unique identifier
    name: StringProperty()  # Item name
    parent_id: IntProperty(default=-1)  # ID of the parent (-1 means no parent)
    order: IntProperty()  # Order within the same parent


class NestedListManager(bpy.types.PropertyGroup):
    """Manages the nested list."""
    # items: CollectionProperty(type=NestedListItem)
    active_index: IntProperty()
    next_id: IntProperty(default=0)

    def add_item(self, name, parent_id=-1):
        """Adds a new item."""
        new_item = self.items.add()
        new_item.id = self.next_id
        new_item.name = name
        new_item.parent_id = parent_id
        new_item.order = self.get_next_order(parent_id)
        self.next_id += 1
        return new_item.id

    def get_next_order(self, parent_id):
        """Get the next available order for a given parent."""
        return max((item.order for item in self.items if item.parent_id == parent_id), default=-1) + 1

    def get_item_by_id(self, item_id):
        """Get an item by its ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_collection_index_from_id(self, item_id):
        """Get the collection index from an item ID."""
        for index, item in enumerate(self.items):
            if item.id == item_id:
                return index
        return -1

    def get_id_from_flattened_index(self, flattened_index):
        """Convert a flattened list index to an item ID."""
        flattened = self.flatten_hierarchy()
        if 0 <= flattened_index < len(flattened):
            return flattened[flattened_index][0].id
        return -1

    def move_item(self, item_id, new_parent_id):
        """Moves an item to a new parent."""
        item = self.get_item_by_id(item_id)
        if item and (new_parent_id == -1 or self.get_item_by_id(new_parent_id)):
            # Prevent moving item to its own descendant
            current = self.get_item_by_id(new_parent_id)
            while current:
                if current.id == item_id:
                    return False
                current = self.get_item_by_id(current.parent_id)

            item.parent_id = new_parent_id
            item.order = self.get_next_order(new_parent_id)
            return True
        return False

    def reorder_item(self, item_id, direction):
        """Reorder an item within the same parent."""
        item = self.get_item_by_id(item_id)
        if not item:
            return False

        siblings = sorted(
            [i for i in self.items if i.parent_id == item.parent_id],
            key=lambda i: i.order
        )
        idx = siblings.index(item)

        if direction == 'UP' and idx > 0:
            swap_item = siblings[idx - 1]
        elif direction == 'DOWN' and idx < len(siblings) - 1:
            swap_item = siblings[idx + 1]
        else:
            return False

        item.order, swap_item.order = swap_item.order, item.order
        return True

    def flatten_hierarchy(self):
        """Flatten the hierarchy into a displayable list with levels for indentation."""
        def collect_items(parent_id, level):
            collected = []
            children = sorted(
                [item for item in self.items if item.parent_id == parent_id],
                key=lambda i: i.order
            )
            for item in children:
                collected.append((item, level))
                collected.extend(collect_items(item.id, level + 1))
            return collected

        return collect_items(-1, 0)


class NLM_UL_List(bpy.types.UIList):
    """Custom UIList to display NestedListItem objects."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        nested_list_manager = context.scene.nested_list_manager
        flattened = nested_list_manager.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            indent = " " * (level * 4)
            layout.label(
                text=f"{indent}{display_item.name} (ID: {display_item.id})")


class NLM_PT_Panel(bpy.types.Panel):
    bl_label = "Nested List Manager"
    bl_idname = "NLM_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Nested List"

    def draw(self, context):
        layout = self.layout
        manager = context.scene.nested_list_manager
        flattened = manager.flatten_hierarchy()

        row = layout.row()
        row.template_list(
            "NLM_UL_List", "", manager, "items", manager, "active_index",
            rows=len(flattened)
        )

        col = row.column(align=True)
        col.operator("nested_list.add_item", icon="ADD", text="")
        col.operator("nested_list.remove_item", icon="REMOVE", text="")
        col.operator("nested_list.move_item", icon="TRIA_RIGHT", text="Move")
        col.operator("nested_list.move_up", icon="TRIA_UP", text="")
        col.operator("nested_list.move_down", icon="TRIA_DOWN", text="")


class NLM_OT_AddItem(bpy.types.Operator):
    bl_idname = "nested_list.add_item"
    bl_label = "Add Item"

    def execute(self, context):
        manager = context.scene.nested_list_manager
        new_id = manager.add_item(name=f"Item {manager.next_id}")
        # Set active_index to the new item's position in the flattened list
        flattened = manager.flatten_hierarchy()
        for i, (item, _) in enumerate(flattened):
            if item.id == new_id:
                manager.active_index = i
                break
        return {'FINISHED'}


class NLM_OT_RemoveItem(bpy.types.Operator):
    bl_idname = "nested_list.remove_item"
    bl_label = "Remove Item"

    def execute(self, context):
        manager = context.scene.nested_list_manager
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            collection_index = manager.get_collection_index_from_id(item_id)
            if collection_index != -1:
                manager.items.remove(collection_index)
                # Update active_index to stay within bounds
                flattened = manager.flatten_hierarchy()
                manager.active_index = min(
                    manager.active_index, len(flattened) - 1)
                return {'FINISHED'}
        return {'CANCELLED'}


class NLM_OT_MoveItem(bpy.types.Operator):
    bl_idname = "nested_list.move_item"
    bl_label = "Move Item"
    bl_description = "Move the selected item to a new parent"

    new_parent_id: IntProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        manager = context.scene.nested_list_manager
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.move_item(item_id, self.new_parent_id):
                self.report(
                    {'INFO'}, f"Moved item {item_id} to parent {self.new_parent_id}")
                return {'FINISHED'}
        return {'CANCELLED'}


class NLM_OT_MoveUp(bpy.types.Operator):
    bl_idname = "nested_list.move_up"
    bl_label = "Move Item Up"

    def execute(self, context):
        manager = context.scene.nested_list_manager
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.reorder_item(item_id, 'UP'):
                # Update active_index to follow the moved item
                flattened = manager.flatten_hierarchy()
                for i, (item, _) in enumerate(flattened):
                    if item.id == item_id:
                        manager.active_index = i
                        break
                return {'FINISHED'}
        return {'CANCELLED'}


class NLM_OT_MoveDown(bpy.types.Operator):
    bl_idname = "nested_list.move_down"
    bl_label = "Move Item Down"

    def execute(self, context):
        manager = context.scene.nested_list_manager
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.reorder_item(item_id, 'DOWN'):
                # Update active_index to follow the moved item
                flattened = manager.flatten_hierarchy()
                for i, (item, _) in enumerate(flattened):
                    if item.id == item_id:
                        manager.active_index = i
                        break
                return {'FINISHED'}
        return {'CANCELLED'}


classes = [
    NestedListItem,
    NestedListManager,
    NLM_UL_List,
    NLM_PT_Panel,
    NLM_OT_AddItem,
    NLM_OT_RemoveItem,
    NLM_OT_MoveItem,
    NLM_OT_MoveUp,
    NLM_OT_MoveDown,
]
