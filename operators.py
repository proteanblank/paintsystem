import bpy

from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
)

from bpy.types import Operator, Context

from bpy.utils import register_classes_factory
from .paint_system import PaintSystem, get_brushes_from_library
from mathutils import Vector
import re


def redraw_panel(self, context: Context):
    # Force the UI to update
    if context.area:
        context.area.tag_redraw()

# bpy.types.Image.pack
# -------------------------------------------------------------------
# Group Operators
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_SaveFileAndImages(Operator):
    """Save all images in the active group"""
    bl_idname = "paint_system.save_file_and_images"
    bl_label = "Save File and Images"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save all images and the blend file"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.get_active_group() and ps.get_active_group().flatten_hierarchy()

    def execute(self, context):
        # ps = PaintSystem(context)
        # flattened = ps.get_active_group().flatten_hierarchy()
        # for item, _ in flattened:
        #     if item.image:
        #         item.image.pack()
        bpy.ops.wm.save_mainfile()
        return {'FINISHED'}


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
    bl_description = "Add a new group"
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
        default=False
    )

    material_template: EnumProperty(
        name="Template",
        items=[
            ('NONE', "None", "Just add node group to material"),
            ('COLOR', "Color", "Color only"),
            ('COLORALPHA', "Color Alpha", "Color and Alpha"),
        ],
        default='COLORALPHA'
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
        ps.create_solid_color_layer("Paper Color", (1, 1, 1, 1))

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
        self.create_material_setup = not groups
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
    bl_description = "Delete the active group"
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


class PAINTSYSTEM_OT_TogglePaintMode(Operator):
    bl_idname = "paint_system.toggle_paint_mode"
    bl_label = "Toggle Paint Mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Toggle between texture paint and object mode"

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT', toggle=True)

        if bpy.context.object.mode == 'TEXTURE_PAINT':
            # Change shading mode
            if bpy.context.space_data.shading.type != 'RENDERED':
                bpy.context.space_data.shading.type = 'RENDERED'

            # if ps.preferences.unified_brush_color:
            #     bpy.context.scene.tool_settings.unified_paint_settings.use_unified_color = True
            # if ps.preferences.unified_brush_size:
            #     bpy.context.scene.tool_settings.unified_paint_settings.use_unified_size = True

        return {'FINISHED'}


class PAINTSYSTEM_OT_AddPresetBrushes(Operator):
    bl_idname = "paint_system.add_preset_brushes"
    bl_label = "Import Paint System Brushes"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Add preset brushes to the active group"

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        get_brushes_from_library()

        return {'FINISHED'}


def set_active_panel_category(category, area_type):
    areas = (
        area for win in bpy.context.window_manager.windows for area in win.screen.areas if area.type == area_type)
    for a in areas:
        for r in a.regions:
            if r.type == 'UI':
                if r.width == 1:
                    with bpy.context.temp_override(area=a):
                        bpy.ops.wm.context_toggle(
                            data_path='space_data.show_region_ui')
                try:
                    print(r.active_panel_category)
                    if r.active_panel_category != category:
                        r.active_panel_category = category
                        a.tag_redraw()
                except NameError as e:
                    raise e


class PAINTSYSTEM_OT_SetActivePanel(Operator):
    bl_idname = "paint_system.set_active_panel"
    bl_label = "Set Active Panel"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Set active panel"
    bl_options = {'INTERNAL'}

    category: StringProperty()

    area_type: StringProperty(
        default='VIEW_3D',
    )

    def execute(self, context: Context):
        print(self.category, self.area_type)
        set_active_panel_category(self.category, self.area_type)
        return {'FINISHED'}


class PAINTSYSTEM_OT_PaintModeSettings(Operator):
    bl_label = "Paint Mode Settings"
    bl_idname = "paint_system.paint_mode_menu"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Paint mode settings"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        col = row.column()
        unified_settings = bpy.context.scene.tool_settings.unified_paint_settings
        col.prop(unified_settings, "use_unified_color", text="Unified Color")
        col.prop(unified_settings, "use_unified_size", text="Unified Size")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_popup(self, width=200)
        return {'FINISHED'}


class PAINTSYSTEM_OT_ToggleClip(Operator):
    bl_idname = "paint_system.toggle_clip"
    bl_label = "Toggle Clipping"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Toggle layer clipping"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        clip_mix_node = ps.find_clip_mix_node()
        return clip_mix_node

    def execute(self, context):
        ps = PaintSystem(context)
        clip_mix_node = ps.find_clip_mix_node()

        clip_mix_node.inputs[0].default_value = not clip_mix_node.inputs[0].default_value

        return {'FINISHED'}


def get_uv_maps_names(self, context: Context):
    return [(uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers]


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
        items=get_uv_maps_names
    )

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        image = bpy.data.images.new(
            name=f"PaintSystem_{active_group.next_id}",
            width=int(self.image_resolution),
            height=int(self.image_resolution),
            alpha=True,
        )
        # image.pack()
        image.generated_color = (0, 0, 0, 0)
        ps.create_image_layer(self.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.name = self.get_next_image_name(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "image_resolution", expand=True)
        # layout.prop(self, "high_bit_float")
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
        items=get_uv_maps_names
    )

    def execute(self, context):
        ps = PaintSystem(context)
        image = bpy.data.images.load(self.filepath, check_existing=True)
        # image.pack()
        ps.create_image_layer(image.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_OpenExistingImage(Operator):
    bl_idname = "paint_system.open_existing_image"
    bl_label = "Open Existing Image"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Open an image from the existing images"

    image_name: StringProperty()

    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_uv_maps_names
    )

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}
        image = bpy.data.images.get(self.image_name)
        if not image:
            return {'CANCELLED'}
        ps.create_image_layer(self.image_name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.image_name = bpy.data.images[0].name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "image_name", bpy.data,
                           "images", text="Image")
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

    def execute(self, context):
        ps = PaintSystem(context)
        ps.create_solid_color_layer(self.name, self.color)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.name = self.get_next_image_name(context)
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
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_name")


# -------------------------------------------------------------------
# Template Material Creation
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_CreateTemplateSetup(Operator):
    bl_idname = "paint_system.create_template_setup"
    bl_label = "Create Template Setup"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Create a template material setup for painting"

    template: EnumProperty(
        name="Template",
        items=[
            ('NONE', "None", "Just add node group to material"),
            ('COLOR', "Color", "Color only"),
            ('COLORALPHA', "Color Alpha", "Color and Alpha"),
        ],
        default='COLORALPHA'
    )

    disable_popup: BoolProperty(
        name="Disable Popup",
        description="Disable popup",
        default=False
    )

    use_alpha_blend: BoolProperty(
        name="Use Alpha Blend",
        description="Use alpha blend instead of alpha clip",
        default=True
    )

    disable_show_backface: BoolProperty(
        name="Disable Show Backface",
        description="Disable Show Backface",
        default=True
    )

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.get_active_group()

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        mat = ps.get_active_material()
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Get position of the rightmost node
        position = Vector((0, 0))
        for node in nodes:
            if node.location.x > position[0]:
                position = node.location

        match self.template:
            case 'NONE':
                node_group = nodes.new('ShaderNodeGroup')
                node_group.node_tree = active_group.node_tree
                node_group.location = position + Vector((200, 0))

            case 'COLOR':
                node_group = nodes.new('ShaderNodeGroup')
                node_group.node_tree = active_group.node_tree
                node_group.location = position + Vector((200, 0))
                vector_scale_node = nodes.new('ShaderNodeVectorMath')
                vector_scale_node.operation = 'SCALE'
                vector_scale_node.location = position + Vector((400, 0))
                output_node = nodes.new('ShaderNodeOutputMaterial')
                output_node.location = position + Vector((600, 0))
                output_node.is_active_output = True
                links.new(
                    vector_scale_node.inputs['Vector'], node_group.outputs['Color'])
                links.new(
                    vector_scale_node.inputs['Scale'], node_group.outputs['Alpha'])
                links.new(output_node.inputs['Surface'],
                          vector_scale_node.outputs['Vector'])

            case 'COLORALPHA':
                node_group = nodes.new('ShaderNodeGroup')
                node_group.node_tree = active_group.node_tree
                node_group.location = position + Vector((200, 0))
                emission_node = nodes.new('ShaderNodeEmission')
                emission_node.location = position + Vector((400, -100))
                transparent_node = nodes.new('ShaderNodeBsdfTransparent')
                transparent_node.location = position + Vector((400, 100))
                shader_mix_node = nodes.new('ShaderNodeMixShader')
                shader_mix_node.location = position + Vector((600, 0))
                output_node = nodes.new('ShaderNodeOutputMaterial')
                output_node.location = position + Vector((800, 0))
                output_node.is_active_output = True
                links.new(
                    emission_node.inputs['Color'], node_group.outputs['Color'])
                links.new(shader_mix_node.inputs[0],
                          node_group.outputs['Alpha'])
                links.new(shader_mix_node.inputs[1],
                          transparent_node.outputs['BSDF'])
                links.new(shader_mix_node.inputs[2],
                          emission_node.outputs['Emission'])
                links.new(output_node.inputs['Surface'],
                          shader_mix_node.outputs['Shader'])
                if self.use_alpha_blend:
                    mat.blend_method = 'BLEND'
                if self.disable_show_backface:
                    mat.show_transparent_back = False

        return {'FINISHED'}

    def invoke(self, context, event):
        if self.disable_popup:
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "template")
        if self.template == 'COLORALPHA':
            layout.prop(self, "use_alpha_blend")
            layout.prop(self, "disable_show_backface")

# -------------------------------------------------------------------
# For testing
# -------------------------------------------------------------------


# class PAINTSYSTEM_OT_Test(Operator):
#     """Test importing node groups from library"""
#     bl_idname = "paint_system.test"
#     bl_label = "Test"

#     node_name: StringProperty()

#     def execute(self, context):
#         return {'FINISHED'}

#     def invoke(self, context, event):
#         return context.window_manager.invoke_props_dialog(self)

#     def draw(self, context):
#         layout = self.layout
#         layout.prop(self, "node_name")


classes = (
    PAINTSYSTEM_OT_SaveFileAndImages,
    PAINTSYSTEM_OT_DuplicateGroupWarning,
    PAINTSYSTEM_OT_NewGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_RenameGroup,
    PAINTSYSTEM_OT_DeleteItem,
    PAINTSYSTEM_OT_MoveUp,
    PAINTSYSTEM_OT_MoveDown,
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_AddPresetBrushes,
    PAINTSYSTEM_OT_SetActivePanel,
    PAINTSYSTEM_OT_PaintModeSettings,
    PAINTSYSTEM_OT_ToggleClip,
    PAINTSYSTEM_OT_NewImage,
    PAINTSYSTEM_OT_OpenImage,
    PAINTSYSTEM_OT_OpenExistingImage,
    PAINTSYSTEM_OT_NewSolidColor,
    PAINTSYSTEM_OT_NewFolder,
    PAINTSYSTEM_OT_CreateTemplateSetup,
    # PAINTSYSTEM_OT_Test,
)

register, unregister = register_classes_factory(classes)
