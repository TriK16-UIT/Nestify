import speech_recognition as sr 
from gtts import gTTS 
from logging_setup import logger
import google.generativeai as genai
import subprocess
from logging_setup import logger
from fuzzywuzzy import process
from utils import convert_command

class VoiceAssistant:
    def __init__(self, google_api_key, device_manager, room_manager):
        self.recognizer = sr.Recognizer()
        self.device_manager = device_manager
        self.room_manager = room_manager
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

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
        action = None
        if "turn on" in command:
            action = "on"
        elif "turn off" in command:
            action = "off"

        if action:
            if "all device" in command:
                room_name = self.extract_room_name(command)
                if room_name:
                    devices = self.room_manager.get_devices_in_room(room_name)
                    for device_name in devices:
                        self.device_manager.control_device(action, device_name)
                else:
                    logger.info("Room not recognized in command.")
                    self.speak("I didn't recognize the room name.")
            else:
                device_name = self.extract_device_name(command)
                if device_name:
                    self.device_manager.control_device(action, device_name)
                    self.speak(f"Turning {action} {device_name.upper()}")
                else:
                    logger.info(f"Device not recognized in command: {command}")
                    self.speak("I didn't recognize the device name.")
        else:
            logger.info("Routing to Gemini Pro API")
            self.route_to_gemini(command)

    def extract_room_name(self, command):
        print(command)
        command = convert_command(command)
        print(command)
        rooms = [room_name for _, room_name in self.room_manager.get_list_of_rooms()]
        if not rooms:
            return None
        best_match, score = process.extractOne(command, rooms)
        print(score)
        if score < 90:
            return None
        print(best_match)
        return best_match

    def extract_device_name(self, command):
        print(command)
        command = convert_command(command)
        print(command)
        devices = [device_name for _, device_name in self.device_manager.get_list_of_devices()]
        if not devices:
            return None
        best_match, score = process.extractOne(command, devices)
        print(score)
        if score < 90:
            return None
        print(best_match)
        return best_match

    def route_to_gemini(self, query):
        try:
            response = self.model.generate_content(query + "Make short answer")
            logger.info(f"Gemini Pro API response: {response.text}")
            self.speak(response.text)
        except Exception as e:
            logger.error(f"Error communicating with Gemini Pro API: {e}")
            self.speak("There was an error processsing your request.")

