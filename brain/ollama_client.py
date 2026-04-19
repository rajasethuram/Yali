import requests
from config.settings import OLLAMA_URL, MODEL

def ask_llm(prompt, timeout=30):
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        return f"LLM Error: {e}"
