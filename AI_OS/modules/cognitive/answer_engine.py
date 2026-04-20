"""
Structured Answer Engine — uses Claude API to generate 4-part answers.
Output: opening (10s) + 3-5 bullets + real example from resume + keywords.
Streams responses via callback for real-time HUD display.
"""
import sys
import json
import time
from pathlib import Path
from typing import Callable, Optional, Generator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MIND_MODEL, CLAUDE_MIND_MAX_TOKENS
from modules.cognitive.resume_parser import get_profile_context_string
from modules.cognitive.intent_classifier import classify_intent, get_response_framework

import anthropic

SYSTEM_PROMPT_TEMPLATE = """You are YALI MIND — an elite real-time interview coach.
Your job: when a professional hears an interview question, you instantly generate a structured, confident answer they can speak aloud.

{profile_context}

RESPONSE FORMAT (always use this exact structure):
[OPENING]
One powerful 10-second opening sentence. Direct, confident, no filler words.

[BULLETS]
- Point 1: concise, specific, impactful
- Point 2: concise, specific, impactful
- Point 3: concise, specific, impactful
(add Point 4 or 5 only if question needs depth)

[EXAMPLE]
One real-world example the candidate can use. Reference their actual companies/skills if profile is loaded. Keep to 2 sentences.

[KEYWORDS]
5 powerful domain-specific keywords/phrases to naturally weave into the answer.

RULES:
- No fluff, no hedging, no "I think" or "maybe"
- Use first person, present/past tense
- Match the FRAMEWORK: {framework}
- Intent type: {intent}
- Be specific, not generic
- If no resume loaded, give a strong template answer they can personalize
- Total response should be speakable in 90-120 seconds"""


def _build_messages(question: str, intent: str, framework: str,
                    conversation_history: list) -> list:
    profile_ctx = get_profile_context_string()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        profile_context=profile_ctx,
        framework=framework,
        intent=intent,
    )

    messages = []
    # Add last N conversation turns for context
    for turn in conversation_history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": f"Interview question: {question}"})

    return system, messages


def generate_answer_streaming(
    question: str,
    on_chunk: Optional[Callable[[str, str], None]] = None,
    conversation_history: Optional[list] = None,
) -> Generator[str, None, None]:
    """
    Streams answer chunks via on_chunk(chunk_text, section_name).
    section_name: 'opening' | 'bullets' | 'example' | 'keywords'
    Yields full text at end.
    """
    if not ANTHROPIC_API_KEY:
        error = "[ERROR] ANTHROPIC_API_KEY not set in .env file. Add your key to .env."
        if on_chunk:
            on_chunk(error, "error")
        return

    conversation_history = conversation_history or []
    intent, confidence, label = classify_intent(question)
    framework = get_response_framework(intent)

    system_prompt, messages = _build_messages(question, intent, framework, conversation_history)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    full_response = []
    current_section = "opening"

    section_map = {
        "[OPENING]": "opening",
        "[BULLETS]": "bullets",
        "[EXAMPLE]": "example",
        "[KEYWORDS]": "keywords",
    }

    try:
        with client.messages.stream(
            model=CLAUDE_MIND_MODEL,
            max_tokens=CLAUDE_MIND_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        ) as stream:
            buffer = ""
            for text in stream.text_stream:
                full_response.append(text)
                buffer += text

                # Detect section transitions
                for marker, section in section_map.items():
                    if marker in buffer:
                        current_section = section
                        buffer = buffer.replace(marker, "").strip()

                # Stream to callback
                if on_chunk and buffer:
                    on_chunk(buffer, current_section)
                    buffer = ""

    except anthropic.AuthenticationError:
        msg = "[ERROR] Invalid Claude API key. Check ANTHROPIC_API_KEY in .env"
        if on_chunk:
            on_chunk(msg, "error")
        return
    except anthropic.RateLimitError:
        msg = "[ERROR] Claude API rate limit hit. Wait 60s and retry."
        if on_chunk:
            on_chunk(msg, "error")
        return
    except Exception as e:
        msg = f"[ERROR] Claude API error: {e}"
        if on_chunk:
            on_chunk(msg, "error")
        return

    full_text = "".join(full_response)
    return full_text


def generate_answer_sync(question: str, conversation_history: Optional[list] = None) -> dict:
    """
    Synchronous version — returns structured dict with all sections.
    Returns: {intent, label, framework, opening, bullets, example, keywords, full_text}
    """
    if not ANTHROPIC_API_KEY:
        return {
            "intent": "error",
            "label": "Error",
            "framework": "",
            "opening": "ANTHROPIC_API_KEY not set. Add your Claude API key to .env file.",
            "bullets": [],
            "example": "",
            "keywords": [],
            "full_text": "",
        }

    conversation_history = conversation_history or []
    intent, confidence, label = classify_intent(question)
    framework = get_response_framework(intent)
    system_prompt, messages = _build_messages(question, intent, framework, conversation_history)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=CLAUDE_MIND_MODEL,
            max_tokens=CLAUDE_MIND_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )
        full_text = response.content[0].text
    except Exception as e:
        return {
            "intent": "error", "label": "Error", "framework": framework,
            "opening": f"API Error: {e}", "bullets": [], "example": "",
            "keywords": [], "full_text": ""
        }

    # Parse sections from response
    parsed = _parse_sections(full_text)
    parsed["intent"] = intent
    parsed["label"] = label
    parsed["framework"] = framework
    parsed["full_text"] = full_text
    return parsed


def _parse_sections(text: str) -> dict:
    result = {"opening": "", "bullets": [], "example": "", "keywords": []}

    sections = {"opening": "", "bullets": "", "example": "", "keywords": ""}
    current = None

    for line in text.split("\n"):
        stripped = line.strip()
        if "[OPENING]" in stripped:
            current = "opening"
        elif "[BULLETS]" in stripped:
            current = "bullets"
        elif "[EXAMPLE]" in stripped:
            current = "example"
        elif "[KEYWORDS]" in stripped:
            current = "keywords"
        elif current and stripped:
            sections[current] += stripped + "\n"

    result["opening"] = sections["opening"].strip()
    result["example"] = sections["example"].strip()

    for line in sections["bullets"].split("\n"):
        line = line.strip().lstrip("-•*").strip()
        if line:
            result["bullets"].append(line)

    for kw in sections["keywords"].split("\n"):
        kw = kw.strip().lstrip("-•*1234567890.").strip()
        if kw:
            result["keywords"].append(kw)

    return result


if __name__ == "__main__":
    print("=== YALI MIND Answer Engine Test ===")
    print("Note: Requires ANTHROPIC_API_KEY in .env\n")

    question = "Tell me about a time you handled a conflict with a teammate."
    print(f"Question: {question}\n")

    def on_chunk(text, section):
        print(f"[{section.upper()}] {text}", end="", flush=True)

    result = generate_answer_streaming(question, on_chunk=on_chunk)
    print("\n\n=== Parsed Sections ===")
    if isinstance(result, str):
        parsed = _parse_sections(result)
        print(json.dumps(parsed, indent=2))
