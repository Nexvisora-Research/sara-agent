"""Persistent memory for UI actions and desktop layouts.

Stores:
- App layouts (window positions, element locations)
- Frequently clicked buttons
- Preferred workflows
- Previous task history
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


@dataclass
class UIActionRecord:
    app: str
    action_type: str
    target_text: str
    x: int
    y: int
    success: bool
    timestamp: float
    task: str = ""
    frequency: int = 1


class UIMemory:
    """Remembers UI elements, app layouts, and action patterns."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._store_path = Path.home() / ".sara" / "computer_use_memory"
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._actions_path = self._store_path / "ui_actions.json"
        self._layouts_path = self._store_path / "app_layouts.json"
        self._workflows_path = self._store_path / "workflows.json"

        self._actions: List[Dict[str, Any]] = self._load_json(self._actions_path)
        self._layouts: Dict[str, Any] = self._load_json(self._layouts_path)
        self._workflows: List[Dict[str, Any]] = self._load_json(self._workflows_path)

    def _load_json(self, path: Path) -> Any:
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("Failed to load %s: %s", path.name, e)
        return [] if "actions" in path.name or "workflows" in path.name else {}

    def _save_json(self, path: Path, data: Any):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save %s: %s", path.name, e)

    def remember_action(self, action: Dict[str, Any], result: Dict[str, Any]):
        if not self.config.memory_enabled:
            return
        action_type = action.get("type", "")
        if action_type in ("wait", "screenshot"):
            return

        record = {
            "action_type": action_type,
            "params": {k: v for k, v in action.items() if k != "type"},
            "success": result.get("success", False),
            "timestamp": time.time(),
        }

        self._actions.append(record)
        if len(self._actions) > self.config.memory_max_actions:
            self._actions = self._actions[-self.config.memory_max_actions:]

        self._save_json(self._actions_path, self._actions)

    def get_action_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._actions[-limit:]))

    def find_frequent_actions(self, app_name: str, min_count: int = 3) -> List[Dict[str, Any]]:
        counts = defaultdict(int)
        for record in self._actions:
            params = record.get("params", {})
            if app_name.lower() in str(params).lower():
                key = (record["action_type"], str(params.get("x", "")), str(params.get("y", "")))
                counts[key] += 1

        frequent = []
        for (action_type, x, y), count in counts.items():
            if count >= min_count:
                frequent.append({
                    "action_type": action_type,
                    "x": int(x) if x else None,
                    "y": int(y) if y else None,
                    "frequency": count,
                })
        return sorted(frequent, key=lambda r: -r["frequency"])

    def remember_layout(self, app_name: str, layout: Dict[str, Any]):
        if not self.config.memory_enabled:
            return
        self._layouts[app_name] = {
            "timestamp": time.time(),
            "layout": layout,
        }
        self._save_json(self._layouts_path, self._layouts)

    def get_layout(self, app_name: str) -> Optional[Dict[str, Any]]:
        entry = self._layouts.get(app_name)
        if entry:
            return entry.get("layout")
        return None

    def remember_workflow(self, name: str, steps: List[Dict[str, Any]]):
        if not self.config.memory_enabled:
            return
        existing = [w for w in self._workflows if w["name"] == name]
        if existing:
            existing[0]["steps"] = steps
            existing[0]["timestamp"] = time.time()
        else:
            self._workflows.append({
                "name": name,
                "steps": steps,
                "timestamp": time.time(),
                "use_count": 0,
            })
        self._save_json(self._workflows_path, self._workflows)

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        for w in self._workflows:
            if w["name"] == name:
                w["use_count"] = w.get("use_count", 0) + 1
                self._save_json(self._workflows_path, self._workflows)
                return w
        return None

    def list_workflows(self) -> List[Dict[str, Any]]:
        return [
            {"name": w["name"], "steps": len(w.get("steps", [])), "use_count": w.get("use_count", 0)}
            for w in self._workflows
        ]

    def clear(self):
        self._actions = []
        self._layouts = {}
        self._workflows = []
        self._save_json(self._actions_path, self._actions)
        self._save_json(self._layouts_path, self._layouts)
        self._save_json(self._workflows_path, self._workflows)
