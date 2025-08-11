import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, EnumProperty
from bpy.utils import register_classes_factory
from .utils import redraw_panel
from ..paintsystem.create import (
    create_image_layer,
    create_folder_layer,
    create_solid_color_layer,
    create_attribute_layer,
    create_adjustment_layer,
    create_shader_layer,
    create_node_group_layer,
    create_gradient_layer,
)
from ..utils import get_next_unique_name
from .common import PSContextMixin

class PAINTSYSTEM_OT_NewImage(PSContextMixin, Operator):
    """Create a new image layer"""
    bl_idname = "paint_system.new_image_layer"
    bl_label = "New Image Layer"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new image layer",
        default="New Image Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        img = bpy.data.images.new(
            name=self.layer_name, width=1024, height=1024, alpha=True)
        img.generated_color = (0, 0, 0, 0)
        layer = create_image_layer(ps_ctx.active_channel, img, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewFolder(PSContextMixin, Operator):
    """Create a new folder layer"""
    bl_idname = "paint_system.new_folder_layer"
    bl_label = "New Folder"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new folder",
        default="New Folder"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_folder_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewSolidColor(PSContextMixin, Operator):
    """Create a new solid color layer"""
    bl_idname = "paint_system.new_solid_color_layer"
    bl_label = "New Solid Color Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new solid color layer",
        default="New Solid Color Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_solid_color_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewAttribute(PSContextMixin, Operator):
    """Create a new attribute layer"""
    bl_idname = "paint_system.new_attribute_layer"
    bl_label = "New Attribute Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new attribute layer",
        default="New Attribute Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_attribute_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewAdjustment(PSContextMixin, Operator):
    """Create a new adjustment layer"""
    bl_idname = "paint_system.new_adjustment_layer"
    bl_label = "New Adjustment Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new adjustment layer",
        default="New Adjustment Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_adjustment_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewShader(PSContextMixin, Operator):
    """Create a new shader layer"""
    bl_idname = "paint_system.new_shader_layer"
    bl_label = "New Shader Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new shader layer",
        default="New Shader Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_shader_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewNodeGroup(PSContextMixin, Operator):
    """Create a new node group layer"""
    bl_idname = "paint_system.new_node_group_layer"
    bl_label = "New Node Group Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new node group layer",
        default="New Node Group Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_node_group_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewGradient(PSContextMixin, Operator):
    """Create a new gradient layer"""
    bl_idname = "paint_system.new_gradient_layer"
    bl_label = "New Gradient Layer"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new gradient layer",
        default="New Gradient Layer"
    )

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        layer = create_gradient_layer(ps_ctx.active_channel, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}

class PAINTSYSTEM_OT_DeleteItem(PSContextMixin, Operator):
    """Remove the active item"""
    bl_idname = "paint_system.delete_item"
    bl_label = "Remove Item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Remove the active item"

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_layer is not None

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        active_layer = ps_ctx.active_layer
        global_layer = ps_ctx.active_global_layer
        item_id = active_layer.id
        order = int(active_layer.order)
        parent_id = int(active_layer.parent_id)
        
        # In case Item type is GRADIENT
        # if item.type == 'GRADIENT':
        #     empty_object = None
        #     if item.node_tree:
        #         empty_object = item.node_tree.nodes["Texture Coordinate"].object
        #     if empty_object and empty_object.type == 'EMPTY':
        #         bpy.data.objects.remove(empty_object, do_unlink=True)
                
        if item_id != -1 and active_channel.remove_item_and_children(item_id):
            # Update active_index
            active_channel.normalize_orders()
            flattened = active_channel.flatten_hierarchy()
            for i, item in enumerate(active_channel.layers):
                if item.order == order and item.parent_id == parent_id:
                    active_channel.active_index = i
                    break

            active_channel.update_node_tree(context)
        active_channel.active_index = min(
            active_channel.active_index, len(active_channel.layers) - 1)
        
        redraw_panel(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        ps_ctx = self.ensure_context(context)
        layout = self.layout
        active_layer = ps_ctx.active_layer
        layout.label(
            text=f"Delete '{active_layer.name}' ?", icon='ERROR')
        layout.label(
            text="Click OK to delete, or cancel to keep the layer")


class PAINTSYSTEM_OT_MoveUp(PSContextMixin, Operator):
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
        ps_ctx = cls.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return False
        item_id = active_channel.get_id_from_flattened_index(active_channel.active_index)
        options = active_channel.get_movement_options(item_id, 'UP')
        return bool(options)

    def invoke(self, context, event):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        options = active_channel.get_movement_options(item_id, 'UP')
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
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}
        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        for op_id, label, props in active_channel.get_movement_menu_items(item_id, 'UP'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}
        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        if active_channel.execute_movement(item_id, 'UP', self.action):
            # Update active_index to follow the moved item
            # active_group.active_index = active_group.layers.values().index(self)

            active_channel.update_node_tree(context)

            # Force the UI to update
            redraw_panel(context)

            return {'FINISHED'}

        return {'CANCELLED'}


class PAINTSYSTEM_OT_MoveDown(PSContextMixin, Operator):
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
        ps_ctx = cls.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return False
        item_id = active_channel.get_id_from_flattened_index(active_channel.active_index)
        options = active_channel.get_movement_options(item_id, 'DOWN')
        return bool(options)

    def invoke(self, context, event):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        options = active_channel.get_movement_options(item_id, 'DOWN')
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
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        for op_id, label, props in active_channel.get_movement_menu_items(item_id, 'DOWN'):
            op = self_menu.layout.operator(op_id, text=label)
            for key, value in props.items():
                setattr(op, key, value)

    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        if not active_channel:
            return {'CANCELLED'}

        item_id = active_channel.get_id_from_flattened_index(
            active_channel.active_index)

        if active_channel.execute_movement(item_id, 'DOWN', self.action):
            # Update active_index to follow the moved item
            # active_group.active_index = active_group.items.values().index(self)

            active_channel.update_node_tree(context)

            # Force the UI to update
            redraw_panel(context)

            return {'FINISHED'}

        return {'CANCELLED'}


classes = (
    PAINTSYSTEM_OT_NewImage,
    PAINTSYSTEM_OT_NewFolder,
    PAINTSYSTEM_OT_NewSolidColor,
    PAINTSYSTEM_OT_NewAttribute,
    PAINTSYSTEM_OT_NewAdjustment,
    PAINTSYSTEM_OT_NewShader,
    PAINTSYSTEM_OT_NewNodeGroup,
    PAINTSYSTEM_OT_NewGradient,
    PAINTSYSTEM_OT_DeleteItem,
    PAINTSYSTEM_OT_MoveUp,
    PAINTSYSTEM_OT_MoveDown,
)

register, unregister = register_classes_factory(classes)