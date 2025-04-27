from bpy.props import EnumProperty, BoolProperty, StringProperty
from bpy.types import Operator, Panel
import bpy
bl_info = {
    "name": "Material Baker",
    "author": "Tawan Sunflower",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Properties > Material > Bake Material",
    "description": "Bakes materials by temporarily switching to Cycles if needed",
    "category": "Material",
}


def bake_node(node_name, bake_type):
    """
    Bakes a specific node from the active material

    Args:
        node_name (str): Name of the node to bake
        bake_type (str): Type of bake to perform ('DIFFUSE', 'NORMAL', etc.)

    Returns:
        bool: True if successful, False otherwise
    """
    obj = bpy.context.object
    if not obj or not obj.active_material:
        return False

    material = obj.active_material
    nodes = material.node_tree.nodes

    # Find the specified node
    target_node = nodes.get(node_name)
    if not target_node:
        return False

    # Create a temporary image texture node for baking
    bake_node = nodes.new('ShaderNodeTexImage')
    bake_node.name = "temp_bake_node"

    # Create a new image for baking
    image_name = f"{material.name}_{node_name}_{bake_type.lower()}"
    image = bpy.data.images.new(image_name, 1024, 1024)
    bake_node.image = image

    # Store active render engine
    original_engine = bpy.context.scene.render.engine

    try:
        # Switch to Cycles if needed
        if bpy.context.scene.render.engine != 'CYCLES':
            bpy.context.scene.render.engine = 'CYCLES'

        # Setup bake settings
        bake_settings = bpy.context.scene.render.bake
        bake_settings.use_selected_to_active = False

        # Configure bake settings based on type
        if bake_type == 'DIFFUSE':
            bake_settings.type = 'DIFFUSE'
            bake_settings.use_pass_direct = True
            bake_settings.use_pass_indirect = True
        elif bake_type == 'NORMAL':
            bake_settings.type = 'NORMAL'
            bake_settings.normal_space = 'TANGENT'
        elif bake_type == 'ROUGHNESS':
            bake_settings.type = 'ROUGHNESS'
        elif bake_type == 'EMISSION':
            bake_settings.type = 'EMIT'

        # Set the target node as active
        nodes.active = target_node

        # Perform bake
        bpy.ops.object.bake(type=bake_settings.type)

        # Save the baked image
        image.save()

        return True

    except Exception as e:
        print(f"Baking failed: {str(e)}")
        return False

    finally:
        # Cleanup
        nodes.remove(bake_node)
        bpy.context.scene.render.engine = original_engine


class MATERIAL_OT_bake_material(Operator):
    bl_idname = "material.bake_material"
    bl_label = "Bake Material"
    bl_description = "Bakes the active material's textures"

    bake_type: EnumProperty(
        name="Bake Type",
        items=[
            ('DIFFUSE', "Diffuse", "Bake diffuse colors"),
            ('NORMAL', "Normal", "Bake normal maps"),
            ('ROUGHNESS', "Roughness", "Bake roughness maps"),
            ('EMISSION', "Emission", "Bake emission maps"),
        ],
        default='DIFFUSE'
    )

    use_selected: BoolProperty(
        name="Selected Objects Only",
        description="Only bake materials for selected objects",
        default=True
    )

    node_name: StringProperty(
        name="Node Name",
        description="Name of the specific node to bake (optional)",
        default=""
    )

    def execute(self, context):
        if self.node_name:
            # Bake specific node
            success = bake_node(self.node_name, self.bake_type)
            if success:
                self.report(
                    {'INFO'}, f"Node '{self.node_name}' baked successfully!")
            else:
                self.report(
                    {'ERROR'}, f"Failed to bake node '{self.node_name}'")
                return {'CANCELLED'}
        else:
            # Original functionality for baking entire material
            original_engine = context.scene.render.engine

            if context.scene.render.engine != 'CYCLES':
                self.report({'INFO'}, "Switching to Cycles for baking...")
                context.scene.render.engine = 'CYCLES'

            bake_settings = context.scene.render.bake
            bake_settings.use_selected_to_active = False

            if self.bake_type == 'DIFFUSE':
                bake_settings.type = 'DIFFUSE'
                bake_settings.use_pass_direct = True
                bake_settings.use_pass_indirect = True
            elif self.bake_type == 'NORMAL':
                bake_settings.type = 'NORMAL'
                bake_settings.normal_space = 'TANGENT'
            elif self.bake_type == 'ROUGHNESS':
                bake_settings.type = 'ROUGHNESS'
            elif self.bake_type == 'EMISSION':
                bake_settings.type = 'EMIT'

            objects_to_bake = context.selected_objects if self.use_selected else context.scene.objects

            try:
                for obj in objects_to_bake:
                    if obj.type == 'MESH' and obj.active_material:
                        context.view_layer.objects.active = obj
                        bpy.ops.object.bake(type=bake_settings.type)

                self.report({'INFO'}, "Baking completed successfully!")

            except Exception as e:
                self.report({'ERROR'}, f"Baking failed: {str(e)}")
                return {'CANCELLED'}

            finally:
                context.scene.render.engine = original_engine

        return {'FINISHED'}


class MATERIAL_PT_baker(Panel):
    bl_label = "Material Baker"
    bl_idname = "MATERIAL_PT_baker"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        op = row.operator("material.bake_material")

        layout.prop(op, "bake_type")
        layout.prop(op, "use_selected")
        layout.prop(op, "node_name")


classes = (
    MATERIAL_OT_bake_material,
    MATERIAL_PT_baker,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
