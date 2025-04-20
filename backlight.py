from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import time

from utils.light_manager import LightManager
from utils.screen_captures.helper import (
    create_output_dir,
    precompute_color_distances,
    get_most_prominent_color_optimized,
    capture_screen_optimized,
    euclidean_distance,
    match_color_from_map_optimized
)

class Backlight:
    def __init__(self, light_manager: LightManager, display_id=None, interval=0.1, duration=None, save_images=False):
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

    def get_commands(self, color_name):
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
                
                commands = self.get_commands(color_name)
                
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