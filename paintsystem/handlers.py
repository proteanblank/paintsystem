import bpy
from .data import parse_context, get_global_layer, sort_actions, get_all_layers

@bpy.app.handlers.persistent
def frame_change_pre(scene):
    if not hasattr(scene, 'ps_scene_data'):
        return
    update_task = {}
    for global_layer in scene.ps_scene_data.layers:
        sorted_actions = sort_actions(bpy.context, global_layer)
        for action in sorted_actions:
            match action.action_bind:
                case 'FRAME':
                    if action.frame <= scene.frame_current:
                        # print(f"Frame {action.frame} found at frame {scene.frame_current}")
                        if action.action_type == 'ENABLE' and update_task.get(global_layer, global_layer.enabled) == False:
                            update_task[global_layer] = True
                        elif action.action_type == 'DISABLE' and update_task.get(global_layer, global_layer.enabled) == True:
                            update_task[global_layer] = False
                case 'MARKER':
                    marker = scene.timeline_markers.get(action.marker_name)
                    if marker and marker.frame <= scene.frame_current:
                        # print(f"Marker {marker.frame} found at frame {scene.frame_current}")
                        if action.action_type == 'ENABLE' and update_task.get(global_layer, global_layer.enabled) == False:
                            update_task[global_layer] = True
                        elif action.action_type == 'DISABLE' and update_task.get(global_layer, global_layer.enabled) == True:
                            update_task[global_layer] = False
                case _:
                    pass
    for global_layer, enabled in update_task.items():
        if global_layer.enabled != enabled:
            # print(f"Updating layer {global_layer.name} to {enabled}")
            global_layer.enabled = enabled


def register():
    bpy.app.handlers.frame_change_pre.append(frame_change_pre)

def unregister():
    bpy.app.handlers.frame_change_pre.remove(frame_change_pre)