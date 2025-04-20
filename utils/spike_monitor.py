import sounddevice as sd
import numpy as np
import threading

from utils.helpers import print_highlighted

class SpikeMonitor:
    def __init__(self, spike_callback, sample_rate=44100, chunk_size=1024, spike_threshold=2, channels=1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.spike_threshold = spike_threshold
        self.spike_lock = threading.Lock()
        self.spike_callback = spike_callback

        
    def start(self):
        print_highlighted("Listening for spikes")
        with sd.InputStream(callback=self.__audio_callback,
                        channels=self.channels,
                        samplerate=self.sample_rate,
                        blocksize=self.chunk_size):
            while True:
                sd.sleep(1000) 

    def __audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Status: {status}")
        volume_norm = np.linalg.norm(indata)

        if volume_norm > self.spike_threshold:
            if not self.spike_lock.locked():  # Only proceed if not already handling a spike
                threading.Thread(target=self.__handle_spike, daemon=True).start()


    def __handle_spike(self):
        with self.spike_lock:
            print("Spike detected! handling")
            self.spike_callback()
            print("Spike handling complete.")

