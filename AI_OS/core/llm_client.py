import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL
from datetime import datetime

YALI_BASE_PROMPT = """You are Yali — a personal AI operating system inspired by Iron Man's JARVIS.
You are precise, intelligent, and efficient.
You never ramble. You never apologize unnecessarily.
You address the user as Raja.
You are confident in your responses.
You give the shortest answer that is fully correct.
When uncertain, you say so in one sentence and proceed.
You are not a chatbot. You are an operating system.

Current date and time: {datetime}
{memory_context}"""


def ask(
    user_prompt: str,
    system_prompt: str = "",
    memory_context: str = "",
    max_tokens: int = 800,
    timeout: int = 30,
) -> str:
    """
    Single entry point for all LLM calls in Yali OS.
    Injects Yali personality + memory context into every call.
    Returns empty string on failure — callers handle fallback.
    """
    if not GROQ_API_KEY:
        return ""

    mem_block = f"\nMemory context about Raja:\n{memory_context}" if memory_context else ""
    base = YALI_BASE_PROMPT.format(
        datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
        memory_context=mem_block,
    )

    full_system = f"{base}\n\n{system_prompt}".strip() if system_prompt else base

    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""


def ask_raw(
    messages: list,
    system_prompt: str = "",
    max_tokens: int = 800,
) -> str:
    """Multi-turn conversation call. messages = [{"role":..., "content":...}]."""
    if not GROQ_API_KEY:
        return ""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            messages=full_messages,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""
