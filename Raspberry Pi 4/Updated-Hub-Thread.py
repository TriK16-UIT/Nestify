import time
import threading
import schedule
import sounddevice
import struct
import pyaudio
import pvporcupine
from config import HUB_ID, COMMAND_CONNECTING, COMMAND_IDLE, COMMAND_SCANNING, GOOGLE_API_KEY
from firebase_handler import FirebaseHandler
from mqtt_handler import MQTTHandler
from bluetooth_handler import BluetoothHandler
from device_manager import DeviceManager
from logging_setup import logger
from voice_assistant import VoiceAssistant
from scenario_scheduler import schedule_scenario_checks

def handle_commands(firebase_handler, bluetooth_handler, device_manager):
    command_ref = firebase_handler.get_reference(f'Hub/{HUB_ID}/command')

    while True:
        command = command_ref.get()
        if command == COMMAND_SCANNING:
            scanned_devices_ref = firebase_handler.get_reference(f'Hub/{HUB_ID}/scanned_devices')
            scanned_devices_ref.set(bluetooth_handler.scan_for_devices())
            command_ref.set(COMMAND_IDLE)
        elif command == COMMAND_CONNECTING:
            ssid = firebase_handler.get_reference(f'Hub/{HUB_ID}/ssid').get()
            password = firebase_handler.get_reference(f'Hub/{HUB_ID}/password').get()
            chosen_device_ref = firebase_handler.get_reference(f'Hub/{HUB_ID}/chosen_device')
            chosen_device_info = chosen_device_ref.get()
            isConnected = bluetooth_handler.connect_device(ssid, password, chosen_device_info['addr'], chosen_device_info['name'])
            if isConnected:
                device_type = None
                if "LIGHT" in chosen_device_info['name'] or "FAN" in chosen_device_info['name']:
                    device_type = 'toggle'
                elif "SENSOR" in chosen_device_info['name']:
                    device_type = 'sensor'
                device_manager.add_device_handler(chosen_device_info['name'], device_type)
            command_ref.set(COMMAND_IDLE)
        time.sleep(1)  # To prevent excessive loop spinning

def listen_for_wake_words(voice_assistant):
    while True:
        if voice_assistant.listen_for_wake_word():
            voice_command = voice_assistant.listen()
            if voice_command:
                voice_assistant.execute_command(voice_command)
        time.sleep(0.5)  # Adjust as needed for responsiveness

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Run pending tasks every second

def listen_for_commands():
    firebase_handler = FirebaseHandler()
    mqtt_handler = MQTTHandler()
    bluetooth_handler = BluetoothHandler()
    device_manager = DeviceManager(mqtt_handler, firebase_handler)
    voice_assistant = VoiceAssistant(GOOGLE_API_KEY, device_manager, firebase_handler)

    logger.info("Starting command listener...")

    # Load initial data
    device_manager.load_message_handlers_from_firebase()
    device_ref = firebase_handler.get_reference('Device')
    device_ref.listen(device_manager.handle_device_change)

    # Schedule the scenario checker
    schedule_scenario_checks(device_manager, firebase_handler, HUB_ID)

    # Create and start threads
    command_thread = threading.Thread(target=handle_commands, args=(firebase_handler, bluetooth_handler, device_manager))
    voice_thread = threading.Thread(target=listen_for_wake_words, args=(voice_assistant,))
    scheduler_thread = threading.Thread(target=run_scheduler)

    command_thread.start()
    voice_thread.start()
    scheduler_thread.start()

    # Join threads to keep the main program running
    command_thread.join()
    voice_thread.join()
    scheduler_thread.join()

if __name__ == "__main__":
    listen_for_commands()
