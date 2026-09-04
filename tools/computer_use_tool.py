"""Computer Use tool for Sara Agent.

Integrates the backend/computer_use subsystem into the agent's tool system.
Provides high-level tools for desktop automation tasks.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from tools.registry import registry, tool_result, tool_error

logger = logging.getLogger(__name__)

_COMPUTER_AGENT_CACHE = None


def _get_computer_agent():
    global _COMPUTER_AGENT_CACHE
    if _COMPUTER_AGENT_CACHE is None:
        from backend.computer_use import ComputerAgent
        from backend.computer_use.config import ComputerUseConfig
        config = ComputerUseConfig.from_env()
        _COMPUTER_AGENT_CACHE = ComputerAgent(config)
    return _COMPUTER_AGENT_CACHE


def _handle_computer_task(args: Dict[str, Any]) -> str:
    task = args.get("task", "")
    if not task:
        return tool_error("Task description is required")

    mode = args.get("mode", "smart")
    agent = _get_computer_agent()
    agent.config.permission_level = mode

    try:
        result = agent.run_task(task)
        return tool_result(
            success=result.get("success", False),
            data={
                "task": result.get("task", ""),
                "success": result.get("success", False),
                "iterations": result.get("iterations", 0),
                "actions_taken": result.get("actions_taken", 0),
                "summary": _summarize_task_result(result),
            },
        )
    except Exception as e:
        logger.exception("Computer task failed")
        return tool_error(str(e))


def _handle_computer_observe(args: Dict[str, Any]) -> str:
    agent = _get_computer_agent()
    try:
        observation = agent.observe()
        summary = {
            "active_window": (observation.get("active_window") or {}).get("title", "Unknown"),
            "window_count": len(observation.get("windows", [])),
            "detected_elements": len(observation.get("elements", [])),
            "ui_tree_available": observation.get("ui_tree") is not None,
            "element_types": _count_element_types(observation.get("elements", [])),
        }
        return tool_result(data={
            "summary": summary,
            "screenshots_available": bool(observation.get("screenshots")),
        })
    except Exception as e:
        return tool_error(str(e))


def _handle_computer_action(args: Dict[str, Any]) -> str:
    action_type = args.get("type", "")
    if not action_type:
        return tool_error("Action type is required")

    agent = _get_computer_agent()
    action = {k: v for k, v in args.items() if k != "mode"}
    mode = args.get("mode", "")

    if mode:
        agent.config.permission_level = mode

    try:
        result = agent.execute_action(action)
        return tool_result(
            success=result.get("success", False),
            data={
                "action": action_type,
                "success": result.get("success", False),
                "error": result.get("error"),
                "screenshot_after": result.get("state_after") is not None,
            },
        )
    except Exception as e:
        return tool_error(str(e))


def _handle_computer_screenshot(args: Dict[str, Any]) -> str:
    from backend.computer_use.vision.screen_capture import ScreenCapture
    from backend.computer_use.config import ComputerUseConfig
    sc = ScreenCapture(ComputerUseConfig.from_env())
    cap = sc.capture_primary()
    if not cap:
        return tool_error("Failed to capture screenshot")

    path = args.get("save_path", "")
    if path:
        try:
            with open(path, "wb") as f:
                f.write(cap.image_data)
        except Exception as e:
            return tool_error(f"Failed to save screenshot: {e}")

    return tool_result(data={
        "width": cap.monitor.width,
        "height": cap.monitor.height,
        "timestamp": cap.timestamp,
        "data": cap.base64,
        "saved_to": path or None,
    })


def _handle_computer_status(args: Dict[str, Any]) -> str:
    agent = _get_computer_agent()
    level = agent.permissions.get_level().value
    from backend.computer_use.permissions import is_autonomous_enabled
    return tool_result(data={
        "permission_level": level,
        "autonomous_enabled": is_autonomous_enabled(),
        "overlay_active": False,
        "subsystems_initialized": agent._initialized,
    })


def _handle_computer_workflow(args: Dict[str, Any]) -> str:
    from backend.computer_use.memory.ui_memory import UIMemory
    from backend.computer_use.config import ComputerUseConfig
    memory = UIMemory(ComputerUseConfig.from_env())

    action = args.get("action", "list")
    name = args.get("name", "")

    if action == "list":
        workflows = memory.list_workflows()
        return tool_result(data={"workflows": workflows})
    elif action == "remember" and name:
        steps = args.get("steps", [])
        memory.remember_workflow(name, steps)
        return tool_result(data={"workflow": name, "steps": len(steps)})
    elif action == "get" and name:
        workflow = memory.get_workflow(name)
        if workflow:
            return tool_result(data=workflow)
        return tool_error(f"Workflow not found: {name}")
    elif action == "clear":
        memory.clear()
        return tool_result(data={"cleared": True})

    return tool_error(f"Unknown action: {action}")


def _summarize_task_result(result: Dict[str, Any]) -> str:
    if result.get("success"):
        return f"Task completed successfully in {result.get('iterations', 0)} iterations with {result.get('actions_taken', 0)} actions"
    return f"Task did not complete. {result.get('iterations', 0)} iterations, {result.get('actions_taken', 0)} actions attempted"


def _count_element_types(elements: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for el in elements:
        t = el.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts


def _check_computer_use_available() -> bool:
    try:
        from backend.computer_use.executor.action_engine import ActionEngine
        from backend.computer_use.config import ComputerUseConfig
        engine = ActionEngine(ComputerUseConfig.from_env())
        return engine.is_available
    except Exception:
        return False


COMPUTER_TASK_SCHEMA = {
    "name": "computer_task",
    "description": "Execute a desktop automation task using the Computer Agent. "
                   "The agent will observe the screen, plan actions, execute them, "
                   "and verify results. Modes: safe (read-only), smart (asks approval), "
                   "autonomous (automatic, disabled by default).",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The task to perform on the desktop",
            },
            "mode": {
                "type": "string",
                "enum": ["safe", "smart", "autonomous"],
                "description": "Permission mode: safe (read-only), smart (approval needed), autonomous (automatic)",
            },
        },
        "required": ["task"],
    },
}

COMPUTER_OBSERVE_SCHEMA = {
    "name": "computer_observe",
    "description": "Observe the current desktop state - active window, "
                   "UI elements, and accessibility tree. Does NOT perform any actions.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

COMPUTER_ACTION_SCHEMA = {
    "name": "computer_action",
    "description": "Execute a single desktop action. Actions: move_mouse, click, "
                   "double_click, drag, scroll, type_text, press_key, hotkey, wait, screenshot.",
    "parameters": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": [
                    "move_mouse", "click", "double_click", "drag",
                    "scroll", "type_text", "press_key", "hotkey",
                    "wait", "screenshot",
                ],
                "description": "Type of action to perform",
            },
            "x": {"type": "integer", "description": "X coordinate for mouse actions"},
            "y": {"type": "integer", "description": "Y coordinate for mouse actions"},
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button for click/drag",
            },
            "text": {"type": "string", "description": "Text to type for type_text"},
            "key": {"type": "string", "description": "Key to press for press_key"},
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of keys for hotkey (e.g. ['ctrl', 'c'])",
            },
            "start_x": {"type": "integer", "description": "Start X for drag"},
            "start_y": {"type": "integer", "description": "Start Y for drag"},
            "end_x": {"type": "integer", "description": "End X for drag"},
            "end_y": {"type": "integer", "description": "End Y for drag"},
            "dx": {"type": "integer", "description": "Horizontal scroll delta"},
            "dy": {"type": "integer", "description": "Vertical scroll delta (negative=up, positive=down)"},
            "seconds": {"type": "number", "description": "Seconds to wait for wait action"},
            "clicks": {"type": "integer", "description": "Number of clicks"},
        },
        "required": ["type"],
    },
}

COMPUTER_SCREENSHOT_SCHEMA = {
    "name": "computer_screenshot",
    "description": "Capture a screenshot of the primary monitor. Returns base64 encoded image.",
    "parameters": {
        "type": "object",
        "properties": {
            "save_path": {
                "type": "string",
                "description": "Optional file path to save the screenshot",
            },
        },
    },
}

COMPUTER_STATUS_SCHEMA = {
    "name": "computer_status",
    "description": "Check the current status of the Computer Use subsystem.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

COMPUTER_WORKFLOW_SCHEMA = {
    "name": "computer_workflow",
    "description": "Manage saved desktop workflows. List, remember, get, or clear automated workflows.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "remember", "get", "clear"],
                "description": "Action to perform on workflows",
            },
            "name": {
                "type": "string",
                "description": "Workflow name (required for remember/get)",
            },
            "steps": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of action steps for remember",
            },
        },
        "required": ["action"],
    },
}


registry.register(
    name="computer_task",
    toolset="computer_use",
    schema=COMPUTER_TASK_SCHEMA,
    handler=_handle_computer_task,
    check_fn=_check_computer_use_available,
    is_async=False,
    description="Execute a full desktop automation task with observe-plan-execute-verify loop",
    emoji="🖥️",
)

registry.register(
    name="computer_observe",
    toolset="computer_use",
    schema=COMPUTER_OBSERVE_SCHEMA,
    handler=_handle_computer_observe,
    check_fn=_check_computer_use_available,
    is_async=False,
    description="Observe current desktop state (window, elements, accessibility tree)",
    emoji="👁️",
)

registry.register(
    name="computer_action",
    toolset="computer_use",
    schema=COMPUTER_ACTION_SCHEMA,
    handler=_handle_computer_action,
    check_fn=_check_computer_use_available,
    is_async=False,
    description="Execute a single desktop action (click, type, move, etc.)",
    emoji="🖱️",
)

registry.register(
    name="computer_screenshot",
    toolset="computer_use",
    schema=COMPUTER_SCREENSHOT_SCHEMA,
    handler=_handle_computer_screenshot,
    check_fn=None,
    is_async=False,
    description="Capture desktop screenshot",
    emoji="📸",
)

registry.register(
    name="computer_status",
    toolset="computer_use",
    schema=COMPUTER_STATUS_SCHEMA,
    handler=_handle_computer_status,
    check_fn=None,
    is_async=False,
    description="Check Computer Use subsystem status",
    emoji="🔌",
)

registry.register(
    name="computer_workflow",
    toolset="computer_use",
    schema=COMPUTER_WORKFLOW_SCHEMA,
    handler=_handle_computer_workflow,
    check_fn=None,
    is_async=False,
    description="Manage saved desktop automation workflows",
    emoji="⚡",
)
