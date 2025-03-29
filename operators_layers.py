import bpy
from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty,
)
import gpu
from bpy.types import Operator, Context
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem, ADJUSTMENT_ENUM, SHADER_ENUM, TEMPLATE_ENUM
from .common import redraw_panel, get_object_uv_maps
import re
import copy
from .common_layers import UVLayerHandler
import numpy
import pathlib
from bpy.app.translations import pgettext_rpt as rpt_

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
        ps = PaintSystem(context)
        mat = ps.get_active_material()
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


class PAINTSYSTEM_OT_NewGroup(UVLayerHandler):
    """Add a new group"""
    bl_idname = "paint_system.new_group"
    bl_label = "Add Paint System"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Add a new group"

    def get_next_group_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        if not hasattr(mat, "paint_system"):
            return "New Group 1"
        groups = ps.get_groups()
        number = get_highest_number_with_prefix(
            'New Group', [item.name for item in groups]) + 1
        return f"New Group {number}"

    material_name: StringProperty(
        name="Material Name",
        default="New Material"
    )

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
        items=TEMPLATE_ENUM,
        default='STANDARD'
    )

    use_alpha_blend: BoolProperty(
        name="Use Alpha Blend",
        description="Use alpha blend instead of alpha clip",
        default=False
    )

    use_backface_culling: BoolProperty(
        name="Use Backface Culling",
        description="Use backface culling",
        default=True
    )

    set_view_transform: BoolProperty(
        name="Set View Transform",
        description="Set view transform to standard",
        default=True
    )
    
    def update_uv_mode(self, context: Context):
        self.uv_map_mode = 'PAINT_SYSTEM' if self.use_paintsystem_uv else 'OPEN'

    use_paintsystem_uv: BoolProperty(
        name="Use Paint System UV",
        description="Use the Paint System UV Map",
        default=True,
        update=update_uv_mode
    )

    hide_template: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        obj = ps.active_object

        if not mat:
            # Create a new material
            mat = bpy.data.materials.new(f"{self.material_name}")
            obj = ps.active_object
            mat.use_nodes = True
            if obj.material_slots and not obj.material_slots[obj.active_material_index].material:
                obj.material_slots[obj.active_material_index].material = mat
            else:
                ps.active_object.data.materials.append(mat)
                ps.active_object.active_material_index = len(
                    obj.material_slots) - 1

        ps.get_material_settings().use_paintsystem_uv = self.use_paintsystem_uv
        # Check for duplicate names
        for group in mat.paint_system.groups:
            if group.name == self.group_name:
                # bpy.ops.paint_system.duplicate_group_warning(
                #     'INVOKE_DEFAULT', group_name=self.group_name)
                self.report({'ERROR'}, "Group name already exists")
                return {'CANCELLED'}

        new_group = ps.add_group(self.group_name)

        if self.create_material_setup:
            bpy.ops.paint_system.create_template_setup(
                'INVOKE_DEFAULT',
                template=self.material_template,
                disable_popup=True,
                use_alpha_blend=self.use_alpha_blend,
                disable_show_backface=self.use_backface_culling,
                uv_map_mode=self.uv_map_mode,
                uv_map_name=self.uv_map_name,
            )

        if self.set_view_transform:
            context.scene.view_settings.view_transform = 'Standard'

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        groups = ps.get_groups()
        self.group_name = self.get_next_group_name(context)
        if groups:
            self.material_template = "NONE"
        if ps.get_active_material():
            self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
            ).use_paintsystem_uv else 'OPEN'
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        ps = PaintSystem(context)
        layout = self.layout
        mat = ps.get_active_material()
        obj = ps.active_object
        split = layout.split(factor=0.4)
        split.scale_y = 1.5
        if not mat:
            split.label(text="New Material Name:")
            split.prop(self, "material_name", text="")
        else:
            split.label(text="Selected Material:")
            row = split.row(align=True)
            row.prop(obj, "active_material", text="")
            # row.operator("material.new", text="", icon='ADD')
        if not self.hide_template:
            # row = layout.row(align=True)
            # row.scale_y = 1.5
            split = layout.split(factor=0.4)
            split.scale_y = 1.5
            split.label(text="Template:")
            split.prop(self, "material_template", text="")
            # row.prop(self, "create_material_setup",
            #         text="Setup Material", icon='CHECKBOX_HLT' if self.create_material_setup else 'CHECKBOX_DEHLT')
            # row.prop(self, "material_template", text="Template")
        row = layout.row()
        row.scale_y = 1.2
        row.prop(self, "use_paintsystem_uv", text="Use Paint System UV",
                 icon='CHECKBOX_HLT' if self.use_paintsystem_uv else 'CHECKBOX_DEHLT')
        if not self.use_paintsystem_uv:
            row = layout.row()
            row.scale_y = 1.2
            row.prop(self, "uv_map_name", text="")
        layout.separator()
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="Advanced Settings:", icon="TOOL_SETTINGS")
        split = box.split(factor=0.4)
        split.label(text="Group Name:")
        split.prop(self, "group_name", text="", icon='NODETREE')
        if self.material_template in ['STANDARD', 'TRANSPARENT']:
            box.prop(self, "use_alpha_blend", text="Use Alpha Blend")
            box.prop(self, "use_backface_culling",
                     text="Use Backface Culling")
        if context.scene.view_settings.view_transform != 'Standard':
            box.prop(self, "set_view_transform",
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
        current_mode = copy.deepcopy(context.object.mode)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        mesh = context.object.data
        uvmap = mesh.uv_layers.new(name=self.uv_map_name)
        # Set active UV Map
        mesh.uv_layers.active = mesh.uv_layers.get(uvmap.name)
        bpy.ops.uv.lightmap_pack(
            PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_MARGIN_DIV=0.2)
        bpy.ops.object.mode_set(mode=current_mode)
        return {'FINISHED'}

    # def invoke(self, context, event):
    #     return context.window_manager.invoke_props_dialog(self)

    # def draw(self, context):
    #     layout = self.layout
    #     layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_NewImage(UVLayerHandler):
    bl_idname = "paint_system.new_image"
    bl_label = "New Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new image"

    def get_next_image_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        base_layer_name = ps.get_active_group(
        ).name if ps.preferences.name_layers_group else "Image"
        flattened = ps.get_active_group().flatten_hierarchy()
        number = get_highest_number_with_prefix(
            base_layer_name, [item[0].name for item in flattened]) + 1
        return f"{base_layer_name} {number}"

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
            ('CUSTOM', "Custom", "Custom Resolution"),
        ],
        default='1024'
    )
    image_width: IntProperty(
        name="Width",
        default=1024,
        min=1,
        description="Width of the image in pixels"
    )
    image_height: IntProperty(
        name="Height",
        default=1024,
        min=1,
        description="Height of the image in pixels"
    )
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        self.set_uv_mode(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        
        image = bpy.data.images.new(
            name=f"PS {mat.name} {active_group.name} {self.name}",
            width=int(self.image_resolution) if self.image_resolution != 'CUSTOM' else self.image_width,
            height=int(self.image_resolution) if self.image_resolution != 'CUSTOM' else self.image_height,
            alpha=True,
        )
        image.generated_color = (0, 0, 0, 0)
        ps.create_image_layer(self.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.get_uv_mode(context)
        self.name = self.get_next_image_name(context)
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        box = layout.box()
        box.label(text="Image Resolution", icon='IMAGE_DATA')
        row = box.row(align=True)
        row.prop(self, "image_resolution", expand=True)
        if self.image_resolution == 'CUSTOM':
            row = box.row(align=True)
            row.prop(self, "image_width", text="Width")
            row.prop(self, "image_height", text="Height")
        box = layout.box()
        self.select_uv_ui(box)


class PAINTSYSTEM_OT_OpenImage(UVLayerHandler):
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

    def execute(self, context):
        ps = PaintSystem(context)
        self.set_uv_mode(context)
        image = bpy.data.images.load(self.filepath, check_existing=True)
        
        ps.create_image_layer(image.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.get_uv_mode(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        self.select_uv_ui(box)


class PAINTSYSTEM_OT_OpenExistingImage(UVLayerHandler):
    bl_idname = "paint_system.open_existing_image"
    bl_label = "Open Existing Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Open an image from the existing images"

    image_name: StringProperty()

    def execute(self, context):
        ps = PaintSystem(context)
        self.set_uv_mode(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        image = bpy.data.images.get(self.image_name)
        if not image:
            self.report({'ERROR'}, "Image not found")
            return {'CANCELLED'}
        
        ps.create_image_layer(self.image_name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.get_uv_mode(context)
        self.image_name = bpy.data.images[0].name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "image_name", bpy.data,
                           "images", text="Image")
        box = layout.box()
        self.select_uv_ui(box)


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


class PAINTSYSTEM_OT_NewShaderLayer(Operator):
    bl_idname = "paint_system.new_shader_layer"
    bl_label = "Add Shader Layer"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add a new shader layer"

    shader_type: EnumProperty(
        name="Shader",
        items=SHADER_ENUM,
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
                          _ in SHADER_ENUM if identifier == self.shader_type)
        ps.create_shader_layer(layer_name, self.shader_type)

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}


class PAITNSYSTEM_OT_NewNodeGroupLayer(Operator):
    bl_idname = "paint_system.new_node_group_layer"
    bl_label = "Add Node Group Layer"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add a new node group layer"

    def get_node_groups(self, context: Context):
        ps = PaintSystem(context)
        node_groups = []
        for node_group in bpy.data.node_groups:
            if node_group.bl_idname == 'ShaderNodeTree' and not node_group.name.startswith("_PS") and not node_group.name.startswith("PS_"):
                node_groups.append((node_group.name, node_group.name, ""))
        return node_groups

    layer_name: StringProperty(
        name="Layer Name",
        default="Custom Node Group"
    )

    node_tree_name: EnumProperty(
        name="Node Tree",
        items=get_node_groups,
    )

    def execute(self, context):
        ps = PaintSystem(context)
        if not self.get_node_groups(context):
            return {'CANCELLED'}

        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not ps.is_valid_ps_nodetree(node_tree):
            self.report({'ERROR'}, "Node Group not compatible")
            return {'CANCELLED'}

        ps.create_node_group_layer(self.layer_name, self.node_tree_name)

        # Force the UI to update
        redraw_panel(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        if not self.get_node_groups(context):
            layout.label(text="No node group found", icon='ERROR')
            return

        layout.prop(self, "node_tree_name")
        node_tree = bpy.data.node_groups.get(self.node_tree_name)
        if not ps.is_valid_ps_nodetree(node_tree):
            layout.label(text="Node Group not compatible", icon='ERROR')
            layout.label(text="Color & Alpha Input/Output Pair not Found")


class PAINTSYSTEM_OT_NewMaskImage(UVLayerHandler):
    bl_idname = "paint_system.new_mask_image"
    bl_label = "New Mask Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Create a new mask image"

    # def get_next_image_name(self, context: Context) -> str:
    #     ps = PaintSystem(context)
    #     base_layer_name = ps.get_active_group(
    #     ).name if ps.preferences.name_layers_group else "Mask"
    #     flattened = ps.get_active_group().flatten_hierarchy()
    #     number = get_highest_number_with_prefix(
    #         base_layer_name, [item[0].name for item in flattened]) + 1
    #     return f"{base_layer_name} {number}"

    # name: StringProperty(
    #     name="Name",
    #     default="Mask",
    # )
    image_resolution: EnumProperty(
        items=[
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
            ('CUSTOM', "Custom", "Custom Resolution"),
        ],
        default='1024'
    )
    image_width: IntProperty(
        name="Width",
        default=1024,
        min=1,
        description="Width of the image in pixels"
    )
    image_height: IntProperty(
        name="Height",
        default=1024,
        min=1,
        description="Height of the image in pixels"
    )
    initial_mask: EnumProperty(
        name="Initial Mask",
        items=[
            ('BLACK', "Black (Transparent)",
             "Start with a black (fully transparent) mask"),
            ('WHITE', "White (Opaque)", "Start with a white (fully opaque) mask"),
        ],
        default='WHITE'
    )
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        self.set_uv_mode(context)
        ps.get_material_settings().use_paintsystem_uv = self.uv_map_mode == "PAINT_SYSTEM"
        active_group = ps.get_active_group()
        active_layer = ps.get_active_layer()
        mat = ps.get_active_material()
        
        image = bpy.data.images.new(
            name=f"PS_MASK {active_group.name} {active_layer.name}",
            width=int(self.image_resolution) if self.image_resolution != 'CUSTOM' else self.image_width,
            height=int(self.image_resolution) if self.image_resolution != 'CUSTOM' else self.image_height,
        )
        image.colorspace_settings.name = 'Non-Color'
        image.generated_color = (
            0, 0, 0, 0) if self.initial_mask == 'BLACK' else (1, 1, 1, 1)
        active_layer.mask_image = image
        active_layer.enable_mask = True
        active_layer.mask_uv_map = self.uv_map_name
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.get_uv_mode(context)
        active_layer = ps.get_active_layer()
        if active_layer.image:
            if active_layer.image.size[0] == active_layer.image.size[1]:
                self.image_resolution = str(active_layer.image.size[0])
            else:
                self.image_resolution = 'CUSTOM'
                self.image_width = active_layer.image.size[0]
                self.image_height = active_layer.image.size[1]
        self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
        ).use_paintsystem_uv else 'OPEN'
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Initial Mask:")
        row = layout.row()
        row.prop(self, "initial_mask", expand=True)
        box = layout.box()
        box.label(text="Image Resolution", icon='IMAGE_DATA')
        row = box.row(align=True)
        row.prop(self, "image_resolution", expand=True)
        if self.image_resolution == 'CUSTOM':
            row = box.row(align=True)
            row.prop(self, "image_width", text="Width")
            row.prop(self, "image_height", text="Height")
        box = layout.box()
        self.select_uv_ui(box)


class PAINTSYSTEM_OT_DeleteMask(Operator):
    bl_idname = "paint_system.delete_mask_image"
    bl_label = "Delete Mask"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete the active mask"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        return active_layer and active_layer.mask_image

    def execute(self, context):
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        if active_layer.mask_image:
            bpy.data.images.remove(active_layer.mask_image)
            active_layer.mask_image = None
            active_layer.enable_mask = False
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        layout.label(
            text=f"Delete {active_layer.name} Mask ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the mask")


class PAINTSYSTEM_OT_InvertColors(Operator):
    bl_idname = "paint_system.invert_colors"
    bl_label = "Invert Colors"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Invert the colors of the active image"

    invert_r: BoolProperty(default=True)
    invert_g: BoolProperty(default=True)
    invert_b: BoolProperty(default=True)
    invert_a: BoolProperty(default=False)
    
    image_name: StringProperty()
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.invert('INVOKE_DEFAULT', invert_r=self.invert_r,
                                 invert_g=self.invert_g, invert_b=self.invert_b, invert_a=self.invert_a)
        return {'FINISHED'}

    def invoke(self, context, event):
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        # Check if image have alpha channel
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        if not image:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        layout.prop(self, "invert_r", text="Red")
        layout.prop(self, "invert_g", text="Green")
        layout.prop(self, "invert_b", text="Blue")
        if image.alp:
            layout.prop(self, "invert_a", text="Alpha")


class PAINTSYSTEM_OT_ExportActiveLayer(Operator):
    bl_idname = "paint_system.export_active_layer"
    bl_label = "Save Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save the active image"

    def execute(self, context):
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        image = active_layer.image
        with bpy.context.temp_override(**{'edit_image': bpy.data.images[image.name]}):
            bpy.ops.image.save_as('INVOKE_DEFAULT', copy=True)
        return {'FINISHED'}


class PAINTSYSTEM_OT_ResizeImage(Operator):
    bl_idname = "paint_system.resize_image"
    bl_label = "Resize Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Resize the active image"

    width: IntProperty(name="Width", default=1024)
    height: IntProperty(name="Height", default=1024)
    
    image_name: StringProperty()

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        image.scale(self.width, self.height)
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        self.width = image.size[0]
        self.height = image.size[1]
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "width")
        row.prop(self, "height")


class PAINTSYSTEM_OT_ClearImage(Operator):
    bl_idname = "paint_system.clear_image"
    bl_label = "Clear Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Clear the active image"
    
    image_name: StringProperty()

    def execute(self, context):
        if not self.image_name:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}
        image: bpy.types.Image = bpy.data.images.get(self.image_name)
        # Replace every pixel with a transparent pixel
        pixels = numpy.empty(len(image.pixels), dtype=numpy.float32)
        pixels[::4] = 0.0
        image.pixels.foreach_set(pixels)
        image.update()
        image.update_tag()
        return {'FINISHED'}


# https://projects.blender.org/blender/blender/src/branch/main/scripts/startup/bl_operators/image.py#L54
class PAINTSYSTEM_OT_ProjectEdit(Operator):
    """Edit a snapshot of the 3D Viewport in an external image editor"""
    bl_idname = "paint_system.project_edit"
    bl_label = "Project Edit"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import os

        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        if not active_layer.image:
            self.report({'ERROR'}, "Layer Does not have an image")
            return {'CANCELLED'}

        EXT = "png"  # could be made an option but for now ok

        for image in bpy.data.images:
            image.tag = True

        # opengl buffer may fail, we can't help this, but best report it.
        try:
            bpy.ops.paint.image_from_view()
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex))
            return {'CANCELLED'}

        image_new = None
        for image in bpy.data.images:
            if not image.tag:
                image_new = image
                break

        if not image_new:
            self.report({'ERROR'}, "Could not make new image")
            return {'CANCELLED'}

        filepath = os.path.basename(bpy.data.filepath)
        filepath = os.path.splitext(filepath)[0]
        # fixes <memory> rubbish, needs checking
        # filepath = bpy.path.clean_name(filepath)

        if bpy.data.is_saved:
            filepath = "//" + filepath
        else:
            filepath = os.path.join(bpy.app.tempdir, "project_edit")

        obj = context.object

        if obj:
            filepath += "_" + bpy.path.clean_name(obj.name)

        filepath_final = filepath + "." + EXT
        i = 0

        while os.path.exists(bpy.path.abspath(filepath_final)):
            filepath_final = filepath + "{:03d}.{:s}".format(i, EXT)
            i += 1

        image_new.name = bpy.path.basename(filepath_final)
        active_layer.edit_external_image = image_new

        image_new.filepath_raw = filepath_final  # TODO, filepath raw is crummy
        image_new.file_format = 'PNG'
        image_new.save()

        filepath_final = bpy.path.abspath(filepath_final)

        try:
            bpy.ops.image.external_edit(filepath=filepath_final)
        except RuntimeError as ex:
            self.report({'ERROR'}, str(ex))

        return {'FINISHED'}


def convert_straight_to_premultiplied(image_name):
    """
    Converts an image in Blender from Straight Alpha to Premultiplied Alpha.

    Args:
        image_name (str): The name of the Blender image to process.
    """
    # Get the image
    image = bpy.data.images.get(image_name)
    if image.filepath:
        image.reload()
    if not image:
        print(f"Image '{image_name}' not found.")
        return

    # Ensure the image has alpha channel
    if image.channels < 4:
        print(f"Image '{image_name}' does not have an alpha channel.")
        return

    # Get pixel data
    pixels = list(image.pixels)  # Copy pixel data
    num_pixels = len(pixels) // 4  # Each pixel has 4 channels (RGBA)

    # Modify pixels
    for i in range(num_pixels):
        r, g, b, a = pixels[i * 4: i * 4 + 4]
        r *= a
        g *= a
        b *= a
        pixels[i * 4: i * 4 + 4] = [r, g, b, a]

    # Apply modified pixel data back to the image
    image.pixels[:] = pixels  # Assign all at once for better performance
    image.update()

    print(f"Image '{image_name}' converted to Premultiplied Alpha.")


def convert_premultiplied_to_straight(image_name):
    """
    Converts an image in Blender from Premultiplied Alpha to Straight Alpha.

    Args:
        image_name (str): The name of the Blender image to process.
    """
    # Get the image
    image = bpy.data.images.get(image_name)
    if image.filepath:
        image.reload()
    print(image_name)
    if not image:
        print(f"Image '{image_name}' not found.")
        return

    # Ensure the image has alpha channel
    if image.channels < 4:
        print(f"Image '{image_name}' does not have an alpha channel.")
        return

    # Get pixel data
    pixels = list(image.pixels)  # Copy pixel data
    num_pixels = len(pixels) // 4  # Each pixel has 4 channels (RGBA)

    # Modify pixels
    for i in range(num_pixels):
        r, g, b, a = pixels[i * 4: i * 4 + 4]

        if a > 0:  # Avoid division by zero
            r /= a
            g /= a
            b /= a

        pixels[i * 4: i * 4 + 4] = [r, g, b, a]

    # Apply modified pixel data back to the image
    image.pixels = pixels  # Assign all at once for better performance
    image.update()  # Update the image

    print(f"Image '{image_name}' converted to Straight Alpha.")


def format_image(image_name):
    image = bpy.data.images.get(image_name)
    if image.filepath:
        image.reload()
    print(image_name)
    if not image:
        print(f"Image '{image_name}' not found.")
        return

    # Ensure the image has alpha channel
    if image.channels < 4:
        print(f"Image '{image_name}' does not have an alpha channel.")
        return

    # Get pixel data
    pixels = list(image.pixels)  # Copy pixel data
    num_pixels = len(pixels) // 4  # Each pixel has 4 channels (RGBA)

    # Modify pixels
    for i in range(num_pixels):
        r, g, b, a = pixels[i * 4: i * 4 + 4]
        
        print(r, g, b, a)

        if a == 0:
            r = 0
            g = 0
            b = 0

        pixels[i * 4: i * 4 + 4] = [r, g, b, a]

    # Apply modified pixel data back to the image
    image.pixels = pixels  # Assign all at once for better performance
    image.update()  # Update the image


class PAINTSYSTEM_OT_ProjectApply(Operator):
    """Project edited image back onto the object"""
    bl_idname = "paint_system.project_apply"
    bl_label = "Project Apply"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()
        return active_layer and active_layer.edit_external_image

    def execute(self, context):
        ps = PaintSystem(context)
        active_layer = ps.get_active_layer()

        current_image_editor = context.preferences.filepaths.image_editor
        editor_path = pathlib.Path(current_image_editor)
        app_name = editor_path.name
        external_image = active_layer.edit_external_image

        external_image_name = str(external_image.name)
        print(external_image_name)
        image = bpy.data.images.get((external_image_name, None))

        if external_image is None:
            self.report({'ERROR'}, rpt_(
                "Could not find image '{:s}'").format(external_image_name))
            return {'CANCELLED'}

        # if app_name == "CLIPStudioPaint.exe":
        #     convert_straight_to_premultiplied(external_image_name)

        active_layer.edit_external_image = None

        image.reload()
        # print("Reloading image")
        bpy.ops.paint.project_image(image=image.name)

        return {'FINISHED'}


class PAINTSYSTEM_OT_QuickEdit(Operator):
    bl_idname = "paint_system.quick_edit"
    bl_label = "Quick Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Quickly edit the active image"

    def execute(self, context):
        bpy.ops.paint_system.project_edit('INVOKE_DEFAULT')
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        current_image_editor = context.preferences.filepaths.image_editor
        image_paint = context.scene.tool_settings.image_paint
        if not current_image_editor:
            layout.prop(context.preferences.filepaths, "image_editor")
        else:
            editor_path = pathlib.Path(current_image_editor)
            app_name = editor_path.name
            layout.label(text=f"Open {app_name}", icon="EXPORT")
        box = layout.box()
        row = box.row()
        row.alignment = "CENTER"
        row.label(text="External Settings:", icon="TOOL_SETTINGS")
        row = box.row()
        row.prop(image_paint, "seam_bleed", text="Bleed")
        row.prop(image_paint, "dither", text="Dither")
        split = box.split()
        split.label(text="Screen Grab Size:")
        split.prop(image_paint, "screen_grab_size", text="")


class PAINTSYSTEM_OT_ApplyEdit(Operator):
    bl_idname = "paint_system.apply_edit"
    bl_label = "Apply Edit"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Apply the edit to the active image"

    def execute(self, context):
        bpy.ops.image.project_apply('INVOKE_DEFAULT')
        return {'FINISHED'}


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
    PAINTSYSTEM_OT_NewShaderLayer,
    PAITNSYSTEM_OT_NewNodeGroupLayer,
    PAINTSYSTEM_OT_NewMaskImage,
    PAINTSYSTEM_OT_DeleteMask,
    PAINTSYSTEM_OT_ExportActiveLayer,
    PAINTSYSTEM_OT_InvertColors,
    PAINTSYSTEM_OT_ResizeImage,
    PAINTSYSTEM_OT_ClearImage,
    PAINTSYSTEM_OT_ProjectEdit,
    PAINTSYSTEM_OT_ProjectApply,
    PAINTSYSTEM_OT_QuickEdit,
)

register, unregister = register_classes_factory(classes)
