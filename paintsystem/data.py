from dataclasses import dataclass
import bpy
from bpy.props import PointerProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty, StringProperty
from bpy.types import PropertyGroup, Image, NodeTree
from bpy.utils import register_classes_factory
from .nested_list_manager import BaseNestedListManager, BaseNestedListItem
from ..custom_icons import get_icon
from ..utils import get_next_unique_name
from .graph import NodeTreeBuilder, START, END
from .graph.premade import create_image_graph
from mathutils import Vector
import time

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
    ('FLOAT', "Value", "Value channel", get_icon('float_socket'), 3),
]

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

def update_active_layer(self, context):
    ps_ctx = parse_context(context)
    active_layer = ps_ctx["active_layer"]
    if active_layer:
        active_layer.update_node_tree(context)

def update_active_channel(self, context):
    ps_ctx = parse_context(context)
    active_channel = ps_ctx["active_channel"]
    if active_channel:
        active_channel.update_node_tree(context)

def update_active_group(self, context):
    ps_ctx = parse_context(context)
    active_group = ps_ctx["active_group"]
    if active_group:
        active_group.update_node_tree(context)

# def update_node_tree(context):
#     parsed_context = parse_context(context)
#     active_group = parsed_context.get("active_group")
#     if not active_group:
#         return
#     node_tree = active_group.node_tree
#     if not isinstance(node_tree, bpy.types.NodeTree):
#         print("Node tree is not a NodeTree")
#         return
    
#     # Ensure node sockets are in the correct order
    
#     nt_interface = node_tree.interface
#     nt_sockets = nt_interface.items_tree
#     input_sockets = [socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == "INPUT"]
#     output_sockets = [socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == "OUTPUT"]
    
#     # Simplified: synchronize output and input sockets with channels
#     channel_names = [channel.name for channel in active_group.channels]
#     channel_types = {channel.name: f"NodeSocket{channel.type.title()}" for channel in active_group.channels}

#     # Helper to sync sockets
#     def sync_sockets(sockets, in_out):
#         offset = len(active_group.channels) * 2 if in_out == "INPUT" else 0
#         for idx, name in enumerate(channel_names):
#             socket = next((s for s in sockets if s.name == name), None)
#             socket_alpha = next((s for s in sockets if s.name == f"{name} Alpha"), None)
#             socket_type = channel_types[name]
#             if not socket:
#                 if idx == len(channel_names) - 1:
#                     nt_interface.new_socket(name=name, socket_type=socket_type, in_out=in_out)
#                     nt_interface.new_socket(name=f"{name} Alpha", socket_type="NodeSocketFloat", in_out=in_out)
#                 else:
#                     # rename socket to name
#                     socket = sockets[idx * 2]
#                     socket.name = name
#                     socket_alpha = sockets[idx * 2 + 1]
#                     socket_alpha.name = f"{name} Alpha"
#             else:
#                 # Move socket if out of order
#                 target_idx = idx * 2
#                 if sockets.index(socket) != target_idx:
#                     nt_interface.move(socket, target_idx + offset)
#                     nt_interface.move(socket_alpha, target_idx + offset + 1)
#                 # Update type if needed
#                 if getattr(socket, "socket_type", None) != socket_type:
#                     socket.socket_type = socket_type

#     sync_sockets(output_sockets, "OUTPUT")
#     sync_sockets(input_sockets, "INPUT")
    
#     # Delete unused sockets
#     expected_sockets = [channel.name for channel in active_group.channels] + [f"{channel.name} Alpha" for channel in active_group.channels]
#     for socket in nt_sockets:
#         if socket.item_type == "SOCKET" and socket.in_out == "INPUT" and socket.name not in expected_sockets:
#             nt_interface.remove(socket)
#         if socket.item_type == "SOCKET" and socket.in_out == "OUTPUT" and socket.name not in expected_sockets:
#             nt_interface.remove(socket)
            
#     # Update the nodes in node tree
#     start_time = time.time()
#     node_builder = NodeTreeBuilder(node_tree, frame_name="Main Graph", verbose=True)
#     node_builder.add_node("group_input", "NodeGroupInput")
#     node_builder.add_node("group_output", "NodeGroupOutput")
    
#     for channel in active_group.channels:
#         start_time_channel = time.time()
#         c_alpha_name = f"{channel.name} Alpha"
#         channel_graph = NodeTreeBuilder(node_tree, frame_name=f"{channel.name} Graph")
#         node_builder.link("group_input", channel_graph, channel.name, "Color")
#         node_builder.link("group_input", channel_graph, c_alpha_name, "Alpha")
#         if len(channel.layers) > 0:
#             previous_layer_graph = None
#             flattened_layers = channel.flatten_hierarchy()
#             for layer, _ in flattened_layers:
#                 # start_time = time.time()
#                 global_layer = get_global_layer(layer)
#                 match global_layer.type:
#                     case "IMAGE":
#                         # print(f"Creating image graph for {global_layer.name}")
#                         layer_graph = create_image_graph(node_tree, global_layer.image, f"{layer.name} Graph")
#                     case _:
#                         pass
#                 if not previous_layer_graph:
#                     channel_graph.link(START, layer_graph, "Color", "Color")
#                     channel_graph.link(START, layer_graph, "Alpha", "Alpha")
#                 else:
#                     channel_graph.link(previous_layer_graph, layer_graph, "Color", "Color")
#                     channel_graph.link(previous_layer_graph, layer_graph, "Alpha", "Alpha")
#                 # print(f"Time taken to link {layer.name} graph: {time.time() - start_time} seconds")
#                 previous_layer_graph = layer_graph
#             channel_graph.link(previous_layer_graph, END, "Color", "Color")
#             channel_graph.link(previous_layer_graph, END, "Alpha", "Alpha")
#         else:
#             channel_graph.link(START, END, "Color", "Color")
#             channel_graph.link(START, END, "Alpha", "Alpha")
#         node_builder.link(channel_graph, "group_output", "Color", channel.name)
#         node_builder.link(channel_graph, "group_output", "Alpha", c_alpha_name)
#         print(f"Time taken to link {channel.name} graph: {time.time() - start_time_channel} seconds")
#         # channel_graph.set_node_offset(Vector((0, len(channel.layers) * 500)))
#     node_builder.compile()
#     print(f"Time taken to compile node tree: {time.time() - start_time} seconds")
class GlobalLayer(PropertyGroup):
            
    def update_node_tree(self, context):
        match self.type:
            case "IMAGE":
                image_graph = create_image_graph(self.node_tree, self.image)
                image_graph.compile()
            case _:
                pass
            
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
            self.update_node_tree(context)
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
    def update_node_tree(self, context):
        global_layer = get_global_layer(self)
        if global_layer:
            global_layer.update_node_tree(context)
    
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
    
    def update_node_tree(self, context):
        self.node_tree.name = self.name
        node_builder = NodeTreeBuilder(self.node_tree, frame_name="Channel Graph", verbose=True)
        node_builder.add_node("group_input", "NodeGroupInput")
        node_builder.add_node("group_output", "NodeGroupOutput")
        flattened_layers = self.flatten_hierarchy()
        if len(flattened_layers) > 0:
            prev_layer_name = None
            for layer, _ in flattened_layers:
                global_layer = get_global_layer(layer)
                match global_layer.type:
                    case "IMAGE":
                        layer_name = layer.name
                        node_builder.add_node(layer_name, "ShaderNodeGroup", {"node_tree": global_layer.node_tree})
                    case _:
                        pass
                if not prev_layer_name:
                    node_builder.link("group_input", layer_name, "Color", "Color")
                    node_builder.link("group_input", layer_name, "Alpha", "Alpha")
                else:
                    node_builder.link(prev_layer_name, layer_name, "Color", "Color")
                    node_builder.link(prev_layer_name, layer_name, "Alpha", "Alpha")
                prev_layer_name = layer_name
            node_builder.link(prev_layer_name, "group_output", "Color", "Color")
            node_builder.link(prev_layer_name, "group_output", "Alpha", "Alpha")
        else:
            node_builder.link("group_input", "group_output", "Color", "Color")
            node_builder.link("group_input", "group_output", "Alpha", "Alpha")
        node_builder.compile()
    
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
        update_active_group(self, context)
        
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
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
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
        default='COLOR',
        update=update_active_group
    )
    use_alpha: BoolProperty(
        name="Use Alpha",
        description="Use alpha channel in the Paint System",
        default=True
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
    def update_node_tree(self, context):
        node_tree = self.node_tree
        node_tree.name = f"Paint System ({self.name})"
        if not isinstance(node_tree, bpy.types.NodeTree):
            print("Node tree is not a NodeTree")
            return
        
        # Ensure node sockets are in the correct order
        
        nt_interface = node_tree.interface
        nt_sockets = nt_interface.items_tree
        
        # Simplified: synchronize output and input sockets with channels
        channel_types = {str(channel.name): f"NodeSocket{channel.type.title()}" for channel in self.channels}

        if len(self.channels) * 4 == len(nt_sockets): # 4 because each channel has 4 sockets (2 input, 2 output)
            # Can be either channel renamed or channel moved
            all_channel_found = True
            input_sockets = [socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == "INPUT"]
            for channel in self.channels:
                if channel.name not in input_sockets:
                    all_channel_found = False
                    break
            if all_channel_found:
                # Channel is moved
                for idx, channel in enumerate(self.channels):
                    expected_output_socket_idx = idx * 2
                    expected_input_socket_idx = (idx + len(self.channels)) * 2
                    output_socket = next((socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == "OUTPUT" and socket.name == channel.name), None)
                    input_socket = next((socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == "INPUT" and socket.name == channel.name), None)
                    if output_socket.index != expected_output_socket_idx:
                        nt_interface.move(output_socket, expected_output_socket_idx)
                        if channel.use_alpha:
                            output_alpha_socket = nt_sockets[output_socket.index + 1]
                            nt_interface.move(output_alpha_socket, expected_output_socket_idx + 1)
                        nt_interface.move(input_socket, expected_input_socket_idx)
                        if channel.use_alpha:
                            input_alpha_socket = nt_sockets[input_socket.index + 1]
                            nt_interface.move(input_alpha_socket, expected_input_socket_idx + 1)
                        continue
            else:
                # Channel is renamed
                for idx, channel in enumerate(self.channels):
                    expected_output_socket_idx = idx * 2
                    expected_input_socket_idx = (idx + len(self.channels)) * 2
                    output_socket = nt_sockets[expected_output_socket_idx]
                    input_socket = nt_sockets[expected_input_socket_idx]
                    if output_socket.name != channel.name:
                        output_socket.name = channel.name
                        input_socket.name = channel.name
                        # Get alpha sockets
                        output_alpha_socket = nt_sockets[expected_output_socket_idx + 1]
                        input_alpha_socket = nt_sockets[expected_input_socket_idx + 1]
                        output_alpha_socket.name = f"{channel.name} Alpha"
                        input_alpha_socket.name = f"{channel.name} Alpha"
                        continue
        elif len(self.channels) * 4 < len(nt_sockets):
            # a channel is deleted
            # print("a channel is deleted")
            expected_sockets = [str(channel.name) for channel in self.channels] + [f"{channel.name} Alpha" for channel in self.channels]
            for socket in nt_sockets[:]:
                if socket.item_type == "SOCKET" and socket.name not in expected_sockets:
                    nt_interface.remove(socket)
        elif len(self.channels) * 4 > len(nt_sockets):
            # a channel is added
            # print("a channel is added")
            # Added channel is always at the of the channel list
            new_channel_name = self.channels[-1].name
            nt_interface.new_socket(name=new_channel_name, socket_type=channel_types[new_channel_name], in_out="INPUT")
            nt_interface.new_socket(name=f"{new_channel_name} Alpha", socket_type="NodeSocketFloat", in_out="INPUT")
            nt_interface.new_socket(name=new_channel_name, socket_type=channel_types[new_channel_name], in_out="OUTPUT")
            nt_interface.new_socket(name=f"{new_channel_name} Alpha", socket_type="NodeSocketFloat", in_out="OUTPUT")
        # print("Done")
        # Check socket type
        for idx, channel in enumerate(self.channels):
            expected_output_socket_idx = idx * 2
            expected_input_socket_idx = (idx + len(self.channels)) * 2
            output_socket = nt_sockets[expected_output_socket_idx]
            input_socket = nt_sockets[expected_input_socket_idx]
            if output_socket.socket_type != channel_types[channel.name]:
                output_socket.socket_type = channel_types[channel.name]
            if input_socket.socket_type != channel_types[channel.name]:
                input_socket.socket_type = channel_types[channel.name]
        node_builder = NodeTreeBuilder(self.node_tree, frame_name="Group Graph", verbose=True)
        node_builder.add_node("group_input", "NodeGroupInput")
        node_builder.add_node("group_output", "NodeGroupOutput")
        for channel in self.channels:
            channel_name = channel.name
            c_alpha_name = f"{channel.name} Alpha"
            node_builder.add_node(channel_name, "ShaderNodeGroup", {"node_tree": channel.node_tree})
            node_builder.link("group_input", channel_name, channel_name, "Color")
            node_builder.link("group_input", channel_name, c_alpha_name, "Alpha")
            node_builder.link(channel_name, "group_output", "Color", channel_name)
            node_builder.link(channel_name, "group_output", "Alpha", c_alpha_name)
        node_builder.compile()
    
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


@dataclass
class PSContext:
    ps_scene_data: PaintSystemGlobalData | None = None
    active_object: bpy.types.Object | None = None
    active_material: bpy.types.Material | None = None
    ps_mat_data: MaterialData | None = None
    active_group: Group | None = None
    active_channel: Channel | None = None
    active_layer: Layer | None = None
    active_global_layer: GlobalLayer | None = None

class PSContextMixin:
    """A mixin for classes that need access to the paint system context."""

    @staticmethod
    def ensure_context(context: bpy.types.Context) -> PSContext:
        """Return a PSContext parsed from Blender context. Safe to call from class or instance methods."""
        parsed_context = parse_context(context)
        return PSContext(
            ps_scene_data=parsed_context.get("ps_scene_data"),
            active_object=parsed_context.get("active_object"),
            active_material=parsed_context.get("active_material"),
            ps_mat_data=parsed_context.get("ps_mat_data"),
            active_group=parsed_context.get("active_group"),
            active_channel=parsed_context.get("active_channel"),
            active_layer=parsed_context.get("active_layer"),
            active_global_layer=parsed_context.get("active_global_layer"),
        )

    @staticmethod
    def parse_context(context: bpy.types.Context) -> dict:
        """Parse the context and return a plain dict. Provided for convenience."""
        return parse_context(context)

    # @classmethod
    # def poll(cls, context):
    #     """Poll the context for paint system data."""
    #     parsed_context = parse_context(context)
    #     cls.ps_scene_data = parsed_context.get("ps_scene_data")
    #     cls.active_object = parsed_context.get("active_object")
    #     cls.active_material = parsed_context.get("active_material")
    #     cls.ps_mat_data = parsed_context.get("ps_mat_data")
    #     cls.active_group = parsed_context.get("active_group")
    #     cls.active_channel = parsed_context.get("active_channel")
    #     cls.active_layer = parsed_context.get("active_layer")
    #     cls.active_global_layer = parsed_context.get("active_global_layer")
    #     return cls._poll(context)

    # @classmethod
    # def _poll(cls, context):
    #     """Override this method to implement custom poll logic."""
    #     return True

classes = (
    GlobalLayer,
    Layer,
    Channel,
    Group,
    PaintSystemGlobalData,
    MaterialData,
    )

register, unregister = register_classes_factory(classes)