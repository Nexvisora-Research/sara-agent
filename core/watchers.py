"""Portable polling monitors for folders, repositories, and logs."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path

from .models import WatchEvent

WatchCallback = Callable[[WatchEvent], Awaitable[None]]


class BaseWatcher(ABC):
    def __init__(self, path: str | Path, callback: WatchCallback, interval: float = 1.0) -> None:
        self.path = Path(path).expanduser().resolve()
        self.callback = callback
        self.interval = interval
        self._stop = asyncio.Event()

    async def run(self) -> None:
        previous = self.snapshot()
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
                break
            except TimeoutError:
                current = self.snapshot()
                if current != previous:
                    await self.callback(self.make_event(previous, current))
                    previous = current

    def stop(self) -> None:
        self._stop.set()

    @abstractmethod
    def snapshot(self) -> object: ...

    @abstractmethod
    def make_event(self, previous: object, current: object) -> WatchEvent: ...


class FolderWatcher(BaseWatcher):
    def snapshot(self) -> object:
        if not self.path.is_dir():
            return ()
        return tuple(
            sorted(
                (str(item.relative_to(self.path)), item.stat().st_mtime_ns, item.stat().st_size)
                for item in self.path.rglob("*")
                if item.is_file()
            )
        )

    def make_event(self, previous: object, current: object) -> WatchEvent:
        return WatchEvent(source="folder", path=str(self.path), kind="changed")


class RepositoryWatcher(FolderWatcher):
    def snapshot(self) -> object:
        git_dir = self.path / ".git"
        targets = [git_dir / "HEAD", git_dir / "index", git_dir / "refs"]
        values: list[tuple[str, int]] = []
        for target in targets:
            if target.is_file():
                values.append((str(target), target.stat().st_mtime_ns))
            elif target.is_dir():
                values.extend(
                    (str(item), item.stat().st_mtime_ns)
                    for item in target.rglob("*")
                    if item.is_file()
                )
        return tuple(sorted(values))

    def make_event(self, previous: object, current: object) -> WatchEvent:
        return WatchEvent(source="repository", path=str(self.path), kind="git-changed")


class LogWatcher(BaseWatcher):
    def snapshot(self) -> object:
        if not self.path.exists():
            return 0
        return self.path.stat().st_size

    def make_event(self, previous: object, current: object) -> WatchEvent:
        return WatchEvent(source="log", path=str(self.path), kind="appended")

