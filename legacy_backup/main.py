from core.ai_manager import AIManager
from agents.general_agent import run
from memory.memory_store import save
from core.voice import listen, speak

HOTWORD = "yali"


def jarvis():
    ai = AIManager()

    print("🚀 YALI REAL-TIME SYSTEM STARTED")
    speak("Yali online and ready")

    while True:

        command = listen()

        if not command:
            # Fallback to text input
            try:
                command = input("🎤 Voice not detected. Type your command: ").strip()
            except EOFError:
                continue

        if not command:
            continue

        print("👂 Heard/Typed:", command)

        command = command.lower().strip()

        # -----------------------------
        # EXIT CONDITION
        # -----------------------------
        if "exit" in command or "shutdown" in command:
            speak("Shutting down system")
            break

        # -----------------------------
        # HOTWORD MODE
        # -----------------------------
        if HOTWORD in command:
            speak("Yes, I am listening")

            task = listen()

            if not task:
                # Fallback to text
                try:
                    task = input("🎤 Voice not detected. Type your task: ").strip()
                except EOFError:
                    speak("I didn't hear anything")
                    continue

            if not task:
                speak("I didn't hear anything")
                continue

            print("🧠 Task:", task)

            result = run(ai, task)

            print("\n🤖 AI RESPONSE:\n", result)

            speak(result)

            speak(result[:180])  # fast voice output

            save(task, result)

        # -----------------------------
        # DIRECT COMMAND MODE
        # -----------------------------
        elif "jarvis" in command:
            task = command.replace("jarvis", "").strip()

            if task:
                result = run(ai, task)

                print("\n🤖 AI RESPONSE:\n", result)

                speak(result[:180])

                save(task, result)


if __name__ == "__main__":
    jarvis()
