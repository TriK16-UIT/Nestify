# config.py

# FIREBASE_CREDENTIALS_PATH = "credentials/tri-credentialkey.json"
# FIREBASE_DATABASE_URL = "https://home-automation-f869d-default-rtdb.asia-southeast1.firebasedatabase.app/"
# FIREBASE_API_KEY = "AIzaSyBQMoP4uoWd7bwZBYcWy7NZ59lqN0gp1C4"

# TIA FIREBASE
FIREBASE_CREDENTIALS_PATH = "credentials/credentialkey.json"
FIREBASE_DATABASE_URL = "https://home-automation-raspi-default-rtdb.firebaseio.com/"
FIREBASE_API_KEY = ""

LOGS_PATH = "logs"

MQTT_BROKER = '127.0.0.1'
MQTT_PORT = 1883

# HUB_ID = 'Hub1'
# TIA HUB_ID
HUB_ID = "-12qUnBABCcvCv0JULl0"
NOROOM_ID = 'NoRoom1'

COMMAND_IDLE = "idle"
COMMAND_SCANNING = "scanning"
COMMAND_CONNECTING = "connecting"

GOOGLE_API_KEY = ""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "STRING",
            "enum": ["device_control", "list_rooms", "general_question"],
            "description": "The type of user request"
        },
        "action": {
            "type": "STRING",
            "enum": ["on", "off", "list"],
            "description": "Device action or list command",
            "nullable": True
        },
        "device": {
            "type": "STRING",
            "description": "Target device (e.g., 'light 1', 'fan 2', 'main light')",
            "nullable": True
        },
        "room": {
            "type": "STRING",
            "description": "Target room (e.g., 'room 1', 'living room', 'kitchen')",
            "nullable": True
        },
        "response": {
            "type": "STRING",
            "description": "Direct response for general questions or confirmations",
            "nullable": True
        }
    },
    "required": ["intent"]
}

## Improved Prompt
PROMPT = """
You are a voice assistant for a smart home automation system. Process user commands and respond with structured JSON output.

CAPABILITIES:
1. Device Control: Turn devices on/off in specific rooms
2. Room Listing: List all available rooms
3. General Questions: Answer non-smart-home related questions

RESPONSE FORMAT:
Always respond with valid JSON containing these fields:
- "intent": Must be one of: "device_control", "list_rooms", "general_question"
- "action": "on", "off", "list", or null
- "device": Device name/identifier or null
- "room": Room name/identifier or null  
- "response": Direct text response or null

PROCESSING RULES:

Device Control:
- Extract action: only "on" or "off" (ignore other actions like "dim", "brighten")
- Convert number words to digits ("one" → "1", "two" → "2")
- Device formats: "{{device}} {{number}}" (e.g., "light 1") or named devices (e.g., "main light")
- Room formats: "room {{number}}" (e.g., "room 1") or named rooms (e.g., "living room", "kitchen")
- If room not specified, set room to null (will be handled by backend)
- No "all devices" control - each device must be specified individually

Room Listing:
- When user asks for rooms/room list, set intent to "list_rooms" and action to "list"

General Questions:
- For non-smart-home questions, set intent to "general_question"
- Provide concise answer in "response" field
- Set action, device, room to null

EXAMPLES:

User: "Turn on light 1 in living room"
Response: {{"intent": "device_control", "action": "on", "device": "light 1", "room": "living room", "response": null}}

User: "Turn off fan 2 in room 3"
Response: {{"intent": "device_control", "action": "off", "device": "fan 2", "room": "room 3", "response": null}}

User: "Turn on the main light"
Response: {{"intent": "device_control", "action": "on", "device": "main light", "room": null, "response": null}}

User: "What rooms are available?"
Response: {{"intent": "list_rooms", "action": "list", "device": null, "room": null, "response": null}}

User: "What is 1 + 1?"
Response: {{"intent": "general_question", "action": null, "device": null, "room": null, "response": "1 + 1 equals 2."}}

User: "Turn on the fan"
Response: {{"intent": "device_control", "action": "on", "device": "fan", "room": null, "response": null}}

Command: "{command}"
"""
