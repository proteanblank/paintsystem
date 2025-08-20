from dataclasses import dataclass
import bpy
from bpy.props import PointerProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty, StringProperty, FloatProperty
from bpy.types import PropertyGroup, Image, NodeTree, Node, NodeSocket, Object
from bpy.utils import register_classes_factory
from bpy.app.handlers import persistent
from .nested_list_manager import BaseNestedListManager, BaseNestedListItem
from ..custom_icons import get_icon
from ..utils import get_next_unique_name
from ..preferences import get_preferences
from ..paintsystem.common import PaintSystemPreferences
from .graph import NodeTreeBuilder, START, END
from .graph.premade import (
    create_image_graph, 
    create_folder_graph, 
    create_solid_graph, 
    create_attribute_graph, 
    create_adjustment_graph, 
    create_gradient_graph,
    create_random_graph,
    create_custom_graph
    )
from mathutils import Vector
from typing import Dict, List

LAYER_TYPE_ENUM = [
    ('FOLDER', "Folder", "Folder layer"),
    ('IMAGE', "Image", "Image layer"),
    ('SOLID_COLOR', "Solid Color", "Solid Color layer"),
    ('ATTRIBUTE', "Attribute", "Attribute layer"),
    ('ADJUSTMENT', "Adjustment", "Adjustment layer"),
    ('SHADER', "Shader", "Shader layer"),
    ('NODE_GROUP', "Node Group", "Node Group layer"),
    ('GRADIENT', "Gradient", "Gradient layer"),
    ('RANDOM', "Random", "Random Color layer"),
]

CHANNEL_TYPE_ENUM = [
    ('COLOR', "Color", "Color channel", get_icon('color_socket'), 1),
    ('VECTOR', "Vector", "Vector channel", get_icon('vector_socket'), 2),
    ('FLOAT', "Value", "Value channel", get_icon('float_socket'), 3),
]

GRADIENT_TYPE_ENUM = [
    ('LINEAR', "Linear Gradient", "Linear gradient"),
    ('RADIAL', "Radial Gradient", "Radial gradient"),
    ('DISTANCE', "Distance Gradient", "Distance gradient"),
]

ADJUSTMENT_TYPE_ENUM = [
    ('ShaderNodeBrightContrast', "Brightness and Contrast", ""),
    ('ShaderNodeGamma', "Gamma", ""),
    ('ShaderNodeHueSaturation', "Hue Saturation Value", ""),
    ('ShaderNodeInvert', "Invert", ""),
    ('ShaderNodeRGBCurve', "RGB Curves", ""),
    # ('ShaderNodeAmbientOcclusion', "Ambient Occlusion", ""),
]

COORDINATE_TYPE_ENUM = [
    ('AUTO', "Auto UV", "Automatically create a new UV Map"),
    ('UV', "Use Existing UV", "Open an existing UV Map"),
    # ('GENERATED', "Generated", "Use a generated output of Texture Coordinate node"),
    ('OBJECT', "Object", "Use a object output of Texture Coordinate node"),
    ('CAMERA', "Camera", "Use a camera output of Texture Coordinate node"),
    ('WINDOW', "Window", "Use a window output of Texture Coordinate node"),
    ('REFLECTION', "Reflection", "Use a reflection output of Texture Coordinate node"),
    ('POSITION', "Position", "Use a position output of Geometry node"),
]

ATTRIBUTE_TYPE_ENUM = [
    ('GEOMETRY', "Geometry", "Geometry"),
    ('OBJECT', "Object", "Object"),
    ('INSTANCER', "Instancer", "Instancer"),
    ('VIEW_LAYER', "View Layer", "View Layer")
]

ACTION_TYPE_ENUM = [
    ('ENABLE', "Enable Layer", "Enable the layer when reached"),
    ('DISABLE', "Disable Layer", "Disable the layer when reached"),
]

ACTION_BIND_ENUM = [
    ('FRAME', "Frame", "Enable/disable the layer on a frame", "KEYTYPE_KEYFRAME_VEC", 0),
    ('MARKER', "Marker", "Enable/disable the layer on a marker", "MARKER_HLT", 1),
]

def _parse_context(context: bpy.types.Context) -> dict:
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
        
        ps_settings = get_preferences(context)
        
        ps_scene_data = context.scene.get("ps_scene_data", None)
        
        ps_object = None
        obj = context.active_object
        if obj and obj.type == 'MESH' and hasattr(obj.active_material, 'ps_mat_data'):
            ps_object = obj
        elif obj and obj.type == 'EMPTY' and obj.parent and obj.parent.type == 'MESH' and hasattr(obj.parent.active_material, 'ps_mat_data'):
            ps_object = obj.parent
            
        if not obj or obj.type != 'MESH' or not ps_object:
            obj = None

        mat = ps_object.active_material if ps_object else None
        
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
            "ps_settings": ps_settings,
            "ps_scene_data": ps_scene_data,
            "active_object": obj,
            "ps_object": ps_object,
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

def update_brush_settings(self=None, context: bpy.types.Context = bpy.context):
    if context.mode != 'PAINT_TEXTURE':
        return
    ps_ctx = _parse_context(context)
    active_layer = ps_ctx["active_layer"]
    brush = context.tool_settings.image_paint.brush
    if not brush:
        return
    brush.use_alpha = not active_layer.lock_alpha

def update_active_image(self=None, context: bpy.types.Context = None):
    context = context or bpy.context
    ps_ctx = _parse_context(context)
    image_paint = context.tool_settings.image_paint
    obj = ps_ctx["ps_object"]
    mat = ps_ctx["active_material"]
    active_channel = ps_ctx["active_channel"]
    if not mat or not active_channel:
        return
    global_layer = ps_ctx["active_global_layer"]
    update_brush_settings(self, context)
    if not global_layer:
        return

    if image_paint.mode == 'MATERIAL':
                image_paint.mode = 'IMAGE'
    selected_image: Image = global_layer.image
    if not selected_image or global_layer.lock_layer or active_channel.use_bake_image:
        image_paint.canvas = None
        # Unable to paint
        return
    else:
        # print("Selected image: ", selected_image)
        image_paint.canvas = selected_image
        if global_layer.uv_map_name:
            obj.data.uv_layers[global_layer.uv_map_name].active = True

def update_active_layer(self, context):
    ps_ctx = _parse_context(context)
    active_layer = ps_ctx["active_layer"]
    if active_layer:
        active_layer.update_node_tree(context)

def update_active_channel(self, context):
    ps_ctx = _parse_context(context)
    active_channel = ps_ctx["active_channel"]
    if active_channel:
        active_channel.update_node_tree(context)

def update_active_group(self, context):
    ps_ctx = _parse_context(context)
    active_group = ps_ctx["active_group"]
    if active_group:
        active_group.update_node_tree(context)

def get_node_from_nodetree(node_tree: NodeTree, identifier: str) -> Node | None:
    for node in node_tree.nodes:
        if node.get("identifier", None) == identifier:
            return node
    return None

def is_valid_ps_nodetree(node_tree: NodeTree) -> bool:
        # check if the node tree has both Color and Alpha inputs and outputs
        has_color_input = False
        has_alpha_input = False
        has_color_output = False
        has_alpha_output = False
        for interface_item in node_tree.interface.items_tree:
            if interface_item.item_type == "SOCKET":
                # print(interface_item.name, interface_item.socket_type, interface_item.in_out)
                if interface_item.name == "Color" and interface_item.socket_type == "NodeSocketColor":
                    if interface_item.in_out == "INPUT":
                        has_color_input = True
                    else:
                        has_color_output = True
                elif interface_item.name == "Alpha" and interface_item.socket_type == "NodeSocketFloat":
                    if interface_item.in_out == "INPUT":
                        has_alpha_input = True
                    else:
                        has_alpha_output = True
        return has_color_input and has_alpha_input and has_color_output and has_alpha_output


class MarkerAction(PropertyGroup):
    action_bind: EnumProperty(
        name="Action Bind",
        description="Action bind",
        items=ACTION_BIND_ENUM
    )
    action_type: EnumProperty(
        name="Action Type",
        description="Action type",
        items=ACTION_TYPE_ENUM
    )
    frame: IntProperty(
        name="Frame",
        description="Frame to enable/disable the layer",
        default=0
    )
    marker_name: StringProperty(
        name="Marker Name",
        description="Marker name",
        default=""
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Enable the layer on a specific frame",
        default=True
    )

class GlobalLayer(PropertyGroup):
            
    def update_node_tree(self, context):
        self.node_tree.name = f".PS_Layer ({self.uid})"
        match self.type:
            case "IMAGE":
                image_graph = create_image_graph(self.node_tree, self.image, self.coord_type, self.uv_map_name)
                image_graph.compile()
            case "FOLDER":
                folder_graph = create_folder_graph(self.node_tree)
                folder_graph.compile()
            case "SOLID_COLOR":
                solid_graph = create_solid_graph(self.node_tree)
                solid_graph.compile()
            case "ATTRIBUTE":
                attribute_graph = create_attribute_graph(self.node_tree)
                attribute_graph.compile()
            case "ADJUSTMENT":
                adjustment_graph = create_adjustment_graph(self.node_tree, self.adjustment_type)
                adjustment_graph.compile()
            case "GRADIENT":
                gradient_graph = create_gradient_graph(self.node_tree, self.gradient_type, self.empty_object)
                gradient_graph.compile()
            case "RANDOM":
                random_graph = create_random_graph(self.node_tree)
                random_graph.compile()
            case "NODE_GROUP":
                custom_graph = create_custom_graph(self.node_tree, self.custom_node_tree, self.custom_color_input, self.custom_alpha_input, self.custom_color_output, self.custom_alpha_output)
                custom_graph.compile()
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
            
    def find_node(self, identifier: str) -> Node | None:
        return get_node_from_nodetree(self.node_tree, identifier)
            
    @property
    def mix_node(self) -> Node | None:
        return self.find_node("mix_rgb")
    
    @property
    def post_mix_node(self) -> Node | None:
        return self.find_node("post_mix")
    
    @property
    def pre_mix_node(self) -> Node | None:
        return self.find_node("pre_mix")
    
    @property
    def is_clip(self) -> bool:
        if self.post_mix_node:
            return self.post_mix_node.inputs["Clip"].default_value
        return False

    @property
    def mix_factor(self) -> float:
        if self.post_mix_node:
            return self.post_mix_node.inputs["Factor"].default_value
        return 1.0
    
    uid: StringProperty()
    
    # name: StringProperty(
    #     name="Name",
    #     description="Layer name",
    #     default="Layer",
    #     update=update_layer_name
    # )
    updating_name_flag: bpy.props.BoolProperty(
        default=False, 
        options={'SKIP_SAVE'} # Don't save this flag in the .blend file
    )
    image: PointerProperty(
        name="Image",
        type=Image,
        update=update_node_tree
    )
    actions: CollectionProperty(
        type=MarkerAction,
        name="Actions",
        description="Collection of actions for the layer"
    )
    active_action_index: IntProperty(
        name="Active Action Index",
        description="Active action index",
        default=0
    )
    custom_node_tree: PointerProperty(
        name="Custom Node Tree",
        type=NodeTree,
        update=update_node_tree
    )
    custom_color_input: IntProperty(
        name="Custom Color Input",
        description="Custom color input",
        default=-1,
        update=update_node_tree
    )
    custom_alpha_input: IntProperty(
        name="Custom Alpha Input",
        description="Custom alpha input",
        default=-1,
        update=update_node_tree
    )
    custom_color_output: IntProperty(
        name="Custom Color Output",
        description="Custom color output",
        default=-1,
        update=update_node_tree
    )
    custom_alpha_output: IntProperty(
        name="Custom Alpha Output",
        description="Custom alpha output",
        default=-1,
        update=update_node_tree
    )
    coord_type: EnumProperty(
        items=COORDINATE_TYPE_ENUM,
        name="Coordinate Type",
        description="Coordinate type",
        default='AUTO',
        update=update_node_tree
    )
    uv_map_name: StringProperty(
        name="UV Map",
        description="Name of the UV map to use",
        update=update_node_tree
    )
    adjustment_type: EnumProperty(
        items=ADJUSTMENT_TYPE_ENUM,
        name="Adjustment Type",
        description="Adjustment type",
        default='ShaderNodeBrightContrast',
        update=update_node_tree
    )
    empty_object: PointerProperty(
        name="Empty Object",
        type=Object,
        update=update_node_tree
    )
    gradient_type: EnumProperty(
        items=GRADIENT_TYPE_ENUM,
        name="Gradient Type",
        description="Gradient type",
        default='LINEAR',
        update=update_node_tree
    )
    type: EnumProperty(
        items=LAYER_TYPE_ENUM,
        default='IMAGE'
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
    enabled: BoolProperty(
        name="Enabled",
        description="Toggle layer visibility",
        default=True,
        update=update_active_channel,
        options=set()
    )
    lock_alpha: BoolProperty(
        name="Lock Alpha",
        description="Lock the alpha channel",
        default=False,
        update=update_brush_settings
    )

class Layer(BaseNestedListItem):
    """Base class for material layers in the Paint System"""
    def update_node_tree(self, context):
        global_layer = get_global_layer(self)
        if global_layer == None:
            return
        if global_layer.type == "IMAGE" and global_layer.coord_type == "AUTO":
            bpy.ops.paint_system.create_paint_system_uv_map('EXEC_DEFAULT')
        if global_layer:
            global_layer.update_node_tree(context)
    
    ref_layer_id: StringProperty()
    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer",
        update=update_node_tree
    )


class Channel(BaseNestedListManager):
    """Custom data for material layers in the Paint System"""
    
    def update_node_tree(self, context):
        if not self.node_tree:
            return
        node_builder = NodeTreeBuilder(self.node_tree, frame_name="Channel Graph", node_width=200)
        node_builder.add_node("group_input", "NodeGroupInput")
        node_builder.add_node("group_output", "NodeGroupOutput")
        flattened_layers = self.flatten_hierarchy()
        @dataclass
        class PreviousLayer:
            color_name: str
            color_socket: str
            alpha_name: str
            alpha_socket: str
            
        previous_dict: Dict[int, PreviousLayer] = {}
        if self.type == "VECTOR" and self.use_normalize:
            node_builder.add_node("normalize", "ShaderNodeVectorMath", {"operation": "MULTIPLY_ADD"}, {1: (0.5, 0.5, 0.5), 2: (0.5, 0.5, 0.5)})
        previous_dict[-1] = PreviousLayer(color_name="group_output", color_socket="Color", alpha_name="group_output", alpha_socket="Alpha")
            
        if len(flattened_layers) > 0:
            for layer, _ in flattened_layers:
                previous_data = previous_dict.get(layer.parent_id, None)
                global_layer = get_global_layer(layer)
                layer_identifier = global_layer.uid
                node_builder.add_node(layer_identifier, "ShaderNodeGroup", {"node_tree": global_layer.node_tree, "mute": not global_layer.enabled})
                # match global_layer.type:
                #     case "IMAGE":
                #         layer_name = layer.name
                #         node_builder.add_node(layer_name, "ShaderNodeGroup", {"node_tree": global_layer.node_tree})
                #     case _:
                #         pass
                node_builder.link(layer_identifier, previous_data.color_name, "Color", previous_data.color_socket)
                node_builder.link(layer_identifier, previous_data.alpha_name, "Alpha", previous_data.alpha_socket)
                previous_dict[layer.parent_id] = PreviousLayer(
                    color_name=layer_identifier,
                    color_socket="Color",
                    alpha_name=layer_identifier,
                    alpha_socket="Alpha"
                )
                if global_layer.type == "FOLDER":
                    previous_dict[layer.id] = PreviousLayer(
                        color_name=layer_identifier,
                        color_socket="Over Color",
                        alpha_name=layer_identifier,
                        alpha_socket="Over Alpha"
                    )
        prev_layer = previous_dict[-1]
        if self.type == "VECTOR" and self.use_normalize:
            node_builder.link("normalize", prev_layer.color_name, "Vector", prev_layer.color_socket)
            node_builder.link("group_input", "normalize", "Color", "Vector")
        else:
            node_builder.link("group_input", prev_layer.color_name, "Color", "Color")
        node_builder.link("group_input", prev_layer.color_name, "Alpha", "Alpha")
        node_builder.compile()
    
    def update_channel_name(self, context):
        """Update the channel name to ensure uniqueness."""
        if self.updating_name_flag:
            return
        if not self.node_tree:
            return
        self.node_tree.name = f".PS_Channel ({self.name})"
        self.updating_name_flag = True
        parsed_context = _parse_context(context)
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
    active_index: IntProperty(name="Active Material Layer Index", update=update_active_image)
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
        default=True,
        update=update_active_group
    )
    use_factor: BoolProperty(
        name="Use Factor",
        description="Use factor for the channel",
        default=False,
        update=update_node_tree
    )
    factor_min: FloatProperty(
        name="Factor Min",
        description="Minimum factor value",
        default=0,
        update=update_node_tree
    )
    factor_max: FloatProperty(
        name="Factor Max",
        description="Maximum factor value",
        default=1,
        update=update_node_tree
    )
    use_normalize: BoolProperty(
        name="Normalize",
        description="Normalize the channel",
        default=False,
        update=update_node_tree
    )
    coord_type: EnumProperty(
        items=COORDINATE_TYPE_ENUM,
        name="Coordinate Type",
        description="Coordinate type",
        default='AUTO'
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
    
    def get_movement_menu_items(self, item_id, direction):
        """
        Get menu items for movement options.
        Returns list of tuples (identifier, label, description)
        """
        options = self.get_movement_options(item_id, direction)
        menu_items = []

        # Map option identifiers to their operators
        operator_map = {
            'UP': 'paint_system.move_up',
            'DOWN': 'paint_system.move_down'
        }

        for identifier, description in options:
            menu_items.append((
                operator_map[direction],
                description,
                {'action': identifier}
            ))

        return menu_items


class Group(PropertyGroup):
    """Base class for Paint System groups"""
    def update_node_tree(self, context):
        if not self.node_tree:
            return
        node_tree = self.node_tree
        node_tree.name = f"Paint System ({self.name})"
        if not isinstance(node_tree, bpy.types.NodeTree):
            return
        
        # Ensure node sockets are in the correct order
        def detect_change(old, new):
            if len(new) > len(old):  # ADD
                for i in range(len(new)):
                    if i >= len(old) or old[i] != new[i]:
                        return "ADD", i

            elif len(new) < len(old):  # REMOVE
                for i in range(len(old)):
                    if i >= len(new) or old[i] != new[i]:
                        return "REMOVE", i

            else:  # Same length: MOVE or RENAME
                # Check if it's a MOVE
                for i in range(len(old)):
                    if old[i] != new[i]:
                        # MOVE: element exists in both lists but index changed
                        if old[i] in new and new[i] in old:
                            return "MOVE", i
                        else:
                            return "RENAME", i

            return None, None  # No change
        
        nt_interface = node_tree.interface
        nt_sockets = nt_interface.items_tree
        
        @dataclass
        class ExpectedSocket:
            name: str
            socket_type: str
            subtype: str = "NONE"
            min_value: float = 0
            max_value: float = 1
        
        expected_sockets: List[ExpectedSocket] = []
        for channel in self.channels:
            expected_sockets.append(ExpectedSocket(channel.name, f"NodeSocket{channel.type.title()}", "FACTOR" if channel.use_factor else "NONE", channel.factor_min, channel.factor_max))
            if channel.use_alpha:
                expected_sockets.append(ExpectedSocket(f"{channel.name} Alpha", "NodeSocketFloat", "FACTOR", 0, 1))
        
        def ensure_sockets(expected_sockets, in_out = "OUTPUT"):
            if in_out == "INPUT":
                offset_idx = len(expected_sockets)
            else:
                offset_idx = 0
            while True:
                output_sockets = [socket for socket in nt_sockets if socket.item_type == "SOCKET" and socket.in_out == in_out]
                output_sockets_names = [socket.name for socket in output_sockets]
                change, idx = detect_change(output_sockets_names, [socket.name for socket in expected_sockets])
                if change is None:
                    break
                match change:
                    case "ADD":
                        socket_name, socket_type, subtype = expected_sockets[idx].name, expected_sockets[idx].socket_type, expected_sockets[idx].subtype
                        socket = nt_interface.new_socket(name=socket_name, socket_type=socket_type, in_out=in_out)
                        if hasattr(socket, "subtype") and subtype:
                            socket.subtype = subtype
                            if subtype == "FACTOR":
                                socket.min_value = expected_sockets[idx].min_value
                                socket.max_value = expected_sockets[idx].max_value
                        nt_interface.move(socket, idx + offset_idx)
                    case "REMOVE":
                        socket = output_sockets[idx]
                        nt_interface.remove(socket)
                    case "MOVE":
                        socket = output_sockets[idx]
                        expected_socket_idx = [socket.name for socket in expected_sockets].index(socket.name)
                        nt_interface.move(socket, expected_socket_idx + offset_idx + 1)
                    case "RENAME":
                        socket = output_sockets[idx]
                        socket.name = expected_sockets[idx].name
            
            # ensure socket type
            for idx, socket in enumerate(output_sockets):
                if socket.socket_type != expected_sockets[idx].socket_type:
                    socket.socket_type = expected_sockets[idx].socket_type
                if hasattr(socket, "subtype") and socket.subtype != expected_sockets[idx].subtype and expected_sockets[idx].subtype:
                    socket.subtype = expected_sockets[idx].subtype
                    if expected_sockets[idx].subtype == "FACTOR":
                        socket.min_value = expected_sockets[idx].min_value
                        socket.max_value = expected_sockets[idx].max_value
                    socket.default_value = expected_sockets[idx].max_value
        
        ensure_sockets(expected_sockets, "OUTPUT")
        ensure_sockets(expected_sockets, "INPUT")
        
        node_builder = NodeTreeBuilder(self.node_tree, frame_name="Group Graph", clear=True)
        node_builder.add_node("group_input", "NodeGroupInput")
        node_builder.add_node("group_output", "NodeGroupOutput")
        for channel in self.channels:
            if not channel.node_tree or len(channel.node_tree.interface.items_tree) == 0:
                # Channel is not valid, skip it
                continue
            channel_name = channel.name
            c_alpha_name = f"{channel.name} Alpha"
            node_builder.add_node(channel_name, "ShaderNodeGroup", {"node_tree": channel.node_tree}, {"Alpha": 1})
            node_builder.link("group_input", channel_name, channel_name, "Color")
                
            if channel.use_alpha:
                node_builder.link("group_input", channel_name, c_alpha_name, "Alpha")
            node_builder.link(channel_name, "group_output", "Color", channel_name)
            if channel.use_alpha:
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
    active_index: IntProperty(name="Active Channel Index", update=update_active_image)
    node_tree: PointerProperty(
        name="Node Tree",
        type=NodeTree
    )

class PaintSystemGlobalData(PropertyGroup):
    """Custom data for the Paint System"""
    clipboard_layers: CollectionProperty(
        type=Layer,
        name="Clipboard Layers",
        description="Collection of layers in the clipboard"
    )
    layers: CollectionProperty(
        type=GlobalLayer,
        name="Paint System Layers",
        description="Collection of layers in the Paint System"
    )
    active_index: IntProperty(name="Active Layer Index")
    active_clipboard_index: IntProperty(name="Active Clipboard Layer Index")

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
    preview_channel: BoolProperty(
        name="Preview Channel",
        description="Preview the channel",
        default=False
    )
    original_node_name: StringProperty(
        name="Original Node Name",
        description="Original node name of the channel"
    )
    original_socket_name: StringProperty(
        name="Original Socket Name",
        description="Original socket name of the channel"
    )


def get_global_layer(layer: Layer) -> GlobalLayer | None:
    """Get the global layer data from the context."""
    if not layer or not bpy.context.scene or not bpy.context.scene.get("ps_scene_data"):
        return None
    for global_layer in bpy.context.scene.ps_scene_data.layers:
        if global_layer.uid == layer.ref_layer_id:
            return global_layer
    return None

def is_global_layer_linked(global_layer: GlobalLayer) -> bool:
    """Check if the global layer is linked"""
    # Check all material in the scene and count the number of times the global layer is used
    count = 0
    for material in bpy.data.materials:
        if hasattr(material, 'ps_mat_data'):
            for group in material.ps_mat_data.groups:
                for channel in group.channels:
                    for layer in channel.layers:
                        if layer.ref_layer_id == global_layer.uid:
                            count += 1
    return count > 1

def sort_actions(context: bpy.types.Context, global_layer: GlobalLayer) -> list[MarkerAction]:
    sorted_actions = []
    if global_layer.actions:
        for action in global_layer.actions:
            if action.action_bind == 'FRAME':
                sorted_actions.append((action.frame, action))
            elif action.action_bind == 'MARKER':
                marker = context.scene.timeline_markers.get(action.marker_name)
                if marker:
                    sorted_actions.append((marker.frame, action))
                else:
                    sorted_actions.append((0, action))
        sorted_actions.sort(key=lambda x: x[0])
    return [x for _, x in sorted_actions]

def get_all_layers(material: bpy.types.Material) -> list[Layer]:
    layers = []
    if not material or not material.ps_mat_data:
        return layers
    for group in material.ps_mat_data.groups:
        for channel in group.channels:
            for layer in channel.layers:
                layers.append(layer)
    return layers
@dataclass
class PSContext:
    ps_settings: PaintSystemPreferences | None = None
    ps_scene_data: PaintSystemGlobalData | None = None
    active_object: bpy.types.Object | None = None
    ps_object: bpy.types.Object | None = None
    active_material: bpy.types.Material | None = None
    ps_mat_data: MaterialData | None = None
    active_group: Group | None = None
    active_channel: Channel | None = None
    active_layer: Layer | None = None
    active_global_layer: GlobalLayer | None = None


def parse_context(context: bpy.types.Context) -> PSContext:
    """Parse the context and return a PSContext object."""
    parsed_context = _parse_context(context)
    return PSContext(
        ps_settings=parsed_context.get("ps_settings"),
        ps_scene_data=parsed_context.get("ps_scene_data"),
        active_object=parsed_context.get("active_object"),
        ps_object=parsed_context.get("ps_object"),
        active_material=parsed_context.get("active_material"),
        ps_mat_data=parsed_context.get("ps_mat_data"),
        active_group=parsed_context.get("active_group"),
        active_channel=parsed_context.get("active_channel"),
        active_layer=parsed_context.get("active_layer"),
        active_global_layer=parsed_context.get("active_global_layer")
    )

class PSContextMixin:
    """A mixin for classes that need access to the paint system context."""

    @staticmethod
    def ensure_context(context: bpy.types.Context) -> PSContext:
        """Return a PSContext parsed from Blender context. Safe to call from class or instance methods."""
        return parse_context(context)

    @staticmethod
    def parse_context(context: bpy.types.Context) -> dict:
        """Parse the context and return a plain dict. Provided for convenience."""
        return _parse_context(context)

classes = (
    MarkerAction,
    GlobalLayer,
    Layer,
    Channel,
    Group,
    PaintSystemGlobalData,
    MaterialData,
    )

@persistent
def save_handler(scene: bpy.types.Scene):
    print("Saving Paint System data...")
    images = []
    ps_ctx = parse_context(bpy.context)
    for layer in ps_ctx.ps_scene_data.layers:
        image = layer.image
        if image and (image.is_dirty):
            images.append(image)
        mask_image = layer.mask_image
        if mask_image and (mask_image.is_dirty):
            images.append(mask_image)
            
    for image in images:
        if not image.is_dirty:
            continue
        if image.packed_file or image.filepath == '':
            image.pack()
        else:
            image.save()


@persistent
def refresh_image(scene: bpy.types.Scene):
    ps_ctx = parse_context(bpy.context)
    active_layer = ps_ctx.active_layer
    if active_layer and active_layer.image:
        active_layer.image.reload()

_register, _unregister = register_classes_factory(classes)

def register():
    """Register the Paint System data module."""
    _register()
    bpy.types.Scene.ps_scene_data = PointerProperty(
        type=PaintSystemGlobalData,
        name="Paint System Data",
        description="Data for the Paint System"
    )
    bpy.types.Material.ps_mat_data = PointerProperty(
        type=MaterialData,
        name="Paint System Material Data",
        description="Material Data for the Paint System"
    )
    bpy.app.handlers.save_pre.append(save_handler)
    bpy.app.handlers.load_post.append(refresh_image)
    
def unregister():
    """Unregister the Paint System data module."""
    bpy.app.handlers.save_pre.remove(save_handler)
    bpy.app.handlers.load_post.remove(refresh_image)
    del bpy.types.Material.ps_mat_data
    del bpy.types.Scene.ps_scene_data
    _unregister()