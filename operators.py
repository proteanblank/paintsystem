import bpy

from bpy.props import (
    BoolProperty,
    StringProperty,
    PointerProperty,
    EnumProperty,
)

from bpy.types import Operator, Image, NodeTree, Context

from bpy.utils import register_classes_factory
from .common import redraw_panel, get_highest_number_with_prefix, get_uv_maps_names, get_node_from_library
from .paint_system import PaintSystem
from mathutils import Vector

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
        ps = PaintSystem(context)
        mat = ps.active_material
        if not mat or not hasattr(mat, "paint_system"):
            return {'CANCELLED'}

        # Check for duplicate names
        for group in mat.paint_system.groups:
            if group.name == self.group_name:
                bpy.ops.paint_system.duplicate_group_warning(
                    'INVOKE_DEFAULT', group_name=self.group_name)
                return {'CANCELLED'}

        ps.add_group(self.group_name)

        # Force the UI to update
        redraw_panel(self, context)

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
        ps = PaintSystem(context)
        mat = ps.active_material
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
        active_group = ps.active_group
        layout = self.layout
        layout.label(
            text=f"Delete '{active_group.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the group")


class PAINTSYSTEM_OT_RenameGroup(Operator):
    bl_idname = "paint_system.rename_group"
    bl_label = "Rename Group"

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.active_group
        return active_group

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        ps = PaintSystem(context)
        active_group = ps.active_group
        layout.prop(active_group, "name")


# -------------------------------------------------------------------
# Layers Operators
# -------------------------------------------------------------------
class PAINTSYSTEM_OT_DeleteItem(Operator):
    """Remove the active item"""
    bl_idname = "paint_system.delete_item"
    bl_label = "Remove Item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.active_layer and ps.active_group

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
        active_layer = ps.active_layer
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

    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        active_group = ps.active_group
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)
        options = active_group.get_movement_options(item_id, 'UP')
        return active_group and options

    def invoke(self, context, event):
        ps = PaintSystem(context)
        active_group = ps.active_group
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
        active_group = ps.active_group
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
        active_group = ps.active_group
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
        active_group = ps.active_group
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)
        options = active_group.get_movement_options(item_id, 'DOWN')
        return active_group and options

    def invoke(self, context, event):
        ps = PaintSystem(context)
        active_group = ps.active_group
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
        active_group = ps.active_group
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
        active_group = ps.active_group
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

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.active_group
        if not active_group:
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT', toggle=True)

        # Change shading mode
        if bpy.context.space_data.shading.type in ['SOLID', 'WIREFRAME']:
            bpy.context.space_data.shading.type = 'MATERIAL'

        return {'FINISHED'}


class PAINTSYSTEM_OT_NewImage(Operator):
    bl_idname = "paint_system.new_image"
    bl_label = "New Image"
    bl_options = {'REGISTER', 'UNDO'}

    def get_next_image_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        flattened = ps.active_group.flatten_hierarchy()
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
    high_bit_float: BoolProperty(
        name="High Bit Float",
        description="Use 32-bit float instead of 16-bit",
        default=False
    )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_uv_maps_names
    )

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.active_group
        image = bpy.data.images.new(
            name=f"PaintSystem_{active_group.next_id}",
            width=int(self.image_resolution),
            height=int(self.image_resolution),
            alpha=True,
        )
        image.generated_color = (0, 0, 0, 0)
        ps.create_image_layer(self.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        self.name = self.get_next_image_name(context)
        layout.prop(self, "name")
        layout.prop(self, "image_resolution", expand=True)
        layout.prop(self, "high_bit_float")
        layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_OpenImage(Operator):
    bl_idname = "paint_system.open_image"
    bl_label = "Open Image"
    bl_options = {'REGISTER', 'UNDO'}

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
        ps.create_image_layer(self.name, image, self.uv_map_name)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_AddFolder(Operator):
    bl_idname = "paint_system.add_folder"
    bl_label = "Add Folder"
    bl_options = {'REGISTER', 'UNDO'}

    def get_next_folder_name(self, context: Context) -> str:
        ps = PaintSystem(context)
        flattened = ps.active_group.flatten_hierarchy()
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
        active_group = ps.active_group
        return active_group

    def execute(self, context):
        ps = PaintSystem(context)
        ps.create_folder(self.folder_name)

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        self.folder_name = self.get_next_folder_name(context)
        layout.prop(self, "folder_name")

# -------------------------------------------------------------------
# Template Material Creation
# -------------------------------------------------------------------


class PAINTSYSTEM_OT_CreateTemplateSetup(Operator):
    bl_idname = "paint_system.create_template_setup"
    bl_label = "Create Template Setup"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    template: EnumProperty(
        items=[
            ('COLOR', "Color", "Color only"),
            ('COLORALPHA', "Color Alpha", "Color and Alpha"),
        ],
        default='COLOR'
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
        return ps.active_group

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.active_group
        mat = ps.active_material
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Get position of the rightmost node
        position = Vector((0, 0))
        for node in nodes:
            if node.location.x > position[0]:
                position = node.location

        match self.template:
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


class PAINTSYSTEM_OT_Test(Operator):
    """Test importing node groups from library"""
    bl_idname = "paint_system.test"
    bl_label = "Test"

    node_name: StringProperty()

    def execute(self, context):
        node = get_node_from_library(self.node_name)
        if node:
            print(f"Found node: {node.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "node_name")


classes = (
    PAINTSYSTEM_OT_DuplicateGroupWarning,
    PAINTSYSTEM_OT_AddGroup,
    PAINTSYSTEM_OT_DeleteGroup,
    PAINTSYSTEM_OT_RenameGroup,
    PAINTSYSTEM_OT_DeleteItem,
    PAINTSYSTEM_OT_MoveUp,
    PAINTSYSTEM_OT_MoveDown,
    PAINTSYSTEM_OT_TogglePaintMode,
    PAINTSYSTEM_OT_NewImage,
    PAINTSYSTEM_OT_OpenImage,
    PAINTSYSTEM_OT_AddFolder,
    PAINTSYSTEM_OT_CreateTemplateSetup,
    PAINTSYSTEM_OT_Test,
)

register, unregister = register_classes_factory(classes)
