"""Kanban Task Board — project management with columns, priorities, and metrics."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from .models import (
    KanbanBoard,
    KanbanColumn,
    KanbanTask,
    TaskPriority,
    WorkflowStatus,
    new_id,
    utc_now,
)

logger = logging.getLogger("sara.maestro.kanban")

# ── Database abstraction ──────────────────────────────────────────────────────
# Accept either raw sqlite3.Connection or core.database.Database so that
# maestro does not have a hard import dependency on core.


class _DatabaseBackend:
    """Thin wrapper to unify raw Connection and core Database."""
    __slots__ = ("_conn", "_db")

    def __init__(self, connection_or_db: Any) -> None:
        self._conn: sqlite3.Connection | None = None
        self._db: Any = None
        if isinstance(connection_or_db, sqlite3.Connection):
            self._conn = connection_or_db
        else:
            self._db = connection_or_db  # core.database.Database

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._conn is not None:
            yield self._conn
        else:
            with self._db.transaction() as conn:
                yield conn


class KanbanTaskStore:
    """SQLite-backed persistent store for kanban tasks.

    Accepts either a raw ``sqlite3.Connection`` or a ``core.database.Database``
    instance (duck-typed via ``.transaction()`` context manager).
    """

    def __init__(self, connection_or_db: Any) -> None:
        self._backend = _DatabaseBackend(connection_or_db)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._backend.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS kanban_tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    column_name TEXT NOT NULL DEFAULT 'backlog',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    assigned_agent TEXT,
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    tags TEXT NOT NULL DEFAULT '[]',
                    board_id TEXT NOT NULL DEFAULT '',
                    parent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_kanban_column ON kanban_tasks(column_name);
                CREATE INDEX IF NOT EXISTS idx_kanban_board ON kanban_tasks(board_id);
                CREATE INDEX IF NOT EXISTS idx_kanban_assigned ON kanban_tasks(assigned_agent);
                CREATE TABLE IF NOT EXISTS kanban_boards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
            """)

    def create_task(self, task: KanbanTask) -> KanbanTask:
        with self._backend.connection() as conn:
            conn.execute(
                """
                INSERT INTO kanban_tasks
                    (id, title, description, column_name, priority, assigned_agent,
                     dependencies, tags, board_id, parent_id, created_at, updated_at,
                     started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id, task.title, task.description, task.column.value,
                    task.priority.value, task.assigned_agent,
                    json.dumps(task.dependencies), json.dumps(task.tags),
                    task.board_id, task.parent_id,
                    task.created_at.isoformat(), task.updated_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                ),
            )
        return task

    def get_task(self, task_id: str) -> KanbanTask | None:
        with self._backend.connection() as conn:
            row = conn.execute(
                "SELECT * FROM kanban_tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return self._row_to_task(row) if row else None

    def list_tasks(self, board_id: str | None = None) -> list[KanbanTask]:
        with self._backend.connection() as conn:
            if board_id:
                rows = conn.execute(
                    "SELECT * FROM kanban_tasks WHERE board_id = ? ORDER BY created_at DESC",
                    (board_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM kanban_tasks ORDER BY created_at DESC"
                ).fetchall()
            return [self._row_to_task(row) for row in rows]

    def list_by_column(self, column: KanbanColumn, board_id: str | None = None) -> list[KanbanTask]:
        with self._backend.connection() as conn:
            if board_id:
                rows = conn.execute(
                    "SELECT * FROM kanban_tasks WHERE column_name = ? AND board_id = ? ORDER BY priority DESC",
                    (column.value, board_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM kanban_tasks WHERE column_name = ? ORDER BY priority DESC",
                    (column.value,),
                ).fetchall()
            return [self._row_to_task(row) for row in rows]

    def update_task(self, task: KanbanTask) -> None:
        task.updated_at = utc_now()
        with self._backend.connection() as conn:
            conn.execute(
                """
                UPDATE kanban_tasks SET
                    title = ?, description = ?, column_name = ?, priority = ?,
                    assigned_agent = ?, dependencies = ?, tags = ?, board_id = ?,
                    parent_id = ?, updated_at = ?, started_at = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    task.title, task.description, task.column.value,
                    task.priority.value, task.assigned_agent,
                    json.dumps(task.dependencies), json.dumps(task.tags),
                    task.board_id, task.parent_id, task.updated_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.id,
                ),
            )

    def move_task(self, task_id: str, column: KanbanColumn) -> KanbanTask | None:
        task = self.get_task(task_id)
        if not task:
            return None
        task.column = column
        task.updated_at = utc_now()
        if column == KanbanColumn.IN_PROGRESS and task.started_at is None:
            task.started_at = utc_now()
        if column == KanbanColumn.COMPLETED:
            task.completed_at = utc_now()
        self.update_task(task)
        return task

    def delete_task(self, task_id: str) -> bool:
        with self._backend.connection() as conn:
            cursor = conn.execute("DELETE FROM kanban_tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0

    def create_board(self, board: KanbanBoard) -> KanbanBoard:
        with self._backend.connection() as conn:
            conn.execute(
                "INSERT INTO kanban_boards (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (board.id, board.name, board.description, board.created_at.isoformat()),
            )
        return board

    def list_boards(self) -> list[KanbanBoard]:
        with self._backend.connection() as conn:
            rows = conn.execute("SELECT * FROM kanban_boards ORDER BY created_at DESC").fetchall()
            return [KanbanBoard(**dict(row)) for row in rows]

    def search_tasks(self, query: str) -> list[KanbanTask]:
        pattern = f"%{query}%"
        with self._backend.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM kanban_tasks
                WHERE title LIKE ? OR description LIKE ? OR assigned_agent LIKE ?
                ORDER BY priority DESC
                """,
                (pattern, pattern, pattern),
            ).fetchall()
            return [self._row_to_task(row) for row in rows]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> KanbanTask:
        return KanbanTask(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            column=KanbanColumn(row["column_name"]),
            priority=TaskPriority(row["priority"]),
            assigned_agent=row["assigned_agent"],
            dependencies=json.loads(row["dependencies"]),
            tags=json.loads(row["tags"]),
            board_id=row["board_id"],
            parent_id=row["parent_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )


class ColumnManager:
    """Manages column transitions and valid moves."""

    VALID_TRANSITIONS: dict[KanbanColumn, list[KanbanColumn]] = {
        KanbanColumn.BACKLOG: [KanbanColumn.READY],
        KanbanColumn.READY: [KanbanColumn.IN_PROGRESS, KanbanColumn.BACKLOG],
        KanbanColumn.IN_PROGRESS: [KanbanColumn.REVIEW, KanbanColumn.READY],
        KanbanColumn.REVIEW: [KanbanColumn.COMPLETED, KanbanColumn.IN_PROGRESS],
        KanbanColumn.COMPLETED: [KanbanColumn.ARCHIVED, KanbanColumn.REVIEW],
        KanbanColumn.ARCHIVED: [],
    }

    def can_move(self, task: KanbanTask, target: KanbanColumn) -> bool:
        allowed = self.VALID_TRANSITIONS.get(task.column, [])
        return target in allowed

    def suggested_next(self, task: KanbanTask) -> KanbanColumn | None:
        allowed = self.VALID_TRANSITIONS.get(task.column, [])
        return allowed[0] if allowed else None


class BoardMetrics:
    """Compute board statistics and cycle times."""

    def compute(self, tasks: list[KanbanTask]) -> dict[str, Any]:
        column_counts: dict[str, int] = Counter()
        priority_counts: dict[str, int] = Counter()
        unassigned = 0
        cycle_times: list[float] = []

        for task in tasks:
            column_counts[task.column.value] += 1
            priority_counts[task.priority.value] += 1
            if not task.assigned_agent:
                unassigned += 1
            if task.started_at and task.completed_at:
                delta = (task.completed_at - task.started_at).total_seconds()
                cycle_times.append(delta)

        total = len(tasks)
        return {
            "total_tasks": total,
            "by_column": dict(column_counts),
            "by_priority": dict(priority_counts),
            "unassigned": unassigned,
            "avg_cycle_time_seconds": sum(cycle_times) / len(cycle_times) if cycle_times else 0,
            "completion_rate": column_counts.get("completed", 0) / total if total else 0,
            "wip_count": column_counts.get("in_progress", 0),
        }


class BoardManager:
    """High-level kanban board operations."""

    def __init__(self, store: KanbanTaskStore) -> None:
        self.store = store
        self.columns = ColumnManager()
        self.metrics = BoardMetrics()

    def create_task(
        self,
        title: str,
        description: str = "",
        column: KanbanColumn = KanbanColumn.BACKLOG,
        priority: TaskPriority = TaskPriority.MEDIUM,
        board_id: str = "",
    ) -> KanbanTask:
        task = KanbanTask(
            title=title,
            description=description,
            column=column,
            priority=priority,
            board_id=board_id,
        )
        return self.store.create_task(task)

    def move_task(self, task_id: str, target_column: KanbanColumn) -> KanbanTask | None:
        task = self.store.get_task(task_id)
        if not task:
            logger.warning("Task %s not found", task_id)
            return None
        if not self.columns.can_move(task, target_column):
            logger.warning("Cannot move task %s from %s to %s", task_id, task.column, target_column)
            return None
        return self.store.move_task(task_id, target_column)

    def get_board_stats(self, board_id: str | None = None) -> dict[str, Any]:
        tasks = self.store.list_tasks(board_id)
        return self.metrics.compute(tasks)
