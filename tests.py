import bpy
from bpy.utils import register_classes_factory
from unittest import TestLoader, TestResult, TextTestRunner
from pathlib import Path
from paint_system import PaintSystem


def run_tests():
    test_loader = TestLoader()

    test_directory = str(Path(__file__).resolve().parent / 'tests')

    test_suite = test_loader.discover(test_directory, pattern='test_*.py')
    runner = TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    return result


class PAINTSYSTEM_OT_run_tests(bpy.types.Operator):
    bl_idname = "paintsystem.run_tests"
    bl_label = "Run Tests"
    bl_description = "Run the test suite for the paint system"
    
    @classmethod
    def poll(cls, context):
        ps = PaintSystem(context)
        return ps.active_object is not None
    
    def execute(self, context):
        result = run_tests()
        print(result)
        return {'FINISHED'}


classes = (
    PAINTSYSTEM_OT_run_tests,
)

register, unregister = register_classes_factory(classes)