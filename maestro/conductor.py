"""Conductor — wiring layer that integrates core (Phase A) with maestro (Phase B).

Usage::

    from maestro.conductor import Conductor

    async def main():
        c = Conductor(db_path="~/.sara/conductor.db")
        result = await c.plan_and_execute("Build a REST API for a todo app")
        print(result)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .kanban import BoardManager, KanbanTaskStore
from .monitor import AlertEngine, WatchManager
from .planner import PlannerAgent
from .reflection import ReflectionAgent
from .router import ModelRouter
from .swarm import AgentSwarm, SwarmMessageBus
from .workflow import WorkflowEngine

logger = logging.getLogger("sara.maestro.conductor")


class Conductor:
    """Integrated entry point that wires core infrastructure and maestro subsystems."""

    def __init__(
        self,
        db_path: str | Path = "~/.sara/conductor.db",
        *,
        database: Any = None,
        event_bus: Any = None,
        orchestrator: Any = None,
        planner: PlannerAgent | None = None,
        router: ModelRouter | None = None,
        reflection: ReflectionAgent | None = None,
        board_manager: BoardManager | None = None,
        watch_manager: WatchManager | None = None,
        workflow_engine: WorkflowEngine | None = None,
        agent_swarm: AgentSwarm | None = None,
    ) -> None:
        # ── Core infrastructure (Phase A) ────────────────────────────────────
        self._db = database
        self._event_bus = event_bus
        self._orchestrator = orchestrator

        if self._db is None:
            from core.database import Database as CoreDatabase
            self._db = CoreDatabase(db_path)

        if self._event_bus is None:
            from core.events import EventBus as CoreEventBus
            self._event_bus = CoreEventBus()

        if self._orchestrator is None:
            from core.orchestrator import AgentOrchestrator
            self._orchestrator = AgentOrchestrator(event_bus=self._event_bus)

        # ── Maestro subsystems (Phase B) ─────────────────────────────────────
        self.planner = planner or PlannerAgent()

        self.router = router or ModelRouter()
        self.router.registry.load_defaults()

        self.reflection = reflection or ReflectionAgent()

        if workflow_engine is not None:
            self.workflow = workflow_engine
        else:
            self.workflow = WorkflowEngine()

        if board_manager is not None:
            self.board = board_manager
        else:
            kstore = KanbanTaskStore(self._db)
            self.board = BoardManager(kstore)

        alert_engine = AlertEngine()
        self.watch = watch_manager or WatchManager(alert_engine=alert_engine)

        if agent_swarm is not None:
            self.swarm = agent_swarm
        else:
            swarm_bus = SwarmMessageBus(core_event_bus=self._event_bus)
            self.swarm = AgentSwarm(message_bus=swarm_bus)

        self._logger = logging.getLogger("sara.maestro.conductor")

    # ── Public API ───────────────────────────────────────────────────────────

    async def plan_and_execute(
        self,
        goal: str,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: decompose goal → execute tasks → reflect on results.

        Returns a dict with keys ``strategy``, ``results``, and ``reflection``.
        """
        self._logger.info("Planning goal: %s", goal)

        # 1. Plan
        strategy = await self.planner.plan(goal, constraints)
        self._logger.info(
            "Strategy built: %d steps across %d parallel groups",
            len(strategy.steps), len(strategy.parallel_groups),
        )

        # 2. Execute each step via the orchestrator
        results = []
        for group in strategy.parallel_groups:
            tasks = [strategy.steps[i] for i in group]
            core_tasks = []
            for pt in tasks:
                core_tasks.append(self._make_core_task(pt))
            if core_tasks:
                agg = await self._orchestrator.run_many(core_tasks)  # type: ignore[union-attr]
                results.append(agg)

        return {
            "strategy": strategy.model_dump(mode="json"),
            "results": [r.model_dump(mode="json") for r in results] if results else [],
        }

    async def reflect_on(
        self,
        task_id: str,
        agent_id: str,
        task_description: str,
        output: str,
    ) -> Any:
        """Run reflection on a single task output."""
        from .models import CritiqueAspect

        report = await self.reflection.reflect(
            task_id=task_id,
            agent_id=agent_id,
            task_description=task_description,
            output=output,
            aspects=list(CritiqueAspect),
        )
        return report

    def select_model(self, task_type: str) -> Any:
        """Use the model router to pick the best model for a task type."""
        return self.router.select_for_task(task_type)

    def create_task(
        self,
        title: str,
        description: str = "",
    ) -> Any:
        """Quick-create a kanban task on the backlog."""
        return self.board.create_task(title, description)

    def get_board_stats(self) -> dict[str, Any]:
        """Return aggregate kanban board metrics."""
        return self.board.get_board_stats()

    # ── Internals ────────────────────────────────────────────────────────────

    def _make_core_task(self, planner_task: Any) -> Any:
        """Convert a ``PlannerTask`` into a ``core.models.AgentTask``."""
        from core.models import AgentRole, AgentTask as CoreAgentTask

        role_map: dict[str, AgentRole] = {
            "planner": AgentRole.PLANNER,
            "research": AgentRole.RESEARCH,
            "coding": AgentRole.CODING,
            "memory": AgentRole.MEMORY,
            "browser": AgentRole.BROWSER,
        }
        return CoreAgentTask(
            title=planner_task.title,
            description=planner_task.title,
            role=role_map.get(planner_task.role or "", AgentRole.PLANNER),
            input_data={
                "description": planner_task.title,
                "priority": planner_task.priority.value if planner_task.priority else "medium",
            },
        )
