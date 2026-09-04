"""AT-SPI bridge for Linux desktop accessibility.

Provides native UI tree access via the Linux Accessibility Toolkit (AT-SPI2).
Falls back gracefully when pyatspi is not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ATSPIBridge:
    """Bridge to the Linux AT-SPI2 accessibility bus.

    Provides access to the native UI accessibility tree of running
    applications. All methods are safe to call when AT-SPI is unavailable.
    """

    def __init__(self):
        self._available = False
        self._registry = None
        self._init_atspi()

    def _init_atspi(self):
        try:
            import pyatspi
            self._registry = pyatspi.Registry
            pyatspi.Registry.getDesktop(0)
            self._available = True
            logger.info("AT-SPI2 accessibility bridge initialized")
        except ImportError:
            logger.debug("pyatspi not available (install python3-pyatspi on Debian/Ubuntu)")
        except Exception as e:
            logger.debug("AT-SPI init failed: %s", e)

    @property
    def is_available(self) -> bool:
        return self._available

    def get_desktop(self, desktop_id: int = 0) -> Optional[Any]:
        if not self._available:
            return None
        try:
            return self._registry.getDesktop(desktop_id)
        except Exception as e:
            logger.debug("getDesktop(%d) failed: %s", desktop_id, e)
            return None

    def get_application_list(self) -> List[Dict[str, Any]]:
        if not self._available:
            return self._fallback_application_list()
        apps = []
        try:
            desktop = self.get_desktop(0)
            if desktop is None:
                return self._fallback_application_list()
            for i in range(desktop.getChildCount()):
                app = desktop[i]
                try:
                    apps.append({
                        "name": app.name or "",
                        "id": i,
                        "child_count": app.getChildCount(),
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.debug("Application list via AT-SPI failed: %s", e)
            return self._fallback_application_list()
        return apps

    def _fallback_application_list(self) -> List[Dict[str, Any]]:
        apps = []
        try:
            import subprocess
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                seen = set()
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(None, 3)
                    if len(parts) >= 4 and parts[3]:
                        name = parts[3].split(" - ")[0].split(" — ")[0]
                        if name not in seen:
                            seen.add(name)
                            apps.append({"name": name, "id": len(apps), "child_count": 0})
        except Exception:
            pass
        return apps

    def get_ui_tree(self, app_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        try:
            desktop = self.get_desktop(0)
            if desktop is None:
                return None
            return self._build_tree(desktop, app_filter, depth=0, max_depth=8)
        except Exception as e:
            logger.debug("UI tree via AT-SPI failed: %s", e)
            return None

    def _build_tree(self, obj: Any, app_filter: Optional[str] = None,
                    depth: int = 0, max_depth: int = 8) -> Dict[str, Any]:
        if depth > max_depth:
            return {"role": "truncated", "name": "", "children": []}

        try:
            name = obj.name or ""
            role_name = obj.getRoleName() if hasattr(obj, "getRoleName") else ""
        except Exception:
            name = ""
            role_name = ""

        if app_filter and app_filter.lower() not in name.lower() and depth < 2:
            return {"role": role_name, "name": name, "children": []}

        try:
            rect = obj.queryComponent().getExtents(0) if hasattr(obj, "queryComponent") else None
        except Exception:
            rect = None

        node = {
            "role": role_name,
            "name": name,
            "rect": {
                "x": rect.x if rect else 0,
                "y": rect.y if rect else 0,
                "width": rect.width if rect else 0,
                "height": rect.height if rect else 0,
            } if rect else {},
            "children": [],
        }

        try:
            for i in range(obj.getChildCount()):
                try:
                    child = obj[i]
                    child_node = self._build_tree(child, app_filter, depth + 1, max_depth)
                    if child_node.get("children") or child_node.get("name"):
                        node["children"].append(child_node)
                except (IndexError, Exception):
                    continue
        except Exception:
            pass

        return node

    def get_applications_with_windows(self) -> List[Dict[str, Any]]:
        apps = []
        if not self._available:
            return apps
        try:
            desktop = self.get_desktop(0)
            if desktop is None:
                return apps
            for i in range(desktop.getChildCount()):
                try:
                    app = desktop[i]
                    app_info = {
                        "name": app.name or "",
                        "id": i,
                        "windows": [],
                    }
                    for j in range(app.getChildCount()):
                        try:
                            win = app[j]
                            win_name = win.name or ""
                            win_role = win.getRoleName() if hasattr(win, "getRoleName") else ""
                            try:
                                comp = win.queryComponent()
                                rect = comp.getExtents(0)
                                bounds = {"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height}
                            except Exception:
                                bounds = {}
                            if win_name or win_role:
                                app_info["windows"].append({
                                    "title": win_name,
                                    "role": win_role,
                                    "bounds": bounds,
                                })
                        except Exception:
                            continue
                    if app_info["windows"]:
                        apps.append(app_info)
                except Exception:
                    continue
        except Exception as e:
            logger.debug("AT-SPI app windows failed: %s", e)
        return apps

    def get_active_element(self) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        try:
            desktop = self.get_desktop(0)
            if desktop is None:
                return None
            focused = desktop.getCurrentlyFocusedAccessible() if hasattr(desktop, "getCurrentlyFocusedAccessible") else None
            if focused:
                name = focused.name or ""
                role = focused.getRoleName() if hasattr(focused, "getRoleName") else ""
                return {"name": name, "role": role}
        except Exception as e:
            logger.debug("Get active element failed: %s", e)
        return None
