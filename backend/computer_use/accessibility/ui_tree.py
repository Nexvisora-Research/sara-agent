"""Native UI tree builder from AT-SPI with element coordinate mapping.

Transforms the raw AT-SPI accessible tree into a structured, serializable
representation with element coordinates used by the planner and executor.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .atspi_bridge import ATSPIBridge

logger = logging.getLogger(__name__)

_ELEMENT_ROLES = {
    "push button", "toggle button", "button",
    "text", "entry", "password text",
    "combo box", "spin button", "slider",
    "check box", "radio button",
    "menu", "menu item", "popup menu",
    "page tab", "tab", "tab list",
    "dialog", "alert", "window", "frame",
    "scroll pane", "split pane",
    "table", "tree", "list",
    "link", "heading",
    "tool bar", "tool tip",
    "status bar", "progress bar",
}


class UITree:
    """Build and query the desktop UI accessibility tree."""

    def __init__(self, bridge: ATSPIBridge):
        self._bridge = bridge

    def get_tree(self) -> Optional[Dict[str, Any]]:
        return self._bridge.get_ui_tree()

    def get_application_summary(self) -> List[Dict[str, Any]]:
        apps = []
        atspi_apps = self._bridge.get_applications_with_windows()
        for app in atspi_apps:
            apps.append({
                "name": app.get("name", ""),
                "windows": [
                    {"title": w.get("title", ""), "bounds": w.get("bounds", {})}
                    for w in app.get("windows", [])
                ],
            })
        return apps

    def flatten_tree(self, node: Optional[Dict[str, Any]] = None,
                     max_depth: int = 10) -> List[Dict[str, Any]]:
        if node is None:
            node = self.get_tree()
        if node is None:
            return []
        flat = []

        def _walk(n: Dict[str, Any], depth: int):
            if depth > max_depth:
                return
            role = (n.get("role") or "").lower()
            name = (n.get("name") or "").strip()
            rect = n.get("rect", {})
            is_interactive = role in _ELEMENT_ROLES
            flat.append({
                "role": role,
                "name": name,
                "bounds": rect,
                "depth": depth,
                "interactive": is_interactive,
            })
            for child in n.get("children", []):
                _walk(child, depth + 1)

        _walk(node, 0)
        return flat

    def find_element(self, text: str, role_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        text_lower = text.lower()
        node = self.get_tree()
        if not node:
            return None
        return self._search_node(node, text_lower, role_hint.lower() if role_hint else None)

    def _search_node(self, node: Dict[str, Any], text_lower: str,
                     role_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
        name = (node.get("name") or "").lower()
        role = (node.get("role") or "").lower()

        if text_lower in name:
            if role_hint is None or role_hint in role:
                rect = node.get("rect", {})
                return {
                    "role": role,
                    "name": node.get("name", ""),
                    "bounds": rect,
                    "found_by": "name_match",
                }

        for child in node.get("children", []):
            result = self._search_node(child, text_lower, role_hint)
            if result:
                return result

        return None
