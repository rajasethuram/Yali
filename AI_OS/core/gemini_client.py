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


def ask_with_search(
    user_prompt: str,
    system_prompt: str = "",
    context: str = "",
    max_tokens: int = 800,
) -> str:
    """
    Ask Gemini 2.0 Flash with Google Search grounding.
    Returns empty string on failure (caller decides fallback).
    """
    client = _get_client()
    if not client:
        return ""

    try:
        from google.genai import types

        full_prompt = user_prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{user_prompt}"

        config_kwargs = {
            "tools": [types.Tool(google_search=types.GoogleSearch())],
            "max_output_tokens": max_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
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
    """Plain Gemini ask — no search tool. Faster, cheaper."""
    client = _get_client()
    if not client:
        return ""

    try:
        from google.genai import types

        full_prompt = user_prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{user_prompt}"

        config_kwargs = {"max_output_tokens": max_tokens}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return response.text or ""
    except Exception as e:
        logger.warning(f"Gemini ask failed: {e}")
        return ""


def is_available() -> bool:
    return bool(GEMINI_API_KEY) and _get_client() is not None
