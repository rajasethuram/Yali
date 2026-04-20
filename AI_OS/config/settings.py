import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# LLM — Claude API (primary), Ollama (fallback)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3"

# UI
HUD_HOST = "0.0.0.0"
HUD_PORT = 8000

# Wake word
WAKE_WORD = "yali"

# Info APIs
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Gmail
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# User profile
USER_NAME = os.getenv("USER_NAME", "User")
USER_EMAIL = os.getenv("USER_EMAIL", "")

# Paths
BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "memory"
RESUME_PATH = MEMORY_DIR / "resume.pdf"
USER_PROFILE_PATH = MEMORY_DIR / "user_profile.json"
KEYLOG_DIR = MEMORY_DIR / "keylog"
FACES_DIR = MEMORY_DIR / "faces"
JOBS_DB_PATH = MEMORY_DIR / "jobs.db"

# YALI MIND
YALI_MIND_STT_CHUNK_SECONDS = 2
YALI_MIND_MAX_CONTEXT_TURNS = 10
YALI_MIND_RESPONSE_TIMEOUT = 8

# Cognitive assistant
CLAUDE_MIND_MODEL = "claude-sonnet-4-6"
CLAUDE_MIND_MAX_TOKENS = 600
