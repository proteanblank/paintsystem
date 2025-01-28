import bpy
from bpy.types import Operator, Context, Node, NodeTree
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem
from typing import List, Tuple
from mathutils import Vector
from .common import redraw_panel, map_range

IMPOSSIBLE_NODES = (
    "ShaderNodeShaderInfo"
)
REQUIRES_INTERMEDIATE_STEP = (
    "ShaderNodeShaderToRGB"
)


def get_connected_nodes(output_node: Node) -> List[Node]:
    """
    Gets all nodes connected to the given output_node, 
    maintaining the order in which they were found and removing duplicates.

    Args:
        node: The output node.

    Returns:
        A list of nodes, preserving the order of discovery and removing duplicates.
    """

    nodes = []
    visited = set()  # Here's where the set is used

    def traverse(node: Node):
        if node not in visited:  # Check if the node has been visited
            visited.add(node)  # Add the node to the visited set
            nodes.append(node)
            for input in node.inputs:
                for link in input.links:
                    traverse(link.from_node)

    traverse(output_node)
    return nodes


def get_active_material_output(node_tree: NodeTree) -> Node:
    """Get the active material output node

    Args:
        node_tree (bpy.types.NodeTree): The node tree to check

    Returns:
        bpy.types.Node: The active material output node
    """
    for node in node_tree.nodes:
        if node.bl_idname == "ShaderNodeOutputMaterial" and node.is_active_output:
            return node
    return None


def is_bakeable(context: Context) -> Tuple[bool, str, List[Node]]:
    """Check if the node tree is multi-user

    Args:
        context (bpy.types.Context): The context to check

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating if the node tree is multi-user and an error message if any
    """
    ps = PaintSystem(context)
    active_group = ps.get_active_group()
    mat = ps.get_active_material()
    if not mat:
        return False, "No active material found.", []
    if not mat.use_nodes:
        return False, "Material does not use nodes.", []
    if not mat.node_tree:
        return False, "Material has no node tree.", []
    if not mat.node_tree.nodes:
        return False, "Material node tree has no nodes.", []
    output_node = get_active_material_output(mat.node_tree)
    if not output_node:
        return False, "No active material output node found.", []
    node_tree = active_group.node_tree

    connected_nodes = get_connected_nodes(output_node)

    ps_groups = []
    impossible_nodes = []

    for node in connected_nodes:
        if node.bl_idname == "ShaderNodeGroup" and node.node_tree == node_tree:
            ps_groups.append(node)
        if node.bl_idname in IMPOSSIBLE_NODES:
            impossible_nodes.append(node)

    if len(ps_groups) != 1:
        print(len(ps_groups))
        return False, "Paint System group is not found or used multiple times.", ps_groups
    if impossible_nodes:
        return False, "Unsupported nodes found.", impossible_nodes

    return True, "", []


def setup_render_settings(bake_type):
    """Setup render settings appropriate for the bake type"""
    cycles = bpy.context.scene.cycles

    # Store original settings
    original_settings = {
        'samples': cycles.samples,
        'use_denoising': cycles.use_denoising,
        'use_adaptive_sampling': cycles.use_adaptive_sampling
    }

    # Configure settings based on bake type
    if bake_type == 'COMBINED':
        cycles.samples = 256
        cycles.use_denoising = True
        cycles.use_adaptive_sampling = True
    elif bake_type == 'DIFFUSE':
        cycles.samples = 128
        cycles.use_denoising = True
        cycles.use_adaptive_sampling = True
    elif bake_type == 'NORMAL':
        cycles.samples = 16
        cycles.use_denoising = False
        cycles.use_adaptive_sampling = False
    elif bake_type == 'ROUGHNESS':
        cycles.samples = 4
        cycles.use_denoising = False
        cycles.use_adaptive_sampling = False
    elif bake_type == 'EMISSION':
        cycles.samples = 1
        cycles.use_denoising = False
        cycles.use_adaptive_sampling = False

    return original_settings


def restore_render_settings(original_settings):
    """Restore render settings to their original values"""
    cycles = bpy.context.scene.cycles
    cycles.samples = original_settings['samples']
    cycles.use_denoising = original_settings['use_denoising']
    cycles.use_adaptive_sampling = original_settings['use_adaptive_sampling']


def bake_node(target_node: Node, bake_type: str, width=1024, height=1024) -> Node:
    """
    Bakes a specific node from the active material with optimized settings

    Args:
        node_name bpy.types.Node: The node to bake
        bake_type (str): Type of bake to perform ('DIFFUSE', 'NORMAL', etc.)

    Returns:
        Image Texture Node: The baked image texture node
    """
    obj = bpy.context.active_object
    if not obj or not obj.active_material:
        return None

    material = obj.active_material
    material.use_nodes = True
    nodes = material.node_tree.nodes

    # Find the specified node
    # target_node = nodes.get(node_name)
    # if not target_node:
    #     return False

    material_output = get_active_material_output(material.node_tree)
    connected_nodes = get_connected_nodes(material_output)

    # Connect the target node to the material output
    links = material.node_tree.links
    # Save the original links from connected_nodes
    original_links = []
    for node in connected_nodes:
        for link in node.inputs[0].links:
            original_links.append(link)
    links.new(target_node.outputs[0], material_output.inputs[0])

    # Create a new image with appropriate settings
    image_name = f"{material.name}_{target_node.name}_{bake_type.lower()}"

    # Set appropriate image settings based on bake type
    if bake_type == 'NORMAL':
        image = bpy.data.images.new(
            name=image_name,
            width=width,
            height=height,
            alpha=True,
            float_buffer=True
        )
        image.colorspace_settings.name = 'Non-Color'
    elif bake_type in ['ROUGHNESS', 'COMBINED']:
        image = bpy.data.images.new(
            name=image_name,
            width=width,
            height=height,
            alpha=True,
            float_buffer=True
        )
        image.colorspace_settings.name = 'Non-Color'
    else:  # DIFFUSE, EMISSION
        image = bpy.data.images.new(
            name=image_name,
            width=width,
            height=height,
            alpha=False
        )
        image.colorspace_settings.name = 'sRGB'

    # Create and set up the image texture node

    bake_node = nodes.new('ShaderNodeTexImage')
    bake_node.name = "temp_bake_node"
    bake_node.image = image  # Link the image to the texture node
    bake_node.location = target_node.location + Vector((0, 300))

    # Store original settings
    original_engine = bpy.context.scene.render.engine

    try:
        # Switch to Cycles if needed
        if bpy.context.scene.render.engine != 'CYCLES':
            bpy.context.scene.render.engine = 'CYCLES'

        # Setup render settings
        original_render_settings = setup_render_settings(bake_type)

        # Select and activate the target node
        for node in nodes:
            node.select = False
        target_node.select = True
        nodes.active = bake_node

        # Configure bake parameters based on type
        bake_params = {
            'type': bake_type if bake_type != 'COMBINED' else 'COMBINED',
            'margin': 16,
            'use_selected_to_active': False,
            'use_clear': True,
            'target': 'IMAGE_TEXTURES'
        }

        # Add specific parameters for each bake type
        if bake_type == 'COMBINED':
            pass
            # bake_params['pass_filter'] = {
            #     'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'EMIT'}
        elif bake_type == 'DIFFUSE':
            bake_params['pass_filter'] = {'COLOR', 'DIRECT', 'INDIRECT'}
        elif bake_type == 'NORMAL':
            bake_params['normal_space'] = 'TANGENT'

        # Perform bake
        bpy.ops.object.bake(**bake_params)

        # Pack the image
        if not image.packed_file:
            image.pack()
            print(f"Image {image.name} packed.")

        for link in original_links:
            links.new(link.from_socket, link.to_socket)
        # nodes.remove(bake_node)
        bpy.context.scene.render.engine = original_engine
        restore_render_settings(original_render_settings)
        return bake_node

    except Exception as e:
        print(f"Baking failed: {str(e)}")
        return None


class PAINTSYSTEM_OT_BakeGroup(Operator):
    bl_idname = "paint_system.bake_group"
    bl_label = "Bake Group"
    bl_description = "Bake the selected group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    bake_started = False

    @classmethod
    def poll(cls, context):
        return is_bakeable(context)[0]

    def update_progress(self, context, progress, text=""):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        active_group.bake_progress = progress
        active_group.bake_status = text
        redraw_panel(self, context)

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        if not mat:
            return {'CANCELLED'}

        connected_node = get_connected_nodes(
            get_active_material_output(mat.node_tree))
        baking_steps: List[Tuple[Node, str]] = []
        for node in connected_node:
            if node.bl_idname in REQUIRES_INTERMEDIATE_STEP:
                if node.bl_idname == "ShaderNodeShaderToRGB":
                    node = node.inputs[0].links[0].from_node
                baking_steps.append((node, "COMBINED"))

        for idx, (node, bake_type) in enumerate(baking_steps):
            tex_node = bake_node(node, bake_type)

        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_BakeGroup,
)

register, unregister = register_classes_factory(classes)
