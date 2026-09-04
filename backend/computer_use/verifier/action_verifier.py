"""Verifies desktop actions by comparing before/after state.

Supports:
- Element presence/absence checks
- Screen change detection
- LLM-based verification of task completion
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


class ActionVerifier:
    """Verifies that desktop actions produced the expected result."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        try:
            from ..vision.llm import call_vision_llm
            self._call_llm = call_vision_llm
        except ImportError:
            self._call_llm = None

    def verify(self, action_result: Dict[str, Any], task: str) -> Dict[str, Any]:
        if not action_result.get("success"):
            return {
                "verified": False,
                "reason": "Action did not succeed",
                "task_complete": False,
            }

        action_type = action_result.get("action_type", "")
        state_before = action_result.get("state_before")
        state_after = action_result.get("state_after")

        if action_type == "click":
            return self._verify_click(action_result, state_before, state_after)
        elif action_type == "type_text":
            return self._verify_type(action_result, state_before, state_after)
        elif action_type == "hotkey":
            return self._verify_hotkey(action_result, state_before, state_after)
        elif action_type in ("move_mouse", "scroll", "press_key"):
            return {"verified": True, "task_complete": False}
        elif action_type == "wait":
            return {"verified": True, "task_complete": False}
        else:
            return self._verify_generic(action_result, state_before, state_after, task)

    def _verify_click(self, result: Dict, before: Dict, after: Dict) -> Dict[str, Any]:
        if not before or not after:
            return {"verified": True, "task_complete": False}
        change = self._detect_screen_change(before, after)
        return {
            "verified": change.get("changed", True),
            "reason": "Screen changed after click" if change.get("changed") else "No visible change after click",
            "change_detected": change.get("changed", False),
            "task_complete": False,
        }

    def _verify_type(self, result: Dict, before: Dict, after: Dict) -> Dict[str, Any]:
        if not before or not after:
            return {"verified": True, "task_complete": False}
        change = self._detect_screen_change(before, after)
        return {
            "verified": True,
            "change_detected": change.get("changed", False),
            "task_complete": False,
        }

    def _verify_hotkey(self, result: Dict, before: Dict, after: Dict) -> Dict[str, Any]:
        if not before or not after:
            return {"verified": True, "task_complete": False}
        change = self._detect_screen_change(before, after)
        return {
            "verified": True,
            "change_detected": change.get("changed", False),
            "task_complete": False,
        }

    def _verify_generic(self, result: Dict, before: Dict, after: Dict, task: str) -> Dict[str, Any]:
        if not self._call_llm or not after:
            return {"verified": True, "task_complete": False}

        try:
            screenshots = after.get("screenshots", []) or after.get("primary_screenshot", "")
            if not screenshots:
                return {"verified": True, "task_complete": False}

            b64 = screenshots[0].get("base64", "") if isinstance(screenshots, list) else screenshots
            if not b64:
                return {"verified": True, "task_complete": False}

            prompt = (
                f"Task: {task}\n"
                "Look at the current screen. Has the task been completed successfully? "
                "Respond with JSON only: {\"task_complete\": true/false, "
                "\"reason\": \"brief explanation\"}"
            )
            text = self._call_llm(prompt, b64, config=self.config)
            if text:
                import re
                match = re.search(r'\{[\s\S]*"task_complete"[\s\S]*\}', text)
                if match:
                    import json
                    data = json.loads(match.group())
                    return {
                        "verified": True,
                        "task_complete": bool(data.get("task_complete", False)),
                        "reason": data.get("reason", ""),
                    }
        except Exception as e:
            logger.debug("LLM verification failed: %s", e)

        return {"verified": True, "task_complete": False}

    def _detect_screen_change(self, before: Dict, after: Dict) -> Dict[str, bool]:
        """Detect if the screen changed between before and after states."""
        try:
            b64_before = self._get_screenshot_b64(before)
            b64_after = self._get_screenshot_b64(after)
            if not b64_before or not b64_after:
                return {"changed": True}

            import base64
            import io
            from PIL import Image

            img_before = Image.open(io.BytesIO(base64.b64decode(b64_before)))
            img_after = Image.open(io.BytesIO(base64.b64decode(b64_after)))

            if img_before.size != img_after.size:
                return {"changed": True}

            diff = self._image_diff_percent(img_before, img_after)
            return {"changed": diff > 2.0, "diff_percent": round(diff, 1)}
        except Exception as e:
            logger.debug("Screen change detection failed: %s", e)
            return {"changed": True}

    def _get_screenshot_b64(self, state: Dict) -> Optional[str]:
        screenshots = state.get("screenshots")
        if isinstance(screenshots, list) and screenshots:
            cap = screenshots[0]
            if isinstance(cap, dict):
                return cap.get("base64", "")
        primary = state.get("primary_screenshot")
        if isinstance(primary, str) and primary:
            return primary
        return None

    def _image_diff_percent(self, img_a, img_b) -> float:
        try:
            import hashlib
            w, h = img_a.size
            if w > 200 or h > 200:
                img_a = img_a.resize((200, 150))
                img_b = img_b.resize((200, 150))
            pixels_a = list(img_a.getdata())
            pixels_b = list(img_b.getdata())
            changed = sum(1 for a, b in zip(pixels_a, pixels_b) if a != b)
            return (changed / len(pixels_a)) * 100 if pixels_a else 0
        except Exception:
            return 100.0
