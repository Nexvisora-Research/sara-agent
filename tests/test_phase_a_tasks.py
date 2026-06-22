"""Focused tests for the Phase A persistent task engine."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from core.database import Database
from core.models import TaskStatus
from core.tasks import BackgroundTaskEngine, TaskStore


class BackgroundTaskEngineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        database = Database(Path(self.tempdir.name) / "phase_a.db")
        self.store = TaskStore(database)
        self.engine = BackgroundTaskEngine(self.store, poll_interval=0.01)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    async def test_persists_and_completes_task_with_logs(self) -> None:
        async def handler(task, context):
            context.log("working")
            return {"answer": task.payload["value"] * 2}

        self.engine.register_handler("double", handler)
        record = self.engine.create_task("Double", "double", {"value": 21})

        self.assertEqual(await self.engine.run_pending(), 1)
        completed = await self.engine.wait(record.id)

        self.assertIsNotNone(completed)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)
        self.assertIn('"answer": 42', completed.result)
        self.assertIn("working", completed.logs)

    async def test_cancels_running_task_and_persists_status(self) -> None:
        started = asyncio.Event()

        async def handler(task, context):
            started.set()
            await asyncio.sleep(60)

        self.engine.register_handler("slow", handler)
        record = self.engine.create_task("Slow", "slow")
        await self.engine.run_pending()
        await started.wait()

        self.assertTrue(await self.engine.cancel(record.id))
        cancelled = self.store.get(record.id)
        self.assertEqual(cancelled.status, TaskStatus.CANCELLED)

    async def test_lists_persisted_tasks(self) -> None:
        async def handler(task, context):
            return "ok"

        self.engine.register_handler("noop", handler)
        self.engine.create_task("One", "noop")
        self.engine.create_task("Two", "noop")
        self.assertEqual(len(self.store.list()), 2)


if __name__ == "__main__":
    unittest.main()
