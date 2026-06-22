"""Tests for the Multi-Agent Planner subsystem."""

import pytest

from maestro.planner import (
    PlannerAgent,
    TaskGraph,
    GoalAnalyzer,
    DependencyResolver,
    ExecutionStrategyBuilder,
)
from maestro.models import PlannerGoal, PlannerTask, TaskPriority


class TestGoalAnalyzer:
    def test_analyze_saas(self):
        analyzer = GoalAnalyzer()
        subs = analyzer.analyze("Build a SaaS platform")
        assert "frontend" in subs
        assert "backend" in subs
        assert "database" in subs

    def test_analyze_api(self):
        analyzer = GoalAnalyzer()
        subs = analyzer.analyze("Create a REST API")
        assert "routes" in subs

    def test_analyze_generic(self):
        analyzer = GoalAnalyzer()
        subs = analyzer.analyze("Research quantum computing")
        assert len(subs) > 0

    def test_estimate_effort_small(self):
        analyzer = GoalAnalyzer()
        assert analyzer.estimate_effort("Fix bug") == "small"

    def test_estimate_effort_large(self):
        analyzer = GoalAnalyzer()
        assert analyzer.estimate_effort("Build " + "x " * 100) == "large"


class TestDependencyResolver:
    def test_resolve_linear(self):
        tasks = [
            PlannerTask(goal_id="g1", title="A", id="a"),
            PlannerTask(goal_id="g1", title="B", id="b", dependencies=["a"]),
            PlannerTask(goal_id="g1", title="C", id="c", dependencies=["b"]),
        ]
        resolver = DependencyResolver()
        resolved = resolver.resolve(tasks)
        ids = [t.id for t in resolved]
        assert ids.index("a") < ids.index("b") < ids.index("c")

    def test_resolve_circular(self):
        tasks = [
            PlannerTask(goal_id="g1", title="A", id="a", dependencies=["c"]),
            PlannerTask(goal_id="g1", title="B", id="b", dependencies=["a"]),
            PlannerTask(goal_id="g1", title="C", id="c", dependencies=["b"]),
        ]
        resolver = DependencyResolver()
        resolved = resolver.resolve(tasks)  # should not hang
        assert len(resolved) == 3


class TestTaskGraph:
    def test_build_and_critical_path(self):
        tasks = [
            PlannerTask(goal_id="g1", title="A", id="a"),
            PlannerTask(goal_id="g1", title="B", id="b", dependencies=["a"]),
            PlannerTask(goal_id="g1", title="C", id="c", dependencies=["a"]),
            PlannerTask(goal_id="g1", title="D", id="d", dependencies=["b", "c"]),
        ]
        graph = TaskGraph()
        root = graph.build(tasks)
        assert len(root.children) == 1  # one root node (A)
        path = graph.critical_path()
        assert len(path) > 0


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_plan_saas(self):
        agent = PlannerAgent()
        strategy = await agent.plan("Build a SaaS platform")
        assert strategy.goal_id
        assert len(strategy.steps) >= 4
        assert strategy.approach == "incremental_build"

    @pytest.mark.asyncio
    async def test_replan(self):
        agent = PlannerAgent()
        goal = PlannerGoal(description="Build an API")
        strategy = await agent.replan(goal, [], "Needs better auth")
        assert strategy.goal_id
