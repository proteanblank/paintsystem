import bpy

from bpy.props import (IntProperty,
                       FloatProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)

from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList,
                       UILayout,
                       Menu)


class PaintSystemLayer(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer"
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True
    )
    opacity: FloatProperty(
        name="Opacity",
        description="Layer opacity",
        min=0.0,
        max=1.0,
        default=1.0
    )
    clip_below: BoolProperty(
        name="Clip Below",
        description="Clip layers below this one",
        default=False
    )
    blend_mode: EnumProperty(
        name="Blend",
        description="Blend mode for this layer",
        items=[
            ('MIX', "Mix", "Regular mixing"),
            ('ADD', "Add", "Additive blending"),
            ('MULTIPLY', "Multiply", "Multiplicative blending"),
            ('SUBTRACT', "Subtract", "Subtractive blending"),
            ('OVERLAY', "Overlay", "Overlay blending"),
        ],
        default='MIX'
    )
    type: EnumProperty(
        name="Type",
        description="Layer type",
        items=[
            ('IMAGE', "Image", "Image layer"),
            ('FOLDER', "Folder", "Folder layer"),
        ],
        default='IMAGE'
    )
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image
    )
    # For indexing
    id: IntProperty()  # Unique identifier
    parent_id: IntProperty(default=-1)  # ID of the parent (-1 means no parent)
    order: IntProperty()  # Order within the same parent


# class PaintSystemImage(PaintSystemLayer):


# class PaintSystemFolder(PaintSystemLayer):
#     layers: CollectionProperty(type=PaintSystemLayer)


class PaintSystemLayers(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Group name",
        default="Group"
    )
    layers: CollectionProperty(type=PaintSystemLayer)
    active_layer_index: IntProperty(name="Active Layer Index")
    # For indexing
    next_id: IntProperty(default=0)

    def add_item(self, data: dict, parent_id=-1):
        """Adds a new item."""
        new_item = self.layers.add()
        new_item.id = self.next_id
        # set the properties from the data dict
        for key, value in data.items():
            setattr(new_item, key, value)
        new_item.parent_id = parent_id
        new_item.order = self.get_next_order(parent_id)
        self.next_id += 1
        return new_item.id

    def get_next_order(self, parent_id):
        """Get the next available order for a given parent."""
        return max((item.order for item in self.layers if item.parent_id == parent_id), default=-1) + 1

    def get_item_by_id(self, item_id):
        """Get an item by its ID."""
        for item in self.layers:
            if item.id == item_id:
                return item
        return None

    def get_collection_index_from_id(self, item_id):
        """Get the collection index from an item ID."""
        for index, item in enumerate(self.layers):
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
            [i for i in self.layers if i.parent_id == item.parent_id],
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
                [item for item in self.layers if item.parent_id == parent_id],
                key=lambda i: i.order
            )
            for item in children:
                collected.append((item, level))
                collected.extend(collect_items(item.id, level + 1))
            return collected

        return collect_items(-1, 0)


class PAINTSYSTEM_OT_addPaintSystem(Operator):
    """Add a new paint system"""
    bl_idname = "paint_system.add_paint_system"
    bl_label = "Add Paint System"
    bl_description = "Add a new paint system"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat:
            mat = bpy.data.materials.new(name="Material")
            mat.use_nodes = True
            context.active_object.data.materials.append(mat)
            context.active_object.active_material = mat

        if not hasattr(mat, "paint_system"):
            self.report({'INFO'}, "Paint system added")
        else:
            self.report({'INFO'}, "Paint system already exists")
        return {'FINISHED'}


class PAINTSYSTEM_OT_duplicateGroupWarning(Operator):
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


class PAINTSYSTEM_OT_addGroup(Operator):
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
        if context.area:
            context.area.tag_redraw()

        # Set the active group to the newly created one
        mat.paint_system.active_group = str(len(mat.paint_system.groups) - 1)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "group_name")


class PAINTSYSTEM_OT_deleteGroup(Operator):
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
        if context.area:
            context.area.tag_redraw()

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


class PAINTSYSTEM_MT_moveMenu(Menu):
    """Provide user a menu to move layers in and out of folders or skip them"""
    bl_label = "Move Menu"
    bl_idname = "paint_system.move_menu"

    action: bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", "")
        )
    )

    target_layer_index = bpy.props.IntProperty()

    # Set the menu operators and draw functions
    def draw(self, context):
        layout = self.layout
        layout.operator("paint_system.layer_action",
                        text="Skip Over Folder").action = self.action
        layout.operator("paint_system.move_layer",
                        text="Move Inside Folder").target_layer_index = self.target_layer_index


class PAINTSYSTEM_OT_layerActions(Operator):
    """Move layers up and down, add and remove"""
    bl_idname = "paint_system.layer_action"
    bl_label = "Layer Actions"
    bl_description = "Move layers up and down, add and remove"
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", "")
        )
    )

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        idx = active_group.active_layer_index

        try:
            item = active_group.layers[idx]
        except IndexError:
            pass
        else:
            if (self.action == 'DOWN' or self.action == 'UP'):
                item_id = active_group.get_id_from_flattened_index(
                    active_group.active_layer_index)
                if item_id != -1:
                    if active_group.reorder_item(item_id, self.action):
                        # Update active_index to follow the moved item
                        flattened = active_group.flatten_hierarchy()
                        for i, (item, _) in enumerate(flattened):
                            if item.id == item_id:
                                active_group.active_layer_index = i
                                break
                        return {'FINISHED'}
                return {'CANCELLED'}

            elif self.action == 'REMOVE':
                bpy.ops.paint_system.delete_layer('INVOKE_DEFAULT')
                # active_group.active_layer_index -= 1
                # active_group.layers.remove(idx)
                # # reselect the active layer if it was the last one
                # active_group.active_layer_index = min(
                #     idx, len(active_group.layers) - 1)

        if self.action == 'ADD':
            pass
            # run addLayer operator
            # new_id = active_group.add_item(name=f"Item {active_group.next_id}")
            # # Set active_index to the new item's position in the flattened list
            # flattened = active_group.flatten_hierarchy()
            # for i, (item, _) in enumerate(flattened):
            #     if item.id == new_id:
            #         active_group.active_layer_index = i
            #         break

            # Force UI update
        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}


class PAINTSYSTEM_OT_addLayer(Operator):
    """Add a new layer"""
    bl_idname = "paint_system.add_layer"
    bl_label = "Add Layer"
    bl_description = "Add a new layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def get_next_layer_number(self, context):
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]

        # Find highest layer number
        highest_num = 0
        for layer in active_group.layers:
            # Check if name matches pattern "Layer X"
            if layer.name.startswith("Layer "):
                try:
                    num = int(layer.name.split(" ")[1])
                    highest_num = max(highest_num, num)
                except (IndexError, ValueError):
                    continue

        return highest_num + 1

    layer_name: StringProperty(
        name="Layer Name",
        description="Name for the new layer",
        default="Layer 1"  # This will be updated in invoke
    )
    type: EnumProperty(
        name="Layer Type",
        description="Type of layer to add",
        items=[
            ('IMAGE', "Image", "Image layer"),
            ('FOLDER', "Folder", "Folder layer"),
        ],
        default='IMAGE'
    )
    resolution: EnumProperty(
        name="Resolution",
        description="Resolution for the new layer",
        items=[
            ('1024', "1024", ""),
            ('2048', "2048", ""),
            ('4096', "4096", ""),
            ('8192', "8192", ""),
        ],
    )

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]

        new_id = active_group.add_item(
            {"name": self.layer_name, "type": self.type})
        # Set active_index to the new item's position in the flattened list
        flattened = active_group.flatten_hierarchy()
        for i, (item, _) in enumerate(flattened):
            if item.id == new_id:
                active_group.active_layer_index = i
                break

        # Force UI update
        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        # Set default name based on highest layer number
        next_num = self.get_next_layer_number(context)
        self.layer_name = f"Layer {next_num}"

        return context.window_manager.invoke_props_dialog(self, confirm_text="Add Layer")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "type")
        layout.prop(self, "layer_name", text="Name")
        if self.type == 'IMAGE':
            layout.label(text="Resolution:")
            layout.prop(self, "resolution", expand=True)


class PAINTSYSTEM_OT_moveLayer(Operator):
    """Move selected layers into a folder"""
    bl_idname = "paint_system.move_layer"
    bl_label = "Move Layer"
    bl_description = "Move selected layers into a folder"
    bl_options = {'REGISTER', 'UNDO'}

    # Property to store target layer index
    target_layer_index: IntProperty(
        name="Target Layer",
        description="Layer to move relative to",
        default=0,
        min=0
    )

    # position: EnumProperty(
    #     items=(
    #         ('OVER', "Over", "Place layer above target"),
    #         ('UNDER', "Under", "Place layer below target"),
    #         ('INSIDE', "Inside", "Place layer inside target folder")
    #     ),
    #     default='INSIDE'
    # )

    def get_layer_items(self, context):
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        idx = active_group.active_layer_index
        flattened = active_group.flatten_hierarchy()

        # Create list of all layers except current one
        items = []
        for i, (layer, _) in enumerate(flattened):
            if i != idx:  # Skip current layer
                items.append(
                    (str(i), layer.name, f"Move relative to {layer.name}"))
        return items

    # Dynamic EnumProperty for target layer selection
    target_layer_enum: EnumProperty(
        name="Target Layer",
        description="Layer to move relative to",
        items=get_layer_items
    )

    # @classmethod
    # def poll(cls, context):
    #     mat = context.active_object.active_material
    #     if not mat or not hasattr(mat, "paint_system"):
    #         return False
    #     active_group_idx = int(mat.paint_system.active_group)
    #     active_group = mat.paint_system.groups[active_group_idx]
    #     return len(active_group.layers) > 1

    # def execute(self, context):
    #     mat = context.active_object.active_material
    #     if not mat or not hasattr(mat, "paint_system"):
    #         return {'CANCELLED'}

    #     active_group_idx = int(mat.paint_system.active_group)
    #     active_group = mat.paint_system.groups[active_group_idx]
    #     source_idx = active_group.active_layer_index
    #     target_idx = int(self.target_layer_enum)

    #     # Get the layers
    #     source_layer = active_group.layers[source_idx]
    #     target_layer = active_group.layers[target_idx]

    #     # Determine new position based on layer types and selected position
    #     if target_layer.type == 'FOLDER':
    #         if self.position == 'INSIDE' and source_layer.type == 'IMAGE':
    #             # Move inside folder logic here
    #             # This would require restructuring the data to support nested layers
    #             pass
    #         else:
    #             # Handle over/under cases
    #             new_idx = target_idx if self.position == 'UNDER' else target_idx
    #             active_group.layers.move(source_idx, new_idx)
    #     else:
    #         # Regular layer movement
    #         new_idx = target_idx if self.position == 'UNDER' else target_idx
    #         active_group.layers.move(source_idx, new_idx)

    #     # Update active layer index
    #     active_group.active_layer_index = new_idx

    #     # Force UI update
    #     if context.area:
    #         context.area.tag_redraw()

    #     return {'FINISHED'}

    def execute(self, context):
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_layer_index)
        # self.target_layer_index = int(self.target_layer_enum)
        if item_id != -1:
            if active_group.move_item(item_id, active_group.get_id_from_flattened_index(self.target_layer_index)):
                self.report(
                    {'INFO'}, f"Moved item {item_id} to parent {self.target_layer_index}")
                return {'FINISHED'}
        return {'CANCELLED'}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_dialog(self)

    # def draw(self, context):
    #     layout = self.layout
    #     mat = context.active_object.active_material
    #     active_group_idx = int(mat.paint_system.active_group)
    #     active_group = mat.paint_system.groups[active_group_idx]
    #     active_layer = active_group.layers[active_group.active_layer_index]

    #     layout.label(text=f"Move '{active_layer.name}'")

    #     # Target layer selection
    #     layout.prop(self, "target_layer_enum", text="Target Layer")


class PAINTSYSTEM_OT_deleteLayer(Operator):
    """Add a new layer"""
    bl_idname = "paint_system.delete_layer"
    bl_label = "delete Layer"
    bl_description = "Delete selected layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        idx = active_group.active_layer_index
        return mat and hasattr(mat, "paint_system") and len(active_group.layers) > 0 and idx >= 0 and idx < len(active_group.layers)

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        idx = active_group.active_layer_index

        item_id = active_group.get_id_from_flattened_index(idx)
        if item_id != -1:
            collection_index = active_group.get_collection_index_from_id(
                item_id)
            if collection_index != -1:
                active_group.layers.remove(collection_index)
                # Update active_index to stay within bounds
                flattened = active_group.flatten_hierarchy()
                active_group.active_layer_index = min(
                    idx, len(flattened) - 1)
                # Force the UI to update
                if context.area:
                    context.area.tag_redraw()
                return {'FINISHED'}
        return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        active_layer = active_group.layers[active_group.active_layer_index]
        layout.label(
            text=f"Delete '{active_layer.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the layer")


def get_groups(self, context):
    mat = context.active_object.active_material
    if not mat or not hasattr(mat, "paint_system"):
        return []
    return [(str(i), group.name, f"Group {i}") for i, group in enumerate(mat.paint_system.groups)]


class PAINTSYSTEM_UL_items(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # col = layout.column(align=True)
        # row = col.row(align=True)
        # row.prop(item, "enabled", text="", emboss=False,
        #          icon='HIDE_OFF' if item.enabled else 'HIDE_ON', icon_only=True)
        # row.prop(item, "name", text="", icon='FILE_IMAGE' if item.type ==
        #          'IMAGE' else 'FILE_FOLDER', emboss=False)
        mat = context.active_object.active_material
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]

        flattened = active_group.flatten_hierarchy()
        if index < len(flattened):
            display_item, level = flattened[index]
            col = layout.column(align=True)
            row = col.row(align=True)

            for _ in range(level):
                row.label(icon='BLANK1')
            row.prop(display_item, "enabled", text="", emboss=False,
                     icon='HIDE_OFF' if display_item.enabled else 'HIDE_ON', icon_only=True)
            row.prop(display_item, "name", text="", icon='FILE_IMAGE' if item.type ==
                     'IMAGE' else 'FILE_FOLDER', emboss=False)
            # row.label(text=f"ID: {display_item.id}")
            # layout.label(
            #     text=f"{indent}{display_item.name} (ID: {display_item.id})")


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


class PaintSystemGroups(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Paint system name",
        default="Paint System"
    )
    groups: CollectionProperty(type=PaintSystemLayers)
    active_group: EnumProperty(
        name="Active Group",
        description="Select active group",
        items=get_groups
    )


class MAT_PT_paintSystemGroups(Panel):
    bl_idname = 'MAT_PT_paintSystemGroups'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System"
    bl_category = 'Paint System'

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system")

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material

        if not mat:
            layout.label(text="No active material")
            return

        if not hasattr(mat, "paint_system"):
            layout.operator("paint_system.add_paint_system")
            return
        # Add Group button and selector
        row = layout.row()
        row.scale_y = 2.0
        row.operator("paint_system.add_group",
                     text="Add New Group", icon='ADD')
        row = layout.row()
        row.operator(
            "paint_system.delete_group", text="Delete Current Group", icon='TRASH')

        if len(mat.paint_system.groups) > 0:
            layout.label(text="Active Group:")
            row = layout.row()
            row.scale_y = 1.5
            row.prop(mat.paint_system, "active_group", text="")


def layers_ui(self, layout: UILayout, layers, lvl=0):
    if lvl == 0:
        col = layout.column(align=True)
    for i, layer in enumerate(layers):
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(layer, "enabled", text="", emboss=False,
                 icon='HIDE_OFF' if layer.enabled else 'HIDE_ON', icon_only=True)
        # Image or folder icon
        row.prop(layer, "name", text="", icon='FILE_IMAGE' if layer.type ==
                 'IMAGE' else 'FILE_FOLDER', emboss=False)


class MAT_PT_paintSystemLayers(Panel):
    bl_idname = 'MAT_PT_paintSystemLayers'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layers"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_paintSystemGroups'

    def get_active_group(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return None
        active_group_idx = int(mat.paint_system.active_group)
        return mat.paint_system.groups[active_group_idx]

    layers: PointerProperty(type=PaintSystemLayers)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0 and mat.paint_system.active_group

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        # Get active group
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]
        flattened = active_group.flatten_hierarchy()

        # Layer list
        row = layout.row()
        row.template_list("PAINTSYSTEM_UL_items", "", active_group,
                          "layers", active_group, "active_layer_index",
                          rows=5)
        col = row.column(align=True)
        col.operator("paint_system.add_layer",
                     icon='ADD', text="")
        col.operator("paint_system.delete_layer",
                     icon='REMOVE', text="")
        col.separator()
        col.operator("paint_system.layer_action",
                     icon='TRIA_UP', text="").action = 'UP'
        col.operator("paint_system.layer_action",
                     icon='TRIA_DOWN', text="").action = 'DOWN'
        col.separator()
        col.operator("paint_system.move_layer",
                     icon='NLA_PUSHDOWN', text="")

        if active_group.active_layer_index >= 0 and active_group.active_layer_index < len(active_group.layers):
            active_layer = flattened[active_group.active_layer_index][0]
            layout.label(text="Layer Settings:")
            layout.prop(active_layer, "opacity", slider=True)
            col = layout.column(align=True)
            row = col.row()
            row.scale_y = 1.5
            row.prop(active_layer, "clip_below",
                     icon='SELECT_INTERSECT')
            row.prop(active_layer, "blend_mode", text="")


classes = (
    PaintSystemLayer,
    PaintSystemLayers,
    PaintSystemGroups,
    PAINTSYSTEM_OT_addPaintSystem,
    PAINTSYSTEM_OT_addGroup,
    PAINTSYSTEM_OT_deleteGroup,
    PAINTSYSTEM_OT_duplicateGroupWarning,
    PAINTSYSTEM_OT_layerActions,
    PAINTSYSTEM_OT_addLayer,
    PAINTSYSTEM_OT_deleteLayer,
    PAINTSYSTEM_OT_moveLayer,
    PAINTSYSTEM_UL_items,
    MAT_PT_paintSystemGroups,
    MAT_PT_paintSystemLayers,


)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Material.paint_system = PointerProperty(type=PaintSystemGroups)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Material.paint_system
