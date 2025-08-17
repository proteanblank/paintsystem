import bpy
from .common import create_mixing_graph

def create_image_graph(node_tree: bpy.types.NodeTree, img: bpy.types.Image):
    builder = create_mixing_graph(node_tree, "image", "Color", "image", "Alpha")
    builder.add_node("image", "ShaderNodeTexImage", {"image": img, "interpolation": "Closest"})
    return builder

def create_folder_graph(node_tree: bpy.types.NodeTree):
    builder = create_mixing_graph(node_tree, "group_input", "Over Color", "group_input", "Over Alpha")
    return builder

def create_solid_graph(node_tree: bpy.types.NodeTree, color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)):
    builder = create_mixing_graph(node_tree, "rgb", "Color")
    builder.add_node("rgb", "ShaderNodeRGB", default_values={0: color})
    return builder

def create_attribute_graph(node_tree: bpy.types.NodeTree):
    builder = create_mixing_graph(node_tree, "attribute", "Color")
    builder.add_node("attribute", "ShaderNodeAttribute")
    return builder