import speech_recognition as sr
import sounddevice
r=sr.Recognizer()
with sr.Microphone(device_index=1) as source:  # Replace with your correct index
    print("Say something!")
    audio = r.listen(source)

with open("test_audio.wav", "wb") as f:
    f.write(audio.get_wav_data())

try:
    print("You said " + r.recognize_google(audio))
except sr.UnknownValueError:
    print("Sphinx could not understand audio")
except sr.RequestError as e:
    print(f"Sphinx error; {e}")