import json
import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RECENT_CONTEXT_MESSAGES = 12
from memory import DATA_DIR
from memory.storage import load_json, save_json, user_directory, validate_user_id

# In-memory cache: { user_id: [ {role, content}, ... ] }
_chat_histories: dict[str, list] = {}
_history_lock = threading.RLock()


def _history_path(user_id: str) -> str:
    return str(user_directory(DATA_DIR, user_id) / "history.json")


def _load_history(user_id: str) -> list:
    """Load chat history from disk, return empty list if not found."""
    path = _history_path(user_id)
    data = load_json(path, [])
    if not isinstance(data, list):
        return []
    return [
        {
            "role": msg.get("role", "assistant"),
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp"),
            "channel": msg.get("channel", "chat"),
        }
        for msg in data
        if isinstance(msg, dict)
    ]


def _save_history(user_id: str) -> None:
    """Persist the current in-memory history to disk."""
    try:
        save_json(_history_path(user_id), _chat_histories[user_id])
    except OSError as e:
        logger.error(f"Could not save history for {user_id}: {e}")


def _get_history(user_id: str) -> list:
    """Return the in-memory history, loading from disk on first access."""
    validate_user_id(user_id)
    with _history_lock:
        if user_id not in _chat_histories:
            _chat_histories[user_id] = _load_history(user_id)
        return _chat_histories[user_id]


def add_message(user_id: str, role: str, content: str, *, channel: str = "chat") -> None:
    """Append a message to a user's full history and persist it."""
    with _history_lock:
        history = _get_history(user_id)
        history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": channel,
            }
        )
        _save_history(user_id)


def get_context(user_id: str, max_messages: int = RECENT_CONTEXT_MESSAGES, *, limit: int | None = None) -> str:
    """Return a recent conversation window formatted for prompting.

    `limit` is a legacy alias kept for backward compatibility.
    """
    if limit is not None:
        max_messages = limit
    history = _get_history(user_id)
    if max_messages > 0:
        history = history[-max_messages:]
    return "".join(f"{msg['role']}: {msg['content']}\n" for msg in history)


def get_recent_messages(user_id: str, n: int = 5) -> list:
    """Return the last n messages for a user."""
    return _get_history(user_id)[-n:]


def get_full_history(user_id: str) -> list:
    """Return the full persisted history for a user."""
    return list(_get_history(user_id))


def clear_history(user_id: str) -> None:
    """Clear conversation history for a specific user (memory + disk)."""
    with _history_lock:
        validate_user_id(user_id)
        _chat_histories[user_id] = []
        _save_history(user_id)
