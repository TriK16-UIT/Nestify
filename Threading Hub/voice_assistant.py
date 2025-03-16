import speech_recognition as sr 
from gtts import gTTS 
from logging_setup import logger
import google.generativeai as genai
import subprocess
import json
import asyncio
from logging_setup import logger
from config import PROMPT

class VoiceAssistant:
    def __init__(self, google_api_key, device_manager, room_manager, loop):
        self.recognizer = sr.Recognizer()
        self.device_manager = device_manager
        self.room_manager = room_manager
        self.loop = loop 
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    # async def run(self):
    #     while True:
    #         if await self.listen_for_wake_word():
    #             command = await self.listen()
    #             if command:
    #                 await self.execute_command(command)
    #         await asyncio.sleep(1)

    def run(self):
        while True:
            if self.listen_for_wake_word():
                command = self.listen()
                if command:
                    self.execute_command(command)

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
            # logger.info("Listening for wake word...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)

            try:
                command = self.recognizer.recognize_google(audio).lower()
                logger.info(f"Recognized speech: {command}")
                if "hey harvey" in command:
                    logger.info("Wake word 'Hey Harvey' detected")
                    self.speak("Hi, what can I help you?")
                    return True
            except sr.UnknownValueError:
                # logger.info("Could not understand the audio")
                return False

    def listen(self):
        with sr.Microphone(device_index=1) as source:
            logger.info("Listening for a command...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)

            try:
                command = self.recognizer.recognize_google(audio).lower()
                logger.info(f"Recognized command: {command}")
                return command
            except sr.UnknownValueError:
                logger.error("Could not understand the audio")
                self.speak("Sorry, I could not understand the command")
                return None

    def execute_command(self, command):
        if not command:
            return

        try:
            prompt = PROMPT.format(command=command)

            response = self.model.generate_content(prompt)

            result = response.text

            result = result.strip().replace("```json", "").replace("```", "").strip()

            logger.info(f"Gemni response: {result}")

            try: 
                print(result)
                data = json.loads(result)
                action = data.get("action", "")
                device = data.get("device", "")
                room = data.get("room", "")

                # Convert action to a JSON format with status key
                action_data = {"status": action.upper()} if action else {}

                if action and device:
                    if device.lower() in [device_name.lower() for _, device_name in self.device_manager.get_list_of_devices()]:
                        future = asyncio.run_coroutine_threadsafe(
                            self.device_manager.control_device(action_data, device),
                            self.loop
                        )
                        future.result()
                        self.speak(f"Turning {action} {device.upper()}")
                    else:
                        logger.info("Device not recognized in command.")
                        self.speak("I didn't recognize the device name.")
                elif action and room:
                    if room.lower() in [room_name.lower() for _, room_name in self.room_manager.get_list_of_rooms()]:
                        if action == "all":
                            future = asyncio.run_coroutine_threadsafe(
                                self.room_manager.get_devices_in_room(room),
                                self.loop
                            )
                            devices = future.result()
                            for device_name, device_type in devices:
                                if device_type == "toggle":
                                    future = asyncio.run_coroutine_threadsafe(
                                        self.device_manager.control_device(action_data, device_name),
                                        self.loop
                                    )
                                    future.result()
                                    self.speak(f"Turning {action} {device_name.upper()}")
                        else:
                            self.speak("At this moment, only support to turn on or off all devices in room but not specific one")
                    else:
                        logger.info("Room not recognized in command.")
                        self.speak("I didn't recognize the room name.")
                else:
                    self.speak("The control command is not in correct format")
            except json.JSONDecodeError:
                self.speak(result)

        except Exception as e:
            logger.error(f"Error processing command with Gemini: {e}")
            self.speak("There was an error processing your request.")

    # def extract_room_name(self, command):
    #     print(command)
    #     command = convert_command(command)
    #     print(command)
    #     rooms = [room_name for _, room_name in self.room_manager.get_list_of_rooms()]
    #     if not rooms:
    #         return None
    #     best_match, score = process.extractOne(command, rooms)
    #     print(score)
    #     if score < 90:
    #         return None
    #     print(best_match)
    #     return best_match

    # def extract_device_name(self, command):
    #     print(command)
    #     command = convert_command(command)
    #     print(command)
    #     devices = [device_name for _, device_name in self.device_manager.get_list_of_devices()]
    #     if not devices:
    #         return None
    #     best_match, score = process.extractOne(command, devices)
    #     print(score)
    #     if score < 90:
    #         return None
    #     print(best_match)
    #     return best_match

    # def route_to_gemini(self, query):
    #     try:
    #         response = self.model.generate_content(query + "Make short answer")
    #         logger.info(f"Gemini Pro API response: {response.text}")
    #         self.speak(response.text)
    #     except Exception as e:
    #         logger.error(f"Error communicating with Gemini Pro API: {e}")
    #         self.speak("There was an error processsing your request.")

