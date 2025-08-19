import bpy
from bpy.types import Operator, Context
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty, PointerProperty
from bpy.utils import register_classes_factory
from .utils import redraw_panel, intern_enum_items
from ..paintsystem.create import (
    add_global_layer,
    add_global_layer_to_channel,
)
from ..paintsystem.data import GRADIENT_TYPE_ENUM, ADJUSTMENT_TYPE_ENUM, COORDINATE_TYPE_ENUM, ATTRIBUTE_TYPE_ENUM, get_global_layer, is_global_layer_linked
from ..utils import get_next_unique_name
from .common import PSContextMixin, scale_content, get_icon, MultiMaterialOperator

def get_object_uv_maps(self, context: Context):
    items = [
        (uv_map.name, uv_map.name, "") for uv_map in context.object.data.uv_layers
    ]
    return intern_enum_items(items)

# class PAINTSYSTEM_OT_NewLayer(PSContextMixin, MultiMaterialOperator):
#     """Create a layer"""
#     bl_idname = "paint_system.new_layer"
#     bl_label = "New Layer"
#     bl_options = {'REGISTER', 'UNDO'}
    
#     @classmethod
#     def poll(cls, context):
#         ps_ctx = cls.ensure_context(context)
#         return ps_ctx.active_channel is not None
    
#     coord_type: EnumProperty(
#         name="AUTO",
#         items=COORDINATE_TYPE_ENUM
#     )
#     uv_map_name: EnumProperty(
#         name="UV Map",
#         items=get_object_uv_maps
#     )
    
#     # layer_type: EnumProperty(
#     #     name="Layer Type",
#     #     description="Type of layer to create",
#     #     items=LAYER_TYPE_ENUM,
#     #     default='IMAGE',
#     # )

#     layer_name: StringProperty(
#         name="Layer Name",
#         description="Name of the new image layer",
#         default="Image Layer"
#     )
    
#     image: PointerProperty(
#         name="Image",
#         description="Image to use for the layer",
#         type=bpy.types.Image,
#         default=None,
#     )
    
#     image_add_type: EnumProperty(
#         name="Image Add Type",
#         description="How to add the image layer",
#         items=[
#             ('NEW', "New Image", "Create a new image layer"),
#             ('IMPORT', "Import Image", "Import an image from file"),
#             ('EXISTING', "Existing Image", "Use an existing image from the blend file"),
#         ],
#         default='NEW',
#     )
    
#     image_width: IntProperty(
#         name="Image Width",
#         description="Width of the new image",
#         default=1024,
#         min=1,
#     )
    
#     image_height: IntProperty(
#         name="Image Height",
#         description="Height of the new image",
#         default=1024,
#         min=1,
#     )
    
#     filepath: StringProperty(
#         subtype='FILE_PATH',
#     )

#     filter_glob: StringProperty(
#         default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
#         options={'HIDDEN'}
#     )
    
#     gradient_type: EnumProperty(
#         name="Gradient Type",
#         description="Type of gradient to create",
#         items=GRADIENT_ENUM,
#         default='LINEAR',
#     )
    
#     adjustment_type: EnumProperty(
#         name="Adjustment Type",
#         description="Type of adjustment to create",
#         items=ADJUSTMENT_ENUM,
#         default='ShaderNodeBrightContrast',
#     )
    
#     attribute_type: EnumProperty(
#         name="Attribute Type",
#         items=[
#             ('GEOMETRY', "Geometry", "Geometry"),
#             ('OBJECT', "Object", "Object"),
#             ('INSTANCER', "Instancer", "Instancer"),
#             ('VIEW_LAYER', "View Layer", "View Layer"),],
#     )

#     def select_uv_ui(self, layout):
#         layout.label(text="UV Map", icon='UV')
#         row = layout.row(align=True)
#         row.prop(self, "uv_map_mode", expand=True)
#         layout.prop(self, "uv_map_name", text="")

#     def invoke(self, context, event):
#         if self.layer_type == 'IMAGE' and self.image_add_type == 'IMPORT':
#             context.window_manager.fileselect_add(self)
#             return {'RUNNING_MODAL'}
#         if self.layer_type in {'FOLDER', 'ADJUSTMENT', 'SHADER', 'GRADIENT'}:
#             return self.execute(context)
#         return context.window_manager.invoke_props_dialog(self)
    
#     def draw(self, context):
#         # Show coordinate selection
#         layout = self.layout
#         if self.layer_type == 'IMAGE':
#             layout.prop(self, "coord_type", text="Coordinate Type")
#         match self.layer_type:
#             case 'IMAGE':
#                 if self.coord_type == 'UV':
#                     self.select_uv_ui(layout)
#                 if self.image_add_type == 'NEW':
#                     box = layout.box()
#                     box.prop(self, "image_width")
#                     box.prop(self, "image_height")
    
#     def process_material(self, context):
#         ps_ctx = self.ensure_context(context)
#         channel = ps_ctx.active_channel
#         if not channel:
#             self.report({'ERROR'}, "No active channel found")
#             return False
#         global_layer = add_global_layer(self.layer_type, self.layer_name)
#         match self.layer_type:
#             case 'IMAGE':
#                 match self.image_add_type:
#                     case 'NEW':
#                         image = bpy.data.images.new(
#                             name=self.layer_name, width=self.image_width, height=self.image_height, alpha=True)
#                         image.generated_color = (0, 0, 0, 0)
#                     case 'IMPORT':
#                         image = bpy.data.images.load(self.filepath, check_existing=True)
#                         if not image:
#                             self.report({'ERROR'}, "Failed to load image")
#                             return False
#                     case 'EXISTING':
#                         image = self.image
#                         if not image:
#                             self.report({'ERROR'}, "No image selected")
#                             return False
#                 global_layer.image = image
#             # case 'SOLID_COLOR':
                
#         layer = add_global_layer_to_channel(channel, global_layer)
#         return True

class PAINTSYSTEM_OT_NewImage(PSContextMixin, MultiMaterialOperator):
    """Create a new image layer"""
    bl_idname = "paint_system.new_image_layer"
    bl_label = "New Image Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None
    
    coord_type: EnumProperty(
        name="Coordinate Type",
        items=COORDINATE_TYPE_ENUM,
        default='AUTO'
    )
    # uv_map_name: EnumProperty(
    #     name="UV Map",
    #     items=get_object_uv_maps
    # )
    uv_map_name: StringProperty(
        name="UV Map",
        description="Name of the UV map to use"
    )
    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new image layer",
        default="Image Layer"
    )
    image_resolution: EnumProperty(
        items=[
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
            ('CUSTOM', "Custom", "Custom Resolution"),
        ],
        default='2048'
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
    image_add_type: EnumProperty(
        name="Image Add Type",
        description="How to add the image layer",
        items=[
            ('NEW', "New Image", "Create a new image layer"),
            ('IMPORT', "Import Image", "Import an image from file"),
            ('EXISTING', "Existing Image", "Use an existing image from the blend file"),
        ],
        default='NEW'
    )
    filepath: StringProperty(
        subtype='FILE_PATH',
    )
    filter_glob: StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp',
        options={'HIDDEN'}
    )

    def store_coord_type(self, context):
        """Store the coord_type from the operator to the active channel"""
        ps_ctx = self.ensure_context(context)
        if ps_ctx.active_channel:
            ps_ctx.active_channel.coord_type = self.coord_type

    def get_coord_type(self, context):
        """Get the coord_type from the active channel and set it on the operator"""
        ps_ctx = self.ensure_context(context)
        if ps_ctx.active_channel:
            self.coord_type = ps_ctx.active_channel.coord_type
            
    def select_coord_type_ui(self, layout, context):
        layout.label(text="Coordinate Type", icon='UV')
        layout.prop(self, "coord_type", text="")
        if self.coord_type == 'UV':
            row = layout.row(align=True)
            row.prop_search(self, "uv_map_name", context.object.data, "uv_layers", text="")
            print(self.uv_map_name)
            if not self.uv_map_name:
                row.alert = True
            
    def get_next_image_name(self, context):
        """Get the next image name from the active channel"""
        ps_ctx = self.ensure_context(context)
        if ps_ctx.active_channel:
            return get_next_unique_name("Image Layer", [layer.name for layer in ps_ctx.active_channel.layers])

    def process_material(self, context):
        self.store_coord_type(context)
        ps_ctx = self.ensure_context(context)
        if self.image_add_type == 'NEW':
            img = bpy.data.images.new(
                name=self.layer_name, width=self.image_width, height=self.image_height, alpha=True)
            img.generated_color = (0, 0, 0, 0)
        elif self.image_add_type == 'IMPORT':
            img = bpy.data.images.load(self.filepath, check_existing=True)
            if not img:
                self.report({'ERROR'}, "Failed to load image")
                return False
        elif self.image_add_type == 'EXISTING':
            img = bpy.data.images.get(self.layer_name)
            if not img:
                self.report({'ERROR'}, "No image selected")
                return False
        global_layer = add_global_layer("IMAGE")
        global_layer.image = img
        global_layer.coord_type = self.coord_type
        global_layer.uv_map_name = self.uv_map_name
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.get_coord_type(context)
        self.layer_name = self.get_next_image_name(context)
        if self.image_add_type == 'IMPORT':
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        if self.image_add_type == 'EXISTING':
            self.layer_name = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        self.multiple_objects_ui(layout, context)
        if self.image_add_type == 'NEW':
            row = layout.row(align=True)
            scale_content(context, row)
            row.prop(self, "layer_name")
            box = layout.box()
            box.label(text="Image Resolution", icon='IMAGE_DATA')
            row = box.row(align=True)
            row.prop(self, "image_resolution", expand=True)
            if self.image_resolution == 'CUSTOM':
                row = box.row(align=True)
                row.prop(self, "image_width", text="Width")
                row.prop(self, "image_height", text="Height")
            
        elif self.image_add_type == 'EXISTING':
            layout.prop_search(self, "layer_name", bpy.data,
                           "images", text="Image")
            
        box = layout.box()
        self.select_coord_type_ui(box, context)


class PAINTSYSTEM_OT_NewFolder(PSContextMixin, MultiMaterialOperator):
    """Create a new folder layer"""
    bl_idname = "paint_system.new_folder_layer"
    bl_label = "New Folder"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new folder",
        default="Folder"
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("FOLDER")
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewSolidColor(PSContextMixin, MultiMaterialOperator):
    """Create a new solid color layer"""
    bl_idname = "paint_system.new_solid_color_layer"
    bl_label = "New Solid Color Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new solid color layer",
        default="Solid Color Layer"
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("SOLID_COLOR")
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewAttribute(PSContextMixin, MultiMaterialOperator):
    """Create a new attribute layer"""
    bl_idname = "paint_system.new_attribute_layer"
    bl_label = "New Attribute Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None
    
    attribute_name: StringProperty(
        name="Attribute Name",
        description="Name of the attribute to use"
    )
    attribute_type: EnumProperty(
        name="Attribute Type",
        items=ATTRIBUTE_TYPE_ENUM,
        default='GEOMETRY'
    )

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new attribute layer",
        default="Attribute Layer"
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("ATTRIBUTE")
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewAdjustment(PSContextMixin, MultiMaterialOperator):
    """Create a new adjustment layer"""
    bl_idname = "paint_system.new_adjustment_layer"
    bl_label = "New Adjustment Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None
    
    adjustment_type: EnumProperty(
        name="Adjustment Type",
        items=ADJUSTMENT_TYPE_ENUM,
        default='ShaderNodeBrightContrast'
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("ADJUSTMENT")
        global_layer.adjustment_type = self.adjustment_type
        layer_name = next(name for adjustment_type, name, description in ADJUSTMENT_TYPE_ENUM if adjustment_type == self.adjustment_type)
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewShader(PSContextMixin, MultiMaterialOperator):
    """Create a new shader layer"""
    bl_idname = "paint_system.new_shader_layer"
    bl_label = "New Shader Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new shader layer",
        default="Shader Layer"
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("SHADER")
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewNodeGroup(PSContextMixin, MultiMaterialOperator):
    """Create a new node group layer"""
    bl_idname = "paint_system.new_node_group_layer"
    bl_label = "New Node Group Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new node group layer",
        default="Node Group Layer"
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        global_layer = add_global_layer("NODE_GROUP")
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}


class PAINTSYSTEM_OT_NewGradient(PSContextMixin, MultiMaterialOperator):
    """Create a new gradient layer"""
    bl_idname = "paint_system.new_gradient_layer"
    bl_label = "New Gradient Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None

    layer_name: StringProperty(
        name="Layer Name",
        description="Name of the new gradient layer",
        default="Gradient Layer"
    )
    
    gradient_type: EnumProperty(
        name="Gradient Type",
        items=GRADIENT_TYPE_ENUM,
        default='LINEAR'
    )

    def process_material(self, context):
        ps_ctx = self.ensure_context(context)
        view_layer = bpy.context.view_layer
        with bpy.context.temp_override():
            if "Paint System Collection" not in view_layer.layer_collection.collection.children:
                collection = bpy.data.collections.new("Paint System Collection")
                view_layer.layer_collection.collection.children.link(collection)
            else:
                collection = view_layer.layer_collection.collection.children["Paint System Collection"]
            empty_object = bpy.data.objects.new(f"{ps_ctx.active_group.name} {self.layer_name}", None)
            empty_object.parent = ps_ctx.ps_object
            collection.objects.link(empty_object)
        empty_object.location = ps_ctx.active_object.location
        if self.gradient_type == 'LINEAR':
            empty_object.empty_display_type = 'SINGLE_ARROW'
        elif self.gradient_type == 'RADIAL':
            empty_object.empty_display_type = 'SPHERE'
        global_layer = add_global_layer("GRADIENT", self.layer_name)
        global_layer.gradient_type = self.gradient_type
        global_layer.empty_object = empty_object
        layer = add_global_layer_to_channel(ps_ctx.active_channel, global_layer, self.layer_name)
        layer.update_node_tree(context)
        ps_ctx.active_channel.update_node_tree(context)
        return {'FINISHED'}

class PAINTSYSTEM_OT_DeleteItem(PSContextMixin, MultiMaterialOperator):
    """Remove the active item"""
    bl_idname = "paint_system.delete_item"
    bl_label = "Remove Item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Remove the active item"

    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_layer is not None

    def process_material(self, context):
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
        
        if not is_global_layer_linked(global_layer):
            # Delete the global layer
            if global_layer.empty_object:
                bpy.data.objects.remove(global_layer.empty_object, do_unlink=True)
            if global_layer.image:
                bpy.data.images.remove(global_layer.image)
            if global_layer.node_tree:
                bpy.data.node_groups.remove(global_layer.node_tree)
            bpy.data.global_layers.remove(global_layer)
        
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


class PAINTSYSTEM_OT_MoveUp(PSContextMixin, MultiMaterialOperator):
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
            return self.process_material(context)

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

    def process_material(self, context):
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


class PAINTSYSTEM_OT_MoveDown(PSContextMixin, MultiMaterialOperator):
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
            return self.process_material(context)

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

    def process_material(self, context):
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


class PAINTSYSTEM_OT_CopyLayer(PSContextMixin, Operator):
    """Copy the active layer"""
    bl_idname = "paint_system.copy_layer"
    bl_label = "Copy Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Copy the active layer"
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_layer is not None
    
    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_layer = ps_ctx.active_layer
        ps_scene_data = ps_ctx.ps_scene_data
        if not ps_scene_data:
            print("No ps_scene_data found")
            return {'CANCELLED'}
        clipboard_layers = bpy.context.scene.ps_scene_data.clipboard_layers
        clipboard_layers.clear()
        clipboard_layer = clipboard_layers.add()
        clipboard_layer.name = active_layer.name
        clipboard_layer.type = active_layer.type
        clipboard_layer.ref_layer_id = active_layer.ref_layer_id
        clipboard_layer.enabled = active_layer.enabled
        clipboard_layer.lock_alpha = active_layer.lock_alpha
        return {'FINISHED'}


class PAINTSYSTEM_OT_CopyAllLayers(PSContextMixin, Operator):
    """Copy all layers"""
    bl_idname = "paint_system.copy_all_layers"
    bl_label = "Copy All Layers"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Copy all layers"
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.ensure_context(context)
        return ps_ctx.active_channel is not None
    
    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        active_channel = ps_ctx.active_channel
        clipboard_layers = bpy.context.scene.ps_scene_data.clipboard_layers
        clipboard_layers.clear()
        for layer in active_channel.layers:
            clipboard_layer = clipboard_layers.add()
            clipboard_layer.name = layer.name
            clipboard_layer.type = layer.type
            clipboard_layer.ref_layer_id = layer.ref_layer_id
            clipboard_layer.enabled = layer.enabled
            clipboard_layer.lock_alpha = layer.lock_alpha
        return {'FINISHED'}


class PAINTSYSTEM_OT_PasteLayer(PSContextMixin, Operator):
    """Paste the copied layer"""
    bl_idname = "paint_system.paste_layer"
    bl_label = "Paste Layer"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = "Paste the copied layer"
    
    linked: BoolProperty(
        name="Linked",
        description="Paste the copied layer as linked",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        return len(bpy.context.scene.ps_scene_data.clipboard_layers) > 0
    
    def execute(self, context):
        ps_ctx = self.ensure_context(context)
        clipboard_layers = bpy.context.scene.ps_scene_data.clipboard_layers
        for layer in clipboard_layers:
            global_layer = get_global_layer(layer)
            if self.linked:
                add_global_layer_to_channel(ps_ctx.active_channel, global_layer, layer.name)
            else:
                # Create a new global layer and copy everything except the uid
                new_global_layer = add_global_layer(global_layer.type, layer.name)
                for prop in global_layer.bl_rna.properties:
                    print(prop)
                    pid = getattr(prop, 'identifier', '')
                    if not pid or getattr(prop, 'is_readonly', False):
                        continue
                    if pid in {"uid", "node_tree"}:
                        continue
                    setattr(new_global_layer, pid, getattr(global_layer, pid))
                layer = add_global_layer_to_channel(ps_ctx.active_channel, new_global_layer, layer.name)
        ps_ctx.active_channel.update_node_tree(context)
        
        return {'FINISHED'}


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
    PAINTSYSTEM_OT_CopyLayer,
    PAINTSYSTEM_OT_CopyAllLayers,
    PAINTSYSTEM_OT_PasteLayer,
)

register, unregister = register_classes_factory(classes)