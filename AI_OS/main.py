"""
YALI AI OS — entry point.
Starts: UI server | voice loop | task queue processor
"""
import asyncio
import threading
import logging
import time

logging.basicConfig(
    filename="logs/system.log",
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("yali")

# ── imports ───────────────────────────────────────────────────────────────────
from core.wakeword_engine import WakeWordEngine
from core.speech_to_text import listen_from_mic
from core.text_to_speech import speak
from core.orchestrator import Orchestrator
from ui.server import run_server, task_queue, broadcast_status

orc = Orchestrator()

# ── voice state ───────────────────────────────────────────────────────────────
_voice_lock = threading.Lock()   # prevent overlapping voice sessions
_voice_busy  = False


def _set_voice_state(state: str):
    """Push listening/speaking/idle state to HUD via WebSocket."""
    asyncio.run_coroutine_threadsafe(
        broadcast_status({"type": "voice", "state": state}),
        _loop,
    )


# ── voice callback — runs when wake word fires ────────────────────────────────
def on_wake():
    global _voice_busy
    with _voice_lock:
        if _voice_busy:
            logger.info("Voice: already active, ignoring wake")
            return
        _voice_busy = True

    try:
        _set_voice_state("listening")
        speak("Yes?")

        text = listen_from_mic(timeout=6, phrase_time_limit=10)
        if not text:
            speak("Didn't catch that.")
            _set_voice_state("idle")
            _voice_busy = False
            return

        print(f"[Yali] Heard: {text}")
        logger.info(f"Voice input: {text}")
        _set_voice_state("thinking")

        # Route through orchestrator (handles finance + general tasks)
        future = asyncio.run_coroutine_threadsafe(
            orc.handle_task(text), _loop
        )
        result = future.result(timeout=60)

        # Orchestrator already calls speak() internally,
        # but if it returned a plain string (finance QA) speak it here.
        if isinstance(result, str) and result:
            speak(result[:400])

        _set_voice_state("idle")
    except Exception as e:
        logger.error(f"Voice loop error: {e}")
        speak("Something went wrong.")
        _set_voice_state("idle")
    finally:
        _voice_busy = False


# ── web task processor ────────────────────────────────────────────────────────
async def task_processor():
    """Drains the HTTP /submit-task queue."""
    while True:
        try:
            task = await asyncio.wait_for(task_queue.get(), timeout=1.0)
            if task:
                logger.info(f"Queue task: {task}")
                await orc.handle_task(task)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Task processor: {e}")
            await asyncio.sleep(0.5)


# ── server thread ─────────────────────────────────────────────────────────────
def _start_server():
    run_server()


# ── main ──────────────────────────────────────────────────────────────────────
_loop: asyncio.AbstractEventLoop = None


def main():
    global _loop

    # 1 — UI server (uvicorn) in background thread
    srv = threading.Thread(target=_start_server, daemon=True)
    srv.start()
    time.sleep(2)   # wait for bind

    # 2 — async event loop for orchestrator + task queue
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    loop_thread = threading.Thread(
        target=_loop.run_forever, daemon=True
    )
    loop_thread.start()

    # schedule task processor in the loop
    asyncio.run_coroutine_threadsafe(task_processor(), _loop)

    # 3 — wake word engine
    ww = WakeWordEngine(callback=on_wake)
    ww.start()

    print("=" * 55)
    print("  YALI OS — online")
    print("  HUD    → http://localhost:8000")
    print("  Voice  → Ctrl+Space (or type 'yali' + Enter)")
    print("  Stop   → Ctrl+C")
    print("=" * 55)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Yali] Shutting down.")
        ww.stop()
        _loop.call_soon_threadsafe(_loop.stop)


if __name__ == "__main__":
    main()
