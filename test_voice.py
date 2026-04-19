from core.voice import listen

print("Testing voice recognition...")
print("Say something...")

result = listen(timeout=10, phrase_time_limit=10)
print(f"Heard: '{result}'")

if result:
    print("Voice recognition is working!")
else:
    print("No speech detected. Check microphone.")