"""
tools/media_tools.py — Media & Volume Controls for Sara AI.

Uses pynput for media keys and amixer/pactl for Linux volume control.
Requires: pip install pynput
System:   amixer (alsa-utils) or pactl (pulseaudio/pipewire)

Functions:
  media_play_pause()  — Toggle play/pause
  media_next()        — Next track
  media_prev()        — Previous track
  set_volume(level)   — Set volume 0–100
  get_volume()        — Get current volume
  mute_volume()       — Mute
  unmute_volume()     — Unmute
"""

import logging
import subprocess
import time

logger = logging.getLogger(__name__)


# ── Subprocess helper ─────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
    """Run a shell command. Returns (success, stdout/stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except Exception as e:
        return False, str(e)


# ── Detect volume backend ─────────────────────────────────────────────────────

def _get_backend() -> str:
    """Returns 'pactl', 'amixer', or 'none'."""
    ok, _ = _run(["which", "pactl"])
    if ok:
        return "pactl"
    ok, _ = _run(["which", "amixer"])
    if ok:
        return "amixer"
    return "none"


# ── Media key helpers ─────────────────────────────────────────────────────────

def _press_media_key(key_name: str) -> bool:
    """Press a media key using pynput. Returns True on success."""
    try:
        from pynput.keyboard import Key, Controller
        kb = Controller()
        key_map = {
            "play_pause": Key.media_play_pause,
            "next":       Key.media_next,
            "prev":       Key.media_previous,
            "mute":       Key.media_volume_mute,
        }
        key = key_map.get(key_name)
        if key is None:
            return False
        kb.press(key)
        time.sleep(0.05)
        kb.release(key)
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.warning(f"pynput key error: {e}")
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def media_play_pause(unused: str = "") -> str:
    """Toggle play/pause on the current media player."""
    if _press_media_key("play_pause"):
        return "⏯️ Play/Pause toggled."
    return "❌ Could not send media key. Run: `pip install pynput`"


def media_next(unused: str = "") -> str:
    """Skip to the next track."""
    if _press_media_key("next"):
        return "⏭️ Skipped to next track."
    return "❌ Could not send next-track key. Run: `pip install pynput`"


def media_prev(unused: str = "") -> str:
    """Go back to the previous track."""
    if _press_media_key("prev"):
        return "⏮️ Went to previous track."
    return "❌ Could not send previous-track key. Run: `pip install pynput`"


def set_volume(level: str) -> str:
    """
    Set system volume to a level 0–100.
    Input: number e.g. '50' or '0' (mute) or '100' (max)
    Uses pactl (PulseAudio/PipeWire) or amixer (ALSA) as fallback.
    """
    level = str(level).strip().rstrip("%")
    try:
        vol = max(0, min(100, int(level)))
    except ValueError:
        return f"❓ Invalid volume level: '{level}'. Use a number 0–100."

    backend = _get_backend()

    if backend == "pactl":
        ok, err = _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{vol}%"])
        if ok:
            return f"🔊 Volume set to **{vol}%**."
        return f"❌ pactl error: {err}"

    if backend == "amixer":
        ok, err = _run(["amixer", "-q", "sset", "Master", f"{vol}%"])
        if ok:
            return f"🔊 Volume set to **{vol}%**."
        return f"❌ amixer error: {err}"

    return "❌ No volume backend found. Install `pulseaudio-utils` or `alsa-utils`."


def get_volume(unused: str = "") -> str:
    """Get the current system volume level."""
    backend = _get_backend()

    if backend == "pactl":
        ok, out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        if ok:
            # Parse e.g. "Volume: front-left: 65536 /  100% / ..."
            import re
            match = re.search(r"(\d+)%", out)
            vol = match.group(1) if match else "?"

            ok2, mute_out = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
            muted = ok2 and "yes" in mute_out.lower()
            mute_str = " 🔇 (Muted)" if muted else ""
            return f"🔊 Current volume: **{vol}%**{mute_str}"
        return f"❌ pactl error: {out}"

    if backend == "amixer":
        ok, out = _run(["amixer", "sget", "Master"])
        if ok:
            import re
            match = re.search(r"\[(\d+)%\]", out)
            vol = match.group(1) if match else "?"
            muted = "[off]" in out
            mute_str = " 🔇 (Muted)" if muted else ""
            return f"🔊 Current volume: **{vol}%**{mute_str}"
        return f"❌ amixer error: {out}"

    return "❌ No volume backend found. Install `pulseaudio-utils` or `alsa-utils`."


def mute_volume(unused: str = "") -> str:
    """Mute the system audio."""
    backend = _get_backend()

    if backend == "pactl":
        ok, err = _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])
        if ok:
            return "🔇 Audio muted."
        return f"❌ pactl error: {err}"

    if backend == "amixer":
        ok, err = _run(["amixer", "-q", "sset", "Master", "mute"])
        if ok:
            return "🔇 Audio muted."
        return f"❌ amixer error: {err}"

    # Fallback: media key
    if _press_media_key("mute"):
        return "🔇 Mute toggled."
    return "❌ Could not mute. Install `pulseaudio-utils` or `alsa-utils`."


def unmute_volume(unused: str = "") -> str:
    """Unmute the system audio."""
    backend = _get_backend()

    if backend == "pactl":
        ok, err = _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
        if ok:
            return "🔊 Audio unmuted."
        return f"❌ pactl error: {err}"

    if backend == "amixer":
        ok, err = _run(["amixer", "-q", "sset", "Master", "unmute"])
        if ok:
            return "🔊 Audio unmuted."
        return f"❌ amixer error: {err}"

    if _press_media_key("mute"):
        return "🔊 Mute toggled (unmuted)."
    return "❌ Could not unmute. Install `pulseaudio-utils` or `alsa-utils`."