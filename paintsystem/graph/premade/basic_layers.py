import bpy
from .common import create_mixing_graph, NodeTreeBuilder, create_coord_graph

def create_image_graph(node_tree: bpy.types.NodeTree, img: bpy.types.Image, coord_type: str, uv_map_name: str):
    builder = NodeTreeBuilder(node_tree, "Image Layer")
    create_mixing_graph(builder, "image", "Color", "image", "Alpha")
    builder.add_node("image", "ShaderNodeTexImage", {"image": img, "interpolation": "Closest"})
    create_coord_graph(builder, coord_type, uv_map_name)
    return builder

def create_folder_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Image Layer")
    create_mixing_graph(builder, "group_input", "Over Color", "group_input", "Over Alpha")
    return builder

def create_solid_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Image Layer")
    create_mixing_graph(builder, "rgb", "Color")
    builder.add_node("rgb", "ShaderNodeRGB")
    return builder

def create_attribute_graph(node_tree: bpy.types.NodeTree):
    builder = NodeTreeBuilder(node_tree, "Image Layer")
    create_mixing_graph(builder, "attribute", "Color")
    builder.add_node("attribute", "ShaderNodeAttribute")
    return builder