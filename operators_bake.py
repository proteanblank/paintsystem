import bpy
from bpy.types import Operator, Context, Node, NodeTree, Image
from bpy.props import (
    BoolProperty,
    StringProperty,
    FloatVectorProperty,
    EnumProperty,
    IntProperty
)
from bpy.utils import register_classes_factory
from .paint_system import PaintSystem, get_nodetree_from_library
from typing import List, Tuple
from mathutils import Vector
from .common import NodeOrganizer, get_object_uv_maps, get_connected_nodes, get_active_material_output
import copy

IMPOSSIBLE_NODES = (
    "ShaderNodeShaderInfo"
)
REQUIRES_INTERMEDIATE_STEP = (
    "ShaderNodeShaderToRGB"
)


def is_bakeable(context: Context) -> Tuple[bool, str, List[Node]]:
    """Check if the node tree is multi-user

    Args:
        context (bpy.types.Context): The context to check

    Returns:
        Tuple[bool, str, List[bpy.types.Node]]: A tuple containing a boolean indicating if the node tree is multi-user and an error message if any
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
    ris_nodes = []
    impossible_nodes = []

    for node, depth in connected_nodes:
        if node.bl_idname == "ShaderNodeGroup" and node.node_tree == node_tree:
            ps_groups.append(node)
        if node.bl_idname in REQUIRES_INTERMEDIATE_STEP:
            ris_nodes.append(node)
        if node.bl_idname in IMPOSSIBLE_NODES:
            impossible_nodes.append(node)

    if len(ps_groups) == 0:
        return False, "Paint System group is not connceted to Material Output.", []
    if len(ps_groups) > 1:
        return False, "Paint System group used Multiple Times.", ps_groups
    if impossible_nodes:
        return False, "Unsupported nodes found.", impossible_nodes

    # TODO: Remove until the intermediate step is implemented
    if ris_nodes:
        return False, "Unsupported nodes found.", ris_nodes

    return True, "", []


def save_cycles_settings():
    """Saves relevant Cycles render settings to a dictionary."""
    settings = {}
    scene = bpy.context.scene

    if scene.render.engine == 'CYCLES':  # Only save if Cycles is the engine
        settings['render_engine'] = scene.render.engine
        settings['device'] = scene.cycles.device
        settings['samples'] = scene.cycles.samples
        settings['preview_samples'] = scene.cycles.preview_samples
        settings['denoiser'] = scene.cycles.denoiser
        settings['use_denoising'] = scene.cycles.use_denoising

        # Add more settings you need to save here!
    return copy.deepcopy(settings)


def rollback_cycles_settings(saved_settings):
    """Rolls back Cycles render settings using the saved dictionary, with robustness checks."""
    scene = bpy.context.scene

    # Only rollback if settings were saved and we are in Cycles
    if saved_settings and scene.render.engine == 'CYCLES':
        try:  # Use a try-except block to catch potential errors during rollback
            # Check if 'engine' attribute still exists
            if 'render_engine' in saved_settings and hasattr(scene.render, 'engine'):
                scene.render.engine = saved_settings['render_engine']

            # Check if 'cycles' and 'device' exist
            if 'device' in saved_settings and hasattr(scene.cycles, 'device'):
                scene.cycles.device = saved_settings['device']
            if 'samples' in saved_settings and hasattr(scene.cycles, 'samples'):
                scene.cycles.samples = saved_settings['samples']
            if 'preview_samples' in saved_settings and hasattr(scene.cycles, 'preview_samples'):
                scene.cycles.preview_samples = saved_settings['preview_samples']
            if 'denoiser' in saved_settings and hasattr(scene.cycles, 'denoiser'):
                scene.cycles.denoiser = saved_settings['denoiser']
            if 'use_denoising' in saved_settings and hasattr(scene.cycles, 'use_denoising'):
                scene.cycles.use_denoising = saved_settings['use_denoising']

            # Add rollbacks for any other settings you saved with similar checks!

        except Exception as e:
            # Log any errors during rollback
            print(f"Error during Cycles settings rollback: {e}")
            # You might want to handle the error more specifically, e.g., show a message to the user.


def bake_node(context: Context, target_node: Node, image: Image, uv_layer: str, output_socket_name: str, alpha_socket_name: str = None, gpu=True) -> Node:
    """
    Bakes a specific node from the active material with optimized settings

    Args:
        context (bpy.types.Context): The context to bake in
        target_node (bpy.types.Node): The node to bake
        image (bpy.types.Image): The image to bake to
        uv_layer (str): The UV layer to bake
        output_socket_name (str): The output socket name
        alpha_socket_name (str): The alpha socket name
        width (int, optional): The width of the image. Defaults to 1024.
        height (int, optional): The height of the image. Defaults to 1024.

    Returns:
        Image Texture Node: The baked image texture node
    """

    # Debug
    print(f"Baking {target_node.name}")
    ps = PaintSystem(context)
    obj = ps.active_object
    if not obj or not obj.active_material:
        return None

    material = obj.active_material
    material.use_nodes = True
    nodes = material.node_tree.nodes
    material_output = get_active_material_output(material.node_tree)
    connected_nodes = get_connected_nodes(material_output)
    last_node_socket = material_output.inputs[0].links[0].from_socket

    # Save the original links from connected_nodes
    links = material.node_tree.links
    original_links = []
    for node, depth in connected_nodes:
        for input_socket in node.inputs:
            for link in input_socket.links:
                original_links.append(link)

    # try:
    # Store original settings
    original_engine = copy.deepcopy(
        getattr(context.scene.render, "engine"))
    # Switch to Cycles if needed
    if context.scene.render.engine != 'CYCLES':
        context.scene.render.engine = 'CYCLES'

    cycles_settings = save_cycles_settings()
    cycles = context.scene.cycles
    cycles.device = 'GPU' if gpu else 'CPU'
    bake_node = None
    node_organizer = NodeOrganizer(material)
    socket_type = target_node.outputs[output_socket_name].type
    if socket_type != 'SHADER':
        bake_nt = get_nodetree_from_library("_PS_Bake")
        bake_node = node_organizer.create_node(
            'ShaderNodeGroup', {'node_tree': bake_nt})
        node_organizer.create_link(
            target_node.name, bake_node.name, output_socket_name, 'Color')
        node_organizer.create_link(
            bake_node.name, material_output.name, 'Shader', 'Surface')
        # Check if target node has Alpha output
        if alpha_socket_name:
            node_organizer.create_link(
                target_node.name, bake_node.name, alpha_socket_name, 'Alpha')
        bake_params = {
            "type": 'COMBINED',
            "pass_filter": {'EMIT', 'DIRECT'},
        }
        cycles.samples = 1
        cycles.use_denoising = False
        cycles.use_adaptive_sampling = False
    else:
        node_organizer.create_link(
            target_node.name, material_output.name, output_socket_name, 'Surface')
        bake_params = {
            "type": 'COMBINED',
        }
        cycles.samples = 128
        cycles.use_denoising = True
        cycles.use_adaptive_sampling = True

    # Create and set up the image texture node
    bake_tex_node = node_organizer.create_node('ShaderNodeTexImage', {
        "name": "temp_bake_node", "image": image, "location": target_node.location + Vector((0, 300))})

    for node in nodes:
        node.select = False
    bake_tex_node.select = True
    nodes.active = bake_tex_node

    # Change the only selected object to the active one
    # TODO: Allow baking multiple objects
    for obj in context.scene.objects:
        if obj != context.active_object:
            obj.select_set(False)
        else:
            obj.select_set(True)

    # Perform bake
    bpy.ops.object.bake(**bake_params, uv_layer=uv_layer, use_clear=True)

    # Pack the image
    if not image.packed_file:
        image.pack()
        image.reload()
        print(f"Image {image.name} packed.")

    # Delete temporary bake node
    if bake_node:
        nodes.remove(bake_node)
    rollback_cycles_settings(cycles_settings)

    # Restore original links
    links.new(material_output.inputs[0], last_node_socket)
    context.scene.render.engine = original_engine

    # Debug
    # print(f"Backed {target_node.name} to {image.name}")

    return bake_tex_node

    # except Exception as e:
    #     print(f"Baking failed: {str(e)}")
    #     return None


class PAINTSYSTEM_OT_MergeGroup(Operator):
    bl_idname = "paint_system.merge_group"
    bl_label = "Merge Group"
    bl_description = "Merge the selected group Layers"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    image_resolution: EnumProperty(
        items=[
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
        ],
        default='1024',
    )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )
    use_gpu: BoolProperty(
        name="Use GPU",
        default=True
    )
    as_new_layer: BoolProperty(
        name="As New Layer",
        default=False
    )

    @classmethod
    def poll(cls, context):
        bakeable, error_message, nodes = is_bakeable(context)
        return bakeable

    def execute(self, context):
        context.window.cursor_set('WAIT')
        ps = PaintSystem(context)
        obj = ps.active_object
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        mat = ps.get_active_material()
        active_group = ps.get_active_group()
        if not mat:
            return {'CANCELLED'}

        active_group.use_bake_image = False
        active_group.update_node_tree()

        bakable, error, problem_nodes = is_bakeable(context)
        if not bakable:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        connected_node = get_connected_nodes(
            get_active_material_output(mat.node_tree))
        baking_steps: List[Tuple[Node, str, str, Image, str]] = []
        image_resolution = int(self.image_resolution)
        for node, depth in connected_node:
            # TODO: Allow Baking inside groups
            if depth != 0:
                continue
            if node.bl_idname in REQUIRES_INTERMEDIATE_STEP:
                # Create a new image with appropriate settings
                image_name = f"{mat.name}_{node.name}"
                image = bpy.data.images.new(
                    name=image_name,
                    width=image_resolution,
                    height=image_resolution,
                    alpha=True,
                )
                image.colorspace_settings.name = 'sRGB'

                if node.bl_idname == "ShaderNodeShaderToRGB":
                    link = node.inputs[0].links[0]
                    baking_steps.append(
                        (link.from_node, link.from_socket.name, None, image, self.uv_map_name))
            if node.bl_idname == "ShaderNodeGroup" and node.node_tree == active_group.node_tree:
                if self.as_new_layer:
                    image = bpy.data.images.new(
                        name=f"{active_group.name}_Merge",
                        width=image_resolution,
                        height=image_resolution,
                        alpha=True,
                    )
                    ps.create_image_layer(
                        image.name, image, self.uv_map_name)
                else:
                    image = active_group.bake_image
                    if not image:
                        # Create a new image with appropriate settings
                        image_name = f"{active_group.name}_bake"
                        image = bpy.data.images.new(
                            name=image_name,
                            width=image_resolution,
                            height=image_resolution,
                            alpha=True,
                        )
                        image.colorspace_settings.name = 'sRGB'
                        active_group.bake_image = image
                baking_steps.append(
                    (node, "Color", "Alpha", image, self.uv_map_name))

        baking_steps.reverse()

        for idx, (node, output_socket_name, alpha_socket_name, image, uv_layer) in enumerate(baking_steps):
            tex_node = bake_node(
                context,
                target_node=node,
                image=image,
                uv_layer=uv_layer,
                output_socket_name=output_socket_name,
                alpha_socket_name=alpha_socket_name,
                gpu=self.use_gpu
            )
            # TODO: Handle nodes that require intermediate steps
            nodes = mat.node_tree.nodes
            nodes.remove(nodes.get(tex_node.name))
            if not tex_node:
                self.report({'ERROR'}, f"Failed to bake {node.name}.")
                return {'CANCELLED'}

        if not self.as_new_layer:
            active_group.use_bake_image = True
            active_group.bake_uv_map = self.uv_map_name

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_gpu", text="Use GPU (Faster)")
        layout.prop(self, "image_resolution", expand=True)
        layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_MergeAndExportGroup(Operator):
    bl_idname = "paint_system.merge_and_export_group"
    bl_label = "Merge and Export Group"
    bl_description = "Merge the selected group Layers and export the baked image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    image_resolution: EnumProperty(
        items=[
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
        ],
        default='1024',
    )
    uv_map_name: EnumProperty(
        name="UV Map",
        items=get_object_uv_maps
    )
    use_gpu: BoolProperty(
        name="Use GPU",
        default=True
    )

    def execute(self, context):
        bpy.ops.paint_system.merge_group(
            image_resolution=self.image_resolution,
            uv_map_name=self.uv_map_name,
            use_gpu=self.use_gpu,
            as_new_layer=False
        )
        bpy.ops.paint_system.export_baked_image()
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_gpu", text="Use GPU (Faster)")
        layout.prop(self, "image_resolution", expand=True)
        layout.prop(self, "uv_map_name")


class PAINTSYSTEM_OT_DeleteBakedImage(Operator):
    bl_idname = "paint_system.delete_bake_image"
    bl_label = "Delete Baked Image"
    bl_description = "Delete the baked image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        image = active_group.bake_image
        if not image:
            self.report({'ERROR'}, "No baked image found.")
            return {'CANCELLED'}

        bpy.data.images.remove(image)
        active_group.bake_image = None

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(
            text="Click OK to delete the baked image.")


def split_area(context: Context, direction='VERTICAL', factor=0.5):
    current_area = context.area
    screen = context.screen
    areas_before = set(screen.areas)
    bpy.ops.screen.area_split(direction=direction, factor=factor)
    areas_after = set(screen.areas)
    new_area_set = areas_after - areas_before
    if not new_area_set:
        print("Failed to create a new area.")
        return
    new_area = new_area_set.pop()
    return new_area


class PAINTSYSTEM_OT_ExportBakedImage(Operator):
    bl_idname = "paint_system.export_baked_image"
    bl_label = "Export Baked Image"
    bl_description = "Export the baked image"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        ps = PaintSystem(context)
        active_group = ps.get_active_group()
        if not active_group:
            return {'CANCELLED'}

        image = active_group.bake_image
        if not image:
            self.report({'ERROR'}, "No baked image found.")
            return {'CANCELLED'}

        image_editor_area = split_area(
            context, direction='VERTICAL', factor=0.5)
        image_editor_area.type = 'IMAGE_EDITOR'  # Set the new area to be Image Editor
        with context.temp_override(area=image_editor_area):
            context.space_data.image = image
            bpy.ops.image.save_as('INVOKE_DEFAULT', copy=True)
            bpy.ops.screen.area_close('INVOKE_DEFAULT')
        return {'FINISHED'}


class PAINTSYSTEM_OT_FocusNode(Operator):
    bl_idname = "paint_system.focus_node"
    bl_label = "Focus Node"
    bl_description = "Focus on the selected node"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    node_name: StringProperty()

    def execute(self, context):
        ps = PaintSystem(context)
        mat = ps.get_active_material()
        nodes = mat.node_tree.nodes
        select_node = nodes.get(self.node_name)
        if not select_node:
            return {'CANCELLED'}
        # Check if Shader Editor is open
        ne_area = None
        for area in context.screen.areas:
            if area.type == 'NODE_EDITOR' and area.ui_type == 'ShaderNodeTree':
                ne_area = area
                break
        if not ne_area:
            ne_area = split_area(context, direction='VERTICAL', factor=0.6)
            ne_area.type = 'NODE_EDITOR'  # Set the new area to be Shader Editor
            ne_area.ui_type = 'ShaderNodeTree'
        with context.temp_override(area=ne_area, region=ne_area.regions[3]):
            context.space_data.node_tree = mat.node_tree
            for node in nodes:
                node.select = False
            select_node.select = True
            nodes.active = select_node
            bpy.ops.node.view_selected('INVOKE_DEFAULT')

        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_MergeGroup,
    PAINTSYSTEM_OT_MergeAndExportGroup,
    PAINTSYSTEM_OT_DeleteBakedImage,
    PAINTSYSTEM_OT_ExportBakedImage,
    PAINTSYSTEM_OT_FocusNode,
)

register, unregister = register_classes_factory(classes)
