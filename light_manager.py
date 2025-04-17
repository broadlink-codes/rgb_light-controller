from typing import Literal, Optional
import json
import requests

from base import SEND_PACKET_ENDPOINT
from config.types import TLightConfig, PowerStatus
from config.color_mapping import light_color_mapping
from utils.helpers import print_highlighted

except_color_commands = [
    "on",
    "off",
    "increase_brightness",
    "decrease_brightness"
]
class LightManager:
    def __init__(self, device_name: str, initial_brightness: int, starting_color="red"):
        self.light_config: Optional[TLightConfig] = None
        self.previous_color: Optional[str] = None
        self.power_status: PowerStatus = PowerStatus.OFF
        self.brightness_level: Optional[int] = None

        ## important sequence of execution
        self.__create_light_config(device_name)
        self.__initialize_light(starting_color, initial_brightness)

    def __create_light_config(self, device_name: str):
        light_config = None
        with open("config/remote_code.json", "r") as file:
            remote_code = json.load(file)

        for device in remote_code:
            if device["device_name"] == device_name:
                light_config = device

        try:
            light_config["color_mapping"] = light_color_mapping[device_name]
        except:
            light_config = None

        if not light_config:
            raise Exception(f"device with name {device_name} not found")

        self.light_config = light_config

    def __initialize_light(self, starting_color, initial_brightness):
        """
        Turn on the light, set it to the starting_color,
        increase brightness to the initial_brightness,
        then turn off the light.
        """
        # turn on -> turn to starting_color -> increase brightness to 2Xmax_brightness -> turn off
        print_highlighted("Initializing light please wait...")
        increase_brightness_commands = ["decrease_brightness"] * self.light_config[
            "max_brightness"
        ] + ["increase_brightness"] * initial_brightness
        commands = ["on", starting_color] + increase_brightness_commands + ["off"]
        self.execute_commands(commands)

        self.previous_color = starting_color
        self.brightness_level = initial_brightness

        print_highlighted("Light initialized successfully...")

    def execute_commands(self, commands: list[str]):

        ## check all commands exist
        for command in commands:
            if command not in self.light_config["command_mapping"]:
                raise Exception(f"Command {command} not supported")

        for command_to_exec in commands:

            if (
                command_to_exec == self.previous_color
                and self.power_status == PowerStatus.ON
            ):
                continue

            pulse_packet = self.light_config["command_mapping"][command_to_exec]
            payload = json.dumps({"packet": pulse_packet})
            headers = {"Content-Type": "application/json"}

            response = requests.request(
                "POST", SEND_PACKET_ENDPOINT, headers=headers, data=payload
            )

            if response.status_code == 200:
                if command_to_exec == PowerStatus.ON.value or command_to_exec == PowerStatus.OFF.value:
                    self.power_status = PowerStatus(command_to_exec)
                elif command_to_exec in except_color_commands:
                    pass
                else:
                    self.previous_color = command_to_exec

                print("Command executed successfully.")
            else:
                print(f"Failed to execute command. Status code: {response.status_code}")
                print(response.json())
