import os
import time
import numpy as np
from collections import Counter, deque, defaultdict
import mss
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Optional, Tuple, List
from sklearn.cluster import KMeans

from utils.light_manager import LightManager

import numpy as np
import cv2

def get_most_prominent_color_optimized(image_np: np.ndarray) -> tuple[int, int, int]:
    """
    Returns the most contrastive (brightest dominant) color from the image.

    Args:
        image_np (np.ndarray): Image as a NumPy array in RGB format.

    Returns:
        tuple[int, int, int]: Dominant contrast color as (R, G, B).
    """
    # Convert to grayscale for brightness detection
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # Use top 0.5% brightest pixels
    threshold = np.percentile(gray, 99.5)
    bright_mask = gray >= threshold

    # Extract corresponding RGB pixels
    bright_pixels = image_np[bright_mask]

    # Use KMeans to find dominant bright color
    if len(bright_pixels) == 0:
        return (0, 0, 0)  # fallback if no bright region found

    kmeans = KMeans(n_clusters=1, random_state=0).fit(bright_pixels)
    dominant_color = tuple(map(int, kmeans.cluster_centers_[0]))
    return dominant_color


# def get_most_prominent_color_optimized(img_array):
#     """
#     Find the most eye-catching color in the image based on saturation, 
#     brightness, and prevalence - optimized version.
#     """
#     # Downsample the image for faster processing
#     h, w, _ = img_array.shape
#     downsample_factor = 4  # Process every 4th pixel
#     downsampled = img_array[::downsample_factor, ::downsample_factor]
    
#     # Reshape the array to a list of pixels
#     pixels = downsampled.reshape(-1, 3)
    
#     # Filter out near-black and near-white colors immediately
#     filtered_pixels = []
#     for pixel in pixels:
#         r, g, b = pixel
#         if not ((r < 30 and g < 30 and b < 30) or (r > 225 and g > 225 and b > 225)):
#             filtered_pixels.append(tuple(pixel))
    
#     # If all pixels were filtered out, take the most common color from original
#     if not filtered_pixels:
#         pixel_tuples = [tuple(pixel) for pixel in pixels]
#         return tuple(int(x) for x in Counter(pixel_tuples).most_common(1)[0][0])
    
#     # Count occurrences of each filtered color
#     color_counter = Counter(filtered_pixels)
    
#     # Get the top 10 most common colors (reduced from 20)
#     common_colors = color_counter.most_common(10)
    
#     max_score = -1
#     most_eye_catching = common_colors[0][0]  # Default to most common
    
#     total_pixels = len(filtered_pixels)
    
#     for color, count in common_colors:
#         r, g, b = color
        
#         # Calculate saturation (0-1)
#         max_val = max(r, g, b)
#         min_val = min(r, g, b)
#         saturation = 0 if max_val == 0 else (max_val - min_val) / max_val
        
#         # Calculate brightness (0-1)
#         brightness = (r + g + b) / (3 * 255)
        
#         # Calculate prevalence weight
#         prevalence = count / total_pixels
        
#         # Score based on weighted saturation, brightness and prevalence
#         eye_catching_score = (saturation * 0.7 + brightness * 0.3) * (prevalence + 0.2)
        
#         if eye_catching_score > max_score:
#             max_score = eye_catching_score
#             most_eye_catching = color
    
#     return tuple(int(x) for x in most_eye_catching)

def capture_screen_optimized(display_id=None):
    """
    Optimized screen capture function using mss which is faster than ImageGrab
    """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1 if display_id is None else display_id]
            sct_img = sct.grab(monitor)
            # Convert directly to numpy array, skipping PIL conversion
            img_array = np.array(sct_img)
            # Convert BGRA to RGB
            img_array = img_array[:, :, [2, 1, 0]]
            # Create PIL image only if needed
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img, img_array
    except Exception as e:
        print(f"Error capturing screen: {e}")
        black_img = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
        return black_img, np.zeros((10, 10, 3), dtype=np.uint8)

def create_output_dir(dir_name="screen_captures"):
    """
    Create directory for saving screenshots if it doesn't exist.
    """
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name

def euclidean_distance(color1, color2):
    """Calculate Euclidean distance between two RGB colors."""
    # Vectorized version
    return np.sqrt(np.sum((np.array(color1) - np.array(color2)) ** 2))

# Pre-compute color distances table
def precompute_color_distances(color_map):
    """Create a lookup table of colors for faster matching"""
    color_distances = {}
    for color_name, color_rgb in color_map.items():
        # Create a tuple for each RGB value from 0-255
        color_distances[color_name] = np.array(color_rgb)
    return color_distances

def match_color_from_map_optimized(rgb, color_map, precomputed_colors):
    """Match an RGB color to the closest color in the color map using vectorized operations."""
    rgb_array = np.array(rgb)
    min_distance = float('inf')
    closest_color = None
    
    for color_name, color_array in precomputed_colors.items():
        distance = np.sqrt(np.sum((rgb_array - color_array) ** 2))
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    
    return closest_color

class ScreenMonitor:
    def __init__(self, light_managers: List[LightManager], display_id=None, save_images=False):
        self.light_managers: List[LightManager] = light_managers
        self.display_id = display_id
        self.save_images = save_images
        self.output_dir = create_output_dir() if save_images else None
                    

        # Keep executor just for saving images
        self.image_executor = ThreadPoolExecutor(max_workers=1)
        
        self.precomputed_color_per_device = {
            light_manager.device_name: precompute_color_distances(
                light_manager.light_config["color_mapping"]
            )
            for light_manager in self.light_managers
        }
            
                
    def process_frame(self, img_array):
        """Process a single frame and update lights if needed"""
        color = get_most_prominent_color_optimized(img_array)
        
      
        color_name_per_device = {
            light_manager.device_name: match_color_from_map_optimized(
                color,
                light_manager.light_config["color_mapping"],
                self.precomputed_color_per_device[light_manager.device_name]
            )
            for light_manager in self.light_managers
        } 
        
        return color_name_per_device
    
    def get_color_name(self):
        """Start monitoring the screen"""
                
        # Capture screen
        pil_img, img_array = capture_screen_optimized(self.display_id)
        
        # Process the frame
        color_name_per_device = self.process_frame(img_array)
        
        # Save the image if requested and color changed
        if self.save_images:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            screen_id = self.display_id if self.display_id is not None else "primary"
            filename = f"{self.output_dir}/screen_{screen_id}_{timestamp_str}.png"
            
            # Save in a separate thread to avoid blocking
            self.image_executor.submit(pil_img.save, filename)
            print(f"    Saving image to: {filename}")
        
        return color_name_per_device
        
    