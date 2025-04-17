import sounddevice as sd
import numpy as np
import threading

from test import lights_on

# ================== CONFIG ==================
SAMPLE_RATE = 44100        # Samples per second
CHUNK_SIZE = 1024          # Buffer size for each read
SPIKE_THRESHOLD = 2        # Adjust based on your environment
# ============================================

spike_lock = threading.Lock()

def audio_callback(indata, frames, time, status):
    if status:
        print(f"Status: {status}")
    volume_norm = np.linalg.norm(indata)

    if volume_norm > SPIKE_THRESHOLD:
        if not spike_lock.locked():  # Only proceed if not already handling a spike
            threading.Thread(target=handle_spike, daemon=True).start()

def handle_spike():
    with spike_lock:
        print("Spike detected! Triggering lights...")
        lights_on()  # Blocking call
        print("Spike handling complete.")

def main():
    print("Listening for spikes... Press Ctrl+C to stop.")
    with sd.InputStream(callback=audio_callback,
                        channels=1,
                        samplerate=SAMPLE_RATE,
                        blocksize=CHUNK_SIZE):
        while True:
            sd.sleep(1000)  # Keep main thread alive

if __name__ == "__main__":
    main()
