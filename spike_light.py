###When there is a spike in sound detect the major color on screen and turn on given light_manager objects with the color###
from typing import List
import json
import time

import threading

from base import CONFIG_FILE_PATH
from utils.light_manager import LightManager
from utils.spike_monitor import SpikeMonitor
from utils.screen_monitor import ScreenMonitor
from config.types import PowerStatus

class SpikeLight:

  def __init__(self, light_managers: List[LightManager]):
    with open(CONFIG_FILE_PATH, "r") as file:
      self.config = json.load(file)

    ## NOTE: pass light_managers in order you want them to light up
    self.light_managers = light_managers
    self.spike_monitor = SpikeMonitor(
      spike_callback=self.__spike_callback,
      **self.config["SPIKE_MONITOR_CONFIG"]
    )
    self.screen_monitor = ScreenMonitor(
      light_managers=self.light_managers,
      **self.config["SCREEN_MONITOR_CONFIG"]
    )

  def __spike_callback(self):
    color_name_per_device = self.screen_monitor.get_color_name()
    #Turn on lights
    for light_manager in self.light_managers:
      color = color_name_per_device.get(light_manager.device_name)
      color = "red" if color == "black" else color
      commands = []
      if light_manager.power_status == PowerStatus.OFF:
        commands.append("on")
      print("Changing color to ", color)
      commands.append(color)
      light_manager.execute_commands(commands)

    #Turn off lights
    for light_manager in self.light_managers:
      light_manager.execute_commands(["off"])

  def start(self):
    threading.Thread(target=self.spike_monitor.start, daemon=True).start()
    while True:
      time.sleep(1000)


