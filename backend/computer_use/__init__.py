"""Computer Use - Desktop AI agent capabilities for Sara.

Provides live desktop vision, accessibility integration, action execution,
task planning, and persistent UI memory. Designed as an extension to the
existing Sara agent architecture.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .config import ComputerUseConfig
from .permissions import PermissionLevel, PermissionManager

logger = logging.getLogger(__name__)


class ComputerAgent:
    """High-level agent for desktop computer use tasks.

    Integrates vision, accessibility, action execution, planning, and
    verification into a single Observe->Analyze->Plan->Execute->Verify loop.
    """

    def __init__(self, config: Optional[ComputerUseConfig] = None):
        self.config = config or ComputerUseConfig()
        self.permissions = PermissionManager(self.config)

        self._screen = None
        self._accessibility = None
        self._executor = None
        self._planner = None
        self._verifier = None
        self._ui_memory = None
        self._overlay = None

        self._initialized = False
        self._task_history: list[dict] = []
        self._current_task: Optional[str] = None

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            from .vision.screen_capture import ScreenCapture
            from .vision.window_tracker import WindowTracker
            from .vision.element_detector import ElementDetector
            from .accessibility.atspi_bridge import ATSPIBridge
            from .accessibility.ui_tree import UITree
            from .executor.action_engine import ActionEngine
            from .planner.task_planner import TaskPlanner
            from .verifier.action_verifier import ActionVerifier
            from .memory.ui_memory import UIMemory

            self._screen = ScreenCapture(self.config)
            self._window_tracker = WindowTracker()
            self._element_detector = ElementDetector(self.config)
            self._accessibility = ATSPIBridge()
            self._ui_tree = UITree(self._accessibility)
            self._executor = ActionEngine(self.config)
            self._planner = TaskPlanner(self.config, self)
            self._verifier = ActionVerifier(self.config)
            self._ui_memory = UIMemory(self.config)
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize ComputerAgent subsystems: %s", e)
            raise

    def observe(self) -> dict[str, Any]:
        """Capture current desktop state: screenshot, window info, UI tree."""
        self._lazy_init()
        state = {"timestamp": time.time()}

        try:
            screenshots = self._screen.capture_all_monitors()
            state["screenshots"] = screenshots
            primary = self._screen.capture_primary()
            if primary:
                state["primary_screenshot"] = primary["base64"]
        except Exception as e:
            logger.warning("Screen capture failed: %s", e)
            state["screenshots"] = []

        try:
            state["active_window"] = self._window_tracker.get_active_window()
            state["windows"] = self._window_tracker.list_windows()
        except Exception as e:
            logger.warning("Window tracking failed: %s", e)
            state["active_window"] = None

        try:
            tree = self._ui_tree.get_tree()
            state["ui_tree"] = tree
        except Exception as e:
            logger.warning("UI tree access failed: %s", e)
            state["ui_tree"] = None

        try:
            state["elements"] = self._element_detector.detect_all(
                state.get("primary_screenshot", "")
            )
        except Exception as e:
            logger.warning("Element detection failed: %s", e)
            state["elements"] = []

        return state

    def analyze(self, observation: dict[str, Any], task: str) -> dict[str, Any]:
        self._lazy_init()
        return self._planner.analyze_screen(observation, task)

    def plan(self, analysis: dict[str, Any], task: str) -> list[dict[str, Any]]:
        self._lazy_init()
        return self._planner.create_plan(analysis, task)

    def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        self._lazy_init()
        level = self.permissions.get_level()

        if level == PermissionLevel.SAFE and action.get("type") in (
            "click", "double_click", "drag", "type_text", "press_key", "hotkey", "scroll"
        ):
            return {"success": False, "error": "Action blocked by Safe Mode permission level"}

        if level == PermissionLevel.SMART:
            if action.get("type") in ("type_text", "hotkey", "press_key"):
                allowed = self.permissions.request_approval(action)
                if not allowed:
                    return {"success": False, "error": "Action denied by user"}

        before = self.observe()
        result = self._executor.execute(action)
        after = self.observe() if result.get("success") else None

        result["state_before"] = before
        result["state_after"] = after
        result["timestamp"] = time.time()

        self._task_history.append({
            "action": action,
            "result": result,
            "timestamp": result["timestamp"],
        })

        try:
            self._ui_memory.remember_action(action, result)
        except Exception as e:
            logger.debug("UI memory store failed: %s", e)

        return result

    def verify(self, action_result: dict[str, Any], expected: str) -> dict[str, Any]:
        self._lazy_init()
        return self._verifier.verify(action_result, expected)

    def run_task(self, task: str, context: Optional[dict] = None) -> dict[str, Any]:
        self._lazy_init()

        level = self.permissions.get_level()
        if level == PermissionLevel.SAFE:
            observation = self.observe()
            return {
                "success": True,
                "task": task,
                "observation": observation,
                "note": "Safe Mode: read-only observation returned. Use Smart or Autonomous mode for actions.",
            }

        self._current_task = task
        task_result = self._planner.execute_task_loop(
            task=task,
            context=context,
            permission_level=level,
        )
        self._current_task = None
        return task_result

    def shutdown(self):
        """Clean up resources: overlay, executor sessions, etc."""
        try:
            if self._executor:
                self._executor.shutdown()
        except Exception as e:
            logger.warning("Executor shutdown failed: %s", e)
        try:
            if self._overlay:
                self._overlay.hide()
        except Exception as e:
            logger.warning("Overlay hide failed: %s", e)


_computer_agent_instance: Optional[ComputerAgent] = None


def get_computer_agent(config: Optional[ComputerUseConfig] = None) -> ComputerAgent:
    global _computer_agent_instance
    if _computer_agent_instance is None:
        _computer_agent_instance = ComputerAgent(config)
    return _computer_agent_instance
