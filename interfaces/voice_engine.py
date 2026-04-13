# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
voice_engine.py — Complete voice I/O pipeline

STT: Groq Whisper API (whisper-large-v3) — NOT local model
TTS: edge-tts with en-GB-RyanNeural (British Jarvis voice)
Wake word: speech_recognition keyword detection (no paid API key)

Architecture:
start_continuous_mode(callback) → background thread →
    records 10s chunks → Groq Whisper transcribes →
    if non-empty: callback(transcript) → speak(response) via edge-tts
"""
import os
import logging
import tempfile
import re

log = logging.getLogger("Voice")

# Available edge-tts voices by language
TTS_VOICES = {
    "en": os.getenv("TTS_VOICE_EN", "en-GB-RyanNeural"),  # British male
    "zh": os.getenv("TTS_VOICE_ZH", "zh-CN-YunxiNeural"),  # Mandarin male
    "zh_female": "zh-CN-XiaoxiaoNeural",  # Mandarin female
    "zh_tw": "zh-TW-YunJheNeural",  # Taiwan Mandarin
}
WAKE_WORD = os.getenv("WAKE_WORD", "jarvis").lower()


def _detect_language(text: str) -> str:
    """Detect if text is Chinese or English.
    If >15% characters are Chinese, treat as Chinese."""
    if not text:
        return "en"
    zh_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len([c for c in text if c.isalpha()])
    if total_chars == 0:
        return "en"
    return "zh" if zh_chars / total_chars > 0.15 else "en"


def _get_tts_voice(text: str) -> str:
    """Select appropriate TTS voice based on text language."""
    lang = _detect_language(text)
    if lang == "zh":
        return TTS_VOICES["zh"]
    return TTS_VOICES["en"]


class VoiceEngine:
    def __init__(self):
        self.running = False
        self._lock = None
        self._thread = None

    def listen_utterance(self, max_seconds=10) -> bytes:
        """Record microphone audio, return WAV bytes."""
        try:
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            import io
            sample_rate = 16000
            audio = sd.rec(int(max_seconds * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
            sd.wait()
            buf = io.BytesIO()
            sf.write(buf, audio, sample_rate, format='WAV', subtype='PCM_16')
            return buf.getvalue()
        except Exception as e:
            log.error(f"Record failed: {e}")
            return b""

    def transcribe(self, audio_bytes: bytes) -> str:
        """Groq Whisper transcription."""
        if not audio_bytes:
            return ""
        try:
            import tempfile
            import os
            from groq import Groq

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            try:
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                with open(tmp_path, "rb") as af:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=af,
                        response_format="text"
                    )
                return str(transcript).strip()
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            return ""

    def speak(self, text: str):
        """edge-tts TTS. Strip markdown. Fallback to pyttsx3."""
        # Clean ALL markdown symbols for TTS
        clean = text
        # Bold/italic
        clean = re.sub(r'\*+', '', clean)
        clean = re.sub(r'_+', '', clean)
        # Headers
        clean = re.sub(r'^#+\s*', '', clean, flags=re.MULTILINE)
        # Code blocks
        clean = re.sub(r'`+', '', clean)
        # Links [text](url)
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        # Emojis (TTS usually fails on these)
        clean = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]', '', clean)
        # Multiple whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean:
            return

        try:
            import edge_tts
            import asyncio
            import tempfile
            import os
            import sounddevice as sd
            import soundfile as sf

            async def _tts():
                communicate = edge_tts.Communicate(clean[:500], _get_tts_voice(clean))
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tmp = f.name
                    await communicate.save(tmp)
                    return tmp

            try:
                loop = asyncio.new_event_loop()
                tmp_path = loop.run_until_complete(_tts())
                loop.close()
                # Play
                data, sr = sf.read(tmp_path)
                sd.play(data, sr)
                sd.wait()
                os.unlink(tmp_path)
            except Exception:
                raise
        except Exception as e:
            log.warning(f"edge-tts failed ({e}), trying pyttsx3")
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(clean[:300])
                engine.runAndWait()
            except Exception as e2:
                log.error(f"TTS completely failed: {e2}")

    def listen_and_transcribe(self) -> str:
        """Record and transcribe one utterance."""
        return self.transcribe(self.listen_utterance())

    def start_continuous_mode(self, callback):
        """Background thread: record → transcribe → callback."""
        import threading
        self.running = True

        def _loop():
            log.info(f"[VOICE] Continuous mode. Say '{WAKE_WORD}' or just speak.")
            while self.running:
                try:
                    audio = self.listen_utterance(max_seconds=6)
                    if not audio:
                        continue
                    text = self.transcribe(audio)
                    if text and len(text) > 2:
                        log.info(f"[VOICE] Heard: {text}")
                        # Check for wakeword if set
                        if WAKE_WORD and WAKE_WORD not in text.lower():
                            continue
                        callback(text)
                except Exception as e:
                    log.debug(f"Voice loop error: {e}")

        self._thread = threading.Thread(target=_loop, daemon=True, name="VoiceLoop")
        self._thread.start()

    def stop(self):
        """Stop continuous mode."""
        self.running = False
