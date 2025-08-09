import bpy
from bpy.props import PointerProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty, StringProperty
from bpy.types import PropertyGroup, Image, NodeTree
from bpy.utils import register_classes_factory
from .nested_list_manager import BaseNestedListManager, BaseNestedListItem
from ..custom_icons import get_icon
from ..utils import get_next_unique_name

LAYER_TYPE_ENUM = [
    ('FOLDER', "Folder", "Folder layer"),
    ('IMAGE', "Image", "Image layer"),
    ('SOLID_COLOR', "Solid Color", "Solid Color layer"),
    ('ATTRIBUTE', "Attribute", "Attribute layer"),
    ('ADJUSTMENT', "Adjustment", "Adjustment layer"),
    ('SHADER', "Shader", "Shader layer"),
    ('NODE_GROUP', "Node Group", "Node Group layer"),
    ('GRADIENT', "Gradient", "Gradient layer"),
]

CHANNEL_TYPE_ENUM = [
    ('COLOR', "Color", "Color channel", get_icon('color_socket'), 1),
    ('VECTOR', "Vector", "Vector channel", get_icon('vector_socket'), 2),
    ('VALUE', "Value", "Value channel", get_icon('value_socket'), 3),
]

class GlobalLayer(PropertyGroup):
    def update_layer_name(self, context):
        """Update the layer name to ensure uniqueness."""
        if self.updating_name_flag:
            return
        self.updating_name_flag = True
        try:
            new_name = get_next_unique_name(self.name, [layer.name for layer in context.scene.ps_scene_data.layers if layer != self])
            if new_name != self.name:
                self.name = new_name

        finally:
            # Always unset the flag when done, even if errors occur
            self.updating_name_flag = False
    
    id: StringProperty()
    
    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer",
        update=update_layer_name
    )
    updating_name_flag: bpy.props.BoolProperty(
        default=False, 
        options={'SKIP_SAVE'} # Don't save this flag in the .blend file
    )
    image: PointerProperty(
        name="Image",
        type=Image
    )
    type: EnumProperty(
        items=LAYER_TYPE_ENUM,
        default='IMAGE'
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
    is_expanded: BoolProperty(
        name="Expanded",
        description="Expand the layer",
        default=True,
        # update=select_layer
    )

class Layer(BaseNestedListItem):
    """Base class for material layers in the Paint System"""
    ref_layer_id: StringProperty()
    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True,
        # update=update_node_tree
    )
    clip: BoolProperty(
        name="Clip to Below",
        description="Clip the layer to the one below",
        default=False,
        # update=update_node_tree
    )
    
class Channel(BaseNestedListManager):
    """Custom data for material layers in the Paint System"""
    
    def update_node_tree(self):
        pass
    
    def update_channel_name(self, context):
        """Update the channel name to ensure uniqueness."""
        if self.updating_name_flag:
            return
        self.updating_name_flag = True
        parsed_context = parse_context(context)
        active_group = parsed_context.get("active_group")
        new_name = get_next_unique_name(self.name, [channel.name for channel in active_group.channels if channel != self])
        if new_name != self.name:
            self.name = new_name
        self.updating_name_flag = False
        
    @property
    def item_type(self):
        return Layer
    
    @property
    def collection_name(self):
        return "layers"
            
    name: StringProperty(
        name="Name",
        description="Channel name",
        default="Channel",
        update=update_channel_name
    )
    updating_name_flag: BoolProperty(
        default=False,
        options={'SKIP_SAVE'}  # Don't save this flag in the .blend file
    )
    layers: CollectionProperty(
        type=Layer,
        name="Material Layers",
        description="Collection of material layers in the Paint System"
    )
    active_index: IntProperty(name="Active Material Layer Index")
    type: EnumProperty(
        items=CHANNEL_TYPE_ENUM,
        name="Channel Type",
        description="Type of the channel",
        default='COLOR'
    )
    order: IntProperty(
        name="Order",
        description="Channel order",
        default=0,
        # update=update_node_tree
    )
    bake_image: PointerProperty(
        name="Bake Image",
        type=Image
    )
    bake_uv_map: StringProperty(
        name="Bake Image UV Map",
        default="UVMap",
        # update=update_node_tree
    )
    use_bake_image: BoolProperty(
        name="Use Bake Image",
        default=False,
        # update=update_node_tree
    )


class Group(PropertyGroup):
    """Base class for Paint System groups"""
    name: StringProperty(
        name="Name",
        description="Group name",
        default="Group"
    )
    channels: CollectionProperty(
        type=Channel,
        name="Channels",
        description="Collection of channels in the Paint System"
    )
    active_index: IntProperty(name="Active Channel Index")
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
    )
    order: IntProperty(
        name="Order",
        description="Group order",
        default=0,
    )

class PaintSystemGlobalData(PropertyGroup):
    """Custom data for the Paint System"""
    layers: CollectionProperty(
        type=GlobalLayer,
        name="Paint System Layers",
        description="Collection of layers in the Paint System"
    )
    active_index: IntProperty(name="Active Layer Index")

class MaterialData(PropertyGroup):
    """Custom data for channels in the Paint System"""
    groups: CollectionProperty(
        type=Group,
        name="Groups",
        description="Collection of groups in the Paint System"
    )
    active_index: IntProperty(name="Active Group Index")
    use_alpha: BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the Paint System",
        default=True
    )


def get_global_layer(layer: Layer) -> GlobalLayer | None:
    """Get the global layer data from the context."""
    if not layer or not bpy.context.scene or not bpy.context.scene.get("ps_scene_data"):
        return None
    for global_layer in bpy.context.scene.ps_scene_data.layers:
        if global_layer.id == layer.ref_layer_id:
            return global_layer
    return None


def parse_context(context: bpy.types.Context) -> dict:
    """
    Parses the Blender context to extract relevant information for the paint system.
    
    Args:
        context (bpy.types.Context): The Blender context to parse.
        
    Returns:
        dict: A dictionary containing parsed context information.
    """
    if not context:
        raise ValueError("Context cannot be None")
    if not isinstance(context, bpy.types.Context):
        raise TypeError("context must be of type bpy.types.Context")
    
    ps_scene_data = context.scene.get("ps_scene_data", None)
    
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        obj = None
    mat = obj.active_material if obj else None
    
    mat_data = None
    groups = None
    active_group = None
    if mat and hasattr(mat, 'ps_mat_data') and mat.ps_mat_data:
        mat_data = mat.ps_mat_data
        groups = mat_data.groups
        if groups and mat_data.active_index >= 0:
            active_group = groups[mat_data.active_index]
    
    channels = None
    active_channel = None
    if active_group:
        channels = active_group.channels
        if channels and active_group.active_index >= 0:
            active_channel = channels[active_group.active_index]

    layers = None
    active_layer = None
    if active_channel:
        layers = active_channel.layers
        if layers and active_channel.active_index >= 0:
            active_layer = layers[active_channel.active_index]
    
    return {
        "ps_scene_data": ps_scene_data,
        "active_object": obj,
        "active_material": mat,
        "ps_mat_data": mat_data,
        "groups": groups,
        "active_group": active_group,
        "channels": channels,
        "active_channel": active_channel,
        "layers": layers,
        "active_layer": active_layer,
        "active_global_layer": get_global_layer(active_layer) if active_layer else None
    }


class PSContextMixin:
    """A mixin for classes that need access to the paint system context."""

    ps_scene_data: PaintSystemGlobalData | None = None
    active_object: bpy.types.Object | None = None
    active_material: bpy.types.Material | None = None
    ps_mat_data: MaterialData | None = None
    active_group: Group | None = None
    active_channel: Channel | None = None
    active_layer: Layer | None = None
    active_global_layer: GlobalLayer | None = None

    @classmethod
    def poll(cls, context):
        """Poll the context for paint system data."""
        parsed_context = parse_context(context)
        cls.ps_scene_data = parsed_context.get("ps_scene_data")
        cls.active_object = parsed_context.get("active_object")
        cls.active_material = parsed_context.get("active_material")
        cls.ps_mat_data = parsed_context.get("ps_mat_data")
        cls.active_group = parsed_context.get("active_group")
        cls.active_channel = parsed_context.get("active_channel")
        cls.active_layer = parsed_context.get("active_layer")
        cls.active_global_layer = parsed_context.get("active_global_layer")
        return cls._poll(context)

    @classmethod
    def _poll(cls, context):
        """Override this method to implement custom poll logic."""
        return True

classes = (
    GlobalLayer,
    Layer,
    Channel,
    Group,
    PaintSystemGlobalData,
    MaterialData,
    )

register, unregister = register_classes_factory(classes)