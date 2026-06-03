"""
Voice Gateway - FastAPI server bridging Flutter voice assistant to Sara Agent.

Architecture:
  Flutter App ──WebSocket──> Voice Gateway ──process_turn()──> Sara Agent
                                        ──Platform Adapter──> Gateway Runner

Endpoints:
  - WS /ws/{device_id}          Real-time audio streaming + bidirectional messages
  - POST /v1/voice/transcribe   Transcribe audio file to text
  - POST /v1/voice/synthesize   Synthesize text to speech audio
  - POST /v1/command            Send a text command to Sara
  - GET  /v1/health             Health check
  - GET  /v1/capabilities       Device capabilities & config
  - POST /v1/settings           Update device settings
  - GET  /v1/settings           Get device settings
  - POST /v1/wakeword/register  Register a wake word model
  - POST /v1/wakeword/trigger   Manually trigger wake word
"""

import asyncio
import inspect
import json
import logging
import os
import wave
from io import BytesIO
import tempfile
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SARA_GATEWAY_URL = os.getenv("SARA_GATEWAY_URL", "http://127.0.0.1:8642")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Capabilities(BaseModel):
    stt: bool = True
    tts: bool = True
    wake_word: bool = True
    streaming: bool = True
    push_to_talk: bool = True
    auto_reconnect: bool = True
    supported_audio_formats: List[str] = ["pcm16", "opus", "mp3", "wav"]
    sample_rate: int = 16000
    frame_duration_ms: int = 20
    tts_voices: List[str] = ["default"]
    wake_word_models: List[str] = ["sara", "hey_sara"]

class DeviceSettings(BaseModel):
    device_id: str = ""
    wake_word_enabled: bool = True
    wake_word_model: str = "sara"
    tts_enabled: bool = True
    tts_voice: str = "default"
    tts_speed: float = 1.0
    stt_language: str = "en"
    auto_send_voice: bool = True
    push_to_talk: bool = False
    sensitivity: float = 0.5
    mute_while_processing: bool = True
    background_listening: bool = True
    home_channel_id: str = "default"

class CommandRequest(BaseModel):
    text: str
    device_id: str = ""
    channel_id: str = "default"

class CommandResponse(BaseModel):
    status: str
    text: str
    audio: Optional[str] = None
    action: Optional[str] = None

class SettingsUpdate(BaseModel):
    wake_word_enabled: Optional[bool] = None
    wake_word_model: Optional[str] = None
    tts_enabled: Optional[bool] = None
    tts_voice: Optional[str] = None
    tts_speed: Optional[float] = None
    stt_language: Optional[str] = None
    auto_send_voice: Optional[bool] = None
    push_to_talk: Optional[bool] = None
    sensitivity: Optional[float] = None
    background_listening: Optional[bool] = None
    home_channel_id: Optional[str] = None

class WakeWordRegister(BaseModel):
    model_id: str
    model_data: str  # base64 encoded model
    labels: List[str] = ["sara"]

# ---------------------------------------------------------------------------
# STT / TTS helpers
# ---------------------------------------------------------------------------

class AudioProcessor:
    """Handles speech-to-text and text-to-speech using Sara's brain or fallback."""

    def __init__(self):
        self._stt_available = False
        self._tts_available = False
        self._whisper_model = None
        self._check_capabilities()

    def _check_capabilities(self):
        try:
            import whisper
            self._stt_available = True
        except ImportError:
            logger.info("whisper not installed, STT will use Sara STT providers")
        try:
            import edge_tts
            self._tts_available = True
        except ImportError:
            logger.info("edge-tts not installed, TTS will use HTTP fallback")

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        if self._stt_available:
            return await self._transcribe_local(audio_data, sample_rate)
        return await self._transcribe_sara_tools(audio_data, sample_rate)

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
    ) -> bytes:
        if self._tts_available:
            return await self._synthesize_local(text, voice, speed)
        return await self._synthesize_http(text, voice, speed)

    async def _transcribe_local(self, audio_data: bytes, sample_rate: int) -> str:
        import whisper
        import numpy as np
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")
        audio_np = self._audio_bytes_to_float32(audio_data, sample_rate)
        result = self._whisper_model.transcribe(audio_np, language="en")
        return result["text"].strip()

    async def _transcribe_sara_tools(
        self,
        audio_data: bytes,
        sample_rate: int,
    ) -> str:
        wav_data = self._ensure_wav_bytes(audio_data, sample_rate)

        def run_transcription() -> str:
            from tools.transcription_tools import transcribe_audio

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_data)
                wav_path = f.name
            try:
                result = transcribe_audio(wav_path)
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

            if not result.get("success"):
                error = result.get("error") or "No speech-to-text provider available"
                raise RuntimeError(error)
            return (result.get("transcript") or "").strip()

        try:
            return await asyncio.to_thread(run_transcription)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Speech-to-text failed: {e}") from e

    def _audio_bytes_to_float32(self, audio_data: bytes, sample_rate: int):
        import numpy as np

        pcm = audio_data
        if audio_data.startswith(b"RIFF"):
            with wave.open(BytesIO(audio_data), "rb") as wav:
                sample_width = wav.getsampwidth()
                channels = wav.getnchannels()
                pcm = wav.readframes(wav.getnframes())
            if sample_width != 2:
                raise ValueError("Only 16-bit PCM WAV audio is supported")
            audio_np = np.frombuffer(pcm, dtype=np.int16)
            if channels > 1:
                audio_np = (
                    audio_np.reshape(-1, channels)
                    .mean(axis=1)
                    .astype(np.int16)
                )
            return audio_np.astype(np.float32) / 32768.0

        return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

    def _ensure_wav_bytes(self, audio_data: bytes, sample_rate: int = 16000) -> bytes:
        if audio_data.startswith(b"RIFF"):
            return audio_data
        out = BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(audio_data)
        return out.getvalue()

    async def _synthesize_local(self, text: str, voice: str, speed: float) -> bytes:
        import edge_tts
        voice_map = {"default": "en-US-AriaNeural", "male": "en-US-GuyNeural"}
        voice_name = voice_map.get(voice, "en-US-AriaNeural")
        communicate = edge_tts.Communicate(
            text,
            voice_name,
            rate=f"{int((speed - 1) * 100):+d}%",
        )
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    async def _synthesize_http(self, text: str, voice: str, speed: float) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SARA_GATEWAY_URL}/v1/audio/speech",
                json={
                    "input": text,
                    "voice": voice,
                    "speed": speed,
                    "response_format": "opus",
                },
            )
            resp.raise_for_status()
            return resp.content


audio_processor = AudioProcessor()

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

class DeviceConnection:
    """Represents a connected Flutter device."""

    def __init__(self, device_id: str, websocket: WebSocket):
        self.device_id = device_id
        self.websocket = websocket
        self.state = ConnectionState.IDLE
        self.settings = DeviceSettings(device_id=device_id)
        self.audio_buffer = bytearray()
        self.connected_at = time.time()
        self.last_activity = time.time()
        self.user_id: Optional[str] = None

    async def send_json(self, data: dict):
        try:
            await self.websocket.send_json(data)
        except Exception:
            logger.error("Failed to send to device %s", self.device_id)

    async def send_audio(self, audio_data: bytes, format: str = "opus"):
        try:
            await self.websocket.send_bytes(audio_data)
        except Exception:
            logger.error("Failed to send audio to device %s", self.device_id)

    async def send_message(self, text: str, is_final: bool = True):
        await self.send_json({
            "type": "message",
            "text": text,
            "is_final": is_final,
            "state": self.state.value,
        })

    async def send_state(self, state: ConnectionState, detail: str = ""):
        self.state = state
        await self.send_json({
            "type": "state_change",
            "state": state.value,
            "detail": detail,
        })

class ConnectionManager:
    """Manages all connected Flutter devices."""

    def __init__(self):
        self._connections: Dict[str, DeviceConnection] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_id: str, ws: WebSocket) -> DeviceConnection:
        async with self._lock:
            conn = DeviceConnection(device_id, ws)
            self._connections[device_id] = conn
            logger.info("Device '%s' connected (total: %d)", device_id, len(self._connections))
            return conn

    async def unregister(self, device_id: str):
        async with self._lock:
            self._connections.pop(device_id, None)
            logger.info("Device '%s' disconnected (total: %d)", device_id, len(self._connections))

    def get(self, device_id: str) -> Optional[DeviceConnection]:
        return self._connections.get(device_id)

    def get_all(self) -> List[DeviceConnection]:
        return list(self._connections.values())

    async def broadcast(self, data: dict):
        for conn in self.get_all():
            await conn.send_json(data)

manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Sara Agent integration
# ---------------------------------------------------------------------------

class SaraBridge:
    """Bridge between Voice Gateway and Sara Agent's process_turn()."""

    def __init__(self):
        self._agent_loop = None
        self._gateway_client = httpx.AsyncClient(base_url=SARA_GATEWAY_URL, timeout=30)
        self._session_cache: Dict[str, str] = {}

    async def process_command(
        self,
        text: str,
        device_id: str = "",
        channel_id: str = "default",
    ) -> CommandResponse:
        try:
            from agent.agent_loop import process_turn
            result = process_turn(
                user_id=f"voice_{device_id}" if device_id else "voice_user",
                user_input=text,
                channel="voice_assistant",
            )
            if inspect.isawaitable(result):
                result = await result
            response_text = (
                result.render_text()
                if hasattr(result, "render_text")
                else getattr(result, "final_text", str(result))
            )
            return CommandResponse(
                status="success",
                text=response_text,
                action=getattr(result, "action", None),
            )
        except ImportError:
            return await self._process_via_gateway(text, device_id, channel_id)
        except Exception as e:
            logger.error("process_turn failed: %s", e)
            return CommandResponse(status="error", text=f"Sorry, I encountered an error: {e}")

    async def _process_via_gateway(self, text: str, device_id: str, channel_id: str) -> CommandResponse:
        try:
            resp = await self._gateway_client.post(
                "/v1/chat/completions",
                json={
                    "model": "sara-agent",
                    "messages": [{"role": "user", "content": text}],
                    "user": f"voice_{device_id}" if device_id else "voice_user",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return CommandResponse(status="success", text=content)
        except Exception as e:
            logger.error("Gateway call failed: %s", e)
            return CommandResponse(status="error", text=f"Gateway error: {e}")

    async def cleanup(self):
        await self._gateway_client.aclose()


sara_bridge = SaraBridge()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Sara Voice Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("Voice Gateway starting on %s:%s", DEFAULT_HOST, DEFAULT_PORT)


@app.on_event("shutdown")
async def shutdown():
    await sara_bridge.cleanup()
    logger.info("Voice Gateway shutdown complete")


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health")
async def health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "devices_connected": len(manager.get_all()),
        "stt_available": audio_processor._stt_available,
        "tts_available": audio_processor._tts_available,
    }


@app.get("/v1/capabilities")
async def capabilities():
    return Capabilities()


@app.post("/v1/command")
async def send_command(req: CommandRequest):
    resp = await sara_bridge.process_command(
        text=req.text,
        device_id=req.device_id,
        channel_id=req.channel_id,
    )
    if resp.status == "success" and resp.text:
        conn = manager.get(req.device_id) if req.device_id else None
        if conn and conn.settings.tts_enabled:
            audio = await audio_processor.synthesize(
                resp.text,
                voice=conn.settings.tts_voice,
                speed=conn.settings.tts_speed,
            )
            resp.audio = audio.hex()
    return resp


@app.post("/v1/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    data = await file.read()
    text = await audio_processor.transcribe(data)
    return {"text": text, "duration": len(data) / 32000}


@app.post("/v1/voice/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice: str = Form("default"),
    speed: float = Form(1.0),
):
    audio = await audio_processor.synthesize(text, voice, speed)
    from fastapi.responses import Response
    return Response(content=audio, media_type="audio/opus")


@app.get("/v1/settings/{device_id}")
async def get_settings(device_id: str):
    conn = manager.get(device_id)
    if not conn:
        return DeviceSettings(device_id=device_id).model_dump()
    return conn.settings.model_dump()


@app.post("/v1/settings/{device_id}")
async def update_settings(device_id: str, update: SettingsUpdate):
    conn = manager.get(device_id)
    if not conn:
        raise HTTPException(404, "Device not connected")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(conn.settings, field, value)
    return conn.settings.model_dump()


@app.post("/v1/wakeword/register")
async def register_wakeword(model: WakeWordRegister):
    path = Path(tempfile.gettempdir()) / f"wakeword_{model.model_id}.ppn"
    import base64
    path.write_bytes(base64.b64decode(model.model_data))
    return {"status": "ok", "path": str(path)}


@app.post("/v1/wakeword/trigger/{device_id}")
async def trigger_wakeword(device_id: str):
    conn = manager.get(device_id)
    if not conn:
        raise HTTPException(404, "Device not connected")
    await conn.send_json({"type": "wakeword", "triggered": True})
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket endpoint (main real-time channel)
# ---------------------------------------------------------------------------

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(ws: WebSocket, device_id: str):
    await ws.accept()
    conn = await manager.register(device_id, ws)

    try:
        await conn.send_json({
            "type": "connected",
            "device_id": device_id,
            "capabilities": {
                "stt": audio_processor._stt_available,
                "tts": audio_processor._tts_available,
                "streaming": True,
            },
            "settings": conn.settings.model_dump(),
        })

        while True:
            raw = await ws.receive()

            if raw["type"] == "websocket.disconnect":
                break

            if raw["type"] == "websocket.receive":
                content = raw.get("bytes") or raw.get("text")
                if content is None:
                    continue

                if isinstance(content, bytes):
                    await _handle_audio_chunk(conn, content)
                else:
                    await _handle_json_message(conn, content)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", device_id)
    except Exception as e:
        logger.error("WebSocket error for %s: %s", device_id, e)
    finally:
        await manager.unregister(device_id)


async def _handle_audio_chunk(conn: DeviceConnection, chunk: bytes):
    conn.audio_buffer.extend(chunk)
    conn.last_activity = time.time()

    if len(conn.audio_buffer) > 320000:  # ~10 seconds at 16kHz
        await _process_audio_buffer(conn)


async def _process_audio_buffer(conn: DeviceConnection):
    if not conn.audio_buffer:
        return

    await conn.send_state(ConnectionState.PROCESSING, "Transcribing...")
    audio_data = bytes(conn.audio_buffer)
    conn.audio_buffer.clear()

    try:
        text = await audio_processor.transcribe(audio_data)
        if not text.strip():
            await conn.send_state(ConnectionState.IDLE, "No speech detected")
            return

        await conn.send_json({"type": "transcription", "text": text})

        resp = await sara_bridge.process_command(
            text=text,
            device_id=conn.device_id,
            channel_id=conn.settings.home_channel_id,
        )

        if resp.status == "success" and resp.text:
            await conn.send_state(ConnectionState.SPEAKING, "Speaking...")
            if conn.settings.tts_enabled:
                audio = await audio_processor.synthesize(
                    resp.text,
                    voice=conn.settings.tts_voice,
                    speed=conn.settings.tts_speed,
                )
                await conn.send_audio(audio)
            await conn.send_message(resp.text)
        else:
            await conn.send_message(resp.text or "Sorry, I couldn't process that.")

    except Exception as e:
        logger.error("Audio processing failed: %s", e)
        await conn.send_json({"type": "error", "message": str(e)})
    finally:
        await conn.send_state(ConnectionState.IDLE)


async def _handle_json_message(conn: DeviceConnection, text: str):
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        await conn.send_json({"type": "error", "message": "Invalid JSON"})
        return

    msg_type = data.get("type", "")

    if msg_type == "ping":
        await conn.send_json({"type": "pong"})

    elif msg_type == "text":
        resp = await sara_bridge.process_command(
            text=data.get("text", ""),
            device_id=conn.device_id,
            channel_id=data.get("channel_id", conn.settings.home_channel_id),
        )
        if resp.status == "success" and resp.text:
            if conn.settings.tts_enabled and data.get("tts", True):
                audio = await audio_processor.synthesize(
                    resp.text,
                    voice=conn.settings.tts_voice,
                    speed=conn.settings.tts_speed,
                )
                await conn.send_audio(audio)
            await conn.send_message(resp.text)
        else:
            await conn.send_message(resp.text or "Error processing request")

    elif msg_type == "audio_end":
        await _process_audio_buffer(conn)

    elif msg_type == "settings":
        for field, value in data.get("settings", {}).items():
            if hasattr(conn.settings, field):
                setattr(conn.settings, field, value)
        await conn.send_json({"type": "settings_ack", "settings": conn.settings.model_dump()})

    elif msg_type == "wakeword":
        await conn.send_state(ConnectionState.LISTENING, "Wake word detected")
        # Start audio accumulation; audio chunks will follow

    elif msg_type == "state":
        if "state" in data:
            conn.state = ConnectionState(data["state"])
        await conn.send_json({"type": "state_ack", "state": conn.state.value})

    else:
        await conn.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start():
    import uvicorn
    host = os.getenv("VOICE_GATEWAY_HOST", DEFAULT_HOST)
    port = int(os.getenv("VOICE_GATEWAY_PORT", str(DEFAULT_PORT)))
    log_level = os.getenv("VOICE_GATEWAY_LOG_LEVEL", "info").lower()
    uvicorn.run(
        "voice_gateway.server:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=os.getenv("VOICE_GATEWAY_RELOAD", "").lower() == "true",
    )


if __name__ == "__main__":
    start()
