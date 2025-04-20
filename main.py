from spike_light import SpikeLight
from utils.light_manager import LightManager

if __name__ == '__main__':
    bottom_light_manager = LightManager(
        device_name="bottom_light",
        initial_brightness=6
    )
    # monitor_back_light_manager = LightManager(
    #     device_name="monitor_backlight",
    #     initial_brightness=9
    # )

    spike_light = SpikeLight(
        light_managers=[bottom_light_manager]
    )
    spike_light.start()

