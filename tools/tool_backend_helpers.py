"""Small helper shims for tool backend and nexvisora-specific settings."""

from __future__ import annotations

import os
from typing import Optional


def _truthy_env(*names: str, default: bool = False) -> bool:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def managed_nexvisora_tools_enabled() -> bool:
    return _truthy_env("sara_MANAGED", "SARA_MANAGED", "nexvisora_MANAGED_TOOLS", "nexvisora_MANAGED", default=False)


def prefers_gateway(tool_key: str) -> bool:
    """Return whether config opts a tool into the managed gateway."""
    try:
        from sara_cli.config import load_config
        config = load_config()
    except Exception:
        config = {}

    section = config.get(str(tool_key), {}) if isinstance(config, dict) else {}
    if not isinstance(section, dict):
        return False

    value = section.get("use_gateway")
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def fal_key_is_configured() -> bool:
    return bool(os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY"))


def resolve_openai_audio_api_key() -> Optional[str]:
    return os.getenv("OPENAI_AUDIO_API_KEY") or os.getenv("VOICE_TOOLS_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")


def has_direct_modal_credentials() -> bool:
    return bool(os.getenv("MODAL_TOKEN_ID") and os.getenv("MODAL_TOKEN_SECRET")) or bool(os.getenv("MODAL_TOKEN"))


def normalize_browser_cloud_provider(value: object = None) -> str:
    text = str(value or "").strip().lower()
    return text or "browser-use"


def normalize_modal_mode(value: object = None) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"managed", "direct", "auto"} else "auto"


def coerce_modal_mode(value: object = None) -> str:
    """Backward-compatible name for modal mode normalization."""
    return normalize_modal_mode(value)


def resolve_modal_backend_state(value: object = None, *, has_direct_credentials: bool = False, **kwargs) -> dict:
    """Resolve modal backend state.

    Backwards-compatible wrapper: older callers pass `has_direct` and
    `managed_ready` keyword args and expect a dict with keys used by
    callers such as `selected_backend`, `mode`, and
    `managed_mode_blocked`.
    """
    # Accept legacy kwarg names for compatibility
    has_direct = bool(
        has_direct_credentials
        or kwargs.get("has_direct")
        or kwargs.get("has_direct_credentials")
    )
    managed_ready = bool(kwargs.get("managed_ready", False))

    mode = normalize_modal_mode(value)

    # Determine selected backend when in auto mode
    if mode == "auto":
        if has_direct:
            selected = "direct"
        elif managed_ready:
            selected = "managed"
        else:
            # Default to direct when neither direct creds nor managed
            # gateway are available — callers will perform final checks.
            selected = "direct"
    else:
        selected = mode

    managed_mode_blocked = selected == "managed" and not managed_ready and not has_direct

    return {
        "mode": mode,
        "selected_backend": selected,
        "has_direct": has_direct,
        "managed_ready": managed_ready,
        "managed_mode_blocked": managed_mode_blocked,
    }
