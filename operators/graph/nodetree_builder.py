import bpy
from bpy.utils import register_classes_factory
from mathutils import Vector, Color
from typing import Dict, List, Union, Sequence, Set
from dataclasses import dataclass, field
from uuid import uuid4
from ..utils.timing_decorator import timing_decorator

# --- Special Identifiers for Graph Start and End ---
# START doesn't map to a real node, it's a conceptual entry point.
# In our context, we'll often connect from nodes that don't need inputs,
# like Texture Coordinate or Geometry.
START = "START_"

# END maps to the final output node of the tree, which is usually 'Material Output'.
END = "END_"

SOCKET_TYPES = ('NodeSocketFloat', 'NodeSocketInt', 'NodeSocketBool',
                'NodeSocketVector', 'NodeSocketColor', 'NodeSocketShader', 'NodeSocketImage')


def get_main_socket_type(socket_type: str) -> str:
    """
    Returns the main socket type of a node based on its outputs.

    Args:
        node (bpy.types.Node): The Blender node to inspect.

    Returns:
        str: The bl_idname of the first output socket, or None if no outputs exist.
    """
    for socket in SOCKET_TYPES:
        if socket_type.startswith(socket):
            return socket
    return None


@dataclass
class Edge:
    """
    Represents a connection (edge) between two nodes in the node graph.

    Attributes:
        source (str): The name of the source node.
        target (str): The name of the target node.
        source_socket (str or int): The output socket on the source node.
        target_socket (str or int): The input socket on the target node.
    """
    source: str
    target: str
    source_socket: Union[str, int] = "Default"
    target_socket: Union[str, int] = "Default"


@dataclass
class Add_Node:
    """
    Represents a node to be added to the node graph.
    Attributes:
        identifier (str): A unique name for the node, used to refer to it in connections.
        node_type (str): The Blender identifier for the node type (e.g., 'ShaderNodeTexNoise').
        properties (dict, optional): A dictionary of properties to set on the node after creation.
    """
    identifier: str
    node_type: str
    properties: dict = None
    default_values: dict = None  # Default values for input sockets, if any
    

@dataclass
class LayerInfo:
    """
    Represents a layer of nodes in the node graph.
    Attributes:
        name (str): The name of the layer.
        nodes (List[str]): A list of node names in this layer.
    """
    width: float = 0
    height: float = 0
    nodes: List[str] = field(default_factory=list)


class NodeTreeBuilder:
    """
    A class to construct Blender node trees in a declarative, graph-based manner.

    This class allows you to define a node graph by adding named nodes and
    specifying the edges (links) between them, similar to libraries like LangGraph.
    Once the graph is defined, the `compile` method builds the actual node tree.
    """

    def __init__(self, node_tree: bpy.types.NodeTree, frame_name="", frame_color:Sequence[float]=None, clear=False, node_width=140):
        """
        Initializes the NodeTreeBuilder.

        Args:
            node_tree (bpy.types.NodeTree): The node tree to build upon (e.g., material.node_tree).
            frame_name (str, optional): The name of the frame. Defaults to None.
            clear (bool): If True, clears the existing nodes in the tree except for the output node.
            node_width (int): The width of the nodes when arranged in the graph.
        """
        if not node_tree:
            raise ValueError("A valid node_tree must be provided.")

        self._id = str(uuid4())  # Unique identifier for this graph instance
        self.tree = node_tree
        self.node_width: float = node_width
        # Stores nodes added by the user, mapping name -> bpy.types.Node
        self.nodes: Dict[str, bpy.types.Node] = {}
        # Stores commands to add nodes
        self.__add_nodes_commands: List[Add_Node] = []
        self.edges: List[Edge] = []  # Stores the connections to be made
        self.compiled = False  # Flag to indicate if the graph has been compiled
        self.frame = self.tree.nodes.new(type='NodeFrame')
        self.sub_graphs: Set['NodeTreeBuilder'] = set()  # List of subgraphs if any
        self.width = 0 # Width of the graph
        self.node_links = []
        self.node_offset = Vector((0, 0))
        
        self.__min_x_pos = 0
        self.__max_x_pos = 0
        
        self.frame.name = self._id if not frame_name else frame_name
        self.frame.label = frame_name
        if frame_color:
            self.frame.use_custom_color = True
            self.frame.color = Color(frame_color)

        if clear:
            self.clear_tree()

        # --- Identify the final output node ---
        # This node will be our 'END' point.
        
    def __str__(self):
        return self.frame.name

    def clear_tree(self, clean: bool = False):
        """        Clears the node tree, removing all nodes except the output node.
        Args:
            clean (bool): If True, removes all nodes including the START and END node.
                          If False, keeps the START and END node intact.
        """
        
        try:
            for link in self.node_links:
                # if link in self.tree.links:   
                    self.tree.links.remove(link)
        except Exception as e:
            print(f"Error removing links: {e}")
            
        for node_name in list(self.nodes.keys()):
            node = self.nodes[node_name]
            if isinstance(node, NodeTreeBuilder):
                continue
            if node.type == 'REROUTE' and (node.name.startswith(START) or node.name.startswith(END)):
                # Keep START and END nodes if clean is False
                if not clean:
                    continue
            self.tree.nodes.remove(node)
            del self.nodes[node_name]

        if clean:
            for idx, edge in enumerate(self.edges):
                if edge.source.startswith(START):
                    self.edges[idx].source = START
                if edge.target.startswith(END):
                    self.edges[idx].target = END
        #     self.tree.nodes.remove(self.frame)
        #     self.frame = None
        
        self.compiled = False  # Reset compiled state

    def add_node(self, identifier: str, node_type: str, properties: dict = None, default_values: dict = None):
        # Store the command to add a node
        """
        Adds a node to the graph definition.

        Args:
            identifier (str): A unique name for the node, used to refer to it in connections.
            node_type (str): The Blender identifier for the node (e.g., 'ShaderNodeTexNoise').
            properties (dict, optional): A dictionary of properties to set on the node after creation.
                                         For example: {'noise_dimensions': '4D'}. Defaults to None.

        Returns:
            The created Blender node object.
        """
        if identifier in self.nodes:
            raise ValueError(
                f"Node with identifier '{identifier}' already exists. Use a unique identifier.")

        self.__add_nodes_commands.append(
            Add_Node(identifier=identifier, node_type=node_type, properties=properties, default_values=default_values))

    def _add_node(self, identifier: str, node_type: str, properties: dict = None, default_values: dict = None):
        """
        Adds a node to the graph definition.

        Args:
            node_type (str): The Blender identifier for the node (e.g., 'ShaderNodeTexNoise').
            properties (dict, optional): A dictionary of properties to set on the node after creation.
                                         For example: {'noise_dimensions': '4D'}. Defaults to None.

        Returns:
            The created Blender node object.
        """

        # Create the actual node in the node tree
        node = self.tree.nodes.new(type=node_type)
        node_name = identifier  # Set the Blender internal name for clarity
        node.parent = self.frame  # Set the parent frame for organization
        node.width = self.node_width
        self.nodes[node_name] = node

        # Set custom properties if provided
        if properties:
            for key, value in properties.items():
                if hasattr(node, key):
                    setattr(node, key, value)
                else:
                    print(
                        f"Warning: Property '{key}' not found on node type '{node_type}'")
        
        # --- Set Input Default Values ---
        # If a default_values dictionary is provided, iterate through it
        if default_values:
            for input_name, value in default_values.items():
                # Check if the input socket exists on the node
                if input_name in node.inputs:
                    try:
                        node.inputs[input_name].default_value = value
                    except Exception as e:
                        print(f"Warning: Could not set default value for input '{input_name}' to '{value}'. Error: {e}")
                else:
                    print(f"Warning: Input socket '{input_name}' not found on node type '{node_type}'.")

        # return node_name

    def link(self, source: str, target: str, source_socket=None, target_socket=None):
        """
        Defines an edge (link) between two nodes.

        The connection is stored and will be created when `compile()` is called.

        Args:
            source_name (str, NodeTreeBuilder): The name of the source node. Can be START or NodeTreeBuilder
            target_name (str, NodeTreeBuilder): The name of the target node. Can be END or NodeTreeBuilder
            source_socket (str or int): The name or index of the output socket on the source node.
            target_socket (str or int): The name or index of the input socket on the target node.
        """
        # Check if the source and target are valid
        if isinstance(source, NodeTreeBuilder):
            # print("Source is a NodeTreeBuilder")
            self.nodes[str(source)] = source
            self.sub_graphs.add(source)
        elif isinstance(source, str):
            if source == END:
                raise ValueError(
                    "Cannot connect from END. END is a conceptual exit point, not a node.")
        else:
            raise ValueError(
                "Source must be a NodeTreeBuilder instance or a string representing a node name.")

        if isinstance(target, NodeTreeBuilder):
            # print("Target is a NodeTreeBuilder")
            self.nodes[str(target)] = target
            self.sub_graphs.add(target)
        elif isinstance(target, str):
            if target == START:
                raise ValueError(
                    "Cannot connect to START. START is a conceptual entry point, not a node.")
        else:
            raise ValueError(
                "Target must be a NodeTreeBuilder instance or a string representing a node name.")

        self.edges.append(Edge(source, target, source_socket, target_socket))
        
    def unlink(self, source: str, target: str):
        """
        Removes a link between two nodes.

        Args:
            source (str): The name of the source node.
            target (str): The name of the target node.
        """
        # Find the edge to remove
        edge_to_remove = None
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                edge_to_remove = edge
                break
        
        if edge_to_remove:
            self.edges.remove(edge_to_remove)
        else:
            print(f"No link found between '{source}' and '{target}'.")
        
    def _get_socket_by_prefix(self, is_input_socket: bool, socket_name: str) -> Union[tuple[bpy.types.Node, bpy.types.NodeSocket], tuple[None, None]]:
        """
        Helper function to find a node and socket based on a name prefix.

        Args:
            is_input (bool): If True, searches in outputs (START nodes), otherwise in inputs (END nodes).
            socket_name (str): The name of the socket to find.

        Returns:
            bpy.types.Node, bpy.types.NodeSocket: The node and socket if found, otherwise None.
        """
        prefix = START if is_input_socket else END
        # print(f"Searching for {'input' if is_input_socket else 'output'} socket with prefix '{prefix}' and name '{socket_name}'")
        for node in self.nodes.values():
            if node.type != 'REROUTE':
                continue
            socket = node.inputs[0] if is_input_socket else node.outputs[0]
            if node.name.startswith(f"{prefix}{socket_name}"):
                return node, socket
        return None, None

    def get_output(self, output_name: str):
        """
        Retrieves an output node and socket based on the output name.

        Args:
            nodetree_builder (NodeTreeBuilder): The NodeTreeBuilder instance to search in.
            output_name (str): The name of the output to find.

        Returns:
            Tuple[bpy.types.Node, bpy.types.NodeSocket]: The output node and socket.

        Raises:
            ValueError: If no output node or socket is found for the given name.
        """
        node, sock = self._get_socket_by_prefix(False, output_name)
        if node is None:
            raise ValueError(f"{self.frame.name} No output node found for '{output_name}'. Ensure it is connected to END.")
        if sock is None:
            raise ValueError(f"{self.frame.name} No output socket found for '{output_name}' on node '{node.name}'.")
        return node, sock
    
    def get_input(self, input_name: str):
        """
        Retrieves an input node and socket based on the input name.

        Args:
            nodetree_builder (NodeTreeBuilder): The NodeTreeBuilder instance to search in.
            input_name (str): The name of the input to find.

        Returns:
            Tuple[bpy.types.Node, bpy.types.NodeSocket]: The input node and socket.

        Raises:
            ValueError: If no input node or socket is found for the given name.
        """
        node, sock = self._get_socket_by_prefix(True, input_name)
        if node is None:
            raise ValueError(f"No input node found for '{input_name}'. Ensure it is connected to START.")
        if sock is None:
            raise ValueError(f"No input socket found for '{input_name}' on node '{node.name}'.")
        return node, sock

    def _create_reroute_node(self, socket_name: str, is_input_socket: bool, edge_idx: int) -> tuple:
        """
        Creates a NodeReroute node, sets its name, label, and parent.
        It also configures the relevant input/output socket and updates the edge
        to point to this newly created reroute node.
        
        Args:
            prefix (str): "START" or "END" to form the node name.
            socket_name (str): The name to assign to the reroute node's socket.
            is_input_socket (bool): True if creating an input reroute (for END),
                                     False if creating an output reroute (for START).
            edge_idx (int): The index of the current edge in `self.edges` to update its source/target.
            
        Returns:
            tuple: A tuple containing the created reroute node and its configured socket.
        """
        prefix = END if is_input_socket else START
        reroute_node = self.tree.nodes.new(type='NodeReroute')
        full_name = f"{prefix}{socket_name}"
        reroute_node.name = full_name
        reroute_node.label = socket_name
        reroute_node.parent = self.frame
        self.nodes[reroute_node.name] = reroute_node # Store the new node

        if is_input_socket:
            sock = reroute_node.inputs[0]
            self.edges[edge_idx].target = reroute_node.name # Update edge target
        else:
            sock = reroute_node.outputs[0]
            self.edges[edge_idx].source = reroute_node.name # Update edge source
            
        sock.name = socket_name # Name the reroute socket
        return reroute_node, sock

    def _resolve_node_and_socket(self, identifier, socket_name: str, is_source: bool, edge_idx: int) -> tuple:
        """
        Resolves a node and its specific socket based on the identifier provided in an edge.
        This function handles:
        1. Nested NodeTreeBuilder instances (compiles them if necessary).
        2. Special 'START'/'END' keywords by creating Reroute nodes.
        3. Existing nodes identified by their name string.
        
        Args:
            identifier: The value from `edge.source` or `edge.target` (can be a string or NodeTreeBuilder instance).
            socket_name (str): The name of the socket to find (e.g., "Output", "Color", etc.).
            is_source (bool): True if resolving a source node (looking for an output socket),
                              False if resolving a target node (looking for an input socket).
            edge_idx (int): The index of the current edge in `self.edges`, used to update `edge.source`/`edge.target`
                            if a new reroute node is created.

        Returns:
            tuple: A tuple containing the resolved node object and its corresponding socket object.
        
        Raises:
            ValueError: If a node is not found or a specified socket does not exist on the node.
        """
        node = None
        sock = None
        
        if isinstance(identifier, NodeTreeBuilder):
            # Handle nested NodeTreeBuilder instances
            if not identifier.compiled:
                identifier.compile()
            identifier.frame.parent = self.frame # Ensure nested graph's frame is parented correctly
            
            if is_source:
                node, sock = identifier.get_output(socket_name)
            else:
                node, sock = identifier.get_input(socket_name)
        
        elif isinstance(identifier, str):
            # Handle special START/END keywords
            if is_source and identifier == START:
                # Try to find node by prefix and create a reroute node if not found
                # node, sock = self._get_socket_by_prefix(False, socket_name)
                node = next((node for node in self.nodes.values() if node.name.startswith(f"{START}{socket_name}")), None)
                if not node:
                    node, sock = self._create_reroute_node(socket_name, False, edge_idx)
                else:
                    sock = node.outputs[0]
            elif not is_source and identifier == END:
                # Try to find node by prefix and create a reroute node if not found
                node = next((node for node in self.nodes.values() if node.name.startswith(f"{END}{socket_name}")), None)
                if not node:
                    node, sock = self._create_reroute_node(socket_name, True, edge_idx)
                else:
                    sock = node.inputs[0]
            else:
                # Assume it's the name of an existing node
                node = self.nodes.get(identifier)
                if node is None:
                    raise ValueError(f"Node '{identifier}' not found in the current tree's nodes.")

                # Retrieve the socket based on node type
                if node.type != 'REROUTE':
                    # For most nodes, get socket by name from inputs/outputs collection
                    if is_source:
                        sock = node.outputs.get(socket_name)
                    else:
                        sock = node.inputs.get(socket_name)
                else:
                    # Reroute nodes typically have only one input and one output socket
                    if is_source:
                        sock = node.outputs[0]
                    else:
                        sock = node.inputs[0]

        # Final check if a socket was successfully found
        if sock is None:
            node_name = getattr(node, 'name', 'Unknown Node') # Safe access to node name
            socket_type_str = "output" if is_source else "input"
            raise ValueError(
                f"Required {socket_type_str} socket '{socket_name}' not found on node '{node_name}' (type: {getattr(node, 'type', 'Unknown')})."
            )
        
        return node, sock

    @timing_decorator("Node Tree Compilation")
    def compile(self, arrange_nodes: bool = True) -> 'NodeTreeBuilder':
        """
        Builds the node tree by creating all the defined links and arranging the nodes.
        """
        # If already compiled, recompile
        if self.compiled:
            print("Graph already compiled. Recompiling...")
            self.clear_tree() # Clear existing nodes and links
            self.compiled = False
        
        # Add all pre-defined nodes to the tree
        for command in self.__add_nodes_commands:
            self._add_node(command.identifier,
                            command.node_type, command.properties, command.default_values)

        # --- Create the links between nodes ---
        for idx, edge in enumerate(self.edges):
            # Resolve the source node and its specific output socket
            source_node, source_sock = self._resolve_node_and_socket(
                edge.source, edge.source_socket, is_source=True, edge_idx=idx
            )
            
            # Resolve the target node and its specific input socket
            target_node, target_sock = self._resolve_node_and_socket(
                edge.target, edge.target_socket, is_source=False, edge_idx=idx
            )

            # Create the link between the resolved source and target sockets
            self.node_links.append(self.tree.links.new(source_sock, target_sock))

        # --- Arrange nodes for clarity (simple horizontal layout) ---
        if arrange_nodes:
            self._arrange_nodes()
        self.compiled = True
        self.tree.update_tag()
        self.frame.width = self.width
        return self

    def _arrange_nodes(self):
        """A simple node arrangement algorithm."""

        # --- 1. Determine End Nodes by Analyzing Connections ---
        # An "end node" is any node within the graph that does not serve as a
        # source for any defined edge. These are the leaves of the graph.
        source_node_names = {str(edge.source) for edge in self.edges}
        # print(f"Source nodes: {source_node_names}")
        
        end_node_names = [name for name in self.nodes if name not in source_node_names]
        
        # print(f"End nodes: {end_node_names}")
        
        # --- 2. Calculate Node Levels with a Backwards Traversal ---
        # We traverse from the end nodes (level 0) backwards. A node's level is
        # its longest path distance from an end node.
        level_map: dict[str, int] = {}  # Stores {node_name: level}
        nodes_to_process = []
        
        for name in end_node_names:
            if name not in level_map:
                level_map[name] = 0
                nodes_to_process.append(name)
                
        # all_edges = [*self.edges, *[edge for subgraph in self.sub_graphs for edge in subgraph.edges]]
        # print(all_edges)
        layer_infos: Dict[int, LayerInfo] = {}
        
        while nodes_to_process:
            current_node_name = nodes_to_process.pop(0)
            current_level = level_map[current_node_name]

            # Find nodes that connect to the current node
            for edge in self.edges:
                if str(edge.target) == current_node_name:
                    source_node_name = str(edge.source)
                    level_map[source_node_name] = max(
                        current_level + 1, level_map.get(source_node_name, 1))
                    nodes_to_process.append(source_node_name)
        
        # print(f"Level map after processing: {level_map}")
                    
        NODE_MARGIN = 20  # Margin between nodes
        
        for name, level in list(level_map.items()):
            if level not in layer_infos:
                layer_infos[level] = LayerInfo()
            for sub_graph in self.sub_graphs:
                if name == str(sub_graph):
                    layer_infos[level].width = sub_graph.width
            else:
                layer_infos[level].width = max(layer_infos[level].width, 0 if name.startswith(START) or name.startswith(END) else self.node_width)
            layer_infos[level].nodes.append(name)
        
        # print("Layer Info:", layer_infos)
        
        def calculate_node_position(name: str, node: bpy.types.Node):
            current_level = level_map.get(name, 1)
            current_level_info = layer_infos.get(current_level, LayerInfo())
            # print(f"Calculating position for node '{name}' at level {current_level} with current level info: {current_level_info}")
            x_pos = -1 * (sum(layer_infos[l].width for l in range(current_level)) + current_level * NODE_MARGIN)
            y_pos = 200
            if not isinstance(node, NodeTreeBuilder):
                if node.type != "FRAME":
                    x_pos -= current_level_info.width
                if node.type == 'REROUTE':
                    y_pos = current_level_info.height
                    current_level_info.height -= NODE_MARGIN
                else:
                    y_pos = current_level_info.height
                    current_level_info.height -= 200 + NODE_MARGIN
            self.__min_x_pos = min(self.__min_x_pos, x_pos)
            self.__max_x_pos = max(self.__max_x_pos, x_pos + current_level_info.width)
            return x_pos, y_pos
        
        for name, node in self.nodes.items():
            x_pos, y_pos = calculate_node_position(name, node)
            # print(f"Positioning node {name} at level {current_level} with x={x_pos}, y={y_pos}")
            pos = Vector((x_pos, y_pos)) + self.node_offset
            if isinstance(node, NodeTreeBuilder):
                node.set_node_offset(pos)
            else:
                node.location_absolute = pos
        self.width = self.__max_x_pos - self.__min_x_pos + 35*2
    
    def set_node_offset(self, offset: Vector):
        """
        Offsets all nodes in the graph by a given vector.

        Args:
            offset (Vector): The offset to apply to each node's location.
        """
        self.node_offset = offset
        self._arrange_nodes()  # Re-arrange nodes after setting the offset


# --- Example Usage within a Blender Operator ---

class EXAMPLE_OT_BuildMyNodeTree(bpy.types.Operator):
    """Builds a sample node tree using the NodeTreeBuilder"""
    bl_idname = "object.build_my_node_tree"
    bl_label = "Build Sample Node Tree"

    def execute(self, context):
        # --- 1. Setup: Get or create a material ---
        # material_name = "NodeBuilderMaterial"
        # mat = bpy.data.materials.get(material_name)

        # if mat is None:
        #     mat = bpy.data.materials.new(name=material_name)

        # mat.use_nodes = True
        snode = context.space_data
        group = snode.edit_tree
        node_tree = group if group else context.material.node_tree
        
        for node in node_tree.nodes:
            node_tree.nodes.remove(node)

        # --- 2. Instantiate the builder ---
        graph_builder = NodeTreeBuilder(
            node_tree, frame_name="Sub Graph", frame_color=(0.27083, 0.130401, 0.130401), clear=True)

        # --- 3. Add Nodes ---
        # The first argument is the unique name we'll use to refer to the node.
        # The second argument is the Blender node type.
        graph_builder.add_node("tex_coord", "ShaderNodeTexCoord")
        graph_builder.add_node("noise_texture", "ShaderNodeTexNoise", properties={
                               'noise_dimensions': '4D'}, default_values={'Scale': 10})
        graph_builder.add_node("color_ramp", "ShaderNodeValToRGB")
        graph_builder.add_node("color_ramp2", "ShaderNodeValToRGB")
        graph_builder.add_node("color_ramp3", "ShaderNodeValToRGB")
        graph_builder.add_node("principled_shader", "ShaderNodeBsdfPrincipled")
        graph_builder.add_node("shader_to_rgb", "ShaderNodeShaderToRGB")
        graph_builder.add_node("mix_rgb", "ShaderNodeMix", properties={
                               'blend_type': 'MULTIPLY', 'data_type': 'RGBA'})

        # --- 4. Add Edges (Define the graph flow) ---
        # An edge from START indicates this is an entry point to the graph.
        # graph_builder.add_edge(START, tex_coord)

        # Connect nodes using their unique names. We can specify sockets by name or index.
        # Using "Default" will try to find the first valid connection.
        graph_builder.link("tex_coord", "noise_texture",
                              source_socket="Generated", target_socket="Vector")
        graph_builder.link("noise_texture", "color_ramp",
                              source_socket="Fac", target_socket="Fac")
        graph_builder.link("noise_texture", "color_ramp2",
                              source_socket="Fac", target_socket="Fac")
        graph_builder.link("color_ramp", "principled_shader",
                              source_socket="Color", target_socket="Base Color")
        graph_builder.link("color_ramp3", "principled_shader",
                              source_socket="Color", target_socket="Alpha")
        graph_builder.link("noise_texture", "principled_shader",
                              source_socket="Fac", target_socket="Roughness")
        graph_builder.link("principled_shader", "shader_to_rgb",
                              source_socket="BSDF", target_socket="Shader")
        graph_builder.link("mix_rgb", "noise_texture",
                              source_socket="Result", target_socket="W")

        # An edge to END connects to the final output node.
        graph_builder.link("shader_to_rgb", END,
                              source_socket="Color", target_socket="Color")
        graph_builder.link("shader_to_rgb", END,
                              source_socket="Alpha", target_socket="Alpha")
        graph_builder.link("shader_to_rgb", END,
                              source_socket="Alpha", target_socket="Alpha")

        graph_builder.link(
            START, "mix_rgb", source_socket="Color", target_socket="A")
        graph_builder.link(
            START, "mix_rgb", source_socket="Alpha", target_socket="Factor")
        
        graph_builder2 = NodeTreeBuilder(
            node_tree, frame_name="Graph 2")
        graph_builder2.add_node("mix_rgb", "ShaderNodeMix",
                            properties={'data_type': 'RGBA'})
        graph_builder2.link(
            START, "mix_rgb", source_socket="Color", target_socket="A")
        graph_builder2.link(
            START, "mix_rgb", source_socket="Alpha", target_socket="Factor")
        graph_builder2.link(
            START, "mix_rgb", source_socket="Alpha", target_socket="B")
        graph_builder2.link(
            "mix_rgb", END, source_socket="Result", target_socket="Color")
        
        graph_builder3 = NodeTreeBuilder(
            node_tree, frame_name="Graph 3")
        graph_builder3.add_node("mix_rgb", "ShaderNodeMix",
                            properties={'data_type': 'RGBA'})
        graph_builder3.link(
            START, "mix_rgb", source_socket="Color", target_socket="A")
        graph_builder3.link(
            "mix_rgb", END, source_socket="Result", target_socket="Color")

        main_graph = NodeTreeBuilder(node_tree)
        main_graph.link(
            graph_builder, graph_builder2, source_socket="Color", target_socket="Color")
        main_graph.link(
            graph_builder, graph_builder2, source_socket="Alpha", target_socket="Alpha")
        main_graph.link(
            graph_builder, graph_builder2, source_socket="Alpha", target_socket="Alpha")
        main_graph.link(
            graph_builder2, graph_builder3, source_socket="Color", target_socket="Color")

        main_graph.compile()
        
        # graph_builder.compile()
        graph_builder.link("color_ramp2", "color_ramp3",
                              source_socket="Color", target_socket="Fac")
        graph_builder2.add_node("mix_rgb2", "ShaderNodeMix",
                            properties={'data_type': 'RGBA'})
        graph_builder2.link(
            "mix_rgb", "mix_rgb2", source_socket="Result", target_socket="A")
        graph_builder2.link(
            "mix_rgb2", END, source_socket="Result", target_socket="Color")
        graph_builder.clear_tree()
        graph_builder2.clear_tree(True)
        main_graph.compile()
        # graph_builder.clear_tree(clean=True)

        self.report({'INFO'}, 'Successfully built the node tree.')
        return {'FINISHED'}


class EXAMPLE_PT_NodeTreeBuilderPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node Builder"
    bl_label = "Node Tree Builder"
    bl_idname = "NODE_PT_node_tree_builder"

    def draw(self, context):
        layout = self.layout
        layout.operator(EXAMPLE_OT_BuildMyNodeTree.bl_idname,
                        text="Build Sample Node Tree")
        
        active_node = context.active_node
        if active_node and hasattr(active_node, 'name'):
            layout.label(text=f"Active Node: {active_node.name}")
            layout.label(text=f"Node Type: {active_node.bl_idname}"
                           f" ({active_node.type})")
            layout.label(text=f"Node Location: {active_node.location[0]:.2f}, {active_node.location[1]:.2f}")
            layout.label(text=f"Node Location: {active_node.location_absolute[0]:.2f}, {active_node.location_absolute[1]:.2f}")
            layout.prop(active_node, "name", text="Node Name")
            layout.prop(active_node, "width", text="Node Width")


classes = (
    EXAMPLE_OT_BuildMyNodeTree,
    EXAMPLE_PT_NodeTreeBuilderPanel,
)

register, unregister = register_classes_factory(classes)
