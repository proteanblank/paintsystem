import bpy
from bpy.types import Image 
import numpy as np
import time

def blender_image_to_numpy(image: Image):
    """Convert Blender image to numpy array."""
    start_time = time.time()
    if image is None:
        return None
        
    # Get image dimensions
    width, height = image.size
    
    # Create numpy array
    pixels = np.array(image.pixels)
    print(f"Time taken to copy pixels: {(time.time() - start_time)*1000} milliseconds")
    
    # Reshape to (height, width, channels)
    if image.channels == 4:  # RGBA
        pixels = pixels.reshape((height, width, 4))
    else:
        raise ValueError(f"Unsupported image format with {image.channels} channels")
    
    # Flip vertically (Blender uses bottom-left origin, numpy uses top-left)
    pixels = np.flipud(pixels)
    end_time = time.time()
    print(f"Blender image to numpy took {(end_time - start_time)*1000} milliseconds")
    return pixels

def numpy_to_blender_image(array, image_name="BrushPainted", create_new=True) -> Image:
    """Convert numpy array back to Blender image."""
    start_time = time.time()
    # Flip vertically back to Blender coordinate system
    array = np.flipud(array)
    
    # Ensure array is in [0, 1] range
    array = np.clip(array, 0, 1)
    
    # Get dimensions
    height, width = array.shape[:2]
    channels = array.shape[2] if len(array.shape) == 3 else 1
    
    # Flatten array
    pixels = array.ravel()
    
    # Try to get the image
    if create_new:
        new_image = bpy.data.images.new(image_name, width=width, height=height, alpha=True)
    else:
        new_image = bpy.data.images.get(image_name)
        if new_image is None:
            raise ValueError(f"Image {image_name} not found")
    
    # Set pixels
    if channels == 4:
        new_image.pixels = pixels
    else:
        raise ValueError(f"Unsupported image format with {channels} channels")
    
    # Update image
    new_image.update()
    end_time = time.time()
    print(f"Numpy to blender image took {(end_time - start_time)*1000} milliseconds")
    return new_image

def switch_image_content(image1: Image, image2: Image):
    """Switch the contents of two images."""
    start_time = time.time()
    temp_pixels = image1.pixels[:]
    image1.pixels = image2.pixels[:]
    image1.update()
    image1.update_tag()
    image2.pixels = temp_pixels
    image2.update()
    image2.update_tag()
    end_time = time.time()
    print(f"Switch image content took {(end_time - start_time)*1000} milliseconds")