from typing import TypedDict

class TLightConfig(TypedDict):
  device_name: str
  color_mapping: dict[str, tuple[int, int, int]]
  command_mapping: dict[str, str]
  max_brightness: int
  