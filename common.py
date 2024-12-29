import bpy


def get_package_name():
    if __package__.startswith('bl_ext'):
        # 4.2
        return __package__
    else:
        return __package__.split(".")[0]
