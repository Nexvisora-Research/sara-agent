"""Concurrent orchestration for Sara's specialized Phase A agents."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from .agents import (
    DEFAULT_AGENT_TYPES,
    AgentContext,
    BaseAgent,
    MessageCallback,
    ProgressCallback,
    cancelled_result,
)
from .events import EventBus
from .models import (
    AgentResult,
    AgentRole,
    AgentTask,
    AggregatedResult,
    Event,
    EventType,
    TaskStatus,
    utc_now,
)


class AgentOrchestrator:
    """Run specialized agents concurrently and aggregate their results."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self._agents: dict[AgentRole, BaseAgent] = {
            role: agent_type() for role, agent_type in DEFAULT_AGENT_TYPES.items()
        }
        self._running: dict[str, asyncio.Task[AgentResult]] = {}
        self._cancellation_events: dict[str, asyncio.Event] = {}
        self._guard = asyncio.Lock()

    def register_agent(self, role: AgentRole, agent: BaseAgent) -> None:
        if agent.role != role:
            raise ValueError(f"agent role {agent.role} does not match registration {role}")
        self._agents[role] = agent

    async def spawn(
        self,
        task: AgentTask,
        *,
        progress_callback: ProgressCallback | None = None,
        message_callback: MessageCallback | None = None,
    ) -> asyncio.Task[AgentResult]:
        if task.role not in self._agents:
            raise KeyError(f"no agent registered for role {task.role}")
        async with self._guard:
            if task.id in self._running:
                raise ValueError(f"task {task.id} is already running")
            cancellation_event = asyncio.Event()
            runner = asyncio.create_task(
                self._execute(task, cancellation_event, progress_callback, message_callback),
                name=f"sara:{task.role.value}:{task.id}",
            )
            self._running[task.id] = runner
            self._cancellation_events[task.id] = cancellation_event
            runner.add_done_callback(lambda _: self._forget(task.id))
        await self.event_bus.publish(
            Event(type=EventType.TASK_CREATED, source_id=task.id)
        )
        return runner

    async def run_many(
        self,
        tasks: Iterable[AgentTask],
        *,
        progress_callback: ProgressCallback | None = None,
        message_callback: MessageCallback | None = None,
    ) -> AggregatedResult:
        started_at = utc_now()
        runners = [
            await self.spawn(
                task,
                progress_callback=progress_callback,
                message_callback=message_callback,
            )
            for task in tasks
        ]
        results = await asyncio.gather(*runners)
        if any(result.status == TaskStatus.FAILED for result in results):
            status = TaskStatus.FAILED
        elif any(result.status == TaskStatus.CANCELLED for result in results):
            status = TaskStatus.CANCELLED
        else:
            status = TaskStatus.COMPLETED
        return AggregatedResult(results=results, status=status, started_at=started_at)

    async def cancel(self, task_id: str) -> bool:
        async with self._guard:
            runner = self._running.get(task_id)
            cancellation_event = self._cancellation_events.get(task_id)
            if runner is None or runner.done():
                return False
            if cancellation_event is not None:
                cancellation_event.set()
            runner.cancel()
        return True

    async def cancel_all(self) -> int:
        async with self._guard:
            task_ids = list(self._running)
        cancelled = await asyncio.gather(*(self.cancel(task_id) for task_id in task_ids))
        return sum(cancelled)

    def _forget(self, task_id: str) -> None:
        self._running.pop(task_id, None)
        self._cancellation_events.pop(task_id, None)

    async def _execute(
        self,
        task: AgentTask,
        cancellation_event: asyncio.Event,
        progress_callback: ProgressCallback | None,
        message_callback: MessageCallback | None,
    ) -> AgentResult:
        task.status = TaskStatus.RUNNING
        task.started_at = utc_now()
        await self.event_bus.publish(
            Event(type=EventType.TASK_STARTED, source_id=task.id)
        )
        context = AgentContext(
            task=task,
            event_bus=self.event_bus,
            cancellation_event=cancellation_event,
            progress_callback=progress_callback,
            message_callback=message_callback,
        )
        try:
            output = await self._agents[task.role].execute(task, context)
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = utc_now()
            result = cancelled_result(task)
            await self.event_bus.publish(
                Event(type=EventType.TASK_CANCELLED, source_id=task.id)
            )
            return result
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.completed_at = utc_now()
            result = AgentResult(
                task_id=task.id,
                role=task.role,
                status=TaskStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                started_at=task.started_at,
                completed_at=task.completed_at,
            )
            await self.event_bus.publish(
                Event(
                    type=EventType.TASK_FAILED,
                    source_id=task.id,
                    payload={"error": result.error},
                )
            )
            return result

        task.status = TaskStatus.COMPLETED
        task.completed_at = utc_now()
        result = AgentResult(
            task_id=task.id,
            role=task.role,
            status=TaskStatus.COMPLETED,
            output=output,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )
        await self.event_bus.publish(
            Event(type=EventType.TASK_COMPLETED, source_id=task.id)
        )
        return result

