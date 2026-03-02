import logging
import bpy
import sys

# Get the add-on name to ensure proper logger naming
from ..preferences import addon_package

_logger_name = addon_package() or "paintsystem"

def get_logger(name=None):
    """
    Get a configured logger for the add-on.
    It automatically respects the 'developer_mode' preference to toggle DEBUG/INFO levels.
    """
    logger_name = f"{_logger_name}.{name}" if name else _logger_name
    logger = logging.getLogger(logger_name)
    
    # Configure the logger only if it hasn't been configured yet
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(f'[{_logger_name}] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    # Dynamically set level based on preferences
    from ..preferences import get_preferences
    try:
        prefs = get_preferences(bpy.context)
        if prefs and prefs.developer_mode:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
    except Exception:
        # Fallback if preferences aren't accessible yet
        logger.setLevel(logging.INFO)

    return logger
