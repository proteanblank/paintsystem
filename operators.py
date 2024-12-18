import bpy

from bpy.props import (
    BoolProperty,
    StringProperty,
    PointerProperty,
    EnumProperty,
)

from bpy.types import Operator, Image, NodeTree, Context

from bpy.utils import register_classes_factory
from .common import get_active_group, get_active_layer, redraw_panel, get_highest_number_with_prefix, on_item_delete, get_uv_maps_names
from .node_manager import get_node_from_library
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
        node_tree = bpy.data.node_groups.new(
            name=f"PS_GRP {self.group_name} (MAT: {mat.name})", type='ShaderNodeTree')
        new_group.node_tree = node_tree
        new_group.update_node_tree()

        # Force the UI to update
        redraw_panel(self, context)

        # Set the active group to the newly created one
        mat.paint_system.active_group = str(len(mat.paint_system.groups) - 1)

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
        mat = context.active_object.active_material
        return mat and hasattr(mat, "paint_system") and len(mat.paint_system.groups) > 0

    def execute(self, context):
        mat = context.active_object.active_material
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}

        use_node_tree = False
        for node in mat.node_tree.nodes:
            if node.type == 'GROUP' and node.node_tree == active_group.node_tree:
                use_node_tree = True
                break

        # 2 users: 1 for the material node tree, 1 for the datablock
        if active_group.node_tree and active_group.node_tree.users <= 1 + use_node_tree:
            bpy.data.node_groups.remove(active_group.node_tree)

        for item, _ in active_group.flatten_hierarchy():
            on_item_delete(item)

        active_group_idx = int(mat.paint_system.active_group)
        mat.paint_system.groups.remove(active_group_idx)

        if mat.paint_system.active_group:
            mat.paint_system.active_group = str(
                min(active_group_idx, len(mat.paint_system.groups) - 1))

        # Force the UI to update
        redraw_panel(self, context)

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


class PAINTSYSTEM_OT_RenameGroup(Operator):
    bl_idname = "paint_system.rename_group"
    bl_label = "Rename Group"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}
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
        active_layer = get_active_layer(cls, context)
        return active_layer

    def execute(self, context):
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}

        active_layer = get_active_layer(self, context)
        if not active_layer:
            return {'CANCELLED'}

        # item_id = active_group.get_id_from_flattened_index(
        #     active_group.active_index)

        # for item in active_group.items:
        #     if item.id == item_id or item.parent_id == item_id:
        #         delete_item(self, context, item)

        # return {'FINISHED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        if item_id != -1 and active_group.remove_item_and_children(item_id, on_item_delete):
            # Update active_index
            flattened = active_group.flatten_hierarchy()
            active_group.active_index = min(
                active_group.active_index, len(flattened) - 1)

            active_group.update_node_tree()

            # Force the UI to update
            redraw_panel(self, context)

            return {'FINISHED'}

        return {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        active_layer = get_active_layer(self, context)
        if not active_layer:
            return {'CANCELLED'}
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

    def invoke(self, context, event):
        active_group = get_active_group(self, context)
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
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}
        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        for op_id, label, props in active_group.get_movement_menu_items(item_id, 'UP'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        active_group = get_active_group(self, context)
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

    def invoke(self, context, event):
        active_group = get_active_group(self, context)
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
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}

        item_id = active_group.get_id_from_flattened_index(
            active_group.active_index)

        for op_id, label, props in active_group.get_movement_menu_items(item_id, 'DOWN'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        active_group = get_active_group(self, context)
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

# -------------------------------------------------------------------
# Image Functions and Operators
# -------------------------------------------------------------------


def create_folder_node_group(name: str, material_name: str) -> NodeTree:
    folder_template = get_node_from_library('_PS_Folder_Template')
    folder_nt = folder_template.copy()
    folder_nt.name = f"PS {name} (MAT: {material_name})"
    return folder_nt


def create_layer_node_group(name: str, material_name: str, image: Image, uv_map_name: str = None) -> NodeTree:
    layer_template = get_node_from_library('_PS_Layer_Template')
    layer_nt = layer_template.copy()
    layer_nt.name = f"PS {name} (MAT: {material_name})"
    # Find the image texture node
    image_texture_node = None
    for node in layer_nt.nodes:
        if node.type == 'TEX_IMAGE':
            image_texture_node = node
            break
    uv_map_node = None
    # Find UV Map node
    for node in layer_nt.nodes:
        print(node.type)
        if node.type == 'UVMAP':
            uv_map_node = node
            break
    # use uv_map_name or default to first uv map
    if uv_map_name:
        uv_map_node.uv_map = uv_map_name
    else:
        uv_map_node.uv_map = bpy.context.object.data.uv_layers[0].name
    image_texture_node.image = image
    return layer_nt


def create_new_layer_with_image(self, context: Context, image: Image, uv_map_name: str):
    # image.use_fake_user = True
    active_group = get_active_group(self, context)
    if not active_group:
        return {'CANCELLED'}

    # Get insertion position
    parent_id, insert_order = active_group.get_insertion_data()

    flattened = active_group.flatten_hierarchy()
    number = get_highest_number_with_prefix(
        'Image', [item[0].name for item in flattened]) + 1
    layer_name = f"Image {number}"

    # Adjust existing items' order
    active_group.adjust_sibling_orders(parent_id, insert_order)

    active_material = context.active_object.active_material

    node_tree = create_layer_node_group(
        layer_name, active_material.name, image, uv_map_name)

    # Create the new item
    new_id = active_group.add_item(
        name=layer_name,
        item_type='IMAGE',
        parent_id=parent_id,
        order=insert_order,
        image=image,
        node_tree=node_tree,
    )

    # Update active index
    if new_id != -1:
        flattened = active_group.flatten_hierarchy()
        for i, (item, _) in enumerate(flattened):
            if item.id == new_id:
                active_group.active_index = i
                break

    # Force the UI to update
    redraw_panel(self, context)
    return {'FINISHED'}


class PAINTSYSTEM_OT_TogglePaintMode(Operator):
    bl_idname = "paint_system.toggle_paint_mode"
    bl_label = "Toggle Paint Mode"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        active_group = get_active_group(self, context)
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
        # context.mesh.uv_layers.new(name=self.name)
        # Create the new image
        active_group = get_active_group(self, context)
        image = bpy.data.images.new(
            name=f"PaintSystem_{active_group.next_id}",
            width=int(self.image_resolution),
            height=int(self.image_resolution),
            alpha=True,
        )
        image.generated_color = (0, 0, 0, 0)
        create_new_layer_with_image(self, context, image, self.uv_map_name)
        active_group.update_node_tree()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
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

    def execute(self, context):
        # Create the new image
        active_group = get_active_group(self, context)
        image = bpy.data.images.load(self.filepath, check_existing=True)
        create_new_layer_with_image(self, context, image)
        active_group.update_node_tree()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PAINTSYSTEM_OT_AddFolder(Operator):
    bl_idname = "paint_system.add_folder"
    bl_label = "Add Folder"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}

        mat = context.active_object.active_material

        # Get insertion position
        parent_id, insert_order = active_group.get_insertion_data()

        # Adjust existing items' order
        active_group.adjust_sibling_orders(parent_id, insert_order)

        flattened = active_group.flatten_hierarchy()
        number = get_highest_number_with_prefix(
            'Folder', [item[0].name for item in flattened]) + 1

        name = f"Folder {number}"

        node_tree = create_folder_node_group(name, mat.name)

        # Create the new item
        new_id = active_group.add_item(
            name=name,
            item_type='FOLDER',
            parent_id=parent_id,
            order=insert_order,
            node_tree=node_tree
        )

        # Update active index
        if new_id != -1:
            flattened = active_group.flatten_hierarchy()
            for i, (item, _) in enumerate(flattened):
                if item.id == new_id:
                    active_group.active_index = i
                    break

        active_group.update_node_tree()

        # Force the UI to update
        redraw_panel(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class IMAGE_OT_SelectImage(Operator):
    bl_idname = "image.select_image"
    bl_label = "Select Image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    image: PointerProperty(type=Image)

    def execute(self, context):
        image_paint = context.scene.tool_settings.image_paint
        image_paint.canvas = self.image
        if image_paint.mode == 'MATERIAL':
            image_paint.mode = 'IMAGE'

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

    def execute(self, context):
        active_group = get_active_group(self, context)
        if not active_group:
            return {'CANCELLED'}

        mat = context.active_object.active_material
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
