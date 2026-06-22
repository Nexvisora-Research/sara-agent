"""Tests for the Agent Swarm Coordination subsystem."""

import pytest

from maestro.swarm import (
    AgentRegistry,
    AgentSwarm,
    SwarmMessageBus,
    SwarmContextManager,
    ConsensusEngine,
    SwarmSupervisor,
)
from maestro.models import (
    SwarmAgentSpec,
    SwarmAgentRole,
    SwarmMessage,
    SwarmConsensusVote,
    WorkflowStatus,
)


class TestAgentRegistry:
    def test_register_and_find(self):
        registry = AgentRegistry()
        spec = SwarmAgentSpec(name="test", role=SwarmAgentRole.PLANNER)
        async def handler(msg): return "ok"
        registry.register(spec, handler)
        assert registry.get(spec.id) is spec
        assert len(registry.find_by_role(SwarmAgentRole.PLANNER)) == 1

    def test_find_by_capability(self):
        registry = AgentRegistry()
        spec = SwarmAgentSpec(
            name="coder", role=SwarmAgentRole.CODING,
            capabilities=["python", "typescript"]
        )
        async def handler(msg): return "ok"
        registry.register(spec, handler)
        assert len(registry.find_by_capability("python")) == 1
        assert len(registry.find_by_capability("rust")) == 0


class TestSwarmMessageBus:
    @pytest.mark.asyncio
    async def test_send_receive(self):
        bus = SwarmMessageBus()
        msg = SwarmMessage(sender_id="a", recipient_id="b", content="hello")
        await bus.send(msg)
        received = await bus.receive("b")
        assert received.content == "hello"

    @pytest.mark.asyncio
    async def test_subscribe_broadcast(self):
        bus = SwarmMessageBus()
        queue = await bus.subscribe("alert")
        msg = SwarmMessage(sender_id="a", message_type="alert", content="warning")
        await bus.send(msg)
        received = await queue.get()
        assert received.content == "warning"


class TestSwarmContextManager:
    @pytest.mark.asyncio
    async def test_set_get(self):
        ctx = SwarmContextManager()
        await ctx.set("key", "value")
        assert await ctx.get("key") == "value"
        assert await ctx.get("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_snapshot(self):
        ctx = SwarmContextManager()
        await ctx.set("a", 1)
        await ctx.set("b", 2)
        snap = await ctx.snapshot()
        assert snap == {"a": 1, "b": 2}


class TestConsensusEngine:
    def test_majority_approval(self):
        engine = ConsensusEngine(required_ratio=0.6)
        run_id = "run1"
        # Two of three approve
        import asyncio
        asyncio.run(engine.vote(SwarmConsensusVote(run_id=run_id, agent_id="a1", approve=True)))
        asyncio.run(engine.vote(SwarmConsensusVote(run_id=run_id, agent_id="a2", approve=True)))
        asyncio.run(engine.vote(SwarmConsensusVote(run_id=run_id, agent_id="a3", approve=False)))
        results = engine.results(run_id)
        assert len(results) == 3
        approvals = sum(1 for r in results if r.approve)
        assert approvals >= 2

    def test_reset(self):
        engine = ConsensusEngine()
        import asyncio
        run_id = "run2"
        asyncio.run(engine.vote(SwarmConsensusVote(run_id=run_id, agent_id="a1", approve=True)))
        assert len(engine.results(run_id)) == 1
        asyncio.run(engine.reset(run_id))
        assert len(engine.results(run_id)) == 0


class TestSwarmSupervisor:
    @pytest.mark.asyncio
    async def test_heartbeat_and_failure(self):
        sup = SwarmSupervisor()
        await sup.heartbeat("agent1")
        healthy = await sup.healthy_agents()
        assert "agent1" in healthy

        for _ in range(3):
            should_remove = await sup.report_failure("agent1")
        assert should_remove
        healthy2 = await sup.healthy_agents()
        assert "agent1" not in healthy2


class TestAgentSwarm:
    @pytest.mark.asyncio
    async def test_run_pipeline(self):
        swarm = AgentSwarm()
        spec = SwarmAgentSpec(name="worker", role=SwarmAgentRole.CODING)
        async def handler(msg): return f"processed: {msg.content}"
        swarm.registry.register(spec, handler)

        run = await swarm.run("hello", [SwarmAgentRole.CODING])
        assert run.status == WorkflowStatus.COMPLETED
        assert run.result
        assert "processed" in run.result
