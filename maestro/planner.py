"""Multi-Agent Planner — hierarchical goal decomposition and task orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from .models import (
    ExecutionStrategy,
    PlannerGoal,
    PlannerTask,
    TaskGraphNode,
    TaskPriority,
    WorkflowStatus,
    new_id,
    utc_now,
)

logger = logging.getLogger("sara.maestro.planner")


class GoalAnalyzer:
    """Decompose a user goal into structured sub-goals."""

    COMMON_PATTERNS: dict[str, list[str]] = {
        "saas": ["frontend", "backend", "database", "authentication", "deployment"],
        "api": ["routes", "models", "validation", "documentation", "tests"],
        "cli": ["argument_parsing", "commands", "output_formatting", "help"],
        "webapp": ["ui", "state_management", "routing", "api_client", "styling"],
        "library": ["public_api", "internals", "tests", "documentation"],
    }

    def analyze(self, description: str) -> list[str]:
        desc_lower = description.lower()
        for keyword, subs in self.COMMON_PATTERNS.items():
            if keyword in desc_lower:
                return list(subs)
        return ["research", "implementation", "testing", "documentation"]

    def estimate_effort(self, description: str) -> str:
        word_count = len(description.split())
        if word_count > 50:
            return "large"
        if word_count > 15:
            return "medium"
        return "small"


class DependencyResolver:
    """Build dependency graphs between planning tasks."""

    def resolve(self, tasks: list[PlannerTask]) -> list[PlannerTask]:
        resolved: list[PlannerTask] = []
        visited: set[str] = set()

        def _visit(task: PlannerTask, path: set[str]) -> None:
            if task.id in visited:
                return
            if task.id in path:
                logger.warning("Circular dependency detected for task %s", task.id)
                return
            path.add(task.id)
            for dep_id in task.dependencies:
                dep = next((t for t in tasks if t.id == dep_id), None)
                if dep:
                    _visit(dep, path)
            visited.add(task.id)
            resolved.append(task)
            path.discard(task.id)

        for task in tasks:
            _visit(task, set())
        return resolved


class TaskGraph:
    """Directed graph of planning tasks for visualization and analysis."""

    def __init__(self) -> None:
        self.nodes: dict[str, TaskGraphNode] = {}

    def build(self, tasks: list[PlannerTask]) -> TaskGraphNode:
        node_map: dict[str, TaskGraphNode] = {}
        roots: list[str] = []
        for task in tasks:
            node = TaskGraphNode(
                task_id=task.id,
                title=task.title,
                dependencies=list(task.dependencies),
            )
            node_map[task.id] = node
            if not task.dependencies:
                roots.append(task.id)

        for task in tasks:
            for dep_id in task.dependencies:
                parent = node_map.get(dep_id)
                if parent:
                    child = node_map[task.id]
                    if child not in parent.children:
                        parent.children.append(child)

        root = TaskGraphNode(task_id="root", title="Root", depth=-1)
        for rid in roots:
            rnode = node_map.get(rid)
            if rnode:
                self._assign_depth(rnode, 0)
                root.children.append(rnode)
        self.nodes = node_map
        return root

    def critical_path(self) -> list[str]:
        def _depth(node: TaskGraphNode) -> int:
            if not node.children:
                return 0
            return 1 + max(_depth(c) for c in node.children)

        def _walk(node: TaskGraphNode) -> list[str]:
            if not node.children:
                return [node.task_id]
            max_depth = -1
            deepest = node.children[0]
            for c in node.children:
                d = _depth(c)
                if d > max_depth:
                    max_depth = d
                    deepest = c
            return [node.task_id] + _walk(deepest)

        root = None
        for node in self.nodes.values():
            if node.depth == 0:
                r = node
                for candidate in self.nodes.values():
                    if candidate.depth == 0:
                        r = candidate
                root = r
                break
        if root is None:
            return []
        return _walk(root)[1:]

    @staticmethod
    def _assign_depth(node: TaskGraphNode, depth: int) -> None:
        node.depth = depth
        for child in node.children:
            TaskGraph._assign_depth(child, depth + 1)


class ExecutionStrategyBuilder:
    """Build execution strategies from goal analysis."""

    def build(
        self,
        goal: PlannerGoal,
        tasks: list[PlannerTask],
    ) -> ExecutionStrategy:
        independent: dict[str, list[str]] = defaultdict(list)
        task_map = {t.id: t for t in tasks}
        for task in tasks:
            if not task.dependencies:
                independent["group_0"].append(task.id)

        for task in tasks:
            for dep_id in task.dependencies:
                dep = task_map.get(dep_id)
                if dep:
                    group_key = f"group_{task.priority}"
                    independent[group_key].append(task.id)

        parallel_groups = list(independent.values())
        steps = [t.title for t in tasks]

        return ExecutionStrategy(
            goal_id=goal.id,
            approach=self._determine_approach(goal),
            steps=steps,
            parallel_groups=parallel_groups,
            estimated_duration_seconds=len(tasks) * 30.0,
            risk_factors=self._assess_risks(goal, tasks),
        )

    def _determine_approach(self, goal: PlannerGoal) -> str:
        desc = goal.description.lower()
        if any(w in desc for w in ["build", "create", "develop", "implement"]):
            return "incremental_build"
        if any(w in desc for w in ["analyze", "research", "investigate"]):
            return "research_first"
        if any(w in desc for w in ["fix", "debug", "repair"]):
            return "diagnose_then_fix"
        return "sequential"

    def _assess_risks(self, goal: PlannerGoal, tasks: list[PlannerTask]) -> list[str]:
        risks: list[str] = []
        if len(tasks) > 10:
            risks.append("High task count may increase coordination overhead")
        if goal.priority == TaskPriority.CRITICAL:
            risks.append("Critical priority increases pressure on execution")
        deps = sum(1 for t in tasks if t.dependencies)
        if deps > len(tasks) / 2:
            risks.append("Many interdependent tasks create blocking risk")
        return risks


class PlannerAgent:
    """Top-level planner that decomposes goals and generates execution plans."""

    def __init__(
        self,
        goal_analyzer: GoalAnalyzer | None = None,
        dep_resolver: DependencyResolver | None = None,
        strategy_builder: ExecutionStrategyBuilder | None = None,
    ) -> None:
        self.goal_analyzer = goal_analyzer or GoalAnalyzer()
        self.dep_resolver = dep_resolver or DependencyResolver()
        self.strategy_builder = strategy_builder or ExecutionStrategyBuilder()
        self._task_graph = TaskGraph()
        self._logger = logging.getLogger("sara.maestro.planner.planner")

    async def plan(self, description: str, constraints: list[str] | None = None) -> ExecutionStrategy:
        goal = PlannerGoal(description=description, constraints=constraints or [])
        sub_goals = self.goal_analyzer.analyze(description)
        tasks = self._create_tasks(goal.id, sub_goals)
        resolved = self.dep_resolver.resolve(tasks)
        self._task_graph.build(resolved)
        strategy = self.strategy_builder.build(goal, resolved)
        self._logger.info("Planned goal %s with %d tasks", goal.id, len(tasks))
        return strategy

    async def replan(
        self,
        original_goal: PlannerGoal,
        failed_tasks: list[PlannerTask],
        feedback: str,
    ) -> ExecutionStrategy:
        updated_desc = f"{original_goal.description}\nFeedback: {feedback}"
        return await self.plan(updated_desc, original_goal.constraints)

    def get_task_graph(self) -> TaskGraph:
        return self._task_graph

    def _create_tasks(self, goal_id: str, sub_goals: list[str]) -> list[PlannerTask]:
        tasks: list[PlannerTask] = []
        prev_id: str | None = None
        for i, sg in enumerate(sub_goals):
            task = PlannerTask(
                goal_id=goal_id,
                title=sg.replace("_", " ").title(),
                description=f"Implement {sg} component",
                role=self._role_for_subgoal(sg),
                dependencies=[prev_id] if prev_id else [],
                priority=len(sub_goals) - i,
            )
            tasks.append(task)
            prev_id = task.id
        return tasks

    @staticmethod
    def _role_for_subgoal(subgoal: str) -> str:
        role_map = {
            "frontend": "coding",
            "backend": "coding",
            "database": "coding",
            "authentication": "coding",
            "deployment": "coding",
            "research": "research",
            "testing": "testing",
            "documentation": "documentation",
            "ui": "coding",
            "api": "coding",
        }
        return role_map.get(subgoal, "coding")
