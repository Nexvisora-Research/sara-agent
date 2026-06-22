"""Persistent asynchronexvisora background task engine."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from .database import Database
from .models import BackgroundTask, TaskStatus, utc_now
from .notifications import NotificationService

TaskHandler = Callable[[BackgroundTask, "TaskExecutionContext"], Awaitable[Any]]


class TaskStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, task: BackgroundTask) -> BackgroundTask:
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO background_tasks (
                    id, title, handler, payload_json, status, created_at,
                    started_at, completed_at, scheduled_at, result, error, logs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._to_values(task),
            )
        return task

    def get(self, task_id: str) -> BackgroundTask | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM background_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list(self, status: TaskStatus | None = None) -> list[BackgroundTask]:
        query = "SELECT * FROM background_tasks"
        values: tuple[str, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            values = (status.value,)
        query += " ORDER BY created_at DESC"
        with self.database.connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [self._from_row(row) for row in rows]

    def due(self, now: datetime) -> list[BackgroundTask]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM background_tasks
                WHERE status = ? AND (scheduled_at IS NULL OR scheduled_at <= ?)
                ORDER BY created_at
                """,
                (TaskStatus.PENDING.value, now.isoformat()),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def save(self, task: BackgroundTask) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE background_tasks SET
                    title = ?, handler = ?, payload_json = ?, status = ?,
                    created_at = ?, started_at = ?, completed_at = ?,
                    scheduled_at = ?, result = ?, error = ?, logs = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.handler,
                    json.dumps(task.payload, sort_keys=True),
                    task.status.value,
                    task.created_at.isoformat(),
                    self._date(task.started_at),
                    self._date(task.completed_at),
                    self._date(task.scheduled_at),
                    task.result,
                    task.error,
                    task.logs,
                    task.id,
                ),
            )

    @staticmethod
    def _date(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    def _to_values(self, task: BackgroundTask) -> tuple[Any, ...]:
        return (
            task.id,
            task.title,
            task.handler,
            json.dumps(task.payload, sort_keys=True),
            task.status.value,
            task.created_at.isoformat(),
            self._date(task.started_at),
            self._date(task.completed_at),
            self._date(task.scheduled_at),
            task.result,
            task.error,
            task.logs,
        )

    @staticmethod
    def _from_row(row: Any) -> BackgroundTask:
        return BackgroundTask(
            id=row["id"],
            title=row["title"],
            handler=row["handler"],
            payload=json.loads(row["payload_json"]),
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=(
                datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None
            ),
            scheduled_at=(
                datetime.fromisoformat(row["scheduled_at"]) if row["scheduled_at"] else None
            ),
            result=row["result"],
            error=row["error"],
            logs=row["logs"],
        )


class TaskExecutionContext:
    def __init__(self, task: BackgroundTask, store: TaskStore) -> None:
        self.task = task
        self._store = store

    def log(self, message: str) -> None:
        timestamp = utc_now().isoformat()
        self.task.logs += f"[{timestamp}] {message}\n"
        self._store.save(self.task)


class BackgroundTaskEngine:
    """Persistent task runner with handler dependency injection."""

    def __init__(
        self,
        store: TaskStore,
        notifications: NotificationService | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.store = store
        self.notifications = notifications or NotificationService()
        self.poll_interval = poll_interval
        self._handlers: dict[str, TaskHandler] = {}
        self._running: dict[str, asyncio.Task[None]] = {}
        self._poller: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._logger = logging.getLogger("sara.phase_a.tasks")

    def register_handler(self, name: str, handler: TaskHandler) -> None:
        if not name.strip():
            raise ValueError("handler name cannot be empty")
        self._handlers[name] = handler

    def create_task(
        self,
        title: str,
        handler: str,
        payload: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
    ) -> BackgroundTask:
        if handler not in self._handlers:
            raise KeyError(f"unknown task handler: {handler}")
        return self.store.create(
            BackgroundTask(
                title=title,
                handler=handler,
                payload=payload or {},
                scheduled_at=scheduled_at,
            )
        )

    async def start(self) -> None:
        if self._poller and not self._poller.done():
            return
        self._stopping.clear()
        self._poller = asyncio.create_task(self._poll(), name="sara:task-poller")

    async def stop(self) -> None:
        self._stopping.set()
        if self._poller:
            await self._poller
        running = list(self._running.values())
        for task in running:
            task.cancel()
        if running:
            await asyncio.gather(*running, return_exceptions=True)

    async def run_pending(self) -> int:
        started = 0
        for record in self.store.due(utc_now()):
            if record.id in self._running:
                continue
            runner = asyncio.create_task(self._execute(record), name=f"sara:task:{record.id}")
            self._running[record.id] = runner
            runner.add_done_callback(lambda _, task_id=record.id: self._running.pop(task_id, None))
            started += 1
        return started

    async def wait(self, task_id: str) -> BackgroundTask | None:
        runner = self._running.get(task_id)
        if runner is not None:
            await runner
        return self.store.get(task_id)

    async def cancel(self, task_id: str) -> bool:
        record = self.store.get(task_id)
        if record is None or record.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            return False
        runner = self._running.get(task_id)
        if runner is not None:
            runner.cancel()
            await asyncio.gather(runner, return_exceptions=True)
        else:
            record.status = TaskStatus.CANCELLED
            record.completed_at = utc_now()
            self.store.save(record)
        return True

    async def _poll(self) -> None:
        while not self._stopping.is_set():
            await self.run_pending()
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self.poll_interval)
            except TimeoutError:
                pass

    async def _execute(self, record: BackgroundTask) -> None:
        handler = self._handlers.get(record.handler)
        if handler is None:
            record.status = TaskStatus.FAILED
            record.error = f"handler is not registered: {record.handler}"
            record.completed_at = utc_now()
            self.store.save(record)
            return
        record.status = TaskStatus.RUNNING
        record.started_at = utc_now()
        self.store.save(record)
        context = TaskExecutionContext(record, self.store)
        try:
            output = await handler(record, context)
        except asyncio.CancelledError:
            record.status = TaskStatus.CANCELLED
            record.completed_at = utc_now()
            self.store.save(record)
            await self.notifications.send("Task cancelled", record.title)
            return
        except Exception as exc:
            self._logger.exception("background task failed: %s", record.id)
            record.status = TaskStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"
        else:
            record.status = TaskStatus.COMPLETED
            record.result = output if isinstance(output, str) else json.dumps(output, default=str)
        record.completed_at = utc_now()
        self.store.save(record)
        await self.notifications.send(f"Task {record.status.value}", record.title)

