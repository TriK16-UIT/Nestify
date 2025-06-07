import speech_recognition as sr 
from gtts import gTTS 
from google import genai
import subprocess
import json
import asyncio
import threading
import time
from config import PROMPT, RESPONSE_SCHEMA

class VoiceAssistant:
    def __init__(self, google_api_key, device_manager, room_manager):
        self.recognizer = sr.Recognizer()
        self.device_manager = device_manager
        self.room_manager = room_manager
        self.loop = asyncio.get_running_loop()
        self.running = False
        self.thread = None
        self.client = genai.Client(api_key=google_api_key)  

    def start_voice_assistant(self):
        """Start the voice assistant in a separate thread"""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("Voice assistant started in background thread")
            return True
        return False

    def stop_voice_assistant(self):
        """Stop the voice assistant thread"""
        if self.thread and self.thread.is_alive():
            self.running = False
            self.thread.join(timeout=2.0)
            print("Voice assistant stopped")
            return True
        return False

    def run(self):
        """Main loop for the voice assistant running in a separate thread"""
        while self.running:
            if self.listen_for_wake_word():
                command = self.listen()
                if command:
                    self.execute_command(command)
            # Small sleep to prevent CPU hogging
            time.sleep(0.1)

    def speak(self, text):
        tts = gTTS(text=text, lang='en')
        tts.save("response.wav")
        subprocess.run(
            ["cvlc", "--play-and-exit", "--no-repeat", "response.wav"],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )

    def listen_for_wake_word(self):
        with sr.Microphone(device_index=1) as source:
            print("Listening for wake word...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)

            try:
                command = self.recognizer.recognize_google(audio).lower()
                print(f"Recognized speech: {command}")
                if "hey harvey" in command:
                    print("Wake word 'Hey Harvey' detected")
                    self.speak("Hi, what can I help you?")
                    return True
            except sr.UnknownValueError:
                # print("Could not understand the audio")
                return False

    def listen(self):
        with sr.Microphone(device_index=1) as source:
            print("Listening for a command...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)

            try:
                command = self.recognizer.recognize_google(audio).lower()
                print(f"Recognized command: {command}")
                return command
            except sr.UnknownValueError:
                print("Could not understand the audio")
                self.speak("Sorry, I could not understand the command")
                return None

    def execute_command(self, command):
        if not command:
            return

        try:
            prompt = PROMPT.format(command=command)

            # Generate content with structured JSON output using the provided schema
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": RESPONSE_SCHEMA,
                },
            )

            # Extract the JSON data directly from the response
            data = json.loads(response.text)
            print(f"Gemini response: {data}")

            # Extract the fields from structured response
            intent = data.get("intent", "")
            action = data.get("action", "")
            device = data.get("device", "")
            room = data.get("room", "")
            response_text = data.get("response", "")

            # Handle different intent types
            if intent == "device_control":
                # Convert action to a JSON format with status key
                action_data = {"status": action.upper()} if action else {}

                if action and device:
                    # Set default room to "No Room" if not specified
                    if not room:
                        room = "No Room"
                    
                    # Check if the room exists
                    if room.lower() in [room_name.lower() for _, room_name in self.room_manager.get_list_of_rooms()]:
                        # Get devices in the room to validate device exists in this room
                        future = asyncio.run_coroutine_threadsafe(
                            self.room_manager.get_devices_in_room(room),
                            self.loop
                        )
                        devices_in_room = future.result()
                        device_names_in_room = [device_name for device_name, _ in devices_in_room]
                        
                        # Check if the device exists in this room
                        if device.lower() in [name.lower() for name in device_names_in_room]:
                            # Send the command to the main event loop
                            future = asyncio.run_coroutine_threadsafe(
                                self.device_manager.control_device(action_data, device),
                                self.loop
                            )
                            future.result()
                            self.speak(f"Turning {action} {device.upper()} in {room}")
                        else:
                            # Device not found in the specified room, list available devices
                            print(f"Device '{device}' not found in room '{room}'")
                            if devices_in_room:
                                devices_list = ", ".join([name for name, _ in devices_in_room])
                                self.speak(f"I couldn't find {device} in {room}. Available devices in {room} are: {devices_list}")
                            else:
                                self.speak(f"I couldn't find {device} in {room}. There are no devices in this room.")
                    else:
                        print("Room not recognized.")
                        self.speak(f"I didn't recognize the room '{room}'.")
                else:
                    self.speak("The control command is not in correct format")
            
            elif intent == "list_rooms":
                # Handle room listing
                room_list = [room_name for _, room_name in self.room_manager.get_list_of_rooms()]
                if room_list:
                    room_text = ", ".join(room_list)
                    self.speak(f"Available rooms are: {room_text}")
                else:
                    self.speak("No rooms are currently configured.")
            
            elif intent == "general_question":
                # Handle general questions by speaking the response
                if response_text:
                    self.speak(response_text)
                else:
                    self.speak("I'm not sure how to answer that question.")
            
            else:
                self.speak("I didn't understand what you wanted me to do.")

        except Exception as e:
            print(f"Error processing command with Gemini: {e}")
            self.speak("There was an error processing your request.")
