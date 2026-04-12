"""
notification_hub.py — Multi-channel notification system

Channels: telegram, voice, webui, desktop
send(msg, channels=["telegram"], priority="normal")
alert(msg) → all channels
windows_toast(msg) → win10toast or plyer

Auto-route:
- priority=high → all channels
- priority=normal → telegram only
"""
import logging
from typing import List

log = logging.getLogger("Notification")


class NotificationHub:
    def __init__(self, voice_engine=None):
        self.voice = voice_engine
        self._channels = ["telegram", "voice", "webui", "desktop"]

    def send(self, message: str, channels: List[str] = None, priority: str = "normal"):
        """Send notification to specified channels."""
        if channels is None:
            channels = ["telegram"] if priority == "normal" else self._channels

        results = {}
        for ch in channels:
            try:
                if ch == "telegram":
                    results[ch] = self._send_telegram(message)
                elif ch == "voice":
                    results[ch] = self._send_voice(message)
                elif ch == "webui":
                    results[ch] = self._send_webui(message)
                elif ch == "desktop":
                    results[ch] = self._send_desktop(message)
            except Exception as e:
                log.debug(f"Notification to {ch} failed: {e}")
                results[ch] = False

        return results

    def alert(self, message: str):
        """Send high-priority alert to all channels."""
        return self.send(message, channels=self._channels, priority="high")

    def _send_telegram(self, message: str) -> bool:
        try:
            from core.llm_gateway import send_telegram_alert
            send_telegram_alert(message)
            return True
        except Exception:
            return False

    def _send_voice(self, message: str) -> bool:
        if self.voice:
            try:
                self.voice.speak(message)
                return True
            except Exception:
                pass
        return False

    def _send_webui(self, message: str) -> bool:
        # This would be wired to kernel's _webui_push
        # For now, just log it
        log.info(f"[WEBUI NOTIFY] {message[:100]}")
        return True

    def _send_desktop(self, message: str) -> bool:
        """Send Windows desktop notification."""
        try:
            from plyer import notification
            notification.notify(
                title="OpenAGI",
                message=message[:256],
                timeout=10
            )
            return True
        except Exception:
            pass
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast("OpenAGI", message[:256], duration=10)
            return True
        except Exception:
            return False
