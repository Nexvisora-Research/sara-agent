"""APScheduler adapter for recurring Phase A task creation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class TaskScheduler:
    """Thin adapter that keeps APScheduler optional until scheduling is used."""

    def __init__(self) -> None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
        except ImportError as exc:
            raise RuntimeError("Scheduling requires: pip install apscheduler") from exc
        self._scheduler = AsyncIOScheduler()

    def add_interval_job(
        self,
        callback: Callable[..., Any],
        *,
        seconds: float,
        job_id: str,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._scheduler.add_job(
            callback,
            "interval",
            seconds=seconds,
            id=job_id,
            kwargs=kwargs or {},
            replace_existing=True,
        )

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

