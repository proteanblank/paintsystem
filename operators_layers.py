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
from .paint_system import PaintSystem, ADJUSTMENT_ENUM, SHADER_ENUM
from .common import redraw_panel, get_object_uv_maps
import re
import copy

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


class PAINTSYSTEM_OT_NewGroup(Operator):
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
            ('NONE', "Manual", "Just add node group to material"),
            ('EXISTING', "Use Existing Setup", "Add to existing material setup"),
            ('STANDARD', "Standard", "Start off with a standard setup"),
            ('TRANSPARENT', "Transparent", "Start off with a transparent setup"),
            ('NORMAL', "Normal", "Start off with a normal painting setup"),
        ],
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

    use_paintsystem_uv: BoolProperty(
        name="Use Paint System UV",
        description="Use the Paint System UV Map",
        default=True
    )

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()

        if not mat:
            # Create a new material
            mat = bpy.data.materials.new("Material")
            mat.use_nodes = True
            ps.active_object.data.materials.append(mat)
        
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
                use_paintsystem_uv=self.use_paintsystem_uv,
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
        layout.prop(self, "group_name")
        row = layout.row(align=True)
        row.scale_y = 1.5
        # row.prop(self, "create_material_setup",
        #          text="Setup Material", icon='CHECKBOX_HLT' if self.create_material_setup else 'CHECKBOX_DEHLT')
        row.prop(self, "material_template", text="Template")
        layout.prop(self, "use_paintsystem_uv", text="Use Paint System UV")
        if self.material_template in ['STANDARD', 'TRANSPARENT']:
            layout.prop(self, "use_alpha_blend", text="Use Alpha Blend")
            layout.prop(self, "use_backface_culling",
                        text="Use Backface Culling")
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


class PAINTSYSTEM_OT_NewImage(Operator):
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
        ],
        default='1024'
    )
    uv_map_mode: EnumProperty(
        name="UV Map",
        items=[
            ('PAINT_SYSTEM', "Paint System UV", "Use the Paint System UV Map"),
            ('OPEN', "Use Existing", "Open an existing UV Map"),
        ]
    )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )
    disable_popup: BoolProperty(default=False)

    def execute(self, context):
        ps = PaintSystem(context)
        ps.get_material_settings().use_paintsystem_uv = self.uv_map_mode == "PAINT_SYSTEM"
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        if self.uv_map_mode == 'PAINT_SYSTEM':
            if 'PaintSystemUVMap' not in [uvmap[0] for uvmap in get_object_uv_maps(self, context)]:
                bpy.ops.paint_system.create_new_uv_map(
                    'INVOKE_DEFAULT', uv_map_name="PaintSystemUVMap")
            self.uv_map_name = "PaintSystemUVMap"
        elif not self.uv_map_name:
            self.report({'ERROR'}, "No UV Map selected")
            return {'CANCELLED'}
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
        ps = PaintSystem(context)
        self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
        ).use_paintsystem_uv else 'OPEN'
        self.name = self.get_next_image_name(context)
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "image_resolution", expand=True)
        layout.label(text="UV Map")
        layout.prop(self, "uv_map_mode", expand=True)
        if self.uv_map_mode == 'OPEN':
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

    uv_map_mode: EnumProperty(
        name="UV Map",
        items=[
            ('PAINT_SYSTEM', "Paint System UV", "Use the Paint System UV Map"),
            ('OPEN', "Use Existing", "Open an existing UV Map"),
        ]
    )

    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )

    def execute(self, context):
        ps = PaintSystem(context)
        ps.get_material_settings().use_paintsystem_uv = self.uv_map_mode == "PAINT_SYSTEM"
        image = bpy.data.images.load(self.filepath, check_existing=True)
        if self.uv_map_mode == 'PAINT_SYSTEM':
            if 'PaintSystemUVMap' not in [uvmap[0] for uvmap in get_object_uv_maps(self, context)]:
                bpy.ops.paint_system.create_new_uv_map(
                    'INVOKE_DEFAULT', uv_map_name="PaintSystemUVMap")
            self.uv_map_name = "PaintSystemUVMap"
        elif not self.uv_map_name:
            self.report({'ERROR'}, "No UV Map selected")
            return {'CANCELLED'}
        ps.create_image_layer(image.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
        ).use_paintsystem_uv else 'OPEN'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "uv_map_mode", expand=True)
        if self.uv_map_mode == 'OPEN':
            layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_OpenExistingImage(Operator):
    bl_idname = "paint_system.open_existing_image"
    bl_label = "Open Existing Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Open an image from the existing images"

    image_name: StringProperty()

    uv_map_mode: EnumProperty(
        name="UV Map",
        items=[
            ('PAINT_SYSTEM', "Paint System UV", "Use the Paint System UV Map"),
            ('OPEN', "Use Existing", "Open an existing UV Map"),
        ]
    )

    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )

    def execute(self, context):
        ps = PaintSystem(context)
        ps.get_material_settings().use_paintsystem_uv = self.uv_map_mode == "PAINT_SYSTEM"
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        image = bpy.data.images.get(self.image_name)
        if not image:
            self.report({'ERROR'}, "Image not found")
            return {'CANCELLED'}
        if self.uv_map_mode == 'PAINT_SYSTEM':
            if 'PaintSystemUVMap' not in [uvmap[0] for uvmap in get_object_uv_maps(self, context)]:
                bpy.ops.paint_system.create_new_uv_map(
                    'INVOKE_DEFAULT', uv_map_name="PaintSystemUVMap")
            self.uv_map_name = "PaintSystemUVMap"
        elif not self.uv_map_name:
            self.report({'ERROR'}, "No UV Map selected")
            return {'CANCELLED'}
        ps.create_image_layer(self.image_name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        ps = PaintSystem(context)
        self.uv_map_mode = 'PAINT_SYSTEM' if ps.get_material_settings(
        ).use_paintsystem_uv else 'OPEN'
        self.image_name = bpy.data.images[0].name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "image_name", bpy.data,
                           "images", text="Image")
        layout.prop(self, "uv_map_mode", expand=True)
        if self.uv_map_mode == 'OPEN':
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
)

register, unregister = register_classes_factory(classes)
