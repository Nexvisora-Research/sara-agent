"""
Voice Assistant Platform Adapter.

Connects Sara Agent to the Voice Gateway (FastAPI server), enabling
voice-controlled interaction through Flutter and native mobile/desktop apps.

The adapter:
- Acts as the bridge between the gateway runner and the voice gateway process
- Manages virtual sessions for voice assistant devices
- Routes incoming voice commands through the standard message pipeline
- Supports wake-word triggered and push-to-talk modes
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    SendResult,
)
from gateway.session import SessionSource, build_session_key

logger = logging.getLogger(__name__)

__all__ = ["VoiceAssistantAdapter", "check_voice_assistant_requirements"]

DEFAULT_VOICE_GATEWAY_HOST = "127.0.0.1"
DEFAULT_VOICE_GATEWAY_PORT = 8765

MAX_MESSAGE_LENGTH = 4096


def check_voice_assistant_requirements() -> bool:
    """Check dependencies for the voice assistant platform."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        import httpx  # noqa: F401
        return True
    except ImportError:
        logger.warning(
            "Voice Assistant: fastapi/uvicorn/httpx not installed. "
            "Run: pip install fastapi uvicorn httpx"
        )
        return False


class VoiceAssistantAdapter(BasePlatformAdapter):
    """Adapter for the Sara Voice Assistant platform.

    Manages virtual device sessions that represent connected Flutter/native
    voice assistant clients. Routes messages through the standard gateway
    pipeline for processing.
    """

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.VOICE_ASSISTANT)
        self._gateway_host = config.extra.get(
            "voice_gateway_host",
            os.getenv("VOICE_GATEWAY_HOST", DEFAULT_VOICE_GATEWAY_HOST),
        )
        self._gateway_port = int(
            config.extra.get(
                "voice_gateway_port",
                os.getenv("VOICE_GATEWAY_PORT", str(DEFAULT_VOICE_GATEWAY_PORT)),
            )
        )
        self._api_key = config.token or config.extra.get("api_key", "")
        self._max_message_length = int(
            config.extra.get("max_message_length", MAX_MESSAGE_LENGTH)
        )
        self._devices: Dict[str, dict] = {}
        self._sessions: Dict[str, str] = {}
        self._health_task: Optional[asyncio.Task] = None

        # Settings from config
        self._default_tts = config.extra.get("tts_enabled", True)
        self._default_wake_word = config.extra.get("wake_word_enabled", True)
        self._default_stt_language = config.extra.get("stt_language", "en")

    @property
    def name(self) -> str:
        return "Voice Assistant"

    @property
    def gateway_url(self) -> str:
        return f"http://{self._gateway_host}:{self._gateway_port}"

    # ------------------------------------------------------------------
    # BasePlatformAdapter required methods
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Start the voice gateway server and mark as connected."""
        self._mark_connected()
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info(
            "Voice Assistant adapter connected (gateway: %s)",
            self.gateway_url,
        )
        return True

    async def disconnect(self) -> None:
        """Disconnect and clean up."""
        if self._health_task:
            self._health_task.cancel()
            self._health_task = None
        self._mark_disconnected()
        logger.info("Voice Assistant adapter disconnected")

    async def send(
        self,
        chat_id: str,
        text: str,
        **kwargs,
    ) -> SendResult:
        """Send a text message to a voice assistant device."""
        device_id = self._resolve_device_id(chat_id)
        if not device_id:
            return SendResult(
                success=False,
                error=f"Unknown device for chat_id: {chat_id}",
            )

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.gateway_url}/v1/command",
                    json={
                        "text": text,
                        "device_id": device_id,
                        "channel_id": chat_id,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                result = resp.json()
                return SendResult(
                    success=True,
                    message_id=result.get("id", str(uuid.uuid4())),
                )
        except httpx.TimeoutException:
            return SendResult(
                success=False,
                error="Voice gateway timed out",
                retryable=True,
            )
        except Exception as e:
            return SendResult(
                success=False,
                error=str(e),
                retryable=True,
            )

    async def send_typing(self, chat_id: str) -> None:
        """Send typing indicator to the device.

        Voice gateway translates this into a visual listening indicator.
        """
        device_id = self._resolve_device_id(chat_id)
        if not device_id:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"{self.gateway_url}/v1/command",
                    json={
                        "text": "",
                        "device_id": device_id,
                        "channel_id": chat_id,
                    },
                    headers=self._headers(),
                    timeout=3,
                )
        except Exception:
            pass

    async def send_voice(self, chat_id: str, audio_path: str) -> SendResult:
        """Send a voice (audio) message to the device."""
        device_id = self._resolve_device_id(chat_id)
        if not device_id:
            return SendResult(
                success=False,
                error=f"Unknown device for chat_id: {chat_id}",
            )
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/v1/voice/synthesize",
                    data={
                        "text": "",
                        "voice": self._default_tts,
                    },
                    files={"file": ("audio.opus", audio_data, "audio/opus")},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> SendResult:
        """Send an image to the device (shown in chat UI)."""
        device_id = self._resolve_device_id(chat_id)
        if not device_id:
            return SendResult(
                success=False,
                error=f"Unknown device for chat_id: {chat_id}",
            )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.gateway_url}/v1/command",
                    json={
                        "text": f"{caption or ''} [Image: {image_url}]",
                        "device_id": device_id,
                        "channel_id": chat_id,
                    },
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return SendResult(success=True)
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def get_chat_info(self, chat_id: str) -> dict:
        """Get info about a voice assistant device session."""
        device_id = self._resolve_device_id(chat_id)
        return {
            "name": f"Voice Device {device_id or chat_id[:8]}",
            "type": "voice_assistant",
            "chat_id": chat_id,
        }

    # ------------------------------------------------------------------
    # Voice Assistant specific API
    # ------------------------------------------------------------------

    def register_device(
        self,
        device_id: str,
        user_id: str = "",
        device_name: str = "",
    ) -> str:
        """Register a connected device and return a virtual chat_id."""
        chat_id = f"voice_{device_id}"
        self._devices[device_id] = {
            "chat_id": chat_id,
            "user_id": user_id or device_id,
            "device_name": device_name or device_id,
            "registered_at": time.time(),
            "last_seen": time.time(),
        }
        self._sessions[chat_id] = device_id
        logger.info(
            "Registered voice device '%s' as chat '%s'",
            device_id,
            chat_id,
        )
        return chat_id

    def unregister_device(self, device_id: str) -> None:
        """Remove a device registration."""
        info = self._devices.pop(device_id, None)
        if info:
            self._sessions.pop(info["chat_id"], None)
            logger.info("Unregistered voice device '%s'", device_id)

    def get_device(self, device_id: str) -> Optional[dict]:
        """Get device info by device_id."""
        return self._devices.get(device_id)

    def get_device_by_chat(self, chat_id: str) -> Optional[dict]:
        """Get device info by chat_id."""
        device_id = self._sessions.get(chat_id)
        if device_id:
            return self._devices.get(device_id)
        return None

    def get_connected_devices(self) -> List[dict]:
        """Return list of all connected device infos."""
        return list(self._devices.values())

    def _resolve_device_id(self, chat_id: str) -> Optional[str]:
        """Resolve a chat_id to a device_id."""
        if chat_id in self._sessions:
            return self._sessions[chat_id]
        for device_id, info in self._devices.items():
            if info["chat_id"] == chat_id:
                return device_id
        return None

    def build_source(self, device_id: str, user_id: str = "") -> SessionSource:
        """Build a SessionSource for a voice assistant device."""
        return SessionSource(
            platform=self.platform,
            platform_id=f"voice_{device_id}",
            user_id=user_id or device_id,
            chat_id=f"voice_{device_id}",
            chat_type="dm",
        )

    def build_session_key(self, device_id: str, user_id: str = "") -> str:
        """Build a deterministic session key for a device."""
        source = self.build_source(device_id, user_id)
        return build_session_key(
            platform=source.platform,
            chat_id=str(source.chat_id),
            user_id=str(source.user_id),
        )

    async def dispatch_voice_input(
        self,
        device_id: str,
        text: str,
        user_id: str = "",
    ) -> Optional[str]:
        """Dispatch transcribed voice input through the gateway pipeline.

        Called by the voice gateway when audio is transcribed to text.
        Routes through the standard message handler for processing.
        """
        source = self.build_source(device_id, user_id)
        event = MessageEvent(
            text=text,
            message_type=MessageType.TEXT,
            source=source,
            message_id=str(uuid.uuid4()),
        )
        if self._message_handler:
            try:
                response = await self._message_handler(event)
                return str(response) if response else None
            except Exception as e:
                logger.error(
                    "Message handler failed for device '%s': %s",
                    device_id,
                    e,
                )
                return None
        return None

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _health_check_loop(self) -> None:
        """Periodically check the voice gateway health."""
        while True:
            await asyncio.sleep(30)
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{self.gateway_url}/v1/health")
                    if resp.status_code == 200:
                        self._mark_connected()
                    else:
                        logger.warning(
                            "Voice gateway health check failed: %d",
                            resp.status_code,
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Voice gateway health check: %s", e)
