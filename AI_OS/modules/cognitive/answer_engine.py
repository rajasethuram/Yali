"""
Structured Answer Engine — uses Groq LLM to generate 4-part answers.
Output: opening (10s) + 3-5 bullets + real example from resume + keywords.
Streams responses via callback for real-time HUD display.
"""
import sys
import json
import time
from pathlib import Path
from typing import Callable, Optional, Generator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GROQ_API_KEY, GROQ_MODEL, CLAUDE_MIND_MAX_TOKENS
from modules.cognitive.resume_parser import get_profile_context_string
from modules.cognitive.intent_classifier import classify_intent, get_response_framework

from groq import Groq

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
                    conversation_history: list) -> tuple:
    profile_ctx = get_profile_context_string()
    system = SYSTEM_PROMPT_TEMPLATE.format(
        profile_context=profile_ctx,
        framework=framework,
        intent=intent,
    )

    messages = [{"role": "system", "content": system}]
    for turn in conversation_history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"Interview question: {question}"})

    return messages


def generate_answer_streaming(
    question: str,
    on_chunk: Optional[Callable[[str, str], None]] = None,
    conversation_history: Optional[list] = None,
) -> str:
    """
    Streams answer chunks via on_chunk(chunk_text, section_name).
    section_name: 'opening' | 'bullets' | 'example' | 'keywords'
    Returns full text at end.
    """
    if not GROQ_API_KEY:
        error = "[ERROR] GROQ_API_KEY not set in .env file. Get free key at console.groq.com"
        if on_chunk:
            on_chunk(error, "error")
        return ""

    conversation_history = conversation_history or []
    intent, confidence, label = classify_intent(question)
    framework = get_response_framework(intent)
    messages = _build_messages(question, intent, framework, conversation_history)

    client = Groq(api_key=GROQ_API_KEY)

    section_map = {
        "[OPENING]": "opening",
        "[BULLETS]": "bullets",
        "[EXAMPLE]": "example",
        "[KEYWORDS]": "keywords",
    }

    full_response = []
    current_section = "opening"
    buffer = ""

    try:
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=CLAUDE_MIND_MAX_TOKENS,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            text = chunk.choices[0].delta.content
            if not text:
                continue
            full_response.append(text)
            buffer += text

            for marker, section in section_map.items():
                if marker in buffer:
                    current_section = section
                    buffer = buffer.replace(marker, "").strip()

            if on_chunk and buffer:
                on_chunk(buffer, current_section)
                buffer = ""

    except Exception as e:
        msg = f"[ERROR] Groq API error: {e}"
        if on_chunk:
            on_chunk(msg, "error")
        return ""

    return "".join(full_response)


def generate_answer_sync(question: str, conversation_history: Optional[list] = None) -> dict:
    """
    Synchronous version — returns structured dict with all sections.
    Returns: {intent, label, framework, opening, bullets, example, keywords, full_text}
    """
    if not GROQ_API_KEY:
        return {
            "intent": "error", "label": "Error", "framework": "",
            "opening": "GROQ_API_KEY not set. Get free key at console.groq.com and add to .env",
            "bullets": [], "example": "", "keywords": [], "full_text": "",
        }

    conversation_history = conversation_history or []
    intent, confidence, label = classify_intent(question)
    framework = get_response_framework(intent)
    messages = _build_messages(question, intent, framework, conversation_history)

    client = Groq(api_key=GROQ_API_KEY)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=CLAUDE_MIND_MAX_TOKENS,
            messages=messages,
        )
        full_text = response.choices[0].message.content
    except Exception as e:
        return {
            "intent": "error", "label": "Error", "framework": framework,
            "opening": f"API Error: {e}", "bullets": [], "example": "",
            "keywords": [], "full_text": ""
        }

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
        line = line.strip().lstrip("-*").strip()
        if line:
            result["bullets"].append(line)

    for kw in sections["keywords"].split("\n"):
        kw = kw.strip().lstrip("-*1234567890.").strip()
        if kw:
            result["keywords"].append(kw)

    return result


if __name__ == "__main__":
    print("=== YALI MIND Answer Engine Test (Groq) ===\n")
    question = "Tell me about a time you handled a conflict with a teammate."
    print(f"Question: {question}\n")

    def on_chunk(text, section):
        print(f"[{section.upper()}] {text}", end="", flush=True)

    result = generate_answer_streaming(question, on_chunk=on_chunk)
    print("\n\n=== Parsed Sections ===")
    if result:
        print(json.dumps(_parse_sections(result), indent=2))
