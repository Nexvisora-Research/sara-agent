"""Voice-driven computer use.

Integrates with Sara's existing STT/TTS pipeline to enable voice commands
for desktop actions. Handles wake word detection, command parsing, and
action execution.
"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .config import ComputerUseConfig

logger = logging.getLogger(__name__)


class VoiceCommandHandler:
    """Listens for voice commands and routes them to computer actions.

    Integrates with existing Sara voice infrastructure (transcription_tools,
    voice_mode, tts_tool) for a complete voice-driven desktop experience.
    """

    WAKE_WORDS = ["hey sara", "sara", "okay sara"]

    COMMAND_PATTERNS: List[tuple[str, str, Callable]] = []

    def __init__(self, computer_agent, config: Optional[ComputerUseConfig] = None):
        self._agent = computer_agent
        self.config = config or ComputerUseConfig()
        self._listening = False
        self._thread: Optional[threading.Thread] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._stt = None
        self._tts = None
        self._init_voice()

    def _init_voice(self):
        try:
            from tools.transcription_tools import transcribe_audio
            self._transcribe = transcribe_audio
        except ImportError:
            self._transcribe = None

        try:
            from tools.tts_tool import text_to_speech_tool
            self._speak = text_to_speech_tool
        except ImportError:
            self._speak = None

    @property
    def is_available(self) -> bool:
        return self._transcribe is not None

    def start_listening(self):
        if self._listening:
            return
        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Voice command listening started")

    def stop_listening(self):
        self._listening = False

    def _listen_loop(self):
        while self._listening:
            try:
                self._listen_once()
            except Exception as e:
                logger.debug("Voice listen cycle error: %s", e)
                time.sleep(1)

    def _listen_once(self):
        try:
            from tools.voice_tools import listen_mic
            audio_text = listen_mic(duration=5)
            if not audio_text:
                return

            text = audio_text.strip().lower()
            if not text:
                return

            wake_detected, command = self._check_wake_word(text)
            if not wake_detected:
                return

            logger.info("Voice command detected: %s", command)
            self._execute_voice_command(command)
        except Exception as e:
            logger.debug("Voice listen failed: %s", e)

    def _check_wake_word(self, text: str) -> tuple[bool, str]:
        for wake in self.WAKE_WORDS:
            if text.startswith(wake):
                command = text[len(wake):].strip()
                if command:
                    return True, command
                return True, "status"
            if wake in text:
                idx = text.index(wake) + len(wake)
                command = text[idx:].strip()
                if command:
                    return True, command
        return False, ""

    def _execute_voice_command(self, command: str):
        command_lower = command.lower().strip()

        if re.search(r'\b(open|launch|start)\s+(.+)', command_lower):
            app = re.search(r'\b(?:open|launch|start)\s+(.+)', command_lower).group(1).strip()
            self._handle_open_app(app)
        elif re.search(r'\b(click|press|tap)\s+', command_lower):
            self._handle_click_command(command)
        elif re.search(r'\btype\s+', command_lower):
            self._handle_type_command(command)
        elif re.search(r'\bsearch\s+(youtube|google|github|amazon)\s+(.+)', command_lower):
            platform = re.search(r'\bsearch\s+(youtube|google|github|amazon)\s+(.+)', command_lower)
            self._handle_search(platform.group(1), platform.group(2))
        elif re.search(r'\b(scroll|scroll down|scroll up)\b', command_lower):
            self._handle_scroll(command_lower)
        elif re.search(r'\b(screenshot|take screenshot|capture)\b', command_lower):
            self._handle_screenshot()
        elif re.search(r'\b(status|what are you doing|what\'s on screen)\b', command_lower):
            self._handle_status()
        elif re.search(r'\b(close|quit|exit)\s+(.+)\b', command_lower):
            app = re.search(r'\b(?:close|quit|exit)\s+(.+)', command_lower)
            if app:
                self._handle_close_app(app.group(1).strip())
        else:
            self._handle_unknown_command(command)

    def _handle_open_app(self, app: str):
        try:
            from tools.system_tools import open_app
            result = open_app(app)
            if "✅" in str(result) or "Opened" in str(result):
                self._speak_result(f"Opening {app}")
            else:
                self._speak_result(f"Could not open {app}")
        except Exception as e:
            logger.error("Voice open app failed: %s", e)
            self._speak_result(f"Failed to open {app}")

    def _handle_search(self, platform: str, query: str):
        urls = {
            "youtube": f"https://youtube.com/results?search_query={query.replace(' ', '+')}",
            "google": f"https://google.com/search?q={query.replace(' ', '+')}",
            "github": f"https://github.com/search?q={query.replace(' ', '+')}",
            "amazon": f"https://amazon.com/s?k={query.replace(' ', '+')}",
        }
        url = urls.get(platform, f"https://google.com/search?q={query.replace(' ', '+')}")
        try:
            import subprocess
            subprocess.Popen(["xdg-open", url])
            self._speak_result(f"Searching {platform} for {query}")
        except Exception as e:
            logger.error("Voice search failed: %s", e)
            self._speak_result(f"Could not open browser")

    def _handle_click_command(self, command: str):
        self._speak_result("Clicking. Please use the computer action tool for precise clicks.")

    def _handle_type_command(self, command: str):
        text = re.sub(r'\btype\s+', '', command, count=1)
        if self._agent:
            try:
                self._agent.execute_action({"type": "type_text", "text": text})
                self._speak_result(f"Typed text")
            except Exception:
                self._speak_result("Could not type")

    def _handle_scroll(self, command: str):
        dy = -3 if "up" in command else 3
        if self._agent:
            try:
                self._agent.execute_action({"type": "scroll", "dy": dy})
            except Exception:
                pass
        self._speak_result(f"Scrolling {'up' if dy < 0 else 'down'}")

    def _handle_screenshot(self):
        try:
            from backend.computer_use.vision.screen_capture import ScreenCapture
            sc = ScreenCapture(self.config)
            path = sc.save_screenshot("voice_capture")
            if path:
                self._speak_result(f"Screenshot saved")
        except Exception:
            self._speak_result("Could not capture screenshot")

    def _handle_status(self):
        try:
            obs = self._agent.observe() if self._agent else {}
            window = (obs.get("active_window") or {}).get("title", "Unknown")
            elements = len(obs.get("elements", []))
            self._speak_result(f"Active window is {window}. Detected {elements} UI elements.")
        except Exception:
            self._speak_result("Could not get desktop status")

    def _handle_close_app(self, app: str):
        try:
            from tools.system_tools import close_app
            close_app(app)
            self._speak_result(f"Closing {app}")
        except Exception:
            self._speak_result(f"Could not close {app}")

    def _handle_unknown_command(self, command: str):
        self._speak_result("I did not understand that command")

    def _speak_result(self, text: str):
        logger.info("Voice response: %s", text)
        if self._speak:
            try:
                self._speak(text)
            except Exception as e:
                logger.debug("TTS failed: %s", e)
