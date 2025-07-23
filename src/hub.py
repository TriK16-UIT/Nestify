import asyncio
import threading
import sounddevice
from firebase_handler import FirebaseHandler
from bluetooth_handler import BluetoothHandler
from storage_handler import StorageHandler
from firestore_handler import FirestoreHandler
from logging_handler import LoggingHandler
from config import HUB_ID, GOOGLE_API_KEY
from device_manager import DeviceManager
from mqtt_handler import MQTTHandler
from scenario_scheduler import run_scheduler
from room_manager import RoomManager
from voice_assistant import VoiceAssistant  # Import your VoiceAssistant class

async def handle_scanning(firebase_handler, bluetooth_handler):
    scanned_devices = await bluetooth_handler.scan_for_devices_async()
    await firebase_handler.set_data(f'Hub/{HUB_ID}/scanned_devices', scanned_devices)
    await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "done_scanning")

async def handle_connecting(firebase_handler, bluetooth_handler, device_manager, logging_handler, ssid, password, addr, name):
    is_connected, response = await bluetooth_handler.connect_device_async(ssid, password, addr, name)
    if is_connected:
        await logging_handler.add_log("INFO", "Connected to device")
        device_type = None
        chosen_device_info_response = await firebase_handler.get_data(f'Hub/{HUB_ID}/chosen_device')
        chosen_device_info = chosen_device_info_response.val()
        if "LIGHT" in chosen_device_info['name'] or "FAN" in chosen_device_info['name']:
            device_type = 'toggle'
        elif "SENSOR" in chosen_device_info['name']:
            device_type = 'sensor'
        elif "MOTION" in chosen_device_info['name']:
            device_type = 'motion'
        await device_manager.add_device_handler(chosen_device_info['name'], device_type)
        await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "done_connecting")
    else:
        await logging_handler.add_log("DANGER", f"Failed to connect to device. {response})")
        await firebase_handler.set_data(f'Hub/{HUB_ID}/command', "done_connecting")

async def listen_for_commands(firebase_handler, bluetooth_handler, logging_handler, device_manager, room_manager):
    await device_manager.load_message_handlers_from_firebase()
    await room_manager.load_rooms_from_firebase()

    room_manager.setup_room_stream()
    device_manager.setup_device_stream()

    asyncio.create_task(run_scheduler(device_manager, firebase_handler))

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
                    asyncio.create_task(handle_connecting(firebase_handler, bluetooth_handler, device_manager, logging_handler, ssid, password, addr, name))

        await asyncio.sleep(1)

async def main():
    firebase_handler = FirebaseHandler()
    storage_handler = StorageHandler()
    bluetooth_handler = BluetoothHandler()
    firestore_handler = FirestoreHandler()
    logging_handler = LoggingHandler(firestore_handler)
    mqtt_handler = MQTTHandler()
    device_manager = DeviceManager(mqtt_handler, storage_handler, firebase_handler, logging_handler)
    room_manager = RoomManager(firebase_handler)

    voice_assistant = VoiceAssistant(GOOGLE_API_KEY, device_manager, room_manager)
    

    try:
        voice_assistant.start_voice_assistant()
        
        await listen_for_commands(firebase_handler, bluetooth_handler, logging_handler, device_manager, room_manager)
    except KeyboardInterrupt:
        voice_assistant.stop_voice_assistant()

if __name__ == "__main__":
    asyncio.run(main())