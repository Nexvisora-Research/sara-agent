import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RECENT_CONTEXT_MESSAGES = 12
from memory import DATA_DIR

# In-memory cache: { user_id: [ {role, content}, ... ] }
_chat_histories: dict[str, list] = {}


def _history_path(user_id: str) -> str:
    user_dir = os.path.join(DATA_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "history.json")


def _load_history(user_id: str) -> list:
    """Load chat history from disk, return empty list if not found."""
    path = _history_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    normalized = []
                    for msg in data:
                        if isinstance(msg, dict):
                            normalized.append(
                                {
                                    "role": msg.get("role", "assistant"),
                                    "content": msg.get("content", ""),
                                    "timestamp": msg.get("timestamp"),
                                    "channel": msg.get("channel", "chat"),
                                }
                            )
                    return normalized
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load history for {user_id}: {e}")
    return []


def _save_history(user_id: str) -> None:
    """Persist the current in-memory history to disk."""
    try:
        with open(_history_path(user_id), "w", encoding="utf-8") as f:
            json.dump(_chat_histories[user_id], f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error(f"Could not save history for {user_id}: {e}")


def _get_history(user_id: str) -> list:
    """Return the in-memory history, loading from disk on first access."""
    if user_id not in _chat_histories:
        _chat_histories[user_id] = _load_history(user_id)
    return _chat_histories[user_id]


def add_message(user_id: str, role: str, content: str, *, channel: str = "chat") -> None:
    """Append a message to a user's full history and persist it."""
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
    _chat_histories[user_id] = []
    _save_history(user_id)
