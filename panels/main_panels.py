import bpy
from bpy.utils import register_classes_factory
from bpy.types import Panel, Menu, UIList
from .common import (
    PSContextMixin,
    get_icon,
    scale_content,
    check_group_multiuser
)

from ..paintsystem.data import LegacyPaintSystemContextParser

class MAT_MT_PaintSystemMaterialSelectMenu(PSContextMixin, Menu):
    bl_label = "Material Select Menu"
    bl_idname = "MAT_MT_PaintSystemMaterialSelectMenu"

    def draw(self, context):
        layout = self.layout
        ps_ctx = self.parse_context(context)
        ob = ps_ctx.ps_object
        for idx, material_slot in enumerate(ob.material_slots):
            is_selected = ob.active_material_index == idx
            mat = material_slot.material is not None
            if mat and hasattr(mat, "paint_system") and mat.paint_system.groups:
                op = layout.operator("paint_system.select_material_index", text=material_slot.material.name if mat else "Empty Material", icon="MATERIAL" if mat else "MESH_CIRCLE", depress=is_selected)
            else:
                op = layout.operator("paint_system.select_material_index", text=material_slot.material.name if mat else "Empty Material", icon="MATERIAL" if mat else "MESH_CIRCLE", depress=is_selected)
            op.index = idx


# class MAT_MT_PaintsystemTemplateSelectMenu(PSContextMixin, Menu):
#     bl_label = "Template Select Menu"
#     bl_idname = "MAT_MT_PaintsystemTemplateSelectMenu"
    
#     def draw(self, context):
#         layout = self.layout
#         ps_ctx = self.parse_context(context)
#         for template in TEMPLATE_ENUM:
#             op = layout.operator("paint_system.new_group", text=template[0], icon=template[3])
#             op.template = template[0]

class MATERIAL_UL_PaintSystemGroups(PSContextMixin, UIList):
    bl_idname = "MATERIAL_UL_PaintSystemGroups"
    bl_label = "Paint System Groups"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        layout.prop(item.node_tree, "name", text="", emboss=False)


class MAT_PT_PaintSystemGroups(PSContextMixin, Panel):
    bl_idname = "MAT_PT_PaintSystemGroups"
    bl_label = "Groups"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    # bl_category = 'Paint System'
    # bl_parent_id = 'MAT_PT_LayerSettings'
    # bl_options = {'DEFAULT_CLOSED'}
    bl_ui_units_x = 12

    def draw(self, context):
        ps_ctx = self.parse_context(context)
        layout = self.layout
        layout.label(text="Groups")
        scale_content(context, layout)
        layout.template_list("MATERIAL_UL_PaintSystemGroups", "", ps_ctx.ps_mat_data, "groups", ps_ctx.ps_mat_data, "active_index")

class MAT_PT_PaintSystemMainPanel(PSContextMixin, Panel):
    bl_idname = 'MAT_PT_PaintSystemMainPanel'
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Paint System"
    bl_category = 'Paint System'
    
    # def draw_header_preset(self, context):
    #     layout = self.layout
    #     row = layout.row(align=True)
    #     row.scale_y = 1.2
    #     row.operator("paint_system.new_group", text="Add", icon="ADD")
    #     row.operator("paint_system.delete_group", text="", icon="REMOVE")
    
    @classmethod
    def poll(cls, context):
        ps_ctx = cls.parse_context(context)
        return ps_ctx.ps_object is not None
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon_value=get_icon("sunflower"))

    def draw(self, context):
        layout = self.layout
        legacy_ps_ctx = LegacyPaintSystemContextParser(context)
        legacy_material_settings = legacy_ps_ctx.get_material_settings()
        if legacy_material_settings and legacy_material_settings.groups:
            box = layout.box()
            box.alert = True
            scale_content(context, box, 1.5, 1.5)
            col = box.column()
            col.label(text="Legacy Paint System Detected", icon="ERROR")
            col.operator("paint_system.update_paint_system_data", text="Update Paint System Data")
            
            return
        ps_ctx = self.parse_context(context)
        ob = ps_ctx.ps_object
        if ob.type != 'MESH':
            return
        mat = ps_ctx.active_material
        groups = ps_ctx.ps_mat_data.groups
        if any([ob.material_slots[i].material for i in range(len(ob.material_slots))]):
            col = layout.column(align=True)
            row = col.row(align=True)
            scale_content(context, row, 1.5, 1.2)
            # if not ps.preferences.use_compact_design:
            #     row.scale_x = 1.5
            #     row.scale_y = 1.2
            # row.prop_enum(ob, "material_slot_selector", "Material", text="")
            # row.template_list("MATERIAL_UL_PaintSystemMatSlots", "", ob, "material_slots", ob, "active_material_index", rows=2)
            # row.template_ID(ob, "material_slots", text="Material Slots")
            row.menu("MAT_MT_PaintSystemMaterialSelectMenu", text="" if ob.active_material else "Empty Material", icon="MATERIAL" if ob.active_material else "MESH_CIRCLE")
            if mat:
                row.prop(mat, "name", text="")
            # row.template_ID(ob, "active_material", text="")
            # row.prop_search(ob, "active_material", ob, "material_slots", text="")
            # row.panel_prop(ob, "material_slots")
            # box = row.box()
            # col = box.column(align=True)
            # for idx, material_slot in enumerate(ob.material_slots):
            #     is_selected = ob.active_material_index == idx
            #     op = col.operator("paint_system.select_material_index", text=material_slot.material.name if material_slot.material else " ", icon="MATERIAL", depress=is_selected, emboss=is_selected)
            #     op.index = idx
            
            # row.operator("object.material_slot_add", icon='ADD', text="")
            ops_row = row.row(align=True)
            if groups:
                ops_row.operator("paint_system.new_group", icon='ADD', text="")
            ops_row.operator("paint_system.delete_group", icon='REMOVE', text="")
            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")
        
        if len(groups) > 1:
            row = col.row(align=True)
            scale_content(context, row, 1.5, 1.2)
            row.popover("MAT_PT_PaintSystemGroups", text=ps_ctx.active_group.node_tree.name, icon="NODETREE")
        
        if ps_ctx.active_group and check_group_multiuser(ps_ctx.active_group.node_tree):
            # Show a warning
            box = layout.box()
            box.alert = True
            box.label(text="Duplicated Paint System Data", icon="ERROR")
            row = box.row(align=True)
            scale_content(context, row, 1.5, 1.5)
            row.operator("paint_system.duplicate_paint_system_data", text="Fix Data Duplication")
            return

        if not ps_ctx.active_group:
            row = layout.row()
            row.scale_x = 2
            row.scale_y = 2
            row.operator("paint_system.new_group", text="Add Paint System", icon="ADD")
            return
        brush_imported = False
        for brush in bpy.data.brushes:
            if brush.name.startswith("PS_"):
                brush_imported = True
                break
        if not brush_imported:
            layout.operator('paint_system.add_preset_brushes')
        # layout.label(text="Welcome to the Paint System!")
        # layout.operator("paint_system.new_image_layer", text="Create New Image Layer")


classes = (
    MATERIAL_UL_PaintSystemGroups,
    MAT_MT_PaintSystemMaterialSelectMenu,
    MAT_PT_PaintSystemMainPanel,
    MAT_PT_PaintSystemGroups,
)

register, unregister = register_classes_factory(classes)