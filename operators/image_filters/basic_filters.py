import bpy
import numpy as np
try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageFilter = None
from ..common import numpy_to_pil, pil_to_numpy, PIL_AVAILABLE as COMMON_PIL_AVAILABLE
from ...paintsystem.image import ImageTiles

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

def gaussian_blur(image_tiles: ImageTiles, gaussian_sigma) -> ImageTiles:
    """
    Apply gaussian blur to ImageTiles.
    """
    blurred_tiles = {
        tile_num: _gaussian_blur_single(tile_array, gaussian_sigma)
        for tile_num, tile_array in image_tiles.tiles.items()
    }
    return ImageTiles(tiles=blurred_tiles)


def _sharpen_image_single(numpy_array, sharpen_amount):
    """Apply sharpen to a single numpy array."""
    if not PIL_AVAILABLE or not COMMON_PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is not available. Please install Pillow to use this feature.")
    img_uint8 = (np.clip(numpy_array, 0, 1) * 255).astype(np.uint8)
    img_pil = Image.fromarray(img_uint8, mode='RGBA')
    sharpened_pil = img_pil.filter(ImageFilter.UnsharpMask(amount=sharpen_amount, radius=1, threshold=0))
    img_smoothed = pil_to_numpy(sharpened_pil)
    return img_smoothed

def sharpen_image(image_tiles: ImageTiles, sharpen_amount) -> ImageTiles:
    """
    Apply sharpen to ImageTiles.
    """
    sharpened_tiles = {
        tile_num: _sharpen_image_single(tile_array, sharpen_amount)
        for tile_num, tile_array in image_tiles.tiles.items()
    }
    return ImageTiles(tiles=sharpened_tiles)


def _smooth_image_single(numpy_array, smooth_amount):
    """Apply smooth to a single numpy array."""
    if not PIL_AVAILABLE or not COMMON_PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is not available. Please install Pillow to use this feature.")
    img_pil = numpy_to_pil(numpy_array)
    smoothed_pil = img_pil.filter(ImageFilter.SMOOTH)
    img_smoothed = pil_to_numpy(smoothed_pil)
    return img_smoothed

def smooth_image(image_tiles: ImageTiles, smooth_amount) -> ImageTiles:
    """
    Apply smooth to ImageTiles.
    """
    smoothed_tiles = {
        tile_num: _smooth_image_single(tile_array, smooth_amount)
        for tile_num, tile_array in image_tiles.tiles.items()
    }
    return ImageTiles(tiles=smoothed_tiles)