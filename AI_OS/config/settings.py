import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# LLM — Groq (free, fast) — all agents
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Finance + web search — Gemini 2.5 Flash (free, Google Search built-in)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# UI
HUD_HOST = "0.0.0.0"
HUD_PORT = 8000

# Cloudflare Tunnel (optional — leave empty for quick random URL)
CLOUDFLARE_TUNNEL_TOKEN = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "")

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

# MiroFish + litellm
MIROFISH_PORT = int(os.getenv("MIROFISH_PORT", "5001"))
LITELLM_PORT = int(os.getenv("LITELLM_PORT", "4000"))

# YALI MIND
YALI_MIND_STT_CHUNK_SECONDS = 2
YALI_MIND_MAX_CONTEXT_TURNS = 10
YALI_MIND_RESPONSE_TIMEOUT = 8

# Cognitive assistant
CLAUDE_MIND_MODEL = GROQ_MODEL  # alias kept for compatibility
CLAUDE_MIND_MAX_TOKENS = 600
