from __future__ import annotations
from typing import TYPE_CHECKING

import bpy
from .common import create_mixing_graph, NodeTreeBuilder, create_coord_graph

if TYPE_CHECKING:
    from ..data import GlobalLayer

IMAGE_LAYER_VERSION = 2
FOLDER_LAYER_VERSION = 1
SOLID_COLOR_LAYER_VERSION = 1
ATTRIBUTE_LAYER_VERSION = 1
ADJUSTMENT_LAYER_VERSION = 1
GRADIENT_LAYER_VERSION = 1
RANDOM_LAYER_VERSION = 1
CUSTOM_LAYER_VERSION = 1
TEXTURE_LAYER_VERSION = 1

ALPHA_OVER_LAYER_VERSION = 1

def get_layer_version_for_type(type: str) -> int:
    match type:
        case "IMAGE":
            return IMAGE_LAYER_VERSION
        case "FOLDER":
            return FOLDER_LAYER_VERSION
        case "SOLID_COLOR":
            return SOLID_COLOR_LAYER_VERSION
        case "ATTRIBUTE":
            return ATTRIBUTE_LAYER_VERSION
        case "ADJUSTMENT":
            return ADJUSTMENT_LAYER_VERSION
        case "GRADIENT":
            return GRADIENT_LAYER_VERSION
        case "RANDOM":
            return RANDOM_LAYER_VERSION
        case "CUSTOM":
            return CUSTOM_LAYER_VERSION
        case "TEXTURE":
            return TEXTURE_LAYER_VERSION
        case _:
            raise ValueError(f"Invalid layer type: {type}")

def create_image_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    img = global_layer.image
    coord_type = global_layer.coord_type
    uv_map_name = global_layer.uv_map_name
    builder = NodeTreeBuilder(node_tree, "Layer", version=IMAGE_LAYER_VERSION)
    create_mixing_graph(builder, "image", "Color", "image", "Alpha")
    builder.add_node("image", "ShaderNodeTexImage", {"image": img, "interpolation": "Closest"})
    create_coord_graph(builder, coord_type, uv_map_name, 'image', 'Vector')
    return builder

def create_folder_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    builder = NodeTreeBuilder(node_tree, "Layer", version=FOLDER_LAYER_VERSION)
    create_mixing_graph(builder, "group_input", "Over Color", "group_input", "Over Alpha")
    return builder

def create_solid_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    builder = NodeTreeBuilder(node_tree, "Layer", version=SOLID_COLOR_LAYER_VERSION)
    create_mixing_graph(builder, "rgb", "Color")
    builder.add_node("rgb", "ShaderNodeRGB", default_outputs={0: (1, 1, 1, 1)})
    return builder

def create_attribute_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    builder = NodeTreeBuilder(node_tree, "Layer", version=ATTRIBUTE_LAYER_VERSION)
    create_mixing_graph(builder, "attribute", "Color")
    builder.add_node("attribute", "ShaderNodeAttribute")
    return builder

def create_adjustment_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    adjustment_type = global_layer.adjustment_type
    builder = NodeTreeBuilder(node_tree, "Layer", version=ADJUSTMENT_LAYER_VERSION)
    create_mixing_graph(builder, "adjustment", "Color")
    builder.add_node("adjustment", adjustment_type)
    if adjustment_type in {"ShaderNodeHueSaturation", "ShaderNodeInvert", "ShaderNodeRGBCurve"}:
        builder.add_node("value", "ShaderNodeValue", default_outputs={0:1})
        builder.link("value", "adjustment", "Value", "Fac")
    builder.link("group_input", "adjustment", "Color", "Color")
    return builder

def create_gradient_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    gradient_type = global_layer.gradient_type
    empty_object = global_layer.empty_object
    builder = NodeTreeBuilder(node_tree, "Layer", version=GRADIENT_LAYER_VERSION)
    create_mixing_graph(builder, "gradient", "Color", "gradient", "Alpha")
    builder.add_node("gradient", "ShaderNodeValToRGB")
    match gradient_type:
        case "LINEAR":
            builder.add_node("map_range", "ShaderNodeMapRange")
            builder.add_node("tex_coord", "ShaderNodeTexCoord", {"object": empty_object})
            builder.add_node("separate_xyz", "ShaderNodeSeparateXYZ")
            builder.link("tex_coord", "separate_xyz", "Object", "Vector")
            builder.link("separate_xyz", "map_range", "Z", "Value")
        case "RADIAL":
            builder.add_node("map_range", "ShaderNodeMapRange", default_values={1: 1, 2: 0})
            builder.add_node("tex_coord", "ShaderNodeTexCoord", {"object": empty_object})
            builder.add_node("vector_math", "ShaderNodeVectorMath", {"operation": "LENGTH"})
            builder.link("tex_coord", "vector_math", "Object", "Vector")
            builder.link("vector_math", "map_range", "Value", "Value")
        case "DISTANCE":
            builder.add_node("map_range", "ShaderNodeMapRange")
            builder.add_node("camera_data", "ShaderNodeCameraData")
            builder.link("camera_data", "map_range", "View Distance", "Value")
        case "GRADIENT_MAP":
            builder.add_node("map_range", "ShaderNodeMapRange")
            builder.link("group_input", "map_range", "Color", "Value")
        case _:
            raise ValueError(f"Invalid gradient type: {gradient_type}")
    builder.link("map_range", "gradient", "Result", "Fac")
    return builder

def create_random_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    builder = NodeTreeBuilder(node_tree, "Layer", version=RANDOM_LAYER_VERSION)
    create_mixing_graph(builder, "white_noise", "Color")
    builder.add_node("object_info", "ShaderNodeObjectInfo")
    builder.add_node("white_noise", "ShaderNodeTexWhiteNoise", {"noise_dimensions": "1D"})
    builder.add_node("add", "ShaderNodeMath", {"operation": "ADD"})
    builder.add_node("add_2", "ShaderNodeMath", {"operation": "ADD"}, {1: 0})
    builder.link("object_info", "add", "Material Index", 0)
    builder.link("object_info", "add", "Random", 1)
    builder.link("add", "add_2", "Value", 0)
    builder.link("add_2", "white_noise", "Value", "W")
    return builder

def create_custom_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    custom_node_tree = global_layer.custom_node_tree
    color_input = global_layer.custom_color_input
    alpha_input = global_layer.custom_alpha_input
    color_output = global_layer.custom_color_output
    alpha_output = global_layer.custom_alpha_output
    builder = NodeTreeBuilder(node_tree, "Layer", version=CUSTOM_LAYER_VERSION)
    if alpha_output != -1:
        create_mixing_graph(builder, "custom_node_tree", color_output, "custom_node_tree", alpha_output)
        builder.link("group_input", "custom_node_tree", "Alpha", alpha_input)
    else:
        create_mixing_graph(builder, "custom_node_tree", color_output)
    builder.add_node("custom_node_tree", "ShaderNodeGroup", {"node_tree": custom_node_tree})
    if color_input != -1:
        builder.link("group_input", "custom_node_tree", "Color", color_input)
    if alpha_input != -1:
        builder.link("group_input", "custom_node_tree", "Alpha", alpha_input)
    return builder

def create_texture_graph(global_layer: "GlobalLayer"):
    node_tree = global_layer.node_tree
    texture_type = global_layer.texture_type
    coord_type = global_layer.coord_type
    uv_map_name = global_layer.uv_map_name
    builder = NodeTreeBuilder(node_tree, "Layer", version=TEXTURE_LAYER_VERSION)
    create_mixing_graph(builder, "texture", "Color")
    builder.add_node("texture", texture_type)
    create_coord_graph(builder, coord_type, uv_map_name, 'texture', 'Vector')
    return builder

def get_alpha_over_nodetree():
    if ".PS Alpha Over" in bpy.data.node_groups:
        return bpy.data.node_groups[".PS Alpha Over"]
    node_tree = bpy.data.node_groups.new(name=".PS Alpha Over", type="ShaderNodeTree")
    node_tree.interface.new_socket("Clip", in_out="INPUT", socket_type="NodeSocketBool")
    node_tree.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    node_tree.interface.new_socket("Over Color", in_out="INPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Over Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
    node_tree.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    node_tree.interface.new_socket("Alpha", in_out="OUTPUT", socket_type="NodeSocketFloat")
    builder = NodeTreeBuilder(node_tree, "Layer", version=ALPHA_OVER_LAYER_VERSION)
    create_mixing_graph(builder, "group_input", "Over Color", "group_input", "Over Alpha")
    builder.compile()
    return node_tree