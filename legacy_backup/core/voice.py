import speech_recognition as sr
import pyttsx3

# -----------------------------
# INIT SPEECH ENGINE (TTS)
# -----------------------------
engine = pyttsx3.init()
engine.setProperty('rate', 140)  # Slower for movie-style
engine.setProperty('volume', 0.9)

# Set a deeper voice if available
voices = engine.getProperty('voices')
if voices:
    # Try to find a male voice
    for voice in voices:
        if 'male' in voice.name.lower() or 'david' in voice.name.lower() or 'zira' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    else:
        engine.setProperty('voice', voices[0].id)  # Default to first

recognizer = sr.Recognizer()
microphone = sr.Microphone()


# -----------------------------
# TEXT TO SPEECH
# -----------------------------
def speak(text):
    if not text:
        return

    print("🗣️ Yali:", text)

    engine.say(text)
    engine.runAndWait()


# -----------------------------
# SPEECH TO TEXT (SAFE + FAST)
# -----------------------------
def listen(timeout=5, phrase_time_limit=6):
    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)

            print("🎧 Listening...")

            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit
            )

        text = recognizer.recognize_google(audio)
        return text.lower().strip()

    except sr.WaitTimeoutError:
        return ""

    except sr.UnknownValueError:
        return ""

    except sr.RequestError:
        print("❌ Speech API error")
        return ""

    except Exception as e:
        print("❌ Voice error:", e)
        return ""
