"""Sara Overlay - Always-on-top desktop assistant.

Shows current task, action, permission requests, agent thoughts, and
action history. Premium Red + Black theme.

Uses tkinter for zero-dependency overlay support. Falls back gracefully
when no GUI toolkit is available (headless/server environments).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config import ComputerUseConfig

logger = logging.getLogger(__name__)


@dataclass
class OverlayState:
    current_task: str = ""
    current_action: str = ""
    permission_request: str = ""
    agent_thoughts: List[str] = field(default_factory=list)
    action_history: List[str] = field(default_factory=list)
    status: str = "idle"


class SaraOverlay:
    """Always-on-top overlay window showing Sara's computer use status.

    Premium Red + Black theme.
    Background: #0a0a0a
    Accent: #ff1744 (Material Red)
    Text: #ffffff
    Secondary: #666666
    """

    PREMIUM_THEME = {
        "bg": "#0a0a0a",
        "fg": "#ffffff",
        "accent": "#ff1744",
        "secondary": "#888888",
        "border": "#ff1744",
        "font_family": "DejaVu Sans",
        "font_size": 10,
        "title_font_size": 13,
    }

    def __init__(self, config: ComputerUseConfig):
        self.config = config
        self._state = OverlayState()
        self._root = None
        self._window = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tk_available = False
        self._init_tk()

    def _init_tk(self):
        try:
            import tkinter as tk
            self._tk = tk
            self._tk_available = True
        except ImportError:
            logger.debug("tkinter not available - overlay disabled in headless environments")

    @property
    def is_available(self) -> bool:
        return self._tk_available and self.config.overlay_enabled

    def show(self):
        if not self.is_available or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_overlay, daemon=True)
        self._thread.start()

    def hide(self):
        self._running = False
        if self._window:
            try:
                self._window.after(0, self._window.destroy)
            except Exception:
                pass
            self._window = None

    def update_state(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._refresh()

    def add_thought(self, thought: str):
        self._state.agent_thoughts.append(thought)
        if len(self._state.agent_thoughts) > 50:
            self._state.agent_thoughts = self._state.agent_thoughts[-50:]
        self._refresh()

    def add_action(self, action_desc: str):
        self._state.action_history.append(action_desc)
        if len(self._state.action_history) > 20:
            self._state.action_history = self._state.action_history[-20:]
        self._refresh()

    def request_permission(self, request: str) -> bool:
        self._state.permission_request = request
        self._state.status = "awaiting_approval"
        self._refresh()
        result_container = [None]

        def _approve():
            result_container[0] = True
            self._state.status = "approved"
            self._state.permission_request = ""
            self._refresh()

        def _deny():
            result_container[0] = False
            self._state.status = "denied"
            self._state.permission_request = ""
            self._refresh()

        if self._window:
            try:
                self._window.after(0, lambda: self._add_permission_buttons(_approve, _deny))
            except Exception:
                pass

        timeout = self.config.overlay_opacity * 100
        for _ in range(int(timeout)):
            if result_container[0] is not None:
                break
            time.sleep(0.1)

        return result_container[0] if result_container[0] is not True else True

    def _add_permission_buttons(self, approve_cb, deny_cb):
        if not self._window:
            return
        try:
            btn_frame = self._tk.Frame(self._window, bg=self.PREMIUM_THEME["bg"])
            btn_frame.pack(side=self._tk.BOTTOM, fill=self._tk.X, padx=10, pady=5)

            approve_btn = self._tk.Button(
                btn_frame, text="✓ Approve", command=approve_cb,
                bg=self.PREMIUM_THEME["accent"], fg="#ffffff",
                relief=self._tk.FLAT, padx=15, pady=4,
                font=(self.PREMIUM_THEME["font_family"], self.PREMIUM_THEME["font_size"]),
            )
            approve_btn.pack(side=self._tk.LEFT, padx=5)

            deny_btn = self._tk.Button(
                btn_frame, text="✗ Deny", command=deny_cb,
                bg="#333333", fg="#ffffff",
                relief=self._tk.FLAT, padx=15, pady=4,
                font=(self.PREMIUM_THEME["font_family"], self.PREMIUM_THEME["font_size"]),
            )
            deny_btn.pack(side=self._tk.LEFT, padx=5)
        except Exception as e:
            logger.debug("Failed to add permission buttons: %s", e)

    def _run_overlay(self):
        try:
            root = self._tk.Tk()
            self._root = root
            root.title("Sara Overlay")
            root.geometry("380x500+50+50")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", self.config.overlay_opacity)
            root.configure(bg=self.PREMIUM_THEME["bg"])

            container = self._tk.Frame(root, bg=self.PREMIUM_THEME["bg"],
                                       highlightbackground=self.PREMIUM_THEME["border"],
                                       highlightthickness=1)
            container.pack(fill=self._tk.BOTH, expand=True, padx=1, pady=1)

            self._build_ui(container)
            root.protocol("WM_DELETE_WINDOW", lambda: None)

            def _check_running():
                if not self._running:
                    root.destroy()
                    return
                root.after(100, _check_running)

            root.after(100, _check_running)
            root.mainloop()
        except Exception as e:
            logger.error("Overlay window failed: %s", e)
            self._running = False

    def _build_ui(self, parent):
        theme = self.PREMIUM_THEME
        title_frame = self._tk.Frame(parent, bg=theme["accent"])
        title_frame.pack(fill=self._tk.X)

        title_label = self._tk.Label(
            title_frame, text="  ◆ SARA OVERLAY", bg=theme["accent"],
            fg="#ffffff", font=(theme["font_family"], theme["title_font_size"], "bold"),
            anchor=self._tk.W, pady=4,
        )
        title_label.pack(fill=self._tk.X)

        content = self._tk.Frame(parent, bg=theme["bg"])
        content.pack(fill=self._tk.BOTH, expand=True, padx=10, pady=8)

        self._status_label = self._tk.Label(
            content, text="STATUS: IDLE", bg=theme["bg"],
            fg=theme["accent"], font=(theme["font_family"], theme["font_size"], "bold"),
            anchor=self._tk.W,
        )
        self._status_label.pack(fill=self._tk.X, pady=(0, 6))

        task_header = self._tk.Label(
            content, text="CURRENT TASK", bg=theme["bg"],
            fg=theme["secondary"], font=(theme["font_family"], 8, "bold"),
            anchor=self._tk.W,
        )
        task_header.pack(fill=self._tk.X)

        self._task_label = self._tk.Label(
            content, text="No active task", bg=theme["bg"],
            fg=theme["fg"], font=(theme["font_family"], theme["font_size"]),
            anchor=self._tk.W, wraplength=340, justify=self._tk.LEFT,
        )
        self._task_label.pack(fill=self._tk.X, pady=(0, 8))

        action_header = self._tk.Label(
            content, text="CURRENT ACTION", bg=theme["bg"],
            fg=theme["secondary"], font=(theme["font_family"], 8, "bold"),
            anchor=self._tk.W,
        )
        action_header.pack(fill=self._tk.X)

        self._action_label = self._tk.Label(
            content, text="—", bg=theme["bg"],
            fg=theme["fg"], font=(theme["font_family"], theme["font_size"]),
            anchor=self._tk.W, wraplength=340,
        )
        self._action_label.pack(fill=self._tk.X, pady=(0, 8))

        thoughts_header = self._tk.Label(
            content, text="AGENT THOUGHTS", bg=theme["bg"],
            fg=theme["secondary"], font=(theme["font_family"], 8, "bold"),
            anchor=self._tk.W,
        )
        thoughts_header.pack(fill=self._tk.X)

        self._thoughts_text = self._tk.Text(
            content, bg="#141414", fg=theme["fg"],
            font=(theme["font_family"], theme["font_size"]),
            height=6, width=42, relief=self._tk.FLAT,
            highlightthickness=0, bd=0,
        )
        self._thoughts_text.pack(fill=self._tk.BOTH, expand=True, pady=(0, 6))

        history_header = self._tk.Label(
            content, text="ACTION HISTORY", bg=theme["bg"],
            fg=theme["secondary"], font=(theme["font_family"], 8, "bold"),
            anchor=self._tk.W,
        )
        history_header.pack(fill=self._tk.X)

        self._history_text = self._tk.Text(
            content, bg="#141414", fg=theme["secondary"],
            font=(theme["font_family"], 8),
            height=4, width=42, relief=self._tk.FLAT,
            highlightthickness=0, bd=0,
        )
        self._history_text.pack(fill=self._tk.BOTH, expand=True)

        close_btn = self._tk.Button(
            content, text="HIDE OVERLAY", command=self.hide,
            bg="#222222", fg="#ffffff",
            relief=self._tk.FLAT, padx=10, pady=2,
            font=(theme["font_family"], 8),
        )
        close_btn.pack(pady=(6, 0))

        self._window = parent

    def _refresh(self):
        if not self._window:
            return
        try:
            self._window.after(0, self._do_refresh)
        except Exception:
            pass

    def _do_refresh(self):
        try:
            if not self._window or not self._window.winfo_exists():
                return
            self._status_label.config(text=f"STATUS: {self._state.status.upper()}")
            self._task_label.config(text=self._state.current_task or "No active task")
            self._action_label.config(text=self._state.current_action or "—")

            self._thoughts_text.delete("1.0", self._tk.END)
            for thought in self._state.agent_thoughts[-5:]:
                self._thoughts_text.insert(self._tk.END, f"• {thought}\n")

            self._history_text.delete("1.0", self._tk.END)
            for action in self._state.action_history[-8:]:
                self._history_text.insert(self._tk.END, f"  {action}\n")
        except Exception as e:
            logger.debug("Overlay refresh error: %s", e)
