# Copyright (c) 2026 Solarix2026
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/Solarix2026/OpenAGI

"""
call_mode.py — Voice call integration for Telegram

Integrate with system phone/VOIP if available.
Primarily: pipe voice_engine into Telegram voice messages.

receive_voice_message(telegram_voice_file) → transcribe → process → TTS reply.
Wire into run_telegram() to handle voice messages.
"""
import logging
import tempfile
import os
import requests

log = logging.getLogger("CallMode")


class CallMode:
    def __init__(self, kernel):
        self.kernel = kernel

    def download_telegram_voice(self, file_id: str) -> bytes:
        """Download voice message from Telegram."""
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not token:
                return b""

            # Get file path from Telegram
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id},
                timeout=10
            )
            result = resp.json()
            if not result.get("ok"):
                return b""

            file_path = result["result"]["file_path"]

            # Download the file
            file_resp = requests.get(
                f"https://api.telegram.org/file/bot{token}/{file_path}",
                timeout=30
            )
            return file_resp.content
        except Exception as e:
            log.error(f"Failed to download voice: {e}")
            return b""

    def process_voice_message(self, file_id: str) -> str:
        """
        Process a voice message from Telegram.
        Returns reply text.
        """
        if not self.kernel.voice:
            return "Voice engine not available."

        # Download voice
        voice_data = self.download_telegram_voice(file_id)
        if not voice_data:
            return "Failed to download voice message."

        # Save temporarily
        with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as f:
            f.write(voice_data)
            temp_path = f.name

        try:
            # Convert to wav and transcribe
            import subprocess
            wav_path = temp_path.replace(".oga", ".wav")

            # Use ffmpeg to convert (if available)
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", temp_path, wav_path],
                    capture_output=True,
                    timeout=10
                )
            except Exception:
                # Fallback: assume voice engine can handle OGG
                wav_path = temp_path

            # Transcribe using voice engine
            transcript = self.kernel.voice.transcribe(open(wav_path, "rb").read())

            if not transcript:
                return "Sorry, I couldn't hear that clearly."

            # Process the transcript
            response = self.kernel.process(transcript)

            # Send voice reply if possible
            if self.kernel.voice:
                # Could send voice back via Telegram here
                pass

            return response

        except Exception as e:
            return f"Voice processing error: {e}"

        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def handle_inline_query(self, query: str) -> dict:
        """Handle inline queries from Telegram."""
        return {"type": "voice", "query": query}
