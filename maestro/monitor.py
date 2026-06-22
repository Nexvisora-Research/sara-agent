"""Watch & Monitoring System — real-time file, repo, and log monitoring with alerting."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .models import (
    WatchEventKind,
    WatchEventRecord,
    WatchTarget,
    WatchTargetType,
    new_id,
    utc_now,
)

logger = logging.getLogger("sara.maestro.monitor")

WatchCallback = Callable[[WatchEventRecord], Awaitable[None]]


class BaseWatcher(ABC):
    """Polling base watcher with configurable interval."""

    def __init__(
        self,
        target: WatchTarget,
        callback: WatchCallback,
    ) -> None:
        self.target = target
        self.callback = callback
        self._stop = asyncio.Event()
        self._running = False

    async def run(self) -> None:
        self._running = True
        previous = self.snapshot()
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.target.interval_seconds)
            except TimeoutError:
                current = self.snapshot()
                events = self.diff(previous, current)
                for event in events:
                    if self._matches_rules(event):
                        await self.callback(event)
                previous = current

    def stop(self) -> None:
        self._stop.set()
        self._running = False

    @abstractmethod
    def snapshot(self) -> object: ...

    @abstractmethod
    def diff(self, previous: object, current: object) -> list[WatchEventRecord]: ...

    def _matches_rules(self, event: WatchEventRecord) -> bool:
        if not self.target.rules:
            return True
        for rule in self.target.rules:
            if rule.event_kind and rule.event_kind != event.kind:
                continue
            if rule.pattern and rule.pattern != "*":
                from fnmatch import fnmatch
                if not fnmatch(event.path, rule.pattern):
                    continue
            return True
        return False


class FileWatcher(BaseWatcher):
    """Monitor a directory for file changes."""

    def snapshot(self) -> object:
        path = Path(self.target.path)
        if not path.is_dir():
            return {}
        snapshot: dict[str, tuple[float, int]] = {}
        for item in path.rglob("*"):
            if item.is_file():
                stat = item.stat()
                snapshot[str(item.relative_to(path))] = (stat.st_mtime_ns, stat.st_size)
        return snapshot

    def diff(self, previous: object, current: object) -> list[WatchEventRecord]:
        prev = dict(previous) if isinstance(previous, dict) else {}
        curr = dict(current) if isinstance(current, dict) else {}
        events: list[WatchEventRecord] = []
        prev_keys = set(prev)
        curr_keys = set(curr)

        for key in curr_keys - prev_keys:
            events.append(WatchEventRecord(
                target_id=self.target.id,
                kind=WatchEventKind.CREATED,
                path=str(Path(self.target.path) / key),
                message=f"File created: {key}",
            ))

        for key in prev_keys - curr_keys:
            events.append(WatchEventRecord(
                target_id=self.target.id,
                kind=WatchEventKind.DELETED,
                path=str(Path(self.target.path) / key),
                message=f"File deleted: {key}",
            ))

        for key in curr_keys & prev_keys:
            if curr[key] != prev[key]:
                events.append(WatchEventRecord(
                    target_id=self.target.id,
                    kind=WatchEventKind.MODIFIED,
                    path=str(Path(self.target.path) / key),
                    message=f"File modified: {key}",
                ))

        return events


class RepoWatcher(FileWatcher):
    """Monitor a git repository for changes (HEAD, index, refs)."""

    def snapshot(self) -> object:
        git_dir = Path(self.target.path) / ".git"
        targets = [git_dir / "HEAD", git_dir / "index"]
        refs_dir = git_dir / "refs"
        snapshot: dict[str, float] = {}
        for target in targets:
            if target.is_file():
                snapshot[str(target)] = target.stat().st_mtime_ns
        if refs_dir.is_dir():
            for item in refs_dir.rglob("*"):
                if item.is_file():
                    snapshot[str(item)] = item.stat().st_mtime_ns
        return snapshot

    def diff(self, previous: object, current: object) -> list[WatchEventRecord]:
        prev = dict(previous) if isinstance(previous, dict) else {}
        curr = dict(current) if isinstance(current, dict) else {}
        events: list[WatchEventRecord] = []
        for key in curr:
            if curr.get(key) != prev.get(key):
                events.append(WatchEventRecord(
                    target_id=self.target.id,
                    kind=WatchEventKind.MODIFIED,
                    path=str(key),
                    message=f"Repository changed: {key}",
                ))
        return events


class LogWatcher(BaseWatcher):
    """Monitor a log file for new content."""

    def snapshot(self) -> object:
        path = Path(self.target.path)
        if not path.exists():
            return 0
        return path.stat().st_size

    def diff(self, previous: object, current: object) -> list[WatchEventRecord]:
        prev_size = int(previous) if isinstance(previous, (int, float)) else 0
        curr_size = int(current) if isinstance(current, (int, float)) else 0
        if curr_size > prev_size:
            return [WatchEventRecord(
                target_id=self.target.id,
                kind=WatchEventKind.MODIFIED,
                path=self.target.path,
                message=f"Log grew by {curr_size - prev_size} bytes",
            )]
        return []


class AlertEngine:
    """Process watch events and trigger configured actions."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[WatchCallback]] = {}

    def on(self, event_kind: str, handler: WatchCallback) -> None:
        self._handlers.setdefault(event_kind, []).append(handler)

    async def emit(self, event: WatchEventRecord) -> None:
        handlers = self._handlers.get(event.kind.value, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception("Alert handler failed for %s", event.id)


class WatchManager:
    """Manage multiple watchers and their lifecycle."""

    def __init__(self, alert_engine: AlertEngine | None = None) -> None:
        self.alert_engine = alert_engine or AlertEngine()
        self._targets: dict[str, WatchTarget] = {}
        self._watchers: dict[str, BaseWatcher] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def add_target(self, target: WatchTarget) -> str:
        self._targets[target.id] = target
        return target.id

    def remove_target(self, target_id: str) -> bool:
        self.stop_watcher(target_id)
        self._tasks.pop(target_id, None)
        self._watchers.pop(target_id, None)
        return self._targets.pop(target_id, None) is not None

    def start_watcher(self, target_id: str) -> bool:
        target = self._targets.get(target_id)
        if not target or not target.enabled:
            return False

        watcher = self._build_watcher(target)
        if not watcher:
            return False

        self._watchers[target_id] = watcher
        task = asyncio.create_task(
            watcher.run(),
            name=f"sara:watch:{target.name}",
        )
        self._tasks[target_id] = task
        logger.info("Started watcher %s (%s)", target.name, target.target_type.value)
        return True

    def stop_watcher(self, target_id: str) -> None:
        watcher = self._watchers.get(target_id)
        if watcher:
            watcher.stop()
        task = self._tasks.get(target_id)
        if task and not task.done():
            task.cancel()

    def start_all(self) -> None:
        for target_id in self._targets:
            if self._targets[target_id].enabled:
                self.start_watcher(target_id)

    def stop_all(self) -> None:
        for target_id in list(self._targets):
            self.stop_watcher(target_id)

    def list_targets(self) -> list[WatchTarget]:
        return list(self._targets.values())

    def get_events(self, target_id: str) -> list[WatchEventRecord]:
        return []

    def _build_watcher(self, target: WatchTarget) -> BaseWatcher | None:
        async def callback(event: WatchEventRecord) -> None:
            await self.alert_engine.emit(event)

        factory: dict[WatchTargetType, type[BaseWatcher]] = {
            WatchTargetType.FOLDER: FileWatcher,
            WatchTargetType.REPOSITORY: RepoWatcher,
            WatchTargetType.LOG: LogWatcher,
        }
        cls = factory.get(target.target_type)
        if cls:
            return cls(target=target, callback=callback)
        logger.warning("No watcher for type %s", target.target_type)
        return None
