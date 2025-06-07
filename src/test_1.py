import speech_recognition as sr 
import sounddevice


print("Available audio input devices:")
devices = sr.Microphone.list_microphone_names()
for i, device in enumerate(devices):
    print(f"[{i}]: {device}")