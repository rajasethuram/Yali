"""
Gemini 2.0 Flash client for YALI Finance + web search.
Free tier: 1,500 req/day, Google Search grounding built-in.
Falls back to Groq (core.llm_client) if GEMINI_API_KEY not set.
"""

import logging
from config.settings import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("yali")

_client = None


def _get_client():
    global _client
    if _client is None and GEMINI_API_KEY:
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.warning(f"Gemini client init failed: {e}")
    return _client


def _build_config(use_search: bool, system_prompt: str, max_tokens: int):
    """Build GenerateContentConfig — thinking disabled for fast finance responses."""
    from google.genai import types
    kwargs = {
        "max_output_tokens": max_tokens,
        # Disable chain-of-thought thinking: thinking tokens eat into budget
        # on gemini-2.5-flash, leaving zero tokens for actual response at low limits.
        "thinking_config": types.ThinkingConfig(thinking_budget=0),
    }
    if use_search:
        kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    if system_prompt:
        kwargs["system_instruction"] = system_prompt
    return types.GenerateContentConfig(**kwargs)


def ask_with_search(
    user_prompt: str,
    system_prompt: str = "",
    context: str = "",
    max_tokens: int = 600,
) -> str:
    """Gemini 2.5 Flash + Google Search grounding. Falls back to '' on failure."""
    client = _get_client()
    if not client:
        return ""
    try:
        full_prompt = f"Context:\n{context}\n\n{user_prompt}" if context else user_prompt
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=_build_config(use_search=True, system_prompt=system_prompt, max_tokens=max_tokens),
        )
        return response.text or ""
    except Exception as e:
        logger.warning(f"Gemini ask_with_search failed: {e}")
        return ""


def ask(
    user_prompt: str,
    system_prompt: str = "",
    context: str = "",
    max_tokens: int = 600,
) -> str:
    """Plain Gemini ask — no search. Faster for summarisation/synthesis."""
    client = _get_client()
    if not client:
        return ""
    try:
        full_prompt = f"Context:\n{context}\n\n{user_prompt}" if context else user_prompt
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=_build_config(use_search=False, system_prompt=system_prompt, max_tokens=max_tokens),
        )
        return response.text or ""
    except Exception as e:
        logger.warning(f"Gemini ask failed: {e}")
        return ""


def is_available() -> bool:
    return bool(GEMINI_API_KEY) and _get_client() is not None
