# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from bpy.utils import register_submodule_factory
import bpy
from .paint_system import PaintSystem
from bpy.app.handlers import persistent

from . import auto_load
bl_info = {
    "name": "Paint System",
    "author": "Tawan Sunflower",
    "description": "",
    "blender": (4, 1, 0),
    "version": (1, 0, 4),
    "location": "View3D > Sidebar > Paint System",
    "warning": "",
    "category": "Node",
}


auto_load.init()


@persistent
def mode_change_handler(scene):
    global previous_mode

    # Get the active object and its mode
    obj = bpy.context.object
    if obj and obj.mode == 'TEXTURE_PAINT':
        update_active_image()


def update_active_image():
    ps = PaintSystem(bpy.context)
    image_paint = bpy.context.tool_settings.image_paint
    mat = ps.active_material
    if not mat:
        return
    active_layer = ps.active_layer
    if not active_layer or active_layer.type != 'IMAGE':
        return
    if image_paint.mode == 'IMAGE':
        image_paint.mode = 'MATERIAL'
    for i, image in enumerate(mat.texture_paint_images):
        if image == active_layer.image:
            mat.paint_active_slot = i
            break


submodules = [
    "operators",
    "properties",
    "panels",
    # "node_organizer",
    # "test",
]


_register, _unregister = register_submodule_factory(__name__, submodules)


def register():
    _register()
    bpy.app.handlers.depsgraph_update_post.append(mode_change_handler)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(mode_change_handler)
    _unregister()
