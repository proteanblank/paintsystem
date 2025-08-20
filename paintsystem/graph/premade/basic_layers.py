import bpy
from .common import create_mixing_graph, NodeTreeBuilder, create_coord_graph

def create_image_graph(node_tree: bpy.types.NodeTree, img: bpy.types.Image, coord_type: str, uv_map_name: str):
    builder = NodeTreeBuilder(node_tree, "Layer")
    create_mixing_graph(builder, "image", "Color", "image", "Alpha")
    builder.add_node("image", "ShaderNodeTexImage", {"image": img, "interpolation": "Closest"})
    create_coord_graph(builder, coord_type, uv_map_name, 'image', 'Vector')
    return builder

def create_folder_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Layer")
    create_mixing_graph(builder, "group_input", "Over Color", "group_input", "Over Alpha")
    return builder

def create_solid_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Layer")
    create_mixing_graph(builder, "rgb", "Color")
    builder.add_node("rgb", "ShaderNodeRGB")
    return builder

def create_attribute_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Layer")
    create_mixing_graph(builder, "attribute", "Color")
    builder.add_node("attribute", "ShaderNodeAttribute")
    return builder

def create_adjustment_graph(node_tree: bpy.types.NodeTree, adjustment_type: str):
    builder = NodeTreeBuilder(node_tree, "Layer")
    create_mixing_graph(builder, "adjustment", "Color")
    builder.add_node("adjustment", adjustment_type)
    if adjustment_type in {"ShaderNodeHueSaturation", "ShaderNodeInvert", "ShaderNodeRGBCurve"}:
        builder.add_node("value", "ShaderNodeValue", default_outputs={0:1})
        builder.link("value", "adjustment", "Value", "Fac")
    builder.link("group_input", "adjustment", "Color", "Color")
    return builder

def create_gradient_graph(node_tree: bpy.types.NodeTree, gradient_type: str, empty_object: bpy.types.Object):
    builder = NodeTreeBuilder(node_tree, "Layer")
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
        case _:
            raise ValueError(f"Invalid gradient type: {gradient_type}")
    builder.link("map_range", "gradient", "Result", "Fac")
    return builder

def create_random_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Layer")
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

def create_custom_graph(node_tree: bpy.types.NodeTree, custom_node_tree: bpy.types.NodeTree, color_input: str|int, alpha_input: str|int, color_output: str|int = -1, alpha_output: str|int = -1):
    builder = NodeTreeBuilder(node_tree, "Layer")
    if alpha_output != -1:
        create_mixing_graph(builder, "custom_node_tree", color_output, "custom_node_tree", alpha_output)
        builder.link("group_input", "custom_node_tree", "Alpha", alpha_input)
    else:
        create_mixing_graph(builder, "custom_node_tree", color_output)
    builder.add_node("custom_node_tree", "ShaderNodeGroup", {"node_tree": custom_node_tree})
    builder.link("group_input", "custom_node_tree", "Color", color_input)
    if alpha_input != -1:
        builder.link("group_input", "custom_node_tree", "Alpha", alpha_input)
    return builder