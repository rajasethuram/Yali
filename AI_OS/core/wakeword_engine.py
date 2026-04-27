"""
Wake word engine — two activation modes:
  1. Hotkey (Ctrl+Space) via `keyboard` lib — hands-free, works while typing
  2. Keyboard fallback  — type 'yali' + Enter (if keyboard lib has no permissions)
"""
import threading
import logging
from config.settings import WAKE_WORD

logger = logging.getLogger("yali")
HOTKEY = "ctrl+space"


class WakeWordEngine:
    def __init__(self, callback=None):
        self.callback = callback
        self._stop = False
        self._mode = "unknown"

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _fire(self):
        logger.info("WakeWord: activated")
        if self.callback:
            threading.Thread(target=self.callback, daemon=True).start()

    def _run(self):
        # Try hotkey mode first
        try:
            import keyboard as kb
            kb.add_hotkey(HOTKEY, self._fire)
            self._mode = "hotkey"
            print(f"[Yali] Wake word: press {HOTKEY.upper()} to activate")
            while not self._stop:
                import time; time.sleep(0.5)
        except Exception as e:
            # Fallback: type wake word + Enter
            self._mode = "keyboard"
            print(f"[Yali] Wake word: type '{WAKE_WORD}' + Enter to activate  (hotkey unavailable: {e})")
            import time
            while not self._stop:
                try:
                    s = input().strip().lower()
                    if s == WAKE_WORD or s.startswith(WAKE_WORD + " "):
                        self._fire()
                except EOFError:
                    time.sleep(0.5)

    def stop(self):
        self._stop = True
        try:
            import keyboard as kb
            kb.remove_hotkey(HOTKEY)
        except Exception:
            pass

    @property
    def mode(self):
        return self._mode
