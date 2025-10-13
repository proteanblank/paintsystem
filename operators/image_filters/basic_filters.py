import bpy
import numpy as np
from PIL import Image, ImageFilter
from .common import blender_image_to_numpy, numpy_to_blender_image, numpy_to_pil, pil_to_numpy

def gaussian_blur(numpy_array, gaussian_sigma):
    img_pil = numpy_to_pil(numpy_array)
    radius = int(gaussian_sigma * 2)
    blurred_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
    img_smoothed = pil_to_numpy(blurred_pil)
    return img_smoothed


def sharpen_image(numpy_array, sharpen_amount):
    img_uint8 = (np.clip(numpy_array, 0, 1) * 255).astype(np.uint8)
    img_pil = Image.fromarray(img_uint8, mode='RGBA')
    sharpened_pil = img_pil.filter(ImageFilter.UnsharpMask(amount=sharpen_amount, radius=1, threshold=0))
    img_smoothed = pil_to_numpy(sharpened_pil)
    return img_smoothed


def smooth_image(numpy_array, smooth_amount):
    img_pil = numpy_to_pil(numpy_array)
    smoothed_pil = img_pil.filter(ImageFilter.SMOOTH)
    img_smoothed = pil_to_numpy(smoothed_pil)
    return img_smoothed