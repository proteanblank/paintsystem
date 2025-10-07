import bpy
from .data import sort_actions, parse_context
from .graph.basic_layers import get_layer_version_for_type
import time
from .graph.nodetree_builder import get_nodetree_version

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


@bpy.app.handlers.persistent
def load_post(scene):
    start_time = time.time()
    ps_ctx = parse_context(bpy.context)
    if not ps_ctx.ps_scene_data:
        return
    # Layer Versioning
    for global_layer in ps_ctx.ps_scene_data.layers:
        target_version = get_layer_version_for_type(global_layer.type)
        if get_nodetree_version(global_layer.node_tree) != target_version:
            print(f"Updating layer {global_layer.name} to version {target_version}")
            global_layer.update_node_tree(bpy.context)
    print(f"Paint System: Checked {len(ps_ctx.ps_scene_data.layers)} layers in {round((time.time() - start_time) * 1000, 2)} ms")


def register():
    bpy.app.handlers.frame_change_pre.append(frame_change_pre)
    bpy.app.handlers.load_post.append(load_post)

def unregister():
    bpy.app.handlers.frame_change_pre.remove(frame_change_pre)
    bpy.app.handlers.load_post.remove(load_post)