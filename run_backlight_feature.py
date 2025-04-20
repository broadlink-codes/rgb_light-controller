import json

from backlight import Backlight
from utils.light_manager import LightManager
from base import CONFIG_FILE_PATH

if __name__ == '__main__':
    with open(CONFIG_FILE_PATH, "r") as file:
      config = json.load(file)

    monitor_back_light_manager = LightManager(
        device_name="monitor_backlight",
        initial_brightness=9
    )

    backlight_obj = Backlight(
        light_manager=monitor_back_light_manager,
        **config["BACKLIGHT_CONFIG"]
    )

    backlight_obj.start()
