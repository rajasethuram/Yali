import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import GROQ_API_KEY, GROQ_MODEL

from groq import Groq


def ask_llm(prompt: str, timeout: int = 30) -> str:
    """Call Groq LLM for task planning. Returns empty string on failure (triggers rule-based fallback)."""
    if not GROQ_API_KEY:
        return ""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""
