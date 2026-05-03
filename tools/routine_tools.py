"""
tools/routine_tools.py — Built-in and custom named desktop routines.
"""

from __future__ import annotations

import re

from memory.user_profile import (
    delete_custom_routine,
    get_custom_routine,
    get_custom_routines,
    save_custom_routine,
)

BUILTIN_ROUTINES: dict[str, list[dict[str, str]]] = {
    "coding time": [
        {"goal": "Open VS Code", "action": "smart_open_app", "input": "vs code"},
        {"goal": "Start coding music", "action": "open_youtube_music", "input": "lofi coding music"},
    ],
    "free time": [
        {"goal": "Open YouTube", "action": "smart_open_app", "input": "youtube"},
        {"goal": "Find a movie pick", "action": "youtube_search", "input": "best movies to watch this weekend trailers"},
    ],
    "movie time": [
        {"goal": "Open YouTube", "action": "smart_open_app", "input": "youtube"},
        {"goal": "Find movie recommendations", "action": "youtube_search", "input": "best thriller and sci-fi movies to watch trailer"},
    ],
    "study time": [
        {"goal": "Open browser", "action": "smart_open_app", "input": "chrome"},
        {"goal": "Open focus music", "action": "open_youtube_music", "input": "deep focus study music"},
        {"goal": "Search study timer", "action": "google_search", "input": "pomodoro timer study with me"},
    ],
    "gaming time": [
        {"goal": "Open Discord", "action": "smart_open_app", "input": "discord"},
        {"goal": "Open Steam", "action": "smart_open_app", "input": "steam"},
        {"goal": "Start gaming music", "action": "open_youtube_music", "input": "gaming soundtrack mix"},
    ],
    "meeting time": [
        {"goal": "Open calendar", "action": "smart_open_app", "input": "google calendar"},
        {"goal": "Open Gmail", "action": "smart_open_app", "input": "gmail"},
        {"goal": "Open meeting app", "action": "smart_open_app", "input": "zoom"},
    ],
    "editing time": [
        {"goal": "Open editing tool", "action": "smart_open_app", "input": "capcut"},
        {"goal": "Open YouTube", "action": "smart_open_app", "input": "youtube"},
        {"goal": "Start focus music", "action": "open_youtube_music", "input": "cinematic focus music"},
    ],
}


def routine_names(user_id: str) -> set[str]:
    return set(BUILTIN_ROUTINES) | set(get_custom_routines(user_id))


def list_routines_text(user_id: str) -> str:
    builtin = sorted(BUILTIN_ROUTINES)
    custom = sorted(get_custom_routines(user_id))
    lines = ["Available routines:"]
    if builtin:
        lines.append("Built-in: " + ", ".join(builtin))
    if custom:
        lines.append("Custom: " + ", ".join(custom))
    if not custom:
        lines.append("Custom: none yet")
    return "\n".join(lines)


def _normalize_goal(action: str, value: str) -> str:
    label = action.replace("_", " ")
    if value:
        return f"{label}: {value}"
    return label


def _parse_single_step(text: str) -> dict[str, str] | None:
    step = text.strip()
    if not step:
        return None

    music_match = re.match(r"^(?:play|open)\s+(.+?)\s+(?:in|on)\s+(?:yt music|youtube music)$", step, re.IGNORECASE)
    if music_match:
        query = music_match.group(1).strip()
        return {"goal": f"Play music: {query}", "action": "open_youtube_music", "input": query}

    if re.fullmatch(r"(?:play|open)\s+(?:yt music|youtube music)", step, re.IGNORECASE):
        return {"goal": "Open YouTube Music", "action": "open_youtube_music", "input": ""}

    yt_match = re.match(
        r"^(?:search(?:\s+(?:in|on))?\s+youtube(?:\s+for)?|find\s+on\s+youtube|open\s+youtube(?:\s+and)?(?:\s+search)?|play\s+youtube)\s+(.+)$",
        step,
        re.IGNORECASE,
    )
    if yt_match:
        query = yt_match.group(1).strip()
        return {"goal": f"Search YouTube: {query}", "action": "youtube_search", "input": query}

    google_match = re.match(r"^(?:google|search(?:\s+google)?\s+for)\s+(.+)$", step, re.IGNORECASE)
    if google_match:
        query = google_match.group(1).strip()
        return {"goal": f"Search Google: {query}", "action": "google_search", "input": query}

    open_match = re.match(r"^(?:open|launch|start)\s+(.+)$", step, re.IGNORECASE)
    if open_match:
        target = open_match.group(1).strip()
        return {"goal": f"Open {target}", "action": "smart_open_app", "input": target}

    return None


def parse_routine_steps(text: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+then\s+", " and ", text.strip(), flags=re.IGNORECASE)
    parts = [part.strip(" ,.") for part in re.split(r"\s+and\s+", normalized) if part.strip(" ,.")]
    steps = []
    for part in parts:
        parsed = _parse_single_step(part)
        if parsed:
            steps.append(parsed)
    return steps


def save_routine_from_text(user_id: str, text: str) -> str | None:
    match = re.match(r"^(?:save|create)\s+routine\s+(.+?)\s*:\s*(.+)$", text.strip(), re.IGNORECASE)
    if not match:
        return None

    name, body = match.groups()
    steps = parse_routine_steps(body)
    if not steps:
        return (
            "❓ I couldn't understand that routine yet.\n"
            "Try: `save routine focus mode: open chrome and play lofi in yt music`"
        )

    routine = {"name": name.strip(), "steps": steps, "source_text": body.strip()}
    save_custom_routine(user_id, name, routine)
    return f"✅ Saved routine `{name.strip()}` with {len(steps)} step(s)."


def delete_routine_from_text(user_id: str, text: str) -> str | None:
    match = re.match(r"^(?:delete|remove)\s+routine\s+(.+)$", text.strip(), re.IGNORECASE)
    if not match:
        return None
    name = match.group(1).strip()
    if delete_custom_routine(user_id, name):
        return f"🗑️ Deleted routine `{name}`."
    return f"❌ I couldn't find routine `{name}`."


def get_routine_steps(user_id: str, name: str) -> list[dict[str, str]] | None:
    key = name.strip().lower()
    if key in BUILTIN_ROUTINES:
        return BUILTIN_ROUTINES[key]
    custom = get_custom_routine(user_id, key)
    if custom:
        return custom.get("steps", [])
    return None


def routine_name_from_text(user_id: str, text: str) -> str | None:
    stripped = text.strip()
    lower = stripped.lower()
    if lower in routine_names(user_id):
        return lower

    match = re.match(r"^(?:run|start|open)\s+routine\s+(.+)$", stripped, re.IGNORECASE)
    if match:
        name = match.group(1).strip().lower()
        if name in routine_names(user_id):
            return name
    return None
