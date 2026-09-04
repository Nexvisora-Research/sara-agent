"""Desktop action execution engine.

Provides mouse, keyboard, and system control actions using pynput and
cross-platform utilities. Each action captures before/after state and
returns structured results.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


class ActionEngine:
    """Executes desktop actions: mouse, keyboard, scroll, type, etc."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._mouse = None
        self._keyboard = None
        self._init_controllers()

    def _init_controllers(self):
        try:
            from pynput.mouse import Controller as MouseController
            from pynput.keyboard import Controller as KeyboardController
            self._mouse = MouseController()
            self._keyboard = KeyboardController()
            logger.debug("Action engine controllers initialized")
        except ImportError:
            logger.error("pynput not available - actions disabled. Install with: pip install pynput")

    @property
    def is_available(self) -> bool:
        return self._mouse is not None and self._keyboard is not None

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "")
        params = {k: v for k, v in action.items() if k != "type"}
        handler = getattr(self, f"_{action_type}", None)
        if not handler:
            return {"success": False, "error": f"Unknown action type: {action_type}"}
        try:
            result = handler(**params)
            result["action_type"] = action_type
            result["success"] = result.get("success", True)
            return result
        except Exception as e:
            logger.exception("Action '%s' failed", action_type)
            return {"success": False, "action_type": action_type, "error": str(e)}

    def _move_mouse(self, x: int, y: int, **kwargs) -> Dict[str, Any]:
        if not self._mouse:
            return {"success": False, "error": "Mouse controller unavailable"}
        self._mouse.position = (x, y)
        time.sleep(self.config.move_speed)
        return {"success": True, "x": x, "y": y}

    def _click(self, button: str = "left", x: Optional[int] = None,
               y: Optional[int] = None, clicks: int = 1, **kwargs) -> Dict[str, Any]:
        if not self._mouse:
            return {"success": False, "error": "Mouse controller unavailable"}
        if x is not None and y is not None:
            self._mouse.position = (x, y)
            time.sleep(self.config.move_speed)
        btn = self._resolve_button(button)
        for _ in range(clicks):
            self._mouse.click(btn)
            time.sleep(self.config.click_delay)
        return {"success": True, "button": button, "x": x, "y": y, "clicks": clicks}

    def _double_click(self, x: Optional[int] = None, y: Optional[int] = None,
                      button: str = "left", **kwargs) -> Dict[str, Any]:
        return self._click(button=button, x=x, y=y, clicks=2)

    def _drag(self, start_x: int, start_y: int, end_x: int, end_y: int,
              button: str = "left", **kwargs) -> Dict[str, Any]:
        if not self._mouse:
            return {"success": False, "error": "Mouse controller unavailable"}
        btn = self._resolve_button(button)
        self._mouse.position = (start_x, start_y)
        time.sleep(self.config.move_speed)
        self._mouse.press(btn)
        time.sleep(0.05)
        steps = 20
        for i in range(1, steps + 1):
            cx = start_x + (end_x - start_x) * i // steps
            cy = start_y + (end_y - start_y) * i // steps
            self._mouse.position = (cx, cy)
            time.sleep(0.01)
        self._mouse.release(btn)
        return {
            "success": True,
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "button": button,
        }

    def _scroll(self, dx: int = 0, dy: int = -1, **kwargs) -> Dict[str, Any]:
        if not self._mouse:
            return {"success": False, "error": "Mouse controller unavailable"}
        self._mouse.scroll(dx, dy)
        return {"success": True, "dx": dx, "dy": dy}

    def _type_text(self, text: str, **kwargs) -> Dict[str, Any]:
        if not self._keyboard:
            return {"success": False, "error": "Keyboard controller unavailable"}
        self._keyboard.type(text)
        return {"success": True, "length": len(text)}

    def _press_key(self, key: str, **kwargs) -> Dict[str, Any]:
        if not self._keyboard:
            return {"success": False, "error": "Keyboard controller unavailable"}
        k = self._resolve_key(key)
        if k is None:
            return {"success": False, "error": f"Unknown key: {key}"}
        self._keyboard.press(k)
        time.sleep(0.05)
        self._keyboard.release(k)
        return {"success": True, "key": key}

    def _hotkey(self, keys: List[str], **kwargs) -> Dict[str, Any]:
        if not self._keyboard:
            return {"success": False, "error": "Keyboard controller unavailable"}
        resolved = []
        for k in keys:
            rk = self._resolve_key(k)
            if rk is None:
                return {"success": False, "error": f"Unknown key: {k}"}
            resolved.append(rk)
        for k in resolved:
            self._keyboard.press(k)
        time.sleep(0.05)
        for k in reversed(resolved):
            self._keyboard.release(k)
        return {"success": True, "keys": keys}

    def _screenshot(self, **kwargs) -> Dict[str, Any]:
        from ..vision.screen_capture import ScreenCapture
        sc = ScreenCapture(self.config)
        cap = sc.capture_primary()
        if not cap:
            return {"success": False, "error": "Screenshot failed"}
        return {
            "success": True,
            "base64": cap.base64,
            "width": cap.monitor.width,
            "height": cap.monitor.height,
            "timestamp": cap.timestamp,
        }

    def _wait(self, seconds: float = 1.0, **kwargs) -> Dict[str, Any]:
        time.sleep(seconds)
        return {"success": True, "seconds": seconds}

    def _resolve_button(self, button: str):
        from pynput.mouse import Button
        mapping = {
            "left": Button.left,
            "right": Button.right,
            "middle": Button.middle,
        }
        return mapping.get(button.lower(), Button.left)

    def _resolve_key(self, key: str):
        from pynput.keyboard import Key
        mapping = {
            "enter": Key.enter, "return": Key.enter,
            "tab": Key.tab,
            "space": Key.space,
            "backspace": Key.backspace,
            "delete": Key.delete,
            "escape": Key.esc, "esc": Key.esc,
            "up": Key.up, "down": Key.down,
            "left": Key.left, "right": Key.right,
            "home": Key.home, "end": Key.end,
            "page_up": Key.page_up, "page_down": Key.page_down,
            "ctrl": Key.ctrl, "ctrl_l": Key.ctrl_l, "ctrl_r": Key.ctrl_r,
            "shift": Key.shift, "shift_l": Key.shift_l, "shift_r": Key.shift_r,
            "alt": Key.alt, "alt_l": Key.alt_l, "alt_r": Key.alt_r,
            "cmd": Key.cmd, "cmd_l": Key.cmd_l, "cmd_r": Key.cmd_r,
            "caps_lock": Key.caps_lock,
            "f1": Key.f1, "f2": Key.f2, "f3": Key.f3,
            "f4": Key.f4, "f5": Key.f5, "f6": Key.f6,
            "f7": Key.f7, "f8": Key.f8, "f9": Key.f9,
            "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        }
        result = mapping.get(key.lower())
        if result is not None:
            return result
        from pynput.keyboard import KeyCode
        if len(key) == 1:
            return KeyCode.from_char(key)
        return None

    def shutdown(self):
        pass
