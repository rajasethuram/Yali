"""
Text-to-speech — pyttsx3.
Thread-safe: uses a dedicated TTS thread + queue so calls from any thread work.
"""
import pyttsx3
import threading
import queue
import logging

logger = logging.getLogger("yali")

_tts_queue: queue.Queue = queue.Queue()
_tts_ready = threading.Event()

_engine = None
_engine_lock = threading.Lock()


def _tts_worker():
    global _engine
    with _engine_lock:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 155)
        _engine.setProperty("volume", 0.9)
        voices = _engine.getProperty("voices")
        # Prefer a female voice (index 1 on most Windows systems)
        if voices and len(voices) > 1:
            _engine.setProperty("voice", voices[1].id)
        elif voices:
            _engine.setProperty("voice", voices[0].id)
        _tts_ready.set()

    while True:
        text = _tts_queue.get()
        if text is None:
            break
        try:
            _engine.say(text)
            _engine.runAndWait()
        except Exception as e:
            logger.warning(f"TTS error: {e}")
        finally:
            _tts_queue.task_done()


# Start TTS worker thread on import
_worker = threading.Thread(target=_tts_worker, daemon=True)
_worker.start()
_tts_ready.wait(timeout=5)


def speak(text: str):
    """Queue text for TTS. Non-blocking — returns immediately."""
    if not text or not text.strip():
        return
    clean = text.strip()
    print(f"[Yali speaks] {clean[:120]}")
    logger.info(f"TTS: {clean[:80]}")
    _tts_queue.put(clean)
