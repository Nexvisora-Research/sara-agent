"""Agent Swarm Coordination — collaborative multi-agent system with messaging and consensus."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from .models import (
    SwarmAgentRole,
    SwarmAgentSpec,
    SwarmConsensusVote,
    SwarmMessage,
    SwarmRun,
    WorkflowStatus,
    new_id,
    utc_now,
)

logger = logging.getLogger("sara.maestro.swarm")

AgentHandler = Callable[[SwarmMessage], Awaitable[str]]


class AgentRegistry:
    """Registry of available swarm agents with their capabilities."""

    def __init__(self) -> None:
        self._agents: dict[str, SwarmAgentSpec] = {}
        self._handlers: dict[str, AgentHandler] = {}

    def register(self, spec: SwarmAgentSpec, handler: AgentHandler) -> None:
        if spec.id in self._agents:
            logger.warning("Overwriting agent %s", spec.id)
        self._agents[spec.id] = spec
        self._handlers[spec.id] = handler

    def get(self, agent_id: str) -> SwarmAgentSpec | None:
        return self._agents.get(agent_id)

    def handler(self, agent_id: str) -> AgentHandler | None:
        return self._handlers.get(agent_id)

    def find_by_role(self, role: SwarmAgentRole) -> list[SwarmAgentSpec]:
        return [a for a in self._agents.values() if a.role == role]

    def find_by_capability(self, capability: str) -> list[SwarmAgentSpec]:
        return [a for a in self._agents.values() if capability in a.capabilities]

    def list(self) -> list[SwarmAgentSpec]:
        return list(self._agents.values())

    def remove(self, agent_id: str) -> bool:
        self._handlers.pop(agent_id, None)
        return self._agents.pop(agent_id, None) is not None


class SwarmMessageBus:
    """Asynchronous message bus for agent-to-agent communication.

    When ``core_event_bus`` is provided (a ``core.events.EventBus`` instance),
    every sent message is bridged to the core event system so subscribers
    outside the swarm can observe agent activity.
    """

    def __init__(self, core_event_bus: Any = None) -> None:
        self._queues: dict[str, asyncio.Queue[SwarmMessage]] = defaultdict(
            lambda: asyncio.Queue(maxsize=1024)
        )
        self._subscribers: dict[str, set[asyncio.Queue[SwarmMessage]]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._core_event_bus = core_event_bus

    async def send(self, message: SwarmMessage) -> None:
        if message.recipient_id:
            queue = self._queues[message.recipient_id]
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(message)
        async with self._lock:
            for queue in self._subscribers.get(message.message_type, set()):
                if not queue.full():
                    queue.put_nowait(message)
        # Bridge to core event bus when available.
        if self._core_event_bus is not None:
            try:
                from core.models import Event as CoreEvent, EventType as CoreEventType
                await self._core_event_bus.publish(
                    CoreEvent(
                        type=CoreEventType.AGENT_MESSAGE,
                        source_id=message.sender_id,
                        payload=message.model_dump(mode="json"),
                    )
                )
            except Exception:
                logger.warning("Failed to bridge swarm message to core event bus", exc_info=True)

    async def receive(self, agent_id: str) -> SwarmMessage:
        return await self._queues[agent_id].get()

    async def subscribe(self, message_type: str) -> asyncio.Queue[SwarmMessage]:
        q: asyncio.Queue[SwarmMessage] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers[message_type].add(q)
        return q

    async def unsubscribe(self, message_type: str, queue: asyncio.Queue[SwarmMessage]) -> None:
        async with self._lock:
            self._subscribers[message_type].discard(queue)


class SwarmContextManager:
    """Shared context store accessible by all swarm agents."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._store[key] = value

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self._store.get(key, default)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._store)


class ConsensusEngine:
    """Vote-based consensus mechanism for swarm decisions."""

    def __init__(self, required_ratio: float = 0.6) -> None:
        self.required_ratio = required_ratio
        self._votes: dict[str, list[SwarmConsensusVote]] = defaultdict(list)

    async def vote(self, vote: SwarmConsensusVote) -> bool:
        self._votes[vote.run_id].append(vote)
        return self._check(vote.run_id)

    async def reset(self, run_id: str) -> None:
        self._votes.pop(run_id, None)

    def _check(self, run_id: str) -> bool:
        votes = self._votes.get(run_id, [])
        if not votes:
            return False
        approvals = sum(1 for v in votes if v.approve)
        return approvals / len(votes) >= self.required_ratio

    def results(self, run_id: str) -> list[SwarmConsensusVote]:
        return list(self._votes.get(run_id, []))


class SwarmSupervisor:
    """Monitors swarm health and handles agent failures."""

    def __init__(self) -> None:
        self._heartbeats: dict[str, float] = {}
        self._failures: dict[str, int] = defaultdict(int)
        self._max_failures = 3

    async def heartbeat(self, agent_id: str) -> None:
        self._heartbeats[agent_id] = utc_now().timestamp()

    async def report_failure(self, agent_id: str) -> bool:
        self._failures[agent_id] += 1
        return self._failures[agent_id] >= self._max_failures

    async def healthy_agents(self) -> list[str]:
        now = utc_now().timestamp()
        return [
            aid
            for aid, ts in self._heartbeats.items()
            if now - ts < 30 and self._failures.get(aid, 0) < self._max_failures
        ]

    async def reset_failures(self, agent_id: str) -> None:
        self._failures[agent_id] = 0


class AgentSwarm:
    """Orchestrate multiple agents working together on a shared goal."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        message_bus: SwarmMessageBus | None = None,
        context: SwarmContextManager | None = None,
        consensus: ConsensusEngine | None = None,
        supervisor: SwarmSupervisor | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.message_bus = message_bus or SwarmMessageBus()
        self.context = context or SwarmContextManager()
        self.consensus = consensus or ConsensusEngine()
        self.supervisor = supervisor or SwarmSupervisor()
        self._logger = logging.getLogger("sara.maestro.swarm.swarm")

    async def run(
        self,
        goal: str,
        pipeline: list[SwarmAgentRole],
        input_data: dict[str, Any] | None = None,
    ) -> SwarmRun:
        run = SwarmRun(goal=goal, status=WorkflowStatus.RUNNING)
        await self.context.set("goal", goal)
        if input_data:
            await self.context.set("input", input_data)

        try:
            previous_result = ""
            for role in pipeline:
                agents = self.registry.find_by_role(role)
                if not agents:
                    self._logger.warning("No agent for role %s, skipping", role)
                    continue
                for agent in agents:
                    run.agents.append(agent.id)
                    msg = SwarmMessage(
                        sender_id="swarm",
                        recipient_id=agent.id,
                        message_type="task",
                        content=previous_result or goal,
                    )
                    await self.message_bus.send(msg)
                    handler = self.registry.handler(agent.id)
                    if handler:
                        result = await handler(msg)
                        previous_result = result
                        await self.context.set(f"result_{agent.id}", result)
                        await self.supervisor.heartbeat(agent.id)

            run.result = previous_result
            run.status = WorkflowStatus.COMPLETED
        except Exception as e:
            self._logger.exception("Swarm run failed")
            run.status = WorkflowStatus.FAILED
            run.error = f"{type(e).__name__}: {e}"

        run.completed_at = utc_now()
        return run

    async def run_with_consensus(
        self,
        goal: str,
        roles: list[SwarmAgentRole],
        input_data: dict[str, Any] | None = None,
    ) -> SwarmRun:
        run = await self.run(goal, roles, input_data)
        if run.status == WorkflowStatus.COMPLETED:
            agents = [self.registry.get(aid) for aid in run.agents if self.registry.get(aid)]
            for agent in agents:
                if agent:
                    vote = SwarmConsensusVote(
                        run_id=run.id,
                        agent_id=agent.id,
                        approve=True,
                        comment="Completed successfully",
                    )
                    await self.consensus.vote(vote)
        return run
