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
                       UIList)


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
            if self.action == 'DOWN' and idx < len(active_group.layers) - 1:
                active_group.layers.move(idx, idx + 1)
                active_group.active_layer_index += 1
                # info = 'Layer "%s" moved down' % (item.name)
                # self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                active_group.layers.move(idx, idx - 1)
                active_group.active_layer_index -= 1
                # info = 'Layer "%s" moved up' % (item.name)
                # self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                bpy.ops.paint_system.delete_layer('INVOKE_DEFAULT')
                # active_group.active_layer_index -= 1
                # active_group.layers.remove(idx)
                # # reselect the active layer if it was the last one
                # active_group.active_layer_index = min(
                #     idx, len(active_group.layers) - 1)

        if self.action == 'ADD':
            # run addLayer operator
            bpy.ops.paint_system.add_layer('INVOKE_DEFAULT')

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

    layer_name: StringProperty(
        name="Layer Name",
        description="Name for the new layer",
        default="New Layer"
    )

    def execute(self, context):
        mat = context.active_object.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]

        # Add new layer at index 0
        new_layer = active_group.layers.add()
        new_layer.name = self.layer_name
        # Move it to the beginning
        active_group.layers.move(len(active_group.layers)-1, 0)
        active_group.active_layer_index = 0

        # Force UI update
        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "layer_name")


class PAINTSYSTEM_OT_deleteLayer(Operator):
    """Add a new layer"""
    bl_idname = "paint_system.delete_layer"
    bl_label = "delete Layer"
    bl_description = "Delete selected layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @ classmethod
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

        # Check if idx is valid
        if idx < 0 or idx >= len(active_group.layers):
            return {'CANCELLED'}

        active_group.active_layer_index -= 1
        active_group.layers.remove(idx)
        # reselect the active layer if it was the last one
        active_group.active_layer_index = min(
            idx, len(active_group.layers) - 1)

        # Force UI update
        if context.area:
            context.area.tag_redraw()

        return {'FINISHED'}

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


class PAINTSYSTEM_UL_layers(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.7)
        split.prop(item, "name", text="", emboss=False)
        split.prop(item, "blend_mode", text="")


class PaintSystemLayer(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer"
    )
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image
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


class PaintSystemFolder(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Folder name",
        default="Folder"
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
    layers: CollectionProperty(type=PaintSystemLayer)


class PaintSystemLayers(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Group name",
        default="Group"
    )
    # items: Folders and layers
    layers: CollectionProperty(type=PaintSystemLayer)
    active_layer_index: IntProperty(name="Active Layer Index")


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


class MAT_PT_paintSystemLayers(Panel):
    bl_idname = 'MAT_PT_paintSystemLayers'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Layers"
    bl_category = 'Paint System'
    bl_parent_id = 'MAT_PT_paintSystemGroups'

    @classmethod
    def poll(cls, context):
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0 and mat.paint_system.active_group

    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
        # Get active group
        active_group_idx = int(mat.paint_system.active_group)
        active_group = mat.paint_system.groups[active_group_idx]

        # Layer list
        row = layout.row()
        rows = 4
        row.template_list("PAINTSYSTEM_UL_layers", "", active_group,
                          "layers", active_group, "active_layer_index",
                          rows=rows)

        # Layer management buttons
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
    PAINTSYSTEM_UL_layers,
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
