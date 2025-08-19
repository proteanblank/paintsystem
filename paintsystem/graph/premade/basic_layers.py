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