import bpy
from .common import create_mixing_graph

def create_image_graph(node_tree: bpy.types.NodeTree, img: bpy.types.Image, coord_type: str, uv_map_name: str):
    builder = create_mixing_graph(node_tree, "image", "Color", "image", "Alpha")
    builder.add_node("image", "ShaderNodeTexImage", {"image": img, "interpolation": "Closest"})
    if coord_type == "AUTO":
        builder.add_node("uvmap", "ShaderNodeUVMap", {"uv_map": "PS_UVMap"})
        builder.link("uvmap", "image", "UV", "Vector")
    elif coord_type == "UV":
        builder.add_node("uvmap", "ShaderNodeUVMap", {"uv_map": uv_map_name})
        builder.link("uvmap", "image", "UV", "Vector")
    elif coord_type in ["OBJECT", "CAMERA", "WINDOW", "REFLECTION"]:
        builder.add_node("tex_coord", "ShaderNodeTexCoord")
        builder.link("tex_coord", "image", coord_type.title(), "Vector")
    elif coord_type == "POSITION":
        builder.add_node("geometry", "ShaderNodeGeometry")
        builder.link("geometry", "image", "Position", "Vector")
    return builder

def create_folder_graph(node_tree: bpy.types.NodeTree):
    builder = create_mixing_graph(node_tree, "group_input", "Over Color", "group_input", "Over Alpha")
    return builder

def create_solid_graph(node_tree: bpy.types.NodeTree):
    builder = create_mixing_graph(node_tree, "rgb", "Color")
    builder.add_node("rgb", "ShaderNodeRGB")
    return builder

def create_attribute_graph(node_tree: bpy.types.NodeTree):
    builder = create_mixing_graph(node_tree, "attribute", "Color")
    builder.add_node("attribute", "ShaderNodeAttribute")
    return builder