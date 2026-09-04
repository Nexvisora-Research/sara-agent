"""Specialized asynchronexvisora agents and their execution context."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .events import EventBus
from .models import (
    AgentMessage,
    AgentProgress,
    AgentResult,
    AgentRole,
    AgentTask,
    Event,
    EventType,
    TaskStatus,
    utc_now,
)

ProgressCallback = Callable[[AgentProgress], Awaitable[None]]
MessageCallback = Callable[[AgentMessage], Awaitable[None]]
AgentHandler = Callable[[AgentTask, "AgentContext"], Awaitable[Any]]


@dataclass(slots=True)
class AgentContext:
    """Dependencies exposed to an agent handler."""

    task: AgentTask
    event_bus: EventBus
    cancellation_event: asyncio.Event
    progress_callback: ProgressCallback | None = None
    message_callback: MessageCallback | None = None

    def raise_if_cancelled(self) -> None:
        if self.cancellation_event.is_set():
            raise asyncio.CancelledError

    async def report_progress(self, percent: float, message: str) -> None:
        self.raise_if_cancelled()
        progress = AgentProgress(task_id=self.task.id, percent=percent, message=message)
        await self.event_bus.publish(
            Event(
                type=EventType.TASK_PROGRESS,
                source_id=self.task.id,
                payload=progress.model_dump(mode="json"),
            )
        )
        if self.progress_callback is not None:
            await self.progress_callback(progress)

    async def send_message(
        self,
        content: str,
        recipient_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        message = AgentMessage(
            sender_id=self.task.id,
            recipient_id=recipient_id or self.task.parent_id,
            content=content,
            metadata=metadata or {},
        )
        await self.event_bus.publish(
            Event(
                type=EventType.AGENT_MESSAGE,
                source_id=self.task.id,
                payload=message.model_dump(mode="json"),
            )
        )
        if self.message_callback is not None:
            await self.message_callback(message)


class BaseAgent(ABC):
    """Unit-testable base class for a specialized agent."""

    role: AgentRole

    def __init__(self, handler: AgentHandler | None = None) -> None:
        self._handler = handler

    async def execute(self, task: AgentTask, context: AgentContext) -> Any:
        if self._handler is not None:
            return await self._handler(task, context)
        return await self.run(task, context)

    @abstractmethod
    async def run(self, task: AgentTask, context: AgentContext) -> Any:
        """Execute role-specific work."""


class _DefaultSpecializedAgent(BaseAgent):
    """Useful baseline implementation, replaceable through dependency injection."""

    async def run(self, task: AgentTask, context: AgentContext) -> Any:
        context.raise_if_cancelled()
        await context.report_progress(10, f"Starting {self.role.value} work")
        await context.send_message(
            f"{self.role.value.title()} agent accepted: {task.description}"
        )
        await context.report_progress(100, "Baseline task completed")
        return {
            "role": self.role.value,
            "task": task.title,
            "description": task.description,
            "status": "baseline_completed",
        }


class PlannerAgent(_DefaultSpecializedAgent):
    role = AgentRole.PLANNER


class ResearchAgent(_DefaultSpecializedAgent):
    role = AgentRole.RESEARCH


class CodingAgent(_DefaultSpecializedAgent):
    role = AgentRole.CODING


class MemoryAgent(_DefaultSpecializedAgent):
    role = AgentRole.MEMORY


class BrowserAgent(_DefaultSpecializedAgent):
    role = AgentRole.BROWSER


DEFAULT_AGENT_TYPES: dict[AgentRole, type[BaseAgent]] = {
    AgentRole.PLANNER: PlannerAgent,
    AgentRole.RESEARCH: ResearchAgent,
    AgentRole.CODING: CodingAgent,
    AgentRole.MEMORY: MemoryAgent,
    AgentRole.BROWSER: BrowserAgent,
}


def cancelled_result(task: AgentTask) -> AgentResult:
    return AgentResult(
        task_id=task.id,
        role=task.role,
        status=TaskStatus.CANCELLED,
        started_at=task.started_at,
        completed_at=utc_now(),
    )
