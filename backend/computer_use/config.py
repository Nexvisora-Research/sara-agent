"""Configuration for Computer Use subsystem."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComputerUseConfig:
    """Configuration for computer use capabilities.

    Values are read from env vars or config dict, with sensible defaults.
    """

    # ── Permission defaults ──────────────────────────────────────────────
    permission_level: str = "smart"

    # ── Screen capture ───────────────────────────────────────────────────
    screen_capture_fps: int = 3
    screen_capture_quality: int = 70
    screen_capture_monitor: int = 0
    screen_capture_dir: str = ""

    # ── Vision / element detection ───────────────────────────────────────
    vision_provider: str = "auto"
    vision_model: str = ""
    vision_base_url: str = ""
    vision_api_key: str = ""

    # ── Element detection thresholds ─────────────────────────────────────
    button_min_area: int = 400
    input_min_area: int = 200
    ocr_confidence: float = 0.6
    template_match_threshold: float = 0.75

    # ── Action execution ─────────────────────────────────────────────────
    action_timeout: float = 10.0
    move_speed: float = 0.2
    click_delay: float = 0.1
    type_interval: float = 0.05

    # ── Overlay ──────────────────────────────────────────────────────────
    overlay_enabled: bool = True
    overlay_opacity: float = 0.92
    overlay_font_size: int = 11

    # ── Memory ───────────────────────────────────────────────────────────
    memory_enabled: bool = True
    memory_max_actions: int = 500

    # ── Planner loop ─────────────────────────────────────────────────────
    planner_max_iterations: int = 20
    planner_verify_retries: int = 3

    @classmethod
    def from_env(cls) -> ComputerUseConfig:
        """Build config from environment variables."""
        return cls(
            permission_level=os.environ.get("COMPUTER_USE_PERMISSION_LEVEL", "smart"),
            screen_capture_fps=int(os.environ.get("COMPUTER_USE_FPS", "3")),
            screen_capture_quality=int(os.environ.get("COMPUTER_USE_QUALITY", "70")),
            screen_capture_monitor=int(os.environ.get("COMPUTER_USE_MONITOR", "0")),
            screen_capture_dir=os.environ.get("COMPUTER_USE_SCREENSHOT_DIR", ""),
            vision_provider=os.environ.get("AUXILIARY_VISION_PROVIDER", "auto"),
            vision_model=os.environ.get("AUXILIARY_VISION_MODEL", ""),
            vision_base_url=os.environ.get("AUXILIARY_VISION_BASE_URL", ""),
            vision_api_key=os.environ.get("AUXILIARY_VISION_API_KEY", ""),
            action_timeout=float(os.environ.get("COMPUTER_USE_ACTION_TIMEOUT", "10")),
            overlay_enabled=os.environ.get("COMPUTER_USE_OVERLAY", "1") == "1",
            memory_enabled=os.environ.get("COMPUTER_USE_MEMORY", "1") == "1",
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ComputerUseConfig:
        known_keys = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in d.items() if k in known_keys}
        return cls(**filtered)
