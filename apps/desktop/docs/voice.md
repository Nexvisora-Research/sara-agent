# Voice

Sara Desktop supports two voice modes: **dictation** (speech-to-text) and **full-duplex conversation** (listen → think → speak → loop).

## Requirements

- A microphone connected to your computer.
- An STT (speech-to-text) provider configured in **Settings → Voice**.
- Microphone permission granted to the app.

## Dictation Mode

Click the **microphone icon** (🎤) in the composer to start dictation. Speak, then click the stop button — your speech is transcribed and inserted into the composer as text.

Use cases:
- Hands-free text input
- Quick note taking
- Writing drafts

## Voice Conversation Mode

Click the **circular voice button** (AudioLines icon) next to the composer to start a full conversation:

1. **Listening** — Sara listens. A sound level indicator shows mic activity.
2. **Transcribing** — After a pause, your speech is transcribed.
3. **Thinking** — Sara processes your request and generates a response.
4. **Speaking** — Sara reads the response aloud.
5. **Loops** — Listening starts again automatically.

### Controls

| Action | How |
|--------|-----|
| Start conversation | Click the AudioLines button |
| End turn early | Click the square stop button (visible while listening) |
| Mute/Unmute mic | Click the mic icon during conversation |
| End conversation | Click the End button (red pill) |
| Space to stop | Press Space while listening to force end turn |

### Mute

While muted, you can still hear Sara's responses but your mic is off. Toggle mute to re-enter the listening loop.

## Providers

### Speech-to-Text (STT)

| Provider | Config Key | Notes |
|----------|------------|-------|
| Local (faster-whisper) | — | Works offline, no key needed |
| Groq | `GROQ_API_KEY` | Fast cloud transcription |
| OpenAI | `OPENAI_API_KEY` | GPT-compatible |
| Mistral | `MISTRAL_API_KEY` | — |
| xAI | `XAI_API_KEY` | — |
| ElevenLabs | `ELEVENLABS_API_KEY` | — |

### Text-to-Speech (TTS)

| Provider | Config Key | Notes |
|----------|------------|-------|
| Edge TTS | — | Free, works offline, natural voices |
| OpenAI | `OPENAI_API_KEY` | — |
| ElevenLabs | `ELEVENLABS_API_KEY` | Premium voices |
| xAI | `XAI_API_KEY` | — |
| Minimax | — | — |
| Mistral | — | — |
| Gemini | — | — |
| Neural TTS | — | Local neural synthesis |

## Configuration

Go to **Settings → Voice** to:
- Enable/disable STT
- Select STT and TTS providers
- Configure provider API keys
- Set max recording duration
- Enable auto-read (auto TTS for every response)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Microphone permission denied" | Grant mic access in your OS settings. On macOS: `tccutil reset Microphone com.nexvisoraresearch.Sara` |
| "No microphone found" | Check your mic is connected and not in use by another app |
| Transcription fails | Check your STT provider key is valid. Try a different provider |
| Playback fails | Check your TTS provider key. Try edge-tts (works without a key) |
| "Speech-to-text disabled" | Enable it in Settings → Voice |
