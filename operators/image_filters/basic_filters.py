import bpy
import numpy as np
from PIL import Image, ImageFilter
from .common import blender_image_to_numpy, numpy_to_blender_image

def gaussian_blur(numpy_array, gaussian_sigma):
    img_uint8 = (np.clip(numpy_array, 0, 1) * 255).astype(np.uint8)
    img_pil = Image.fromarray(img_uint8, mode='RGBA')
    radius = int(gaussian_sigma * 2)
    blurred_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
    img_smoothed = np.array(blurred_pil, dtype=np.float64) / 255.0
    return img_smoothed