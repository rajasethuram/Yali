import speech_recognition as sr

print("Available microphones:")
for index, name in enumerate(sr.Microphone.list_microphone_names()):
    print(f"{index}: {name}")

# Test with default
recognizer = sr.Recognizer()
try:
    with sr.Microphone() as source:
        print("Testing default microphone...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Say 'test'...")
        audio = recognizer.listen(source, timeout=5)
        text = recognizer.recognize_google(audio)
        print(f"Recognized: {text}")
except Exception as e:
    print(f"Error: {e}")