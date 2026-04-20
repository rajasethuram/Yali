import requests
from config.settings import OLLAMA_URL, MODEL

SYSTEM_PROMPT = """You are YALI, a production-grade Artificial Intelligence Operating System assistant inspired by Iron Man JARVIS.

You are NOT a chatbot.

You are the central intelligence layer of a full operating system that can:
- Listen to voice commands
- Execute system-level actions
- Run automation workflows
- Control files, applications, and browser
- Use local AI models (Ollama)
- Coordinate multiple AI agents

...existing code...
"""

class AIManager:
    def generate(self, prompt):
        full_prompt = SYSTEM_PROMPT + "\n\nUser: " + prompt
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return f"AI Error: {e}"
