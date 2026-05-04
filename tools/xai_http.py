"""Shared helpers for direct xAI HTTP integrations."""

from __future__ import annotations


def sara_xai_user_agent() -> str:
    """Return a stable sara-specific User-Agent for xAI HTTP calls."""
    try:
        from sara_cli import __version__
    except Exception:
        __version__ = "unknown"
    return f"sara-Agent/{__version__}"
