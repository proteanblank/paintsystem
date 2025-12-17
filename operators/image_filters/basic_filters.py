import bpy
import numpy as np
try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageFilter = None
from ..common import blender_image_to_numpy, numpy_to_blender_image, numpy_to_pil, pil_to_numpy, PIL_AVAILABLE as COMMON_PIL_AVAILABLE

def _gaussian_blur_single(numpy_array, gaussian_sigma):
    """Apply gaussian blur to a single numpy array."""
    if not PIL_AVAILABLE or not COMMON_PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is not available. Please install Pillow to use this feature.")
    
    # Handle alpha channel correctly for straight alpha (Blender format)
    # Convert to premultiplied alpha (RGBa), blur, then convert back to straight alpha (RGBA)
    # This prevents dark edges when blurring alpha transitions
    
    img_pil = numpy_to_pil(numpy_array)
    
    # Check if image has alpha channel
    if img_pil.mode == 'RGBA':
        # Convert to premultiplied alpha (RGBa mode)
        img_pil = img_pil.convert('RGBa')
        radius = int(gaussian_sigma * 2)
        blurred_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
        # Convert back to straight alpha (RGBA)
        blurred_pil = blurred_pil.convert('RGBA')
    else:
        # No alpha channel, blur directly
        radius = int(gaussian_sigma * 2)
        blurred_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
    
    img_smoothed = pil_to_numpy(blurred_pil)
    return img_smoothed

def gaussian_blur(numpy_array_or_tiles, gaussian_sigma):
    """
    Apply gaussian blur to numpy array or dictionary of tiles.
    For UDIM images, pass a dictionary mapping tile numbers to numpy arrays.
    For non-UDIM images, pass a single numpy array.
    """
    if isinstance(numpy_array_or_tiles, dict):
        # Dictionary of tiles (UDIM) - apply filter to each tile
        return {tile_num: _gaussian_blur_single(tile_array, gaussian_sigma) 
                for tile_num, tile_array in numpy_array_or_tiles.items()}
    else:
        # Single array (non-UDIM)
        return _gaussian_blur_single(numpy_array_or_tiles, gaussian_sigma)


def _sharpen_image_single(numpy_array, sharpen_amount):
    """Apply sharpen to a single numpy array."""
    if not PIL_AVAILABLE or not COMMON_PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is not available. Please install Pillow to use this feature.")
    img_uint8 = (np.clip(numpy_array, 0, 1) * 255).astype(np.uint8)
    img_pil = Image.fromarray(img_uint8, mode='RGBA')
    sharpened_pil = img_pil.filter(ImageFilter.UnsharpMask(amount=sharpen_amount, radius=1, threshold=0))
    img_smoothed = pil_to_numpy(sharpened_pil)
    return img_smoothed

def sharpen_image(numpy_array_or_tiles, sharpen_amount):
    """
    Apply sharpen to numpy array or dictionary of tiles.
    For UDIM images, pass a dictionary mapping tile numbers to numpy arrays.
    For non-UDIM images, pass a single numpy array.
    """
    if isinstance(numpy_array_or_tiles, dict):
        # Dictionary of tiles (UDIM) - apply filter to each tile
        return {tile_num: _sharpen_image_single(tile_array, sharpen_amount) 
                for tile_num, tile_array in numpy_array_or_tiles.items()}
    else:
        # Single array (non-UDIM)
        return _sharpen_image_single(numpy_array_or_tiles, sharpen_amount)


def _smooth_image_single(numpy_array, smooth_amount):
    """Apply smooth to a single numpy array."""
    if not PIL_AVAILABLE or not COMMON_PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is not available. Please install Pillow to use this feature.")
    img_pil = numpy_to_pil(numpy_array)
    smoothed_pil = img_pil.filter(ImageFilter.SMOOTH)
    img_smoothed = pil_to_numpy(smoothed_pil)
    return img_smoothed

def smooth_image(numpy_array_or_tiles, smooth_amount):
    """
    Apply smooth to numpy array or dictionary of tiles.
    For UDIM images, pass a dictionary mapping tile numbers to numpy arrays.
    For non-UDIM images, pass a single numpy array.
    """
    if isinstance(numpy_array_or_tiles, dict):
        # Dictionary of tiles (UDIM) - apply filter to each tile
        return {tile_num: _smooth_image_single(tile_array, smooth_amount) 
                for tile_num, tile_array in numpy_array_or_tiles.items()}
    else:
        # Single array (non-UDIM)
        return _smooth_image_single(numpy_array_or_tiles, smooth_amount)