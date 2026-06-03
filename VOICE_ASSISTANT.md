# Sara Voice Assistant

Voice-controlled interface for Sara Agent with wake word detection,
native mobile/desktop apps, and background listening.

## Architecture

```
┌─────────────────────┐     WebSocket      ┌──────────────────────┐
│   Flutter App       │ ◄───────────────── │   Voice Gateway      │
│   (Mobile/Desktop)  │     REST + Audio   │   (FastAPI Server)   │
│                     │                    │                      │
│  ┌───────────────┐  │                    │  ┌────────────────┐  │
│  │Wake Word      │  │                    │  │STT (Whisper)   │  │
│  │Detection      │  │                    │  │TTS (Edge-TTS)  │  │
│  └───────────────┘  │                    │  └────────────────┘  │
│  ┌───────────────┐  │                    │         │            │
│  │Audio Recording│  │                    │  ┌────────────────┐  │
│  │& Playback     │  │                    │  │Sara Bridge     │  │
│  └───────────────┘  │                    │  │(process_turn)  │  │
│  ┌───────────────┐  │                    │  └────────────────┘  │
│  │Background     │  │                    │         │            │
│  │Service        │  │                    │         ▼            │
│  └───────────────┘  │                    │  ┌────────────────┐  │
└─────────────────────┘                    │  │Sara Gateway   │  │
                                           │  │Platform Adapter│  │
                                           │  └────────────────┘  │
                                           └──────────────────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │  Sara Agent      │
                                           │  (process_turn)  │
                                           └──────────────────┘
```

## Components

### 1. Voice Gateway (`voice_gateway/`)
FastAPI server that bridges Flutter apps to Sara Agent.

**Endpoints:**
- `WS /ws/{device_id}` — Real-time bidirectional audio/text streaming
- `POST /v1/command` — Send text commands to Sara
- `POST /v1/voice/transcribe` — Speech-to-text (Whisper)
- `POST /v1/voice/synthesize` — Text-to-speech (Edge-TTS)
- `GET /v1/health` — Health check
- `POST /v1/settings/{device_id}` — Update device settings
- `GET /v1/capabilities` — Device capabilities

### 2. Platform Adapter (`gateway/platforms/voice_assistant.py`)
Registers "voice_assistant" as a first-class Sara platform.

- Inherits `BasePlatformAdapter`
- Manages virtual device sessions
- Routes voice input through standard `process_turn()` pipeline
- Supports send/send_voice/send_image/send_typing

### 3. Flutter App (`sara_app/`)
Cross-platform mobile/desktop frontend.

**Features:**
- Wake word detection (Picovoice Porcupine + energy-based fallback)
- Push-to-talk and hands-free voice modes
- Real-time audio visualization
- Chat history with message bubbles
- Text-to-speech for responses
- Background service (Android Foreground Service / iOS Audio Background)
- Connection status indicator
- Full settings panel (server URL, TTS, STT, sensitivity)

### 4. Wake Word Detection (`sara_app/lib/services/wake_word_service.dart`)
- Primary: Picovoice Porcupine (on-device, low latency)
- Fallback: Energy-based voice activity detection
- Configurable sensitivity
- Cooldown period to prevent re-triggering

## Setup

### Prerequisites
```bash
# Python dependencies
pip install fastapi uvicorn httpx pydantic python-multipart

# Optional: Local STT
pip install openai-whisper  # or: pip install faster-whisper

# Optional: Local TTS
pip install edge-tts
```

### Environment Variables
```bash
# Enable the voice assistant platform
export VOICE_ASSISTANT_ENABLED=true

# Voice gateway host/port (defaults: 127.0.0.1:8765)
export VOICE_GATEWAY_HOST=127.0.0.1
export VOICE_GATEWAY_PORT=8765

# Features
export VOICE_ASSISTANT_TTS=true
export VOICE_ASSISTANT_WAKE_WORD=true
export VOICE_ASSISTANT_STT_LANGUAGE=en

# Home channel (optional)
export VOICE_ASSISTANT_HOME_CHANNEL=default
```

For voice input, configure at least one STT provider. The simplest local path is:

```bash
source .venv/bin/activate
pip install faster-whisper
```

You can also use Sara's normal STT provider settings, such as
`sara_LOCAL_STT_COMMAND`, `GROQ_API_KEY`, `VOICE_TOOLS_OPENAI_KEY`,
`MISTRAL_API_KEY`, or `XAI_API_KEY`.

### Start the Voice Gateway
```bash
# Standalone
python -m voice_gateway.main

# Or via the Sara gateway (auto-starts with platform adapter)
sara gateway start
```

### Flutter App
```bash
cd sara_app

bash tool/setup_platforms.sh doctor
flutter run
```

If Linux fails with a missing `gtk+-3.0` CMake package, install the Linux
desktop headers. Linux microphone recording also needs `parecord`, provided
by `pulseaudio-utils` on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev mesa-utils pulseaudio-utils
```

For Android and macOS setup details, see `sara_app/README.md`.

## WebSocket Protocol

### Client → Server
```json
// Text message
{"type": "text", "text": "what's the weather?"}

// Audio chunk (binary PCM16 frames)
// Followed by:
{"type": "audio_end"}

// Wake word triggered
{"type": "wakeword", "triggered": true}

// State update
{"type": "state", "state": "listening"}

// Settings update
{"type": "settings", "settings": {"tts_enabled": true}}
```

### Server → Client
```json
// Connection established
{"type": "connected", "device_id": "...", "capabilities": {...}}

// State change
{"type": "state_change", "state": "processing", "detail": "..."}

// Transcription result
{"type": "transcription", "text": "what's the weather?"}

// Response message
{"type": "message", "text": "It's 72°F and sunny.", "is_final": true}

// Audio response (binary Opus frames)

// Error
{"type": "error", "message": "..."}

// Health
{"type": "pong"}
```

## Commands
- `/voice on` — Enable voice reply mode
- `/voice off` — Disable voice reply mode
- `/voice tts` — TTS for all messages
- `/voice status` — Show current voice mode

## Tool Integration
The voice assistant platform is fully integrated with:
- **send_message tool** — Send messages to voice devices
- **cron scheduler** — Deliver scheduled messages
- **gateway auth** — Allowlist support via `VOICE_ASSISTANT_ALLOWED_USERS`
- **system prompt** — Platform hints for concise TTS-friendly responses
