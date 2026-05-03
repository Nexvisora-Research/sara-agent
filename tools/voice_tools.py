"""
tools/voice_tools.py — Voice Input (Speech-to-Text) for Sara AI.

Uses SpeechRecognition with Google STT (free, no API key needed for basic use).
Requires: pip install SpeechRecognition pyaudio

Functions:
  listen_mic(duration)     — Record from mic and return transcribed text
  list_audio_devices()     — List available audio input devices
"""

import logging

logger = logging.getLogger(__name__)


def listen_mic(duration: str = "5") -> str:
    """
    Listen to the microphone and transcribe speech to text.
    Input: duration in seconds (default 5). Example: '5' or '10'
    Requires: pip install SpeechRecognition pyaudio
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return (
            "❌ SpeechRecognition not installed.\n"
            "Run: `pip install SpeechRecognition pyaudio`"
        )

    # Parse duration
    try:
        secs = max(1, min(int(str(duration).strip() or "5"), 30))
    except ValueError:
        secs = 5

    r = sr.Recognizer()
    r.pause_threshold = 1.0
    r.energy_threshold = 300

    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=secs + 2, phrase_time_limit=secs)

        # Try Google STT (free, online)
        try:
            text = r.recognize_google(audio)
            logger.info(f"Voice transcribed: {text!r}")
            return f"🎤 You said: \"{text}\""
        except sr.UnknownValueError:
            return "🎤 Could not understand audio. Please speak clearly."
        except sr.RequestError as e:
            # Fallback: try offline Sphinx if available
            try:
                text = r.recognize_sphinx(audio)
                return f"🎤 (offline) You said: \"{text}\""
            except Exception:
                return f"❌ Google STT failed: {e}. Check your internet connection."

    except sr.WaitTimeoutError:
        return "⌛ No speech detected within the time limit. Try speaking sooner."
    except OSError as e:
        if "pyaudio" in str(e).lower() or "portaudio" in str(e).lower():
            return (
                "❌ PyAudio / PortAudio not found.\n"
                "Linux: install PortAudio first, then reinstall PyAudio.\n"
                "Try: `sudo apt install portaudio19-dev` (Debian/Ubuntu)\n"
                "Then: `pip install pyaudio`"
            )
        return f"❌ Microphone error: {e}"
    except Exception as e:
        return f"❌ Voice input error: {e}"


def list_audio_devices(unused: str = "") -> str:
    """List all available audio input (microphone) devices."""
    try:
        import speech_recognition as sr
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list:
            return "🎙️ No microphones found."
        lines = "\n".join(f"  [{i}] {name}" for i, name in enumerate(mic_list))
        return f"🎙️ Available microphones:\n{lines}"
    except ImportError:
        return "❌ SpeechRecognition not installed. Run: `pip install SpeechRecognition pyaudio`"
    except Exception as e:
        return f"❌ Could not list devices: {e}"
