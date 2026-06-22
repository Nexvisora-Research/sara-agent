"""Tests for the Watch & Monitoring subsystem."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from maestro.monitor import (
    FileWatcher,
    LogWatcher,
    RepoWatcher,
    WatchManager,
    AlertEngine,
)
from maestro.models import WatchTarget, WatchTargetType, WatchEventKind, WatchEventRecord


class TestFileWatcher:
    @pytest.mark.asyncio
    async def test_detect_creation(self):
        with tempfile.TemporaryDirectory() as td:
            events = []
            async def cb(e): events.append(e)
            target = WatchTarget(
                name="test", target_type=WatchTargetType.FOLDER, path=td, interval_seconds=0.1
            )
            watcher = FileWatcher(target=target, callback=cb)
            run_task = asyncio.create_task(watcher.run())
            await asyncio.sleep(0.15)
            (Path(td) / "new.txt").write_text("hello")
            await asyncio.sleep(0.3)
            watcher.stop()
            await run_task
            assert len(events) >= 1
            assert events[0].kind == WatchEventKind.CREATED


class TestLogWatcher:
    @pytest.mark.asyncio
    async def test_detect_growth(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_path = f.name
            f.write("line1\n")
        try:
            events = []
            async def cb(e): events.append(e)
            target = WatchTarget(
                name="log", target_type=WatchTargetType.LOG, path=log_path, interval_seconds=0.1
            )
            watcher = LogWatcher(target=target, callback=cb)
            run_task = asyncio.create_task(watcher.run())
            await asyncio.sleep(0.15)
            with open(log_path, "a") as f:
                f.write("line2\n")
            await asyncio.sleep(0.3)
            watcher.stop()
            await run_task
            assert len(events) >= 1
        finally:
            import os
            os.unlink(log_path)


class TestAlertEngine:
    @pytest.mark.asyncio
    async def test_emit_routes_to_handler(self):
        engine = AlertEngine()
        received = []
        async def handler(e): received.append(e)
        engine.on("created", handler)
        event = WatchEventRecord(target_id="t1", kind=WatchEventKind.CREATED, path="/test")
        await engine.emit(event)
        assert len(received) == 1


class TestWatchManager:
    @pytest.mark.asyncio
    async def test_lifecycle(self):
        mgr = WatchManager()
        target = WatchTarget(
            name="test", target_type=WatchTargetType.FOLDER, path="/tmp", interval_seconds=10
        )
        tid = mgr.add_target(target)
        assert mgr.list_targets()[0].name == "test"
        mgr.remove_target(tid)
        assert len(mgr.list_targets()) == 0
