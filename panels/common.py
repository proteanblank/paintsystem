import bpy

# --
from ..paintsystem.data import PSContextMixin, get_global_layer, Channel
from ..custom_icons import get_icon
from ..preferences import get_preferences
from ..utils.nodes import find_node

def scale_content(context, layout, scale_x=1.2, scale_y=1.2):
    """Scale the content of the panel."""
    prefs = get_preferences(context)
    if not prefs.use_compact_design:
        layout.scale_x = scale_x
        layout.scale_y = scale_y
    return layout

icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()

def icon_parser(icon: str, default="NONE") -> str:
    if icon in icons:
        return icon
    return default


def get_icon_from_channel(channel: Channel) -> int:
    type_to_icon = {
        'COLOR': 'color_socket',
        'VECTOR': 'vector_socket',
        'FLOAT': 'float_socket',
    }
    return get_icon(type_to_icon.get(channel.type, 'color_socket'))


def get_group_node(context: bpy.types.Context) -> bpy.types.Node:
    ps_ctx = PSContextMixin.ensure_context(context)
    if not ps_ctx.active_group:
        return None
    return find_node(ps_ctx.active_material.node_tree, {'bl_idname': 'ShaderNodeGroup', 'node_tree': ps_ctx.active_group.node_tree})


def get_event_icons(kmi: bpy.types.KeyMapItem) -> list[str]:
    """Return a list of icons for a keymap item, including modifiers

    Args:
        kmi: KeyMapItem object

    Returns:
        list: List of Blender icon identifiers
    """
    
    if not kmi:
        return []
    # Create a list to store all icons
    icons = []

    # Add modifier icons first (in standard order)
    if kmi.ctrl:
        icons.append('EVENT_CTRL')
    if kmi.alt:
        icons.append('EVENT_ALT')
    if kmi.shift:
        icons.append('EVENT_SHIFT')
    if kmi.oskey:
        icons.append('EVENT_OS')

    # Dictionary mapping key types to icons
    key_icons = {
        # Mouse
        'LEFTMOUSE': 'MOUSE_LMB',
        'RIGHTMOUSE': 'MOUSE_RMB',
        'MIDDLEMOUSE': 'MOUSE_MMB',
        'WHEELUPMOUSE': 'MOUSE_LMB_DRAG',
        'WHEELDOWNMOUSE': 'MOUSE_LMB_DRAG',

        # Special keys
        'ESC': 'EVENT_ESC',
        'RET': 'EVENT_RETURN',
        'SPACE': 'EVENT_SPACEKEY',
        'TAB': 'EVENT_TAB',
        'DEL': 'EVENT_DELETEKEY',
        'BACK_SPACE': 'EVENT_BACKSPACEKEY',
        'COMMA': 'EVENT_COMMA',
        'PERIOD': 'EVENT_PERIOD',
        'SEMI_COLON': 'EVENT_SEMI_COLON',
        'QUOTE': 'EVENT_QUOTE',

        # Numbers
        '0': 'EVENT_0',
        '1': 'EVENT_1',
        '2': 'EVENT_2',
        '3': 'EVENT_3',
        '4': 'EVENT_4',
        '5': 'EVENT_5',
        '6': 'EVENT_6',
        '7': 'EVENT_7',
        '8': 'EVENT_8',
        '9': 'EVENT_9',

        # Letters
        'A': 'EVENT_A',
        'B': 'EVENT_B',
        'C': 'EVENT_C',
        'D': 'EVENT_D',
        'E': 'EVENT_E',
        'F': 'EVENT_F',
        'G': 'EVENT_G',
        'H': 'EVENT_H',
        'I': 'EVENT_I',
        'J': 'EVENT_J',
        'K': 'EVENT_K',
        'L': 'EVENT_L',
        'M': 'EVENT_M',
        'N': 'EVENT_N',
        'O': 'EVENT_O',
        'P': 'EVENT_P',
        'Q': 'EVENT_Q',
        'R': 'EVENT_R',
        'S': 'EVENT_S',
        'T': 'EVENT_T',
        'U': 'EVENT_U',
        'V': 'EVENT_V',
        'W': 'EVENT_W',
        'X': 'EVENT_X',
        'Y': 'EVENT_Y',
        'Z': 'EVENT_Z',

        # Function keys
        'F1': 'EVENT_F1',
        'F2': 'EVENT_F2',
        'F3': 'EVENT_F3',
        'F4': 'EVENT_F4',
        'F5': 'EVENT_F5',
        'F6': 'EVENT_F6',
        'F7': 'EVENT_F7',
        'F8': 'EVENT_F8',
        'F9': 'EVENT_F9',
        'F10': 'EVENT_F10',
        'F11': 'EVENT_F11',
        'F12': 'EVENT_F12',

        # Arrows
        'LEFT_ARROW': 'EVENT_LEFT_ARROW',
        'RIGHT_ARROW': 'EVENT_RIGHT_ARROW',
        'UP_ARROW': 'EVENT_UP_ARROW',
        'DOWN_ARROW': 'EVENT_DOWN_ARROW',

        # Numpad
        'NUMPAD_0': 'EVENT_0',
        'NUMPAD_1': 'EVENT_1',
        'NUMPAD_2': 'EVENT_2',
        'NUMPAD_3': 'EVENT_3',
        'NUMPAD_4': 'EVENT_4',
        'NUMPAD_5': 'EVENT_5',
        'NUMPAD_6': 'EVENT_6',
        'NUMPAD_7': 'EVENT_7',
        'NUMPAD_8': 'EVENT_8',
        'NUMPAD_9': 'EVENT_9',
        'NUMPAD_PLUS': 'EVENT_PLUS',
        'NUMPAD_MINUS': 'EVENT_MINUS',
        'NUMPAD_ASTERIX': 'EVENT_ASTERISK',
        'NUMPAD_SLASH': 'EVENT_SLASH',
        'NUMPAD_PERIOD': 'EVENT_PERIOD',
        'NUMPAD_ENTER': 'EVENT_RETURN',
    }

    # Add the key icon if it exists in our mapping
    if kmi.type in key_icons:
        icons.append(key_icons[kmi.type])
    else:
        # Fall back to a generic keyboard icon for unknown keys
        icons.append('KEYINGSET')

    return icons

def find_keymap(keymap_name):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km in kc.keymaps:
            if km:
                kmi = km.keymap_items.get(keymap_name)
                if kmi:
                    return kmi
    return None

def find_keymap_by_name(keymap_name) -> list[bpy.types.KeyMapItem]:
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc:
        for km in kc.keymaps:
            if km:
                for kmi in km.keymap_items:
                    if kmi.name == keymap_name:
                        return kmi
    return None