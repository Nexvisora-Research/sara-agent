"""Shared safe storage helpers for Sara's per-user memory files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from utils import atomic_json_write

_SAFE_USER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def validate_user_id(user_id: str) -> str:
    """Validate and return a filesystem-safe user identifier."""
    value = str(user_id or "").strip()
    if value in {".", ".."} or not _SAFE_USER_ID.fullmatch(value):
        raise ValueError("user_id must be 1-128 characters: letters, numbers, _, ., -")
    return value


def user_directory(data_dir: str | Path, user_id: str) -> Path:
    """Return a validated user's directory and create it if necessary."""
    directory = Path(data_dir) / validate_user_id(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_json(path: str | Path, default: Any) -> Any:
    """Load JSON, returning *default* for missing or malformed files."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path: str | Path, value: Any) -> None:
    """Persist JSON atomically so interrupted writes keep the old value."""
    atomic_json_write(path, value)
