"""Permission levels for Computer Use.

Three tiers:
- SAFE: read-only, no desktop actions permitted
- SMART: actions allowed but risky ones prompt for approval
- AUTONOMOUS: full control (DISABLED by default)
"""

from __future__ import annotations

import enum
import logging
import threading
from typing import Any, Callable, Dict, Optional

from .config import ComputerUseConfig

logger = logging.getLogger(__name__)


class PermissionLevel(enum.Enum):
    SAFE = "safe"
    SMART = "smart"
    AUTONOMOUS = "autonomous"


_APPROVAL_CALLBACKS: list[Callable[[dict], bool]] = []
_lock = threading.Lock()


def register_approval_callback(cb: Callable[[dict], bool]):
    with _lock:
        _APPROVAL_CALLBACKS.append(cb)


_AUTONOMOUS_ENABLED = False


def enable_autonomous():
    global _AUTONOMOUS_ENABLED
    _AUTONOMOUS_ENABLED = True
    logger.warning("AUTONOMOUS MODE ENABLED - Computer Agent has full system control")


def disable_autonomous():
    global _AUTONOMOUS_ENABLED
    _AUTONOMOUS_ENABLED = False


def is_autonomous_enabled() -> bool:
    return _AUTONOMOUS_ENABLED


class PermissionManager:
    """Manages permission level and approval flow for computer actions."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config

    def get_level(self) -> PermissionLevel:
        raw = self.config.permission_level.strip().lower()
        if raw == "autonomous":
            if not _AUTONOMOUS_ENABLED:
                logger.warning("Autonomous mode requested but not enabled. Falling back to smart.")
                return PermissionLevel.SMART
            return PermissionLevel.AUTONOMOUS
        elif raw == "safe":
            return PermissionLevel.SAFE
        return PermissionLevel.SMART

    def request_approval(self, action: dict[str, Any]) -> bool:
        """Request user approval for a smart-mode action via registered callbacks."""
        with _lock:
            if not _APPROVAL_CALLBACKS:
                return False
            for cb in _APPROVAL_CALLBACKS:
                try:
                    if cb(action):
                        return True
                except Exception:
                    continue
        return False

    def check_action_allowed(self, action_type: str) -> bool:
        level = self.get_level()
        if level == PermissionLevel.SAFE:
            return False
        if level == PermissionLevel.AUTONOMOUS:
            return True
        if action_type in ("move_mouse", "screenshot"):
            return True
        return False
