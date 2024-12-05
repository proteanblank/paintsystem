import bpy
import os

from bpy.utils import register_classes_factory
from bpy.app.handlers import persistent
from bpy.types import (Panel, Operator, PropertyGroup, UIList)
from bpy.props import (IntProperty, PointerProperty,
                       StringProperty, CollectionProperty)


import bpy
from bpy.types import (Panel, Operator, PropertyGroup, UIList)
from bpy.props import (IntProperty, PointerProperty,
                       StringProperty, CollectionProperty)


class PaintSystemLayer(PropertyGroup):
    """Group of properties representing a paint layer"""
    name: StringProperty(
        name="Name",
        description="Layer name",
        default="Layer"
    )
    image: PointerProperty(
        name="Image",
        type=bpy.types.Image
    )
    node_name: StringProperty(
        name="Node Name",
        description="Name of the associated texture node"
    )


class PaintSystemSettings(PropertyGroup):
    """Paint system settings for materials"""
    layers: CollectionProperty(type=PaintSystemLayer)
    active_layer_index: IntProperty(
        name="Active Layer Index",
        default=0,
        update=lambda self, context: update_active_paint_slot(self, context)
    )


def update_active_paint_slot(self, context):
    """Update the active paint slot when layer selection changes"""
    obj = context.active_object
    if not obj or not obj.active_material:
        return

    mat = obj.active_material
    ps_settings = mat.paint_system

    if ps_settings.active_layer_index >= len(ps_settings.layers):
        return

    # Get the active layer
    layer = ps_settings.layers[ps_settings.active_layer_index]

    # Set the active image in image paint mode
    if layer.image:
        obj.active_material.paint_active_slot = ps_settings.active_layer_index
        bpy.data.brushes["Draw"].texture_slot.texture = None


class PAINTSYSTEM_UL_layers(UIList):
    """Paint System Layer List"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon='IMAGE_DATA')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='IMAGE_DATA')


class PAINTSYSTEM_OT_add_setup(Operator):
    """Create the Paint System node group in the active material"""
    bl_idname = "paint_system.add_setup"
    bl_label = "Add Setup"

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "No active material")
            return {'CANCELLED'}

        mat = obj.active_material
        node_group_name = f"{mat.name} Layers"

        # Create unique node group for this material
        if node_group_name not in bpy.data.node_groups:
            group = bpy.data.node_groups.new(node_group_name, "ShaderNodeTree")

            # Create group inputs/outputs using interface
            group.interface.new_socket(
                name="Base Color", in_out='INPUT', socket_type='NodeSocketColor')
            group.interface.new_socket(
                name="Color", in_out='OUTPUT', socket_type='NodeSocketColor')

            # Add group input/output nodes
            input_node = group.nodes.new("NodeGroupInput")
            output_node = group.nodes.new("NodeGroupOutput")
            input_node.location = (-300, 0)
            output_node.location = (300, 0)

            # Link input to output initially
            group.links.new(input_node.outputs[0], output_node.inputs[0])

        # Add group node to material if not present
        if not any(node.type == 'GROUP' and node.node_tree and node.node_tree.name == node_group_name
                   for node in mat.node_tree.nodes):
            group_node = mat.node_tree.nodes.new("ShaderNodeGroup")
            group_node.node_tree = bpy.data.node_groups[node_group_name]

            # Try to connect to Principled BSDF
            principled = next(
                (n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                mat.node_tree.links.new(
                    group_node.outputs[0], principled.inputs['Base Color'])

        return {'FINISHED'}


def rebuild_layer_connections(context, material):
    """
    Rebuild all layer connections based on the PaintSystemSettings layer order
    """
    node_group_name = f"{material.name} Layers"
    group_node = next((n for n in material.node_tree.nodes if n.type == 'GROUP' and
                      n.node_tree and n.node_tree.name == node_group_name), None)

    if not group_node or not group_node.node_tree:
        return

    group = group_node.node_tree
    ps_settings = material.paint_system

    # Get input and output nodes
    input_node = next(n for n in group.nodes if n.type == 'GROUP_INPUT')
    output_node = next(n for n in group.nodes if n.type == 'GROUP_OUTPUT')

    # Clear all mix node connections
    for node in group.nodes:
        if node.type == 'MIX_RGB':
            for input in node.inputs:
                if input.is_linked:
                    for link in input.links:
                        group.links.remove(link)
            for output in node.outputs:
                if output.is_linked:
                    for link in output.links:
                        group.links.remove(link)

    # Rebuild connections based on layer order
    previous_node = input_node

    for i, layer in enumerate(ps_settings.layers):
        if layer.node_name not in group.nodes:
            continue

        tex_node = group.nodes[layer.node_name]
        mix_node = group.nodes[f"Mix_{layer.name}"]

        # Connect texture node to mix node
        group.links.new(tex_node.outputs['Color'], mix_node.inputs[2])
        group.links.new(tex_node.outputs['Alpha'], mix_node.inputs[0])

        # Connect previous node to mix node
        group.links.new(previous_node.outputs[0], mix_node.inputs[1])

        previous_node = mix_node

    # Connect last node to output
    group.links.new(previous_node.outputs[0], output_node.inputs[0])


class PAINTSYSTEM_OT_move_layer(Operator):
    """Move layer up or down in the stack"""
    bl_idname = "paint_system.move_layer"
    bl_label = "Move Layer"

    direction: StringProperty(
        name="Direction",
        description="Direction to move layer (UP or DOWN)",
        default="UP"
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            return {'CANCELLED'}

        mat = obj.active_material
        ps_settings = mat.paint_system

        old_index = ps_settings.active_layer_index
        new_index = old_index - 1 if self.direction == "UP" else old_index + 1

        if new_index < 0 or new_index >= len(ps_settings.layers):
            return {'CANCELLED'}

        # Swap layers
        ps_settings.layers.move(old_index, new_index)
        ps_settings.active_layer_index = new_index

        # Rebuild connections
        rebuild_layer_connections(context, mat)

        return {'FINISHED'}


class PAINTSYSTEM_OT_add_layer(Operator):
    """Add a new paint layer"""
    bl_idname = "paint_system.add_layer"
    bl_label = "Add Layer"

    resolution_x: IntProperty(
        name="Width",
        description="Texture width in pixels",
        default=1024,
        min=1,
        soft_max=8192
    )

    resolution_y: IntProperty(
        name="Height",
        description="Texture height in pixels",
        default=1024,
        min=1,
        soft_max=8192
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(self, "resolution_x")
        col.prop(self, "resolution_y")

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'ERROR'}, "No active material")
            return {'CANCELLED'}

        mat = obj.active_material
        ps_settings = mat.paint_system
        node_group_name = f"{mat.name} Layers"

        group_node = next((n for n in mat.node_tree.nodes if n.type == 'GROUP' and
                          n.node_tree and n.node_tree.name == node_group_name), None)

        if not group_node:
            self.report(
                {'ERROR'}, "Paint System setup not found. Click 'Add Setup' first.")
            return {'CANCELLED'}

        group = group_node.node_tree

        # Create new layer in the collection
        layer = ps_settings.layers.add()
        layer_index = len(ps_settings.layers) - 1
        layer.name = f"Layer_{layer_index + 1}"

        # Create new image texture with transparent black
        img_name = f"{obj.name}_{mat.name}_{layer.name}"
        img = bpy.data.images.new(
            img_name, self.resolution_x, self.resolution_y, alpha=True)
        img.pixels = [0.0] * (4 * self.resolution_x * self.resolution_y)
        layer.image = img

        # Add nodes to group with custom names
        tex_node = group.nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        # tex_node.image.use_alpha = True
        tex_node.name = f"Texture_{layer.name}"
        layer.node_name = tex_node.name

        mix_node = group.nodes.new("ShaderNodeMixRGB")
        mix_node.use_alpha = True
        mix_node.blend_type = 'MIX'
        mix_node.name = f"Mix_{layer.name}"

        # Rebuild all connections
        rebuild_layer_connections(context, mat)

        # Set the new layer as active
        ps_settings.active_layer_index = layer_index

        return {'FINISHED'}


class PAINTSYSTEM_OT_remove_layer(Operator):
    """Remove the active paint layer"""
    bl_idname = "paint_system.remove_layer"
    bl_label = "Remove Layer"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            return False
        ps_settings = obj.active_material.paint_system
        return len(ps_settings.layers) > 0

    def execute(self, context):
        obj = context.active_object
        mat = obj.active_material
        ps_settings = mat.paint_system
        node_group_name = f"{mat.name} Layers"

        if ps_settings.active_layer_index >= len(ps_settings.layers):
            return {'CANCELLED'}

        # Get the active layer
        layer = ps_settings.layers[ps_settings.active_layer_index]

        # Get the node group
        group_node = next((n for n in mat.node_tree.nodes if n.type == 'GROUP' and
                          n.node_tree and n.node_tree.name == node_group_name), None)

        if group_node and group_node.node_tree:
            group = group_node.node_tree

            # Remove the nodes
            if layer.node_name in group.nodes:
                tex_node = group.nodes[layer.node_name]
                mix_node = group.nodes[f"Mix_{layer.name}"]
                group.nodes.remove(mix_node)
                group.nodes.remove(tex_node)

            # Remove the image
            if layer.image:
                bpy.data.images.remove(layer.image)

        # Remove the layer from the collection
        ps_settings.layers.remove(ps_settings.active_layer_index)

        # Adjust active index if needed
        if ps_settings.active_layer_index >= len(ps_settings.layers):
            ps_settings.active_layer_index = max(
                0, len(ps_settings.layers) - 1)

        # Rebuild connections
        rebuild_layer_connections(context, mat)

        return {'FINISHED'}


class PAINTSYSTEM_PT_main_panel(Panel):
    """Paint System Main Panel"""
    bl_label = "Paint System"
    bl_idname = "PAINTSYSTEM_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Paint System'

    def has_paint_system_setup(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            return False

        mat = obj.active_material
        node_group_name = f"{mat.name} Layers"

        return any(node.type == 'GROUP' and
                   node.node_tree and
                   node.node_tree.name == node_group_name
                   for node in mat.node_tree.nodes)

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if obj and obj.type == 'MESH':
            if obj.active_material:
                mat = obj.active_material

                if not self.has_paint_system_setup(context):
                    layout.operator("paint_system.add_setup")

                if hasattr(mat, 'paint_system'):
                    ps_settings = mat.paint_system

                    row = layout.row()
                    rows = 2 if len(ps_settings.layers) > 0 else 2
                    row.template_list("PAINTSYSTEM_UL_layers", "", ps_settings, "layers",
                                      ps_settings, "active_layer_index", rows=rows)

                    col = row.column(align=True)
                    col.operator("paint_system.add_layer", icon='ADD', text="")
                    col.operator("paint_system.remove_layer",
                                 icon='REMOVE', text="")
                    col.separator()
                    col.operator("paint_system.move_layer",
                                 icon='TRIA_UP', text="")
                    col.operator("paint_system.move_layer",
                                 icon='TRIA_DOWN', text="")
            else:
                layout.label(text="Add a material first")
        else:
            layout.label(text="Select a mesh object")


classes = (
    PaintSystemLayer,
    PaintSystemSettings,
    PAINTSYSTEM_UL_layers,
    PAINTSYSTEM_OT_add_setup,
    PAINTSYSTEM_OT_add_layer,
    PAINTSYSTEM_OT_remove_layer,
    PAINTSYSTEM_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Material.paint_system = PointerProperty(type=PaintSystemSettings)


def unregister():
    del bpy.types.Material.paint_system
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
