import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 140)
engine.setProperty('volume', 0.9)

voices = engine.getProperty('voices')
if voices:
    engine.setProperty('voice', voices[0].id)

def speak(text):
    if not text:
        return
    print(f"TTS: {text}")
    engine.say(text)
    engine.runAndWait()
