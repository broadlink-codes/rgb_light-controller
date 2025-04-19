import os
import time
import numpy as np
from collections import Counter, deque, defaultdict
import mss
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Optional, Tuple

from utils.light_manager import LightManager

def get_most_prominent_color_optimized(img_array):
    """
    Find the most eye-catching color in the image based on saturation, 
    brightness, and prevalence - optimized version.
    """
    # Downsample the image for faster processing
    h, w, _ = img_array.shape
    downsample_factor = 4  # Process every 4th pixel
    downsampled = img_array[::downsample_factor, ::downsample_factor]
    
    # Reshape the array to a list of pixels
    pixels = downsampled.reshape(-1, 3)
    
    # Filter out near-black and near-white colors immediately
    filtered_pixels = []
    for pixel in pixels:
        r, g, b = pixel
        if not ((r < 30 and g < 30 and b < 30) or (r > 225 and g > 225 and b > 225)):
            filtered_pixels.append(tuple(pixel))
    
    # If all pixels were filtered out, take the most common color from original
    if not filtered_pixels:
        pixel_tuples = [tuple(pixel) for pixel in pixels]
        return tuple(int(x) for x in Counter(pixel_tuples).most_common(1)[0][0])
    
    # Count occurrences of each filtered color
    color_counter = Counter(filtered_pixels)
    
    # Get the top 10 most common colors (reduced from 20)
    common_colors = color_counter.most_common(10)
    
    max_score = -1
    most_eye_catching = common_colors[0][0]  # Default to most common
    
    total_pixels = len(filtered_pixels)
    
    for color, count in common_colors:
        r, g, b = color
        
        # Calculate saturation (0-1)
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        saturation = 0 if max_val == 0 else (max_val - min_val) / max_val
        
        # Calculate brightness (0-1)
        brightness = (r + g + b) / (3 * 255)
        
        # Calculate prevalence weight
        prevalence = count / total_pixels
        
        # Score based on weighted saturation, brightness and prevalence
        eye_catching_score = (saturation * 0.7 + brightness * 0.3) * (prevalence + 0.2)
        
        if eye_catching_score > max_score:
            max_score = eye_catching_score
            most_eye_catching = color
    
    return tuple(int(x) for x in most_eye_catching)

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
    def __init__(self, light_manager, display_id=None, interval=0.1, duration=None, save_images=False):
        self.light_manager: LightManager = light_manager
        self.display_id = display_id
        self.interval = interval
        self.duration = duration
        self.save_images = save_images
        self.output_dir = create_output_dir() if save_images else None
        self.running = False
        self.blink_wait_time = 0.1
        
        # Create a queue for commands and a separate thread for execution
        self.command_queue = deque()
        self.command_lock = threading.Lock()
        self.command_thread = None
        
        # Keep executor just for saving images
        self.image_executor = ThreadPoolExecutor(max_workers=1)
        
        self.precomputed_colors = precompute_color_distances(
            self.light_manager.light_config["color_mapping"])
        self.last_color = None
        self.last_color_name = None
        self.command_in_progress = False

    def beautify_command_executor(self, color_name):
        if color_name == "black":
            if self.light_manager.power_status.value == "off":
                return []
            else:
                return ["blink_mode", f"wait_{self.blink_wait_time}", "off"]
        else:
            if self.light_manager.power_status.value == "off":
                return ["on", color_name, "normal_mode"]
            else:
                return ["blink_mode", f"wait_{self.blink_wait_time}", color_name, "normal_mode"]
            
    
    
    def command_worker(self):
        """Worker thread that processes commands sequentially"""
        while self.running:
            # Check if there are commands to process
            with self.command_lock:
                if self.command_queue and not self.command_in_progress:
                    commands = self.command_queue.popleft()
                    self.command_in_progress = True
                else:
                    commands = None
            
            # Execute the commands if we have any
            if commands:
                print(f"Executing commands: {commands}")
                try:
                    self.light_manager.execute_commands(commands)
                finally:
                    # Mark as complete even if there was an exception
                    with self.command_lock:
                        self.command_in_progress = False
            else:
                # No commands to process, sleep briefly to avoid CPU spin
                time.sleep(0.05)
                # Mark as complete even if there was an exception
                with self.command_lock:
                    self.command_in_progress = False
                
    def process_frame(self, img_array):
        """Process a single frame and update lights if needed"""
        color = get_most_prominent_color_optimized(img_array)
        
        # Only process if color has changed significantly to avoid flickering
        if self.last_color is None or euclidean_distance(color, self.last_color) > 20:
            self.last_color = color
            color_name = match_color_from_map_optimized(
                color, 
                self.light_manager.light_config["color_mapping"],
                self.precomputed_colors
            )
            
            # Only update if the color name has changed
            if self.light_manager.power_status.value == "off" or color_name != self.light_manager.previous_color:
                
                commands = self.beautify_command_executor(color_name)
                
                print(f"commands after beautify: {commands}")
                # Add commands to the queue for sequential execution
                with self.command_lock:
                    self.command_queue.append(commands)
                
                # Print the result with timestamp
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                display_text = f"Screen {self.display_id}" if self.display_id is not None else "Primary screen"
                print(f"[{timestamp}] {display_text} - Color: RGB{color} -> {color_name}")
                
                return color_name
        
        return None
    
    def start(self):
        """Start monitoring the screen"""
        self.running = True
        
        # Start the command processing thread
        self.command_thread = threading.Thread(target=self.command_worker)
        self.command_thread.daemon = True
        self.command_thread.start()
        
        start_time = time.time()
        
        try:
            while self.running:
                # Check if duration limit reached
                if self.duration and time.time() - start_time > self.duration:
                    print(f"Duration limit of {self.duration} seconds reached. Exiting.")
                    break
                
                loop_start = time.time()
                
                # Capture screen
                pil_img, img_array = capture_screen_optimized(self.display_id)
                
                # Process the frame
                color_name = self.process_frame(img_array)
                
                # Save the image if requested and color changed
                if self.save_images and color_name is not None:
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                    screen_id = self.display_id if self.display_id is not None else "primary"
                    filename = f"{self.output_dir}/screen_{screen_id}_{timestamp_str}.png"
                    
                    # Save in a separate thread to avoid blocking
                    self.image_executor.submit(pil_img.save, filename)
                    print(f"    Saving image to: {filename}")
                
                # Calculate how long to sleep to maintain desired interval
                processing_time = time.time() - loop_start
                sleep_time = max(0, self.interval - processing_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.running = False
            # Wait for command thread to finish
            if self.command_thread and self.command_thread.is_alive():
                self.command_thread.join(timeout=1.0)
            self.image_executor.shutdown()
    
    def stop(self):
        """Stop the monitoring"""
        self.running = False

def monitor_screen(interval, light_manager, display_id=None, duration=None, save_images=False):
    """
    Legacy function that creates and starts a ScreenMonitor instance
    """
    monitor = ScreenMonitor(
        light_manager=light_manager,
        display_id=display_id,
        interval=interval,
        duration=duration,
        save_images=save_images
    )
    monitor.start()