Project: YALI_IRON_MAN_AI_OS_V2

See the README for start instructions. This file contains the same architecture notes.
YALI_IRON_MAN_AI_OS_V2 - Architecture (text)

Components:

- Wake Word Engine (Porcupine or keyboard fallback) -> triggers Orchestrator
- Orchestrator (async main controller) -> routes commands to Agent Swarm
- Agent Swarm:
  - Planner Agent: generates step plan
  - Executor Agent: runs actions via tools
  - Validator Agent: confirms success
  - Self-Healing Agent: retries/replans on failure
- Brain (Ollama client) -> provides reasoning and planning assistance
- Tools: system_tools, file_tools, web_tools
- HUD Dashboard: FastAPI + WebSocket serving static glass UI
- Memory store: persistent JSON logs

Data flow:

Wakeword -> STT -> Orchestrator -> Planner -> Executor -> Validator -> TTS + HUD
