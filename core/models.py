"""Shared, serializable models for Sara Phase A."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class AgentRole(StrEnum):
    PLANNER = "planner"
    RESEARCH = "research"
    CODING = "coding"
    MEMORY = "memory"
    BROWSER = "browser"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(StrEnum):
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    AGENT_MESSAGE = "agent.message"


class AgentTask(BaseModel):
    """A unit of work assigned to one specialized agent."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    description: str
    role: AgentRole
    parent_id: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AgentMessage(BaseModel):
    """A message exchanged between a parent and child agent."""

    sender_id: str
    recipient_id: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class AgentProgress(BaseModel):
    task_id: str
    percent: float = Field(ge=0.0, le=100.0)
    message: str
    timestamp: datetime = Field(default_factory=utc_now)


class AgentResult(BaseModel):
    task_id: str
    role: AgentRole
    status: TaskStatus
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime = Field(default_factory=utc_now)


class AggregatedResult(BaseModel):
    """Ordered results from a concurrent orchestration run."""

    results: list[AgentResult]
    status: TaskStatus
    started_at: datetime
    completed_at: datetime = Field(default_factory=utc_now)


class Event(BaseModel):
    type: EventType
    source_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class BackgroundTask(BaseModel):
    """Persistent background task record."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    handler: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    scheduled_at: datetime | None = None
    result: str | None = None
    error: str | None = None
    logs: str = ""


class WatchEvent(BaseModel):
    source: str
    path: str
    kind: str
    timestamp: datetime = Field(default_factory=utc_now)
