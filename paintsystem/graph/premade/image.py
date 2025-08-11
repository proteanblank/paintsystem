import bpy
from .common import get_library_nodetree
from ..nodetree_builder import NodeTreeBuilder, START, END

def create_image_graph(node_tree: bpy.types.NodeTree, img: bpy.types.Image) -> NodeTreeBuilder:
    pre_mix = get_library_nodetree(".PS Pre Mix")
    post_mix = get_library_nodetree(".PS Post Mix")
    builder = NodeTreeBuilder(node_tree, "Image Layer", clear=True)
    builder.add_node("group_input", "NodeGroupInput")
    builder.add_node("group_output", "NodeGroupOutput")
    builder.add_node("pre_mix", "ShaderNodeGroup", {"node_tree": pre_mix})
    builder.add_node("post_mix", "ShaderNodeGroup", {"node_tree": post_mix})
    builder.add_node("mix_rgb", "ShaderNodeMix", {"blend_type": "MIX", "data_type": "RGBA"})
    builder.add_node("image", "ShaderNodeTexImage", {"image": img})
    builder.link("image", "pre_mix", "Alpha", "Over Alpha")
    builder.link("group_input", "pre_mix", "Color", "Color")
    builder.link("group_input", "pre_mix", "Alpha", "Alpha")
    builder.link("pre_mix", "mix_rgb", "Color", "A")
    builder.link("pre_mix", "mix_rgb", "Over Alpha", "Factor")
    builder.link("image", "mix_rgb", "Color", "B")
    builder.link("mix_rgb", "post_mix", "Result", "Color")
    builder.link("pre_mix", "post_mix", "Over Alpha", "Over Alpha")
    builder.link("group_input", "post_mix", "Alpha", "Alpha")
    builder.link("post_mix", "group_output", "Color", "Color")
    builder.link("post_mix", "group_output", "Alpha", "Alpha")
    return builder