"""
memory/user_profile.py — Rich per-user profile with long-term memory.

Stored as  memory/data/<user_id>/profile.json

Schema:
  name          str | None
  language      str          e.g. "en", "hi", "fr"
  timezone      str          e.g. "Asia/Kolkata"
  interests     list[str]    e.g. ["coding", "music", "fitness"]
  dislikes      list[str]
  preferences   dict         free-form key:value pairs
  notes         list[str]    user-saved notes
  facts         list[str]    facts Sara learned about the user
  last_seen     str          ISO timestamp
  onboarded     bool         True once onboarding is complete
  created_at    str          ISO timestamp
"""

import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

_profiles: dict[str, dict] = {}

DEFAULT_PROFILE = {
    "name":             None,
    "language":         "en",
    "timezone":         "Asia/Kolkata",
    "interests":        [],
    "dislikes":         [],
    "preferences":      {},
    "notes":            [],
    "facts":            [],
    "last_seen":        None,
    "onboarded":        False,
    "created_at":       None,
    "telegram_chat_id": None,   # stored by telegram_bot for auto-train notifications
    "custom_routines":  {},
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _profile_path(user_id: str) -> str:
    user_dir = os.path.join(DATA_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "profile.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_profile(user_id: str) -> dict:
    path = _profile_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_PROFILE, **data}   # merge in new default keys
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load profile for {user_id}: {e}")
    profile = dict(DEFAULT_PROFILE)
    profile["created_at"] = _now_iso()
    return profile


def _save_profile(user_id: str) -> None:
    try:
        with open(_profile_path(user_id), "w", encoding="utf-8") as f:
            json.dump(_profiles[user_id], f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"Could not save profile for {user_id}: {e}")


def _get(user_id: str) -> dict:
    """Return (and cache) a user's profile, loading from disk on first call."""
    if user_id not in _profiles:
        _profiles[user_id] = _load_profile(user_id)
    return _profiles[user_id]


# ── Public API ────────────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict:
    """Return the full profile dict for a user."""
    return _get(user_id)


def is_onboarded(user_id: str) -> bool:
    """Return True if onboarding has been completed."""
    return bool(_get(user_id).get("onboarded"))


def mark_onboarded(user_id: str) -> None:
    """Mark onboarding complete and save."""
    p = _get(user_id)
    p["onboarded"] = True
    touch_last_seen(user_id)


def touch_last_seen(user_id: str) -> None:
    """Update last_seen timestamp and persist."""
    _get(user_id)["last_seen"] = _now_iso()
    _save_profile(user_id)


# ── Name ─────────────────────────────────────────────────────────────────────

def get_name(user_id: str) -> str | None:
    return _get(user_id).get("name")


def set_name(user_id: str, name: str) -> None:
    _get(user_id)["name"] = name.strip()
    _save_profile(user_id)


# ── Language & Timezone ───────────────────────────────────────────────────────

def get_language(user_id: str) -> str:
    return _get(user_id).get("language", "en")


def set_language(user_id: str, lang: str) -> None:
    _get(user_id)["language"] = lang.strip().lower()
    _save_profile(user_id)


def set_timezone(user_id: str, tz: str) -> None:
    _get(user_id)["timezone"] = tz.strip()
    _save_profile(user_id)


# ── Interests & Dislikes ──────────────────────────────────────────────────────

def add_interest(user_id: str, interest: str) -> None:
    """Add a topic the user is interested in (no duplicates)."""
    p = _get(user_id)
    interest = interest.strip().lower()
    if interest and interest not in p["interests"]:
        p["interests"].append(interest)
        _save_profile(user_id)


def set_interests(user_id: str, interests: list[str]) -> None:
    """Replace interests from a list."""
    p = _get(user_id)
    p["interests"] = [i.strip().lower() for i in interests if i.strip()]
    _save_profile(user_id)


def add_dislike(user_id: str, dislike: str) -> None:
    p = _get(user_id)
    dislike = dislike.strip().lower()
    if dislike and dislike not in p["dislikes"]:
        p["dislikes"].append(dislike)
        _save_profile(user_id)


# ── Preferences (free-form key:value) ─────────────────────────────────────────

def set_preference(user_id: str, key: str, value: str) -> None:
    """Store an arbitrary user preference, e.g. set_preference(id, 'tone', 'formal')."""
    _get(user_id)["preferences"][key.strip()] = value.strip()
    _save_profile(user_id)


def get_preference(user_id: str, key: str, default=None):
    return _get(user_id)["preferences"].get(key, default)


# ── Notes (user-saved) ────────────────────────────────────────────────────────

def save_note(user_id: str, note: str) -> None:
    _get(user_id).setdefault("notes", []).append(note.strip())
    _save_profile(user_id)


def get_notes(user_id: str) -> list:
    return _get(user_id).get("notes", [])


def clear_notes(user_id: str) -> None:
    _get(user_id)["notes"] = []
    _save_profile(user_id)


# ── Custom routines ───────────────────────────────────────────────────────────

def save_custom_routine(user_id: str, name: str, routine: dict) -> None:
    routines = _get(user_id).setdefault("custom_routines", {})
    routines[name.strip().lower()] = routine
    _save_profile(user_id)


def get_custom_routine(user_id: str, name: str) -> dict | None:
    return _get(user_id).get("custom_routines", {}).get(name.strip().lower())


def get_custom_routines(user_id: str) -> dict:
    return dict(_get(user_id).get("custom_routines", {}))


def delete_custom_routine(user_id: str, name: str) -> bool:
    routines = _get(user_id).get("custom_routines", {})
    key = name.strip().lower()
    if key not in routines:
        return False
    routines.pop(key, None)
    _save_profile(user_id)
    return True


# ── Interactive onboarding helper (CLI) ─────────────────────────────────────
def interactive_onboard(user_id: str = "default") -> None:
    """Run a short interactive prompt to populate the user's profile.

    Safe to call from a terminal. Skips fields the user leaves blank.
    Marks the profile as onboarded when finished.
    """
    p = _get(user_id)
    if p.get("onboarded"):
        print("Profile already onboarded. Use get_profile_summary() to view it.")
        return

    print("Welcome — let's set up your Sara profile. Press Enter to skip any question.")
    try:
        name = input("Your name: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nOnboarding cancelled.")
        return
    if name:
        set_name(user_id, name)

    try:
        lang = input("Preferred language (en): ").strip()
    except (EOFError, KeyboardInterrupt):
        lang = ""
    if lang:
        set_language(user_id, lang)

    try:
        tz = input("Timezone (e.g. Europe/London, UTC): ").strip()
    except (EOFError, KeyboardInterrupt):
        tz = ""
    if tz:
        set_timezone(user_id, tz)

    try:
        interests_raw = input("Interests (comma-separated): ").strip()
    except (EOFError, KeyboardInterrupt):
        interests_raw = ""
    if interests_raw:
        interests = [i.strip() for i in interests_raw.split(",") if i.strip()]
        set_interests(user_id, interests)

    try:
        tone = input("Preferred reply tone (casual/formal, default casual): ").strip()
    except (EOFError, KeyboardInterrupt):
        tone = ""
    if tone:
        set_preference(user_id, "tone", tone)

    # Finalize
    mark_onboarded(user_id)
    print("\nThanks — your profile has been saved. You can view it with /profile or by calling get_profile_summary().")


# ── Facts (things Sara learns) ────────────────────────────────────────────────

def add_fact(user_id: str, fact: str) -> None:
    """Store a fact Sara learned about the user, e.g. 'likes Python', 'works at Google'."""
    p = _get(user_id)
    fact = fact.strip()
    if fact and fact not in p.get("facts", []):
        p.setdefault("facts", []).append(fact)
        _save_profile(user_id)


def get_facts(user_id: str) -> list:
    return _get(user_id).get("facts", [])


# ── Rich Context String (injected into AI system prompt) ─────────────────────

def get_full_context_string(user_id: str) -> str:
    """
    Build a natural-language context block about the user
    to inject into the LLM system prompt.
    """
    p = _get(user_id)
    lines = []

    name = p.get("name")
    if name:
        lines.append(f"- User's name: {name}")

    lang = p.get("language", "en")
    if lang != "en":
        lines.append(f"- Preferred language: {lang} (respond in this language when appropriate)")

    tz = p.get("timezone")
    if tz:
        lines.append(f"- Timezone: {tz}")

    interests = p.get("interests", [])
    if interests:
        lines.append(f"- Interests: {', '.join(interests)}")

    dislikes = p.get("dislikes", [])
    if dislikes:
        lines.append(f"- Dislikes/avoid: {', '.join(dislikes)}")

    prefs = p.get("preferences", {})
    if prefs:
        pref_str = ", ".join(f"{k}={v}" for k, v in prefs.items())
        lines.append(f"- Preferences: {pref_str}")

    facts = p.get("facts", [])
    if facts:
        lines.append(f"- Things you know: {'; '.join(facts[-5:])}")  # last 5 facts

    last_seen = p.get("last_seen")
    if last_seen:
        lines.append(f"- Last active: {last_seen[:10]}")

    if not lines:
        return ""

    return "📋 USER PROFILE:\n" + "\n".join(lines)


# ── Profile Summary (for /profile command) ────────────────────────────────────

def get_profile_summary(user_id: str) -> str:
    """Human-readable profile for the /profile Telegram command."""
    p = _get(user_id)

    name      = p.get("name") or "_(not set)_"
    language  = p.get("language", "en")
    timezone  = p.get("timezone") or "_(not set)_"
    interests = ", ".join(p.get("interests", [])) or "_(none yet)_"
    dislikes  = ", ".join(p.get("dislikes", [])) or "_(none yet)_"
    notes_n   = len(p.get("notes", []))
    facts_n   = len(p.get("facts", []))
    created   = (p.get("created_at") or "")[:10] or "_(unknown)_"
    last_seen = (p.get("last_seen") or "")[:10] or "-(never)-"

    prefs = p.get("preferences", {})
    pref_str = "\n".join(f"    • {k}: {v}" for k, v in prefs.items()) or "    _(none)_"

    return (
        f"👤 *Your Sara AI Profile*\n\n"
        f"  Name: *{name}*\n"
        f"  Language: `{language}`\n"
        f"  Timezone: `{timezone}`\n"
        f"  Interests: {interests}\n"
        f"  Dislikes: {dislikes}\n"
        f"  Saved Notes: {notes_n}\n"
        f"  Facts Sara knows: {facts_n}\n"
        f"  Preferences:\n{pref_str}\n"
        f"  Member since: `{created}`\n"
        f"  Last active: `{last_seen}`"
    )


# ── Telegram info (for auto-trainer notifications) ───────────────────────────

# In-memory store for the live bot reference (not persisted to JSON)
_telegram_bots: dict[str, object] = {}  # user_id -> telegram.Bot instance


def set_telegram_info(user_id: str, bot, chat_id: str) -> None:
    """Store the Telegram bot instance and chat_id for a user (in-memory only)."""
    _telegram_bots[user_id] = bot
    _get(user_id)["telegram_chat_id"] = chat_id
    _save_profile(user_id)


def get_telegram_info(user_id: str) -> tuple:
    """Return (bot, chat_id) for push notifications. bot may be None."""
    bot     = _telegram_bots.get(user_id)
    chat_id = _get(user_id).get("telegram_chat_id") or ""
    return bot, chat_id
