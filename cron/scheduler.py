"""Minimal cron scheduler compatibility surface."""

from __future__ import annotations

_HOME_TARGET_ENV_VARS = {
    "telegram": "TELEGRAM_HOME_CHANNEL",
    "discord": "DISCORD_HOME_CHANNEL",
    "slack": "SLACK_HOME_CHANNEL",
    "matrix": "MATRIX_HOME_ROOM",
}


def tick(*args, **kwargs):
    """Placeholder scheduler tick.

    The full gateway scheduler is optional for CLI chat startup. Returning an
    empty list keeps callers that poll for due jobs in a harmless no-op state.
    """
    return []
