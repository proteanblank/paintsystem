import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, PointerProperty


class BaseNestedListItem(bpy.types.PropertyGroup):
    """Base class for nested list items that handles the hierarchy."""
    id: IntProperty()  # Unique identifier
    parent_id: IntProperty(default=-1)  # ID of the parent (-1 means no parent)
    order: IntProperty()  # Order within the same parent

    def draw_item(self, layout):
        """Override this method to customize how the item is displayed."""
        raise NotImplementedError("Subclasses must implement draw_item")

    def copy_from(self, other):
        """Override this method to copy custom properties from another item."""
        self.id = other.id
        self.parent_id = other.parent_id
        self.order = other.order


class BaseNestedListManager(bpy.types.PropertyGroup):
    """Base class for managing nested lists. Override 'item_type' in subclasses."""
    active_index: IntProperty()
    next_id: IntProperty(default=0)

    @property
    def items(self):
        """Override this property to return your CollectionProperty of items."""
        raise NotImplementedError("Subclasses must implement items property")

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

    def create_item(self):
        """Override this method to customize item creation."""
        raise NotImplementedError("Subclasses must implement create_item")

    def add_item(self, parent_id=-1, **kwargs):
        """Adds a new item."""
        new_item = self.create_item(**kwargs)
        new_item.id = self.next_id
        new_item.parent_id = parent_id
        new_item.order = self.get_next_order(parent_id)
        self.next_id += 1
        return new_item.id

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


class BaseNestedList(bpy.types.UIList):
    """Base UIList class for displaying nested items."""

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        manager = self.get_manager(context)
        flattened = manager.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            row = layout.row()
            row.separator(factor=level)  # Indentation
            display_item.draw_item(row)  # Call the item's custom draw method

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")


class BaseNestedListPanel:
    """Base class for nested list panels. Inherit from this and bpy.types.Panel."""

    def draw(self, context):
        layout = self.layout
        manager = self.get_manager(context)
        flattened = manager.flatten_hierarchy()

        row = layout.row()
        row.template_list(
            self.ul_class.__name__, "",
            manager, "items",
            manager, "active_index",
            rows=len(flattened)
        )

        self.draw_operators(row.column(align=True))

    def draw_operators(self, layout):
        """Override this to customize the operator buttons."""
        layout.operator(self.ops_add, icon="ADD", text="")
        layout.operator(self.ops_remove, icon="REMOVE", text="")
        layout.operator(self.ops_move, icon="TRIA_RIGHT", text="")
        layout.operator(self.ops_move_up, icon="TRIA_UP", text="")
        layout.operator(self.ops_move_down, icon="TRIA_DOWN", text="")

    @property
    def ul_class(self):
        """Override this to return your UIList class."""
        raise NotImplementedError("Subclasses must implement ul_class")

    @property
    def ops_add(self): return "nested_list.add_item"
    @property
    def ops_remove(self): return "nested_list.remove_item"
    @property
    def ops_move(self): return "nested_list.move_item"
    @property
    def ops_move_up(self): return "nested_list.move_up"
    @property
    def ops_move_down(self): return "nested_list.move_down"

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")


class BaseNestedListAddOperator(bpy.types.Operator):
    """Base class for adding items."""
    bl_idname = "nested_list.add_item"
    bl_label = "Add Item"

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")

    def execute(self, context):
        manager = self.get_manager(context)
        new_id = manager.add_item()
        # Set active_index to the new item's position
        flattened = manager.flatten_hierarchy()
        for i, (item, _) in enumerate(flattened):
            if item.id == new_id:
                manager.active_index = i
                break
        return {'FINISHED'}


class BaseNestedListRemoveOperator(bpy.types.Operator):
    """Base class for removing items."""
    bl_idname = "nested_list.remove_item"
    bl_label = "Remove Item"

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")

    def execute(self, context):
        manager = self.get_manager(context)
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            collection_index = manager.get_collection_index_from_id(item_id)
            if collection_index != -1:
                manager.items.remove(collection_index)
                flattened = manager.flatten_hierarchy()
                manager.active_index = min(
                    manager.active_index, len(flattened) - 1)
                return {'FINISHED'}
        return {'CANCELLED'}


class BaseNestedListMoveOperator(bpy.types.Operator):
    """Base class for moving items to new parents."""
    bl_idname = "nested_list.move_item"
    bl_label = "Move Item"
    bl_description = "Move the selected item to a new parent"

    new_parent_id: IntProperty()

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        manager = self.get_manager(context)
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.move_item(item_id, self.new_parent_id):
                self.report(
                    {'INFO'}, f"Moved item {item_id} to parent {self.new_parent_id}")
                return {'FINISHED'}
        return {'CANCELLED'}


class BaseNestedListMoveUpOperator(bpy.types.Operator):
    """Base class for moving items up."""
    bl_idname = "nested_list.move_up"
    bl_label = "Move Item Up"

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")

    def execute(self, context):
        manager = self.get_manager(context)
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.reorder_item(item_id, 'UP'):
                flattened = manager.flatten_hierarchy()
                for i, (item, _) in enumerate(flattened):
                    if item.id == item_id:
                        manager.active_index = i
                        break
                return {'FINISHED'}
        return {'CANCELLED'}


class BaseNestedListMoveDownOperator(bpy.types.Operator):
    """Base class for moving items down."""
    bl_idname = "nested_list.move_down"
    bl_label = "Move Item Down"

    def get_manager(self, context):
        """Override this to return the appropriate manager instance."""
        raise NotImplementedError("Subclasses must implement get_manager")

    def execute(self, context):
        manager = self.get_manager(context)
        item_id = manager.get_id_from_flattened_index(manager.active_index)
        if item_id != -1:
            if manager.reorder_item(item_id, 'DOWN'):
                flattened = manager.flatten_hierarchy()
                for i, (item, _) in enumerate(flattened):
                    if item.id == item_id:
                        manager.active_index = i
                        break
                return {'FINISHED'}
        return {'CANCELLED'}
