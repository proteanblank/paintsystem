import bpy

from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
)
import gpu
from bpy.types import Operator, Context
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem, ADJUSTMENT_ENUM
from .common import redraw_panel, get_object_uv_maps
import re

# bpy.types.Image.pack
# -------------------------------------------------------------------
# Group Operators
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_DuplicateGroupWarning(Operator):
    """Warning for duplicate group name"""
    bl_idname = "paint_system.duplicate_group_warning"
    bl_label = "Warning"
    bl_options = {'INTERNAL'}
    bl_description = "Warning for duplicate group name"

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


class PAINTSYSTEM_OT_NewGroup(Operator):
    """Add a new group"""
    bl_idname = "paint_system.new_group"
    bl_label = "Add Group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Add a new group"

    group_name: StringProperty(
        name="Group Name",
        description="Name for the new group",
        default="New Group"
    )

    create_material_setup: BoolProperty(
        name="Create Material Setup",
        description="Create a template material setup for painting",
        default=True
    )

    material_template: EnumProperty(
        name="Template",
        items=[
            ('NONE', "Manual Adjustment", "Just add node group to material"),
            ('STANDARD', "Standard", "Start off with a standard setup"),
            ('TRANSPARENT', "Transparent", "Start off with a transparent setup"),
            ('NORMAL', "Normal", "Start off with a normal painting setup"),
        ],
        default='STANDARD'
    )

    set_view_transform: BoolProperty(
        name="Set View Transform",
        description="Set view transform to standard",
        default=True
    )

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        # Check for duplicate names
        for group in mat.paint_system.groups:
            if group.name == self.group_name:
                bpy.ops.paint_system.duplicate_group_warning(
                    'INVOKE_DEFAULT', group_name=self.group_name)
                return {'CANCELLED'}

        new_group = ps.add_group(self.group_name)

        if self.create_material_setup:
            bpy.ops.paint_system.create_template_setup(
                'INVOKE_DEFAULT', template=self.material_template, disable_popup=True)

        if self.set_view_transform:
            context.scene.view_settings.view_transform = 'Standard'

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        groups = ps.get_groups()
        if groups:
            self.material_template = "NONE"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "group_name")
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.prop(self, "create_material_setup",
                 text="Setup Material", icon='CHECKBOX_HLT' if self.create_material_setup else 'CHECKBOX_DEHLT')
        row.prop(self, "material_template", text="")
        # layout.label(text="Setup material for painting",
        #              icon='QUESTION')
        if context.scene.view_settings.view_transform != 'Standard':
            layout.prop(self, "set_view_transform",
                        text="Set View Transform to Standard")


class PAINTSYSTEM_OT_DeleteGroup(Operator):
    """Delete the active group"""
    bl_idname = "paint_system.delete_group"
    bl_label = "Delete Group"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete the active group"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        return mat and hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0 and mat.paint_system.active_group

    def execute(self, context):
        ps = PaintSystem(context)
        ps.delete_active_group()

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        layout = self.layout
        layout.label(
            text=f"Delete '{active_group.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the group")


class PAINTSYSTEM_OT_RenameGroup(Operator):
    bl_idname = "paint_system.rename_group"
    bl_label = "Rename Group"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Rename the active group"

    new_name: StringProperty(name="New Name")

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        return active_group

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        active_group.name = self.new_name
        redraw_panel(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.new_name = PaintSystem(context).get_active_group().name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "new_name")


# -------------------------------------------------------------------
# Layers Operators
# -------------------------------------------------------------------
class PAINTSYSTEM_OT_DeleteItem(Operator):
    """Remove the active item"""
    bl_idname = "paint_system.delete_item"
    bl_label = "Remove Item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Remove the active item"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.get_active_layer() and ps.get_active_group()

    def execute(self, context):
        ps = PaintSystem(context)
        if ps.delete_active_item():
            return {'FINISHED'}
        return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        layout.label(
            text=f"Delete '{active_layer.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the layer")


class PAINTSYSTEM_OT_MoveUp(Operator):
    """Move the active item up"""
    bl_idname = "paint_system.move_up"
    bl_label = "Move Item Up"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Move the active item up"

    action: EnumProperty(
        items=[
            ('MOVE_INTO', "Move Into", "Move into folder"),
            ('MOVE_ADJACENT', "Move Adjacent", "Move as sibling"),
            ('MOVE_OUT', "Move Out", "Move out of folder"),
            ('SKIP', "Skip", "Skip over item"),
        ]
    )

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)
        options = active_group.get_movement_options(item_id, 'UP')
        return active_group and options

    def invoke(self, context, event):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        options = active_group.get_movement_options(item_id, 'UP')
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
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        for op_id, label, props in active_group.get_movement_menu_items(item_id, 'UP'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        if active_group.execute_movement(item_id, 'UP', self.action):
            # Update active_index to follow the moved item
            flattened = active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == item_id:
                    active_group.active_index = i
                    break

            active_group.update_node_tree()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}


class PAINTSYSTEM_OT_MoveDown(Operator):
    """Move the active item down"""
    bl_idname = "paint_system.move_down"
    bl_label = "Move Item Down"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Move the active item down"

    action: EnumProperty(
        items=[
            ('MOVE_OUT_BOTTOM', "Move Out Bottom", "Move out of folder"),
            ('MOVE_INTO_TOP', "Move Into Top", "Move to top of folder"),
            ('MOVE_ADJACENT', "Move Adjacent", "Move as sibling"),
            ('SKIP', "Skip", "Skip over item"),
        ]
    )

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)
        options = active_group.get_movement_options(item_id, 'DOWN')
        return active_group and options

    def invoke(self, context, event):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        options = active_group.get_movement_options(item_id, 'DOWN')
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
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        for op_id, label, props in active_group.get_movement_menu_items(item_id, 'DOWN'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        if active_group.execute_movement(item_id, 'DOWN', self.action):
            # Update active_index to follow the moved item
            flattened = active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == item_id:
                    active_group.active_index = i
                    break

            active_group.update_node_tree()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}


def get_highest_number_with_prefix(prefix, string_list):
    highest_number = 0
    for string in string_list:
        if string.startswith(prefix):
            # Extract numbers from the string using regex
            match = re.search(r'\d+', string)
            if match:
                number = int(match.group())
                if number > highest_number:
                    highest_number = number
    return highest_number


class PAINTSYSTEM_OT_CreateNewUVMap(Operator):
    bl_idname = "paint_system.create_new_uv_map"
    bl_label = "Create New UV Map"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new UV Map"

    uv_map_name: StringProperty(
        name="Name",
        default="UVMap"
    )

    def execute(self, context):
        current_mode = context.object.mode
        context.object.data.uv_layers.new(name=self.uv_map_name)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=0.05)
        bpy.ops.object.mode_set(mode=current_mode)
        return {'FINISHED'}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_dialog(self)

    # def draw(self, context):
    #     layout = self.layout
    #     layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_NewImage(Operator):
    bl_idname = "paint_system.new_image"
    bl_label = "New Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new image"

    def get_next_image_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        flattened = ps.get_active_group().flatten_hierarchy()
        number = get_highest_number_with_prefix(
            'Image', [item[0].name for item in flattened]) + 1
        return f"Image {number}"

    name: StringProperty(
        name="Name",
        default="Image",
    )
    image_resolution: EnumProperty(
        items=[
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
        ],
        default='1024'
    )
    # high_bit_float: BoolProperty(
    #     name="High Bit Float",
    #     description="Use 32-bit float instead of 16-bit",
    #     default=False
    # )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        if not get_object_uv_maps(self, context):
            bpy.ops.paint_system.create_new_uv_map('INVOKE_DEFAULT')
        image = bpy.data.images.new(
            name=f"PS {mat.name} {active_group.name} {self.name}",
            width=int(self.image_resolution),
            height=int(self.image_resolution),
            alpha=True,
        )
        image.generated_color = (0, 0, 0, 0)
        ps.create_image_layer(self.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.name = self.get_next_image_name(context)
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "image_resolution", expand=True)
        if not get_object_uv_maps(self, context):
            layout.label(text="No UV Maps found. Creating new UV Map")
        else:
            layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_OpenImage(Operator):
    bl_idname = "paint_system.open_image"
    bl_label = "Open Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Open an image"

    filepath: StringProperty(
        subtype='FILE_PATH',
    )

    filter_glob: StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )

    def execute(self, context):
        ps = PaintSystem(context)
        image = bpy.data.images.load(self.filepath, check_existing=True)
        if not get_object_uv_maps(self, context):
            bpy.ops.paint_system.create_new_uv_map('INVOKE_DEFAULT')
        ps.create_image_layer(image.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        if not get_object_uv_maps(self, context):
            layout.label(text="No UV Maps found. Creating new UV Map")
        else:
            layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_OpenExistingImage(Operator):
    bl_idname = "paint_system.open_existing_image"
    bl_label = "Open Existing Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Open an image from the existing images"

    image_name: StringProperty()

    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        image = bpy.data.images.get(self.image_name)
        if not image:
            return {'CANCELLED'}
        if not get_object_uv_maps(self, context):
            bpy.ops.paint_system.create_new_uv_map('INVOKE_DEFAULT')
        ps.create_image_layer(self.image_name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.image_name = bpy.data.images[0].name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "image_name", bpy.data,
                           "images", text="Image")
        if not get_object_uv_maps(self, context):
            layout.label(text="No UV Maps found. Creating new UV Map")
        else:
            layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_NewSolidColor(Operator):
    bl_idname = "paint_system.new_solid_color"
    bl_label = "New Solid Color"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new solid color"

    def get_next_image_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        flattened = ps.get_active_group().flatten_hierarchy()
        number = get_highest_number_with_prefix(
            'Color', [item[0].name for item in flattened]) + 1
        return f"Color {number}"

    name: StringProperty(
        name="Name",
        default="Color",
    )

    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        ps.create_solid_color_layer(self.name, self.color)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.name = self.get_next_image_name(context)
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "color")


class PAINTSYSTEM_OT_NewFolder(Operator):
    bl_idname = "paint_system.new_folder"
    bl_label = "Add Folder"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add a new folder"

    def get_next_folder_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        flattened = ps.get_active_group().flatten_hierarchy()
        number = get_highest_number_with_prefix(
            'Folder', [item[0].name for item in flattened]) + 1
        return f"Folder {number}"

    folder_name: StringProperty(
        name="Name",
        default="Folder"
    )
    disable_popup: BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        return active_group

    def execute(self, context):
        ps = PaintSystem(context)
        ps.create_folder(self.folder_name)

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        self.folder_name = self.get_next_folder_name(context)
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_name")


class PAINTSYSTEM_OT_NewAdjustmentLayer(Operator):
    bl_idname = "paint_system.new_adjustment_layer"
    bl_label = "Add Adjustment Layer"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add a new adjustment layer"

    adjustment_type: EnumProperty(
        name="Adjustment",
        items=ADJUSTMENT_ENUM,
        default='ShaderNodeBrightContrast'
    )

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        return active_group

    def execute(self, context):
        ps = PaintSystem(context)
        # Look for get name from in adjustment_enum based on adjustment_type
        layer_name = next(name for identifier, name,
                          _ in ADJUSTMENT_ENUM if identifier == self.adjustment_type)
        ps.create_adjustment_layer(layer_name, self.adjustment_type)

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_dialog(self)

    # def draw(self, context):
    #     layout = self.layout
    #     layout.prop(self, "adjustment_name")


classes = (
    PAINTSYSTEM_OT_DuplicateGroupWarning,
    PAINTSYSTEM_OT_NewGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_RenameGroup,
    PAINTSYSTEM_OT_DeleteItem,
    PAINTSYSTEM_OT_MoveUp,
    PAINTSYSTEM_OT_MoveDown,
    PAINTSYSTEM_OT_CreateNewUVMap,
    PAINTSYSTEM_OT_NewImage,
    PAINTSYSTEM_OT_OpenImage,
    PAINTSYSTEM_OT_OpenExistingImage,
    PAINTSYSTEM_OT_NewSolidColor,
    PAINTSYSTEM_OT_NewFolder,
    PAINTSYSTEM_OT_NewAdjustmentLayer,
)

register, unregister = register_classes_factory(classes)
