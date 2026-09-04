"""Real-time screen capture with multi-monitor support.

Uses mss for fast cross-platform capture. Falls back to PIL/GDK where mss
is unavailable. Supports 1-5 FPS streaming via polling.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


@dataclass
class MonitorInfo:
    id: int
    width: int
    height: int
    left: int
    top: int
    name: str
    is_primary: bool = False


@dataclass
class CaptureResult:
    monitor: MonitorInfo
    image_data: bytes
    base64: str
    timestamp: float
    format: str = "png"


class ScreenCapture:
    """Fast cross-platform screen capture with multi-monitor support."""

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._mss = None
        self._pil = None
        self._backend = None
        self._last_capture: Optional[CaptureResult] = None
        self._capture_dir = self._resolve_capture_dir()
        self._init_backend()

    def _resolve_capture_dir(self) -> Path:
        if self.config.screen_capture_dir:
            d = Path(self.config.screen_capture_dir)
        else:
            d = Path.home() / ".sara" / "screenshots"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _init_backend(self):
        if self._mss is not None:
            return
        try:
            import mss
            self._mss = mss.mss()
            self._backend = "mss"
            logger.debug("Screen capture backend: mss")
        except ImportError:
            try:
                from PIL import ImageGrab
                self._pil = ImageGrab
                self._backend = "pil"
                logger.debug("Screen capture backend: PIL (no mss)")
            except ImportError:
                logger.warning("No screen capture backend available (install mss or Pillow)")

    def list_monitors(self) -> List[MonitorInfo]:
        if self._backend == "mss":
            monitors = []
            for i, m in enumerate(self._mss.monitors):
                monitors.append(MonitorInfo(
                    id=i,
                    width=m["width"],
                    height=m["height"],
                    left=m["left"],
                    top=m["top"],
                    name=m.get("name", f"Monitor {i}"),
                    is_primary=(i == 0),
                ))
            return monitors
        return [MonitorInfo(0, 1920, 1080, 0, 0, "Primary", True)]

    def capture_monitor(self, monitor_id: int = 0) -> Optional[CaptureResult]:
        if self._backend == "mss":
            try:
                monitors = self._mss.monitors
                if monitor_id < 0 or monitor_id >= len(monitors):
                    monitor_id = 0
                raw = self._mss.grab(monitors[monitor_id])
                m = monitors[monitor_id]
                png_data = self._mss._raw_to_png(raw)
                b64 = base64.b64encode(png_data).decode("utf-8")
                info = MonitorInfo(
                    id=monitor_id,
                    width=raw.size[0],
                    height=raw.size[1],
                    left=m["left"],
                    top=m["top"],
                    name=m.get("name", f"Monitor {monitor_id}"),
                    is_primary=(monitor_id == 0),
                )
                result = CaptureResult(
                    monitor=info,
                    image_data=png_data,
                    base64=b64,
                    timestamp=time.time(),
                )
                self._last_capture = result
                return result
            except Exception as e:
                logger.error("mss capture failed: %s", e)
                return None

        elif self._backend == "pil":
            try:
                img = self._pil.grab()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_data = buf.getvalue()
                b64 = base64.b64encode(png_data).decode("utf-8")
                info = MonitorInfo(
                    id=0,
                    width=img.width,
                    height=img.height,
                    left=0,
                    top=0,
                    name="Primary",
                    is_primary=True,
                )
                result = CaptureResult(
                    monitor=info,
                    image_data=png_data,
                    base64=b64,
                    timestamp=time.time(),
                )
                self._last_capture = result
                return result
            except Exception as e:
                logger.error("PIL capture failed: %s", e)
                return None

        return None

    def capture_primary(self) -> Optional[CaptureResult]:
        return self.capture_monitor(0)

    def capture_all_monitors(self) -> List[CaptureResult]:
        results = []
        if self._backend == "mss":
            for i in range(1, len(self._mss.monitors)):
                cap = self.capture_monitor(i)
                if cap:
                    results.append(cap)
        cap = self.capture_primary()
        if cap:
            results.insert(0, cap)
        return results

    def save_screenshot(self, prefix: str = "desktop") -> Optional[str]:
        cap = self.capture_primary()
        if not cap:
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self._capture_dir / f"{prefix}_{ts}.png"
        try:
            with open(path, "wb") as f:
                f.write(cap.image_data)
            return str(path)
        except Exception as e:
            logger.error("Failed to save screenshot: %s", e)
            return None

    def stream_frames(self, fps: int = 3):
        """Generator yielding CaptureResult at target FPS."""
        interval = 1.0 / max(1, min(fps, 5))
        while True:
            cap = self.capture_primary()
            if cap:
                yield cap
            time.sleep(interval)

    def get_last_capture(self) -> Optional[CaptureResult]:
        return self._last_capture
