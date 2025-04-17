import os
from dotenv import dotenv_values


config = dotenv_values(".env")

__get_env = lambda key: config.get(key, os.environ.get(key))

BROADLINK_API_URL = __get_env("BROADLINK_API_URL")
SEND_PACKET_ENDPOINT = BROADLINK_API_URL.rstrip("/") + "/send-packet"
