import asyncio
import threading
import sounddevice
from firebase_handler import FirebaseHandler
from bluetooth_handler import BluetoothHandler
from config import HUB_ID, GOOGLE_API_KEY
from device_manager import DeviceManager
from mqtt_handler import MQTTHandler
from scenario_scheduler import run_scheduler
from room_manager import RoomManager
from voice_assistant import VoiceAssistant  # Import your VoiceAssistant class

async def handle_scanning(firebase_handler, bluetooth_handler):
    scanned_devices = await bluetooth_handler.scan_for_devices_async()
    print(f"Scanned devices: {scanned_devices}")
    await firebase_handler.set_data(f'Hub/{HUB_ID}/scanned_devices', scanned_devices)
    await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "done_scanning")

async def handle_connecting(firebase_handler, bluetooth_handler, device_manager, ssid, password, addr, name):
    is_connected = await bluetooth_handler.connect_device_async(ssid, password, addr, name)
    if is_connected:
        device_type = None
        chosen_device_info_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/chosen_device')
        chosen_device_info = chosen_device_info_response.val()
        if "LIGHT" in chosen_device_info['name'] or "FAN" in chosen_device_info['name']:
            device_type = 'toggle'
        elif "SENSOR" in chosen_device_info['name']:
            device_type = 'sensor'
        await device_manager.add_device_handler(chosen_device_info['name'], device_type)
        await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "done_connecting")

async def listen_for_commands(firebase_handler, bluetooth_handler, device_manager, room_manager):
    await device_manager.load_message_handlers_from_firebase()
    await room_manager.load_rooms_from_firebase()

    room_manager.setup_room_stream()
    device_manager.setup_device_stream()

    asyncio.create_task(run_scheduler(device_manager, firebase_handler, HUB_ID))

    while True:
        command_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/command')
        command = command_response.val()

        if command == "scanning":
            await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "idle")
            asyncio.create_task(handle_scanning(firebase_handler, bluetooth_handler))

        elif command == "connecting":
            await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "idle")
            ssid_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/ssid')
            password_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/password')
            chosen_device_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/chosen_device')

            ssid = ssid_response.val()
            password = password_response.val()
            chosen_device = chosen_device_response.val()

            if ssid and password and chosen_device:
                addr = chosen_device.get('addr')
                name = chosen_device.get('name')
                if addr and name:
                    asyncio.create_task(handle_connecting(firebase_handler, bluetooth_handler, device_manager, ssid, password, addr, name))

        await asyncio.sleep(1)

async def main():
    firebase_handler = FirebaseHandler()
    bluetooth_handler = BluetoothHandler()
    mqtt_handler = MQTTHandler()
    device_manager = DeviceManager(mqtt_handler, firebase_handler)
    room_manager = RoomManager(firebase_handler)

    # Get the asyncio event loop
    loop = asyncio.get_event_loop()

    # Start the voice assistant in a separate thread
    voice_assistant = VoiceAssistant(GOOGLE_API_KEY, device_manager, room_manager, loop)
    voice_thread = threading.Thread(target=voice_assistant.run, daemon=True)
    voice_thread.start()

    # Start listening for commands
    await listen_for_commands(firebase_handler, bluetooth_handler, device_manager, room_manager)

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())