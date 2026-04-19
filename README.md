YALI_IRON_MAN_AI_OS_V2

Production-grade prototype of YALI — an Iron Man inspired AI Operating System.

This repository provides a runnable local prototype combining:
- Wake-word activation (Porcupine recommended, keyboard fallback included)
- Speech-to-text (SpeechRecognition) and text-to-speech (pyttsx3)
- Simple orchestrator + async agent swarm (planner, executor, validator, self-healer)
- Ollama local LLM client integration
- System tools (open apps, run shell), file tools
- Glassmorphism HUD dashboard (static web + WebSocket updates via FastAPI)

This is a developer-focused prototype: Porcupine and advanced hardware integrations are optional and documented below.

Quick start (Windows)

1. Create and activate a virtual environment (Python 3.10+)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements

```powershell
pip install -r requirements.txt
```

3. Start Ollama (optional, for LLM features)

```powershell
# ollama serve
```

4. Run the system

```powershell
python main.py
```

5. Open the HUD in a browser: http://localhost:8000

Example commands

- "Yali, open chrome"
- "Yali, search EPAM jobs"
- "Yali, create file report.txt with Hello World"

Notes

- Wake-word: Porcupine integration is scaffolded in `core/wakeword_engine.py`. If you don't have Porcupine the system will fall back to keyboard activation.
- UI is a minimal glass-style dashboard served by FastAPI in `ui/server.py`.

---

See `ARCHITECTURE.md` for a text-based architecture diagram.
