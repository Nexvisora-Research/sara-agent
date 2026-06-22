"""Tests for the Kanban Task Board subsystem."""

import tempfile
import sqlite3

import pytest

from maestro.kanban import (
    BoardManager,
    KanbanTaskStore,
    ColumnManager,
    BoardMetrics,
)
from maestro.models import KanbanTask, KanbanBoard, KanbanColumn, TaskPriority


@pytest.fixture
def store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ks = KanbanTaskStore(conn)
    return ks


@pytest.fixture
def board_manager(store):
    return BoardManager(store)


class TestKanbanTaskStore:
    def test_create_and_get(self, store):
        task = store.create_task(KanbanTask(title="Test task"))
        assert task.id
        got = store.get_task(task.id)
        assert got is not None
        assert got.title == "Test task"

    def test_list_by_column(self, store):
        store.create_task(KanbanTask(title="A", column=KanbanColumn.BACKLOG))
        store.create_task(KanbanTask(title="B", column=KanbanColumn.IN_PROGRESS))
        backlog = store.list_by_column(KanbanColumn.BACKLOG)
        assert len(backlog) == 1
        assert backlog[0].title == "A"

    def test_move_task(self, store):
        task = store.create_task(KanbanTask(title="Move me"))
        moved = store.move_task(task.id, KanbanColumn.IN_PROGRESS)
        assert moved is not None
        assert moved.column == KanbanColumn.IN_PROGRESS
        assert moved.started_at is not None

    def test_delete_task(self, store):
        task = store.create_task(KanbanTask(title="Delete me"))
        assert store.delete_task(task.id)
        assert store.get_task(task.id) is None

    def test_search(self, store):
        store.create_task(KanbanTask(title="Database optimization"))
        store.create_task(KanbanTask(title="Frontend styling"))
        results = store.search_tasks("database")
        assert len(results) == 1
        assert "database" in results[0].title.lower()

    def test_board_crud(self, store):
        board = KanbanBoard(name="Sprint 1")
        store.create_board(board)
        boards = store.list_boards()
        assert len(boards) == 1
        assert boards[0].name == "Sprint 1"


class TestColumnManager:
    def test_valid_transitions(self):
        mgr = ColumnManager()
        task = KanbanTask(title="t")
        assert mgr.can_move(task, KanbanColumn.READY)
        assert not mgr.can_move(task, KanbanColumn.COMPLETED)  # skip ready & in_progress


class TestBoardMetrics:
    def test_compute(self):
        metrics = BoardMetrics()
        tasks = [
            KanbanTask(title="A", column=KanbanColumn.COMPLETED,
                       started_at=__import__("maestro.models").models.utc_now(),
                       completed_at=__import__("maestro.models").models.utc_now()),
            KanbanTask(title="B", column=KanbanColumn.IN_PROGRESS),
        ]
        # Fix timestamp for completed task
        from maestro.models import utc_now
        tasks[0].started_at = utc_now()
        tasks[0].completed_at = utc_now()

        stats = metrics.compute(tasks)
        assert stats["total_tasks"] == 2
        assert stats["wip_count"] == 1


class TestBoardManager:
    def test_create_move_stats(self, board_manager):
        task = board_manager.create_task("Test", priority=TaskPriority.HIGH)
        assert task.priority == TaskPriority.HIGH

        moved = board_manager.move_task(task.id, KanbanColumn.READY)
        assert moved is not None and moved.column == KanbanColumn.READY

        # Invalid move
        assert board_manager.move_task(task.id, KanbanColumn.COMPLETED) is None

        stats = board_manager.get_board_stats()
        assert stats["total_tasks"] == 1
