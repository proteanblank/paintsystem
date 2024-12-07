import bpy
from bpy.types import Panel, PropertyGroup, UIList, Operator
from bpy.props import StringProperty, IntProperty, CollectionProperty

# Example property group for list items


class CustomListItem(PropertyGroup):
    name: StringProperty(name="Name", default="Item")

# Main property group


class CustomListProperties(PropertyGroup):
    active_index: IntProperty()
    items: CollectionProperty(type=CustomListItem)

# Panel class with custom list drawing


class CUSTOM_PT_list_panel(Panel):
    bl_label = "Custom List"
    bl_idname = "CUSTOM_PT_list_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Custom'

    def draw(self, context):
        layout = self.layout
        custom_list = context.scene.custom_list

        # Add button
        row = layout.row()
        row.operator("custom_list.add_item", text="Add Item")
        row.operator("custom_list.remove_item", text="Remove Item")

        # Draw custom list
        box = layout.box()
        for index, item in enumerate(custom_list.items):
            row = box.row()
            # Create clickable button that looks like a regular item
            props = row.operator("custom_list.select_item", text=item.name)
            props.index = index

            # Highlight active item
            if index == custom_list.active_index:
                row.prop(item, "name", text="")

# Operator to add items


class CUSTOM_OT_add_item(Operator):
    bl_idname = "custom_list.add_item"
    bl_label = "Add Item"

    def execute(self, context):
        custom_list = context.scene.custom_list
        item = custom_list.items.add()
        item.name = f"Item {len(custom_list.items)}"
        custom_list.active_index = len(custom_list.items) - 1
        return {'FINISHED'}

# Operator to remove items


class CUSTOM_OT_remove_item(Operator):
    bl_idname = "custom_list.remove_item"
    bl_label = "Remove Item"

    def execute(self, context):
        custom_list = context.scene.custom_list
        if custom_list.items:
            custom_list.items.remove(custom_list.active_index)
            custom_list.active_index = min(
                custom_list.active_index, len(custom_list.items) - 1)
        return {'FINISHED'}

# Operator to handle item selection


class CUSTOM_OT_select_item(Operator):
    bl_idname = "custom_list.select_item"
    bl_label = "Select Item"

    index: IntProperty()

    def execute(self, context):
        context.scene.custom_list.active_index = self.index
        return {'FINISHED'}


# Registration
classes = (
    CustomListItem,
    CustomListProperties,
    CUSTOM_PT_list_panel,
    CUSTOM_OT_add_item,
    CUSTOM_OT_remove_item,
    CUSTOM_OT_select_item,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.custom_list = bpy.props.PointerProperty(
        type=CustomListProperties)


def unregister():
    del bpy.types.Scene.custom_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# if __name__ == "__main__":
#     register()
