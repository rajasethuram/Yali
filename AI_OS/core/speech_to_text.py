import speech_recognition as sr

recognizer = sr.Recognizer()

def listen_from_mic(timeout=5, phrase_time_limit=8):
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("STT: Listening...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio)
        return text
    except Exception as e:
        return ""
