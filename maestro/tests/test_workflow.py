"""Tests for the Workflow Engine subsystem."""

import pytest

from maestro.workflow import (
    WorkflowRegistry,
    WorkflowRunner,
    StepExecutor,
    WorkflowEngine,
)
from maestro.models import (
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepType,
    WorkflowStatus,
)


class TestWorkflowRegistry:
    def test_register_and_get(self):
        reg = WorkflowRegistry()
        wf = WorkflowDefinition(name="test", description="test workflow")
        reg.register(wf)
        assert reg.get("test") is wf
        assert reg.get(wf.id) is wf

    def test_list(self):
        reg = WorkflowRegistry()
        reg.register(WorkflowDefinition(name="a"))
        reg.register(WorkflowDefinition(name="b"))
        assert len(reg.list()) == 2


class TestStepExecutor:
    @pytest.mark.asyncio
    async def test_execute_with_retry(self):
        executor = StepExecutor()
        attempt_count = 0

        async def failing_handler(step, ctx):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not ready yet")
            return "success"

        executor.register_handler("flaky", failing_handler)
        step = WorkflowStep(name="flaky-step", handler="flaky", retry_count=3, retry_delay_seconds=0.01)
        result = await executor.execute(step, {})
        assert result == "success"
        assert attempt_count == 3


class TestWorkflowRunner:
    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        executor = StepExecutor()
        results = []

        async def step_a(step, ctx):
            results.append("a")
            return "A"
        async def step_b(step, ctx):
            results.append("b")
            return "B"

        executor.register_handler("a", step_a)
        executor.register_handler("b", step_b)

        wf = WorkflowDefinition(name="seq", steps=[
            WorkflowStep(name="step_a", handler="a"),
            WorkflowStep(name="step_b", handler="b", depends_on=["step_a"]),
        ])
        runner = WorkflowRunner(executor)
        execution = await runner.run(wf)
        assert execution.status == WorkflowStatus.COMPLETED
        assert results == ["a", "b"]

    @pytest.mark.asyncio
    async def test_conditional_skip(self):
        executor = StepExecutor()
        executed = []

        async def handler(step, ctx):
            executed.append(step.name)
            return "ok"

        executor.register_handler("h", handler)
        wf = WorkflowDefinition(name="cond", steps=[
            WorkflowStep(name="always", handler="h"),
            WorkflowStep(name="skipped", handler="h", condition="False"),
        ])
        runner = WorkflowRunner(executor)
        execution = await runner.run(wf)
        assert execution.status == WorkflowStatus.COMPLETED
        assert executed == ["always"]


class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_run_by_name(self):
        engine = WorkflowEngine()
        async def handler(step, ctx): return "done"
        engine.executor.register_handler("h", handler)
        engine.registry.register(WorkflowDefinition(name="test", steps=[
            WorkflowStep(name="s1", handler="h"),
        ]))
        execution = await engine.run("test")
        assert execution.status == WorkflowStatus.COMPLETED
        assert engine.get_execution(execution.id) is not None
