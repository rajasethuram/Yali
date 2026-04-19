"""
Wake word engine scaffold.
Uses Picovoice Porcupine if available; falls back to keyboard activation (type 'yali').
"""
import threading
import time
from config.settings import WAKE_WORD

class WakeWordEngine:
    def __init__(self, callback=None):
        self.callback = callback
        self._stop = False

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        # Placeholder: Porcupine integration would go here.
        # Fallback: simple keyboard-based activation loop
        print("WakeWord: Listening (type 'yali' + Enter to activate)")
        while not self._stop:
            try:
                s = input().strip().lower()
            except EOFError:
                time.sleep(0.5)
                continue
            if s == WAKE_WORD:
                print("WakeWord: activated")
                if self.callback:
                    self.callback()

    def stop(self):
        self._stop = True
