"""
Streaming Speech-to-Text engine using faster-whisper.
Captures mic in 2-second chunks, streams transcribed text via callback.
"""
import threading
import queue
import time
import sys
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import YALI_MIND_STT_CHUNK_SECONDS

try:
    import noisereduce as nr
    NOISE_REDUCE = True
except ImportError:
    NOISE_REDUCE = False

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = YALI_MIND_STT_CHUNK_SECONDS
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_DURATION
SILENCE_THRESHOLD = 0.01
MIN_SPEECH_DURATION = 0.3  # seconds of speech needed to transcribe


class STTEngine:
    def __init__(self, model_size: str = "base", on_transcript: Optional[Callable] = None):
        self.model_size = model_size
        self.on_transcript = on_transcript or (lambda text, is_final: print(f"[STT] {text}"))
        self.model = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._capture_thread = None
        self._transcribe_thread = None
        self._full_transcript = []
        self._session_audio = []

    def _load_model(self):
        if self.model is None:
            print(f"[STT] Loading faster-whisper '{self.model_size}' model...")
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            print("[STT] Model loaded.")

    def _is_silent(self, audio: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(audio ** 2))
        return rms < SILENCE_THRESHOLD

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass
        audio = indata[:, 0].copy()
        self._audio_queue.put(audio)
        self._session_audio.append(audio)

    def _capture_loop(self):
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=CHUNK_SAMPLES,
            callback=self._audio_callback,
        ):
            print("[STT] Microphone capturing...")
            while self._running:
                time.sleep(0.1)

    def _transcribe_loop(self):
        buffer = []
        buffer_duration = 0.0

        while self._running or not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                # Flush buffer on silence
                if buffer and buffer_duration >= MIN_SPEECH_DURATION:
                    self._transcribe_buffer(buffer, is_final=False)
                    buffer = []
                    buffer_duration = 0.0
                continue

            if self._is_silent(chunk):
                if buffer and buffer_duration >= MIN_SPEECH_DURATION:
                    self._transcribe_buffer(buffer, is_final=True)
                    buffer = []
                    buffer_duration = 0.0
            else:
                buffer.append(chunk)
                buffer_duration += CHUNK_DURATION

                # Auto-flush every 4 seconds of speech
                if buffer_duration >= 4.0:
                    self._transcribe_buffer(buffer, is_final=False)
                    buffer = []
                    buffer_duration = 0.0

        # Final flush
        if buffer and buffer_duration >= MIN_SPEECH_DURATION:
            self._transcribe_buffer(buffer, is_final=True)

    def _transcribe_buffer(self, buffer: list, is_final: bool):
        audio = np.concatenate(buffer)

        if NOISE_REDUCE:
            try:
                import noisereduce as nr
                audio = nr.reduce_noise(y=audio, sr=SAMPLE_RATE)
            except Exception:
                pass

        segments, _ = self.model.transcribe(
            audio,
            language="en",
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )

        text = " ".join(seg.text.strip() for seg in segments).strip()
        if text:
            self._full_transcript.append(text)
            self.on_transcript(text, is_final)

    def start(self):
        self._load_model()
        self._running = True
        self._full_transcript = []
        self._session_audio = []

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._transcribe_thread = threading.Thread(target=self._transcribe_loop, daemon=True)

        self._capture_thread.start()
        self._transcribe_thread.start()
        print("[STT] Engine started. Listening...")

    def stop(self) -> str:
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=3)
        if self._transcribe_thread:
            self._transcribe_thread.join(timeout=5)
        full_text = " ".join(self._full_transcript)
        print(f"[STT] Engine stopped. Full transcript: {full_text[:200]}")
        return full_text

    def get_transcript(self) -> str:
        return " ".join(self._full_transcript)

    def capture_single_question(self, timeout: float = 10.0) -> str:
        """Capture one question (stops after silence or timeout)."""
        self._load_model()
        result = []
        done_event = threading.Event()

        def on_text(text, is_final):
            result.append(text)
            if is_final:
                done_event.set()

        self.on_transcript = on_text
        self.start()
        done_event.wait(timeout=timeout)
        self.stop()
        return " ".join(result).strip()


_engine_instance: Optional[STTEngine] = None


def get_stt_engine(on_transcript: Optional[Callable] = None) -> STTEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = STTEngine(model_size="base", on_transcript=on_transcript)
    elif on_transcript:
        _engine_instance.on_transcript = on_transcript
    return _engine_instance


if __name__ == "__main__":
    print("Testing STT engine — speak for 10 seconds...")
    engine = STTEngine(model_size="base")
    engine.start()
    time.sleep(10)
    transcript = engine.stop()
    print(f"\nFull transcript:\n{transcript}")
