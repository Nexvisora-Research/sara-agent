"""Focused tests for the Phase A asynchronexvisora subagent subsystem."""

from __future__ import annotations

import asyncio
import unittest

from core.agents import CodingAgent
from core.models import AgentRole, AgentTask, EventType, TaskStatus
from core.orchestrator import AgentOrchestrator


class AgentOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_agents_concurrently_and_preserves_result_order(self) -> None:
        release = asyncio.Event()
        entered = 0
        lock = asyncio.Lock()

        async def handler(task, context):
            nonlocal entered
            async with lock:
                entered += 1
                if entered == 2:
                    release.set()
            await asyncio.wait_for(release.wait(), timeout=1)
            await context.report_progress(100, "done")
            return task.title

        orchestrator = AgentOrchestrator()
        orchestrator.register_agent(AgentRole.CODING, CodingAgent(handler))
        tasks = [
            AgentTask(title="first", description="one", role=AgentRole.CODING),
            AgentTask(title="second", description="two", role=AgentRole.CODING),
        ]

        aggregate = await orchestrator.run_many(tasks)

        self.assertEqual(aggregate.status, TaskStatus.COMPLETED)
        self.assertEqual([result.output for result in aggregate.results], ["first", "second"])

    async def test_cancellation_returns_cancelled_result(self) -> None:
        started = asyncio.Event()

        async def handler(task, context):
            started.set()
            await asyncio.sleep(60)

        orchestrator = AgentOrchestrator()
        orchestrator.register_agent(AgentRole.CODING, CodingAgent(handler))
        agent_task = AgentTask(title="slow", description="wait", role=AgentRole.CODING)
        runner = await orchestrator.spawn(agent_task)
        await started.wait()

        self.assertTrue(await orchestrator.cancel(agent_task.id))
        result = await runner

        self.assertEqual(result.status, TaskStatus.CANCELLED)

    async def test_progress_and_parent_message_are_published(self) -> None:
        orchestrator = AgentOrchestrator()
        queue = await orchestrator.event_bus.subscribe()
        task = AgentTask(
            title="child",
            description="communicate",
            role=AgentRole.RESEARCH,
            parent_id="parent-task",
        )

        result = await (await orchestrator.spawn(task))
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertIn(EventType.TASK_PROGRESS, {event.type for event in events})
        message = next(event for event in events if event.type == EventType.AGENT_MESSAGE)
        self.assertEqual(message.payload["recipient_id"], "parent-task")


if __name__ == "__main__":
    unittest.main()
