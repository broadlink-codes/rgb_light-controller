import time
import numpy as np
import argparse
import os
from PIL import ImageGrab, Image
from collections import Counter
from utils.light_manager import LightManager
import mss
import mss.tools

def get_most_prominent_color(img_array):
    """
    Find the most eye-catching color in the image based on saturation, 
    brightness, and prevalence.
    """
    # Reshape the array to a list of pixels
    pixels = img_array.reshape(-1, 3)
    
    # Convert each pixel to a tuple (for hashability in Counter)
    pixel_tuples = [tuple(pixel) for pixel in pixels]
    
    # Count occurrences of each color
    color_counter = Counter(pixel_tuples)
    
    # Get the top 20 most common colors
    common_colors = color_counter.most_common(20)
    
    max_score = -1
    most_eye_catching = common_colors[0][0]  # Default to most common
    
    for color, count in common_colors:
        r, g, b = color
        
        # Skip near-black and near-white colors
        if (r < 30 and g < 30 and b < 30) or (r > 225 and g > 225 and b > 225):
            continue
        
        # Calculate saturation (0-1)
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = 0 if max_val == 0 else (max_val - min_val) / max_val
        
        # Calculate brightness (0-1)
        brightness = (r + g + b) / (3 * 255)
        
        # Calculate prevalence weight
        prevalence = count / len(pixels)
        
        # Score based on weighted saturation, brightness and prevalence
        # High saturation and moderate-high brightness make colors eye-catching
        # We want colors that stand out but also have reasonable presence
        eye_catching_score = (saturation * 0.7 + brightness * 0.3) * (prevalence + 0.2)
        
        if eye_catching_score > max_score:
            max_score = eye_catching_score
            most_eye_catching = color
    
    return tuple(int(x) for x in most_eye_catching)

def capture_screen(display_id=None):
    """
    Capture the screen and return as PIL Image and numpy array.
    If display_id is specified, capture only that display.
    """
    try:
        with mss.mss() as sct:
          monitor = sct.monitors[display_id]
          if monitor:
              sct_img = sct.grab(monitor)
              img = Image.frombytes("RGB", sct_img.size, sct_img.rgb, "raw", "RGB")
              screenshot = img
          else:
              raise Exception(f"Error: Display with ID {display_id} not found.")
          
        return screenshot, np.array(screenshot)
    except TypeError:
        # Fallback for older versions that don't support the display parameter
        try:
            screenshot = ImageGrab.grab()
            return screenshot, np.array(screenshot)
        except Exception as e:
            print(f"Error capturing screen: {e}")
            # Return a small black image in case of error
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
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5

def match_color_from_map(rgb, color_map):
    """Match an RGB color to the closest color in the color map using Euclidean distance."""
    min_distance = float('inf')
    closest_color = None
    
    for color_name, color_rgb in color_map.items():
        distance = euclidean_distance(rgb, color_rgb)
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name
    
    return closest_color

def monitor_screen(interval, light_manager: LightManager, display_id=None, duration=None, save_images=False):
    """
    Monitor screen colors at specified intervals.
    
    Args:
        interval: Time between screen captures in seconds
        display_id: ID of the display to capture (None for primary display)
        duration: Total monitoring duration in seconds (None for indefinite)
        save_images: Whether to save the captured images
    """
    start_time = time.time()
    output_dir = create_output_dir() if save_images else None
    
    try:
        while True:
            # Check if duration limit reached
            if duration and time.time() - start_time > duration:
                print(f"Duration limit of {duration} seconds reached. Exiting.")
                break
                
            # Capture screen and get the most prominent color
            timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            pil_img, img_array = capture_screen(display_id)
            color = get_most_prominent_color(img_array)
            
            # Print the result with timestamp
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            display_text = f"Screen {display_id}" if display_id is not None else "Primary screen"
            print(f"[{timestamp}] {display_text} - Most prominent color: RGB{color}")

            color_name = match_color_from_map(color, light_manager.light_config["color_mapping"])


            commands = ["off" if color_name == "black" else color_name]
            if light_manager.power_status.value == "off" and color_name != "black":
                commands = ["on"] + commands

            light_manager.execute_commands(commands)
            
            # Save the image if requested
            if save_images:
                screen_id = display_id if display_id is not None else "primary"
                filename = f"{output_dir}/screen_{screen_id}_{timestamp_str}.png"
                pil_img.save(filename)
                print(f"    Saved image to: {filename}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(f"Error: {e}")