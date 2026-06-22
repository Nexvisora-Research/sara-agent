"""Notification fan-out for background jobs and watchers."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

NotificationCallback = Callable[[str, str], Awaitable[None]]


class NotificationService:
    def __init__(self) -> None:
        self._callbacks: list[NotificationCallback] = []
        self._logger = logging.getLogger("sara.phase_a.notifications")

    def register(self, callback: NotificationCallback) -> None:
        self._callbacks.append(callback)

    async def send(self, title: str, message: str) -> None:
        self._logger.info("%s: %s", title, message)
        for callback in tuple(self._callbacks):
            try:
                await callback(title, message)
            except Exception:
                self._logger.exception("notification callback failed")

