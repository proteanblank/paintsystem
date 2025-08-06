import bpy

from bpy.props import (IntProperty,
                       FloatVectorProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.types import (PropertyGroup, Context,
                       NodeTreeInterface, Nodes, Node, NodeTree, NodeLinks, NodeSocket, Image)
from bpy.utils import register_classes_factory

LAYER_ENUM = [
    ('FOLDER', "Folder", "Folder layer"),
    ('IMAGE', "Image", "Image layer"),
    ('SOLID_COLOR', "Solid Color", "Solid Color layer"),
    ('ATTRIBUTE', "Attribute", "Attribute layer"),
    ('ADJUSTMENT', "Adjustment", "Adjustment layer"),
    ('SHADER', "Shader", "Shader layer"),
    ('NODE_GROUP', "Node Group", "Node Group layer"),
    ('GRADIENT', "Gradient", "Gradient layer"),
]

# def update_active_image(self=None, context: Context = None):
#     context = context or bpy.context
#     ps = PaintSystem(context)
#     if not ps.settings.allow_image_overwrite:
#         return
#     image_paint = context.tool_settings.image_paint
#     mat = ps.get_active_material()
#     active_group = ps.get_active_group()
#     if not mat or not active_group:
#         return
#     active_layer = ps.get_active_layer()
#     update_brush_settings(self, context)
#     if not active_layer:
#         return

#     if image_paint.mode == 'MATERIAL':
#                 image_paint.mode = 'IMAGE'
#     selected_image: Image = active_layer.mask_image if active_layer.edit_mask else active_layer.image
#     if not selected_image or active_layer.lock_layer or active_group.use_bake_image:
#         image_paint.canvas = None
#         # Unable to paint
#         return
#     else:
#         # print("Selected image: ", selected_image)
#         image_paint.canvas = selected_image
#         uv_map_node = ps.find_uv_map_node()
#         if uv_map_node:
#             ps.active_object.data.uv_layers[uv_map_node.uv_map].active = True


# def update_brush_settings(self=None, context: Context = bpy.context):
#     if context.mode != 'PAINT_TEXTURE':
#         return
#     ps = PaintSystem(context)
#     active_layer = ps.get_active_layer()
#     brush = context.tool_settings.image_paint.brush
#     if not brush:
#         return
#     brush.use_alpha = not active_layer.lock_alpha

class PaintSystemLayer(PropertyGroup):

    layer_name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer",
        # update=update_paintsystem_data
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True,
        # update=update_node_tree
    )
    image: PointerProperty(
        name="Image",
        type=Image
    )
    type: EnumProperty(
        items=LAYER_ENUM,
        default='IMAGE'
    )
    sub_type: StringProperty(
        name="Sub Type",
        default="",
    )
    clip: BoolProperty(
        name="Clip to Below",
        description="Clip the layer to the one below",
        default=False,
        # update=update_node_tree
    )
    lock_alpha: BoolProperty(
        name="Lock Alpha",
        description="Lock the alpha channel",
        default=False,
        # update=update_brush_settings
    )
    lock_layer: BoolProperty(
        name="Lock Layer",
        description="Lock the layer",
        default=False,
        # update=update_active_image
    )
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
    )
    edit_mask: BoolProperty(
        name="Edit Mask",
        description="Edit mask",
        default=False,
    )
    mask_image: PointerProperty(
        name="Mask Image",
        type=Image,
        # update=update_node_tree
    )
    enable_mask: BoolProperty(
        name="Enabled Mask",
        description="Toggle mask visibility",
        default=False,
        # update=update_node_tree
    )
    mask_uv_map: StringProperty(
        name="Mask UV Map",
        default="",
        # update=update_node_tree
    )
    external_image: PointerProperty(
        name="Edit External Image",
        type=Image,
    )
    expanded: BoolProperty(
        name="Expanded",
        description="Expand the layer",
        default=True,
        # update=select_layer
    )


classes = (
    PaintSystemLayer,
)

register, unregister = register_classes_factory(classes)