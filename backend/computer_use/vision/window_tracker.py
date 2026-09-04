"""Active window tracking and window listing for Linux desktops.

Supports EWMH/NetWM compliant window managers via X11. Falls back to
xdotool or wmctrl where available.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    id: int
    title: str
    wm_class: str
    wm_instance: str
    x: int
    y: int
    width: int
    height: int
    is_active: bool
    pid: Optional[int] = None
    desktop: int = 0


class WindowTracker:
    """Tracks active windows and lists all visible windows on the desktop."""

    def __init__(self):
        self._ewmh = None
        self._x11_display = None
        self._init_backend()

    def _init_backend(self):
        try:
            from ewmh import EWMH
            self._ewmh = EWMH()
            logger.debug("Window tracker backend: EWMH")
        except ImportError:
            logger.debug("EWMH not available, falling back to CLI tools")

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if self._ewmh:
            try:
                win = self._ewmh.getActiveWindow()
                if win:
                    title = self._ewmh.getWmName(win)
                    wm_class = self._ewmh.getWmClass(win) or ("", "")
                    geom = self._ewmh.getGeometry(win) if hasattr(self._ewmh, "getGeometry") else None
                    pid = None
                    try:
                        pid_win = self._ewmh.getWmPid(win)
                        if pid_win:
                            pid = int(pid_win) if hasattr(pid_win, "__int__") else None
                    except Exception:
                        pass
                    return {
                        "id": str(win),
                        "title": title or "",
                        "wm_class": wm_class[1] if wm_class and len(wm_class) > 1 else "",
                        "wm_instance": wm_class[0] if wm_class else "",
                        "x": geom.x if geom else 0,
                        "y": geom.y if geom else 0,
                        "width": geom.width if geom else 0,
                        "height": geom.height if geom else 0,
                        "pid": pid,
                    }
            except Exception as e:
                logger.debug("EWMH active window failed: %s", e)

        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowpid"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                return {"id": parts[0] if parts else "", "title": self._get_title(parts[0]) if parts else ""}
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                wid = result.stdout.strip()
                return {"id": wid, "title": self._get_title(wid)}
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["wmctrl", "-a", ":ACTIVE:", "-lp"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        parts = line.split(None, 3)
                        if len(parts) >= 4:
                            return {"id": parts[0], "title": parts[3]}
        except Exception:
            pass

        return None

    def _get_title(self, wid: str) -> str:
        try:
            result = subprocess.run(
                ["xdotool", "getwindowname", wid],
                capture_output=True, text=True, timeout=2,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def list_windows(self) -> List[Dict[str, Any]]:
        windows = []

        if self._ewmh:
            try:
                for win in self._ewmh.getClientList():
                    try:
                        title = self._ewmh.getWmName(win) or ""
                        wm_class = self._ewmh.getWmClass(win) or ("", "")
                        geom = self._ewmh.getGeometry(win) if hasattr(self._ewmh, "getGeometry") else None
                        windows.append({
                            "id": str(win),
                            "title": title,
                            "wm_class": wm_class[1] if wm_class and len(wm_class) > 1 else "",
                            "x": geom.x if geom else 0,
                            "y": geom.y if geom else 0,
                            "width": geom.width if geom else 0,
                            "height": geom.height if geom else 0,
                        })
                    except Exception:
                        continue
                return windows
            except Exception as e:
                logger.debug("EWMH list windows failed: %s", e)

        try:
            result = subprocess.run(
                ["wmctrl", "-lG"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(None, 7)
                    if len(parts) >= 7:
                        windows.append({
                            "id": parts[0],
                            "desktop": parts[1],
                            "pid": parts[2],
                            "x": int(parts[3]),
                            "y": int(parts[4]),
                            "width": int(parts[5]),
                            "height": int(parts[6]),
                            "title": parts[7] if len(parts) > 7 else "",
                        })
        except Exception:
            pass

        return windows
