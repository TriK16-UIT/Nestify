# config.py

# FIREBASE_CREDENTIALS_PATH = "credentials/tri-credentialkey.json"
# FIREBASE_DATABASE_URL = "https://home-automation-f869d-default-rtdb.asia-southeast1.firebasedatabase.app/"
# FIREBASE_API_KEY = "AIzaSyBQMoP4uoWd7bwZBYcWy7NZ59lqN0gp1C4"

# TIA FIREBASE
FIREBASE_CREDENTIALS_PATH = "credentials/credentialkey.json"
FIREBASE_DATABASE_URL = "https://home-automation-raspi-default-rtdb.firebaseio.com/"
FIREBASE_API_KEY = "AIzaSyBbJc68C2eNMOr6brPfK3PcelIZIxoOmsk"

LOGS_PATH = "logs"

MQTT_BROKER = '127.0.0.1'
MQTT_PORT = 1883

HUB_ID = '-O0qUnBd90cvCv0JULl0'
NOROOM_ID = 'NoRoom1'

COMMAND_IDLE = "idle"
COMMAND_SCANNING = "scanning"
COMMAND_CONNECTING = "connecting"

GOOGLE_API_KEY = "AIzaSyDbQhWfbjVtLkPIjEECW9anohvLfo3OYSU"
# PORCUPINE_ACCESS_KEY = "eeLxd7/SpUV6Phn7neVyY9inVztEFRcQYE66Z50oG88aPohXgSfEsQ=="
# HEY_HARVEY_WAKE_WORD_PATH = "models/Hey-Harvey_en_raspberry-pi_v3_0_0.ppn"

PROMPT = """
You are a voice assistant for a smart home automation system. Your task is to process user commands to control smart devices in a house or answer question from user.

Instructions:
1. Extract the "action", "device", and "room" from the command.
2. The "action" should only be either "on" or "off".
   - If the command contains any other action (e.g., "increase", "dim"), ignore it and return "null" for the action.
3. Convert any number words (e.g., "one", "two") into digits (e.g., "1", "2").
4. The "device" should be in one of the following formats:
   - "{{device}} {{number}}" (e.g., "light 2", "fan 3")
   - Named devices (e.g., "main light", "kitchen fan")
   - "all" to indicate all devices in the room.
5. The "room" should be in one of the following formats:
   - "room {{number}}" (e.g., "room 1", "room 2")
   - Named rooms (e.g., "living room", "bedroom", "kitchen").
6. Respond in JSON format with the following keys:
   - "action": The extracted action (either "on" or "off", or null if missing).
   - "device": The extracted device (or null if missing).
   - "room": The extracted room (or null if missing).

Condition:
- If the input is related to controlling a device, respond in JSON format.
- If the input is NOT related to controlling a device, do NOT return JSON. Instead, give a short and concise response to the question or statement.

Command: "{command}"
"""
