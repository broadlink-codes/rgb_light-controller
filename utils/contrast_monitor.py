import numpy as np
import threading
import cv2
import time
import mss
from utils.helpers import print_highlighted

class ContrastMonitor:
    def __init__(self, change_callback, threshold=150, min_area_percentage=0.05, cooldown_frames=15, 
                 monitor_number=1, fps=30, region=None):
        """
        Monitor for detecting sudden contrast or brightness changes on screen.
        
        Args:
            change_callback: Function to call when a significant change is detected
            threshold: Threshold for pixel difference to consider as significant change (0-255)
            min_area_percentage: Minimum percentage of the frame that must change to trigger callback
            cooldown_frames: Number of frames to wait before detecting another event
            monitor_number: Which monitor to capture (1 = primary monitor)
            fps: Target frames per second for capturing
            region: (x, y, width, height) for capturing a specific region, None for full screen
        """
        self.change_callback = change_callback
        self.threshold = threshold
        self.min_area_percentage = min_area_percentage
        self.cooldown_frames = cooldown_frames
        self.monitor_number = monitor_number
        self.region = region
        self.fps = fps
        self.frame_time = 1.0 / fps
        
        self.cooldown_counter = 0
        self.previous_frame = None
        self.change_lock = threading.Lock()
        self.running = False
    
    def start(self):
        """Start monitoring the screen for contrast changes."""
        self.running = True
        print_highlighted("Monitoring screen for contrast/brightness changes")
        
        # Initialize screen capture
        with mss.mss() as sct:
            # Get monitor information
            if self.region:
                monitor = {"left": self.region[0], "top": self.region[1], 
                           "width": self.region[2], "height": self.region[3]}
            else:
                monitor = sct.monitors[self.monitor_number]
            
            try:
                while self.running:
                    loop_start = time.time()
                    
                    # Capture screen
                    screenshot = sct.grab(monitor)
                    
                    # Convert to numpy array and then to grayscale
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)  # mss captures BGRA
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)  # Downscale for performance
                    gray = cv2.GaussianBlur(gray, (5, 5), 0)  # Reduce noise
                    
                    if self.previous_frame is not None:
                        self._process_frame(gray)
                        
                    self.previous_frame = gray
                    
                    # Decrement cooldown if active
                    if self.cooldown_counter > 0:
                        self.cooldown_counter -= 1
                    
                    # Control frame rate
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.frame_time - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                print("Monitoring stopped by user")
            finally:
                self.running = False
    
    def stop(self):
        """Stop the monitoring process"""
        self.running = False
    
    def _process_frame(self, current_frame):
        """
        Process the current frame and detect significant changes.
        
        Args:
            current_frame: Grayscale frame to analyze
        """
        # Skip processing if in cooldown period
        if self.cooldown_counter > 0:
            return
            
        # Calculate absolute difference between current and previous frame
        frame_diff = cv2.absdiff(current_frame, self.previous_frame)
        
        # Count pixels that exceed the threshold
        significant_changes = np.sum(frame_diff > self.threshold)
        total_pixels = current_frame.size
        change_percentage = significant_changes / total_pixels
        
        # If enough of the frame changed significantly, trigger callback
        if change_percentage >= self.min_area_percentage:
            if not self.change_lock.locked():
                threading.Thread(target=self._handle_change, 
                                args=(change_percentage, frame_diff.mean()),
                                daemon=True).start()
    
    def _handle_change(self, change_percentage, mean_diff):
        """
        Handle a detected contrast/brightness change.
        
        Args:
            change_percentage: Percentage of frame that changed
            mean_diff: Mean intensity of the difference
        """
        with self.change_lock:
            print(f"Sudden change detected! {change_percentage:.2%} of frame changed (avg diff: {mean_diff:.1f})")
            self.change_callback()
            print("Change handling complete.")
            # Set cooldown to prevent multiple triggers for the same event
            self.cooldown_counter = self.cooldown_frames


# Example usage
if __name__ == "__main__":
    def flash_detected():
        print("Flash detected on screen!")
        # Your reaction code here
    
    # Create and start the monitor (monitoring primary screen)
    monitor = ScreenContrastMonitor(
        change_callback=flash_detected,
        threshold=40,
        min_area_percentage=0.1,
        fps=20  # Lower for better performance
    )
    
    # To monitor just a portion of the screen (e.g., game window)
    # monitor = ScreenContrastMonitor(
    #     change_callback=flash_detected,
    #     region=(100, 100, 800, 600)  # x, y, width, height
    # )
    
    try:
        # Start monitoring in the current thread
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()