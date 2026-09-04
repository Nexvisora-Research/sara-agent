"""Workflow Engine — reusable sequential, parallel, and conditional step execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .models import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
    new_id,
    utc_now,
)

logger = logging.getLogger("sara.maestro.workflow")

StepHandler = Callable[[WorkflowStep, dict[str, Any]], Awaitable[Any]]


class WorkflowRegistry:
    """Registry of named workflow definitions."""

    def __init__(self) -> None:
        self._by_id: dict[str, WorkflowDefinition] = {}
        self._by_name: dict[str, str] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._by_id[workflow.id] = workflow
        self._by_name[workflow.name] = workflow.id

    def get(self, name_or_id: str) -> WorkflowDefinition | None:
        if name_or_id in self._by_id:
            return self._by_id[name_or_id]
        wf_id = self._by_name.get(name_or_id)
        return self._by_id.get(wf_id) if wf_id else None

    def list(self) -> list[WorkflowDefinition]:
        return list(self._by_id.values())

    def remove(self, name_or_id: str) -> bool:
        wf = self.get(name_or_id)
        if not wf:
            return False
        self._by_id.pop(wf.id, None)
        self._by_name.pop(wf.name, None)
        return True

    def load_yaml(self, path: str | Path) -> WorkflowDefinition:
        import yaml
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        steps = [WorkflowStep(**s) for s in data.get("steps", [])]
        wf = WorkflowDefinition(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            steps=steps,
            tags=data.get("tags", []),
        )
        self.register(wf)
        return wf


class StepExecutor:
    """Execute individual workflow steps with retry and timeout."""

    def __init__(self) -> None:
        self._handlers: dict[str, StepHandler] = {}

    def register_handler(self, name: str, handler: StepHandler) -> None:
        if not name.strip():
            raise ValueError("Handler name cannot be empty")
        self._handlers[name] = handler

    async def execute(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> Any:
        handler = self._handlers.get(step.handler)
        if not handler:
            raise ValueError(f"No handler registered for step handler: {step.handler}")

        last_error: Exception | None = None
        for attempt in range(step.retry_count + 1):
            try:
                if step.timeout_seconds:
                    result = await asyncio.wait_for(
                        handler(step, context),
                        timeout=step.timeout_seconds,
                    )
                else:
                    result = await handler(step, context)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "Step %s attempt %d failed: %s", step.name, attempt + 1, e
                )
                if attempt < step.retry_count:
                    await asyncio.sleep(step.retry_delay_seconds)
        raise last_error or RuntimeError(f"Step {step.name} failed")


class WorkflowRunner:
    """Execute a workflow definition step by step."""

    def __init__(self, executor: StepExecutor) -> None:
        self.executor = executor

    async def run(
        self,
        definition: WorkflowDefinition,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        execution = WorkflowExecution(workflow_id=definition.id)
        context = dict(initial_context or {})

        try:
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = utc_now()
            completed: set[str] = set()
            step_names: dict[str, str] = {s.id: s.name for s in definition.steps}

            while True:
                ready = self._ready_steps(definition.steps, completed, step_names)
                if not ready:
                    break

                for step in ready:
                    if self._is_skipped(step, context):
                        completed.add(step.id)
                        continue

                    execution.current_step = step.id
                    parallel_steps = [s for s in ready if s.step_type == WorkflowStepType.PARALLEL]

                    if step.step_type == WorkflowStepType.PARALLEL or len(parallel_steps) > 1:
                        results = await asyncio.gather(
                            *(self.executor.execute(s, context) for s in [step] if s.step_type != WorkflowStepType.PARALLEL),
                            return_exceptions=True,
                        )
                        for s, r in zip([step], results):
                            if isinstance(r, Exception):
                                execution.status = WorkflowStatus.FAILED
                                execution.error = f"{type(r).__name__}: {r}"
                                execution.completed_at = utc_now()
                                return execution
                            execution.step_results[s.id] = r
                            context[s.name] = r
                    else:
                        result = await self.executor.execute(step, context)
                        execution.step_results[step.id] = result
                        context[step.name] = result

                    completed.add(step.id)

            execution.status = WorkflowStatus.COMPLETED
        except Exception as e:
            logger.exception("Workflow execution failed")
            execution.status = WorkflowStatus.FAILED
            execution.error = f"{type(e).__name__}: {e}"

        execution.completed_at = utc_now()
        return execution

    def _ready_steps(
        self,
        steps: list[WorkflowStep],
        completed: set[str],
        step_names: dict[str, str],
    ) -> list[WorkflowStep]:
        completed_names = {step_names[sid] for sid in completed}
        return [
            s
            for s in steps
            if s.id not in completed
            and all(dep in completed_names for dep in s.depends_on)
        ]

    def _is_skipped(self, step: WorkflowStep, context: dict[str, Any]) -> bool:
        if not step.condition:
            return False
        try:
            return not bool(_safe_eval(step.condition, context))
        except Exception:
            logger.warning("Condition eval failed for step %s: %s", step.name, step.condition)
            return False


def _safe_eval(expr: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a boolean expression using only context variables."""
    import ast
    allowed_ops = (ast.And, ast.Or, ast.Not, ast.Compare, ast.Eq, ast.NotEq,
                   ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot,
                   ast.In, ast.NotIn, ast.Name, ast.Constant, ast.BoolOp,
                   ast.Expression, ast.Load, ast.UnaryOp, ast.USub)
    try:
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_ops):
                raise ValueError(f"Unsupported expression: {type(node).__name__}")
            if isinstance(node, ast.Name):
                if node.id not in context:
                    raise NameError(f"Unknown variable: {node.id}")
        code = compile(tree, "<safe_eval>", "eval")
        return bool(eval(code, {"__builtins__": {}}, context))
    except Exception:
        raise


class WorkflowEngine:
    """High-level workflow lifecycle manager."""

    def __init__(
        self,
        registry: WorkflowRegistry | None = None,
        executor: StepExecutor | None = None,
    ) -> None:
        self.registry = registry or WorkflowRegistry()
        self.executor = executor or StepExecutor()
        self.runner = WorkflowRunner(self.executor)
        self._executions: dict[str, WorkflowExecution] = {}

    async def run(
        self,
        workflow_name: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        definition = self.registry.get(workflow_name)
        if not definition:
            raise KeyError(f"Workflow not found: {workflow_name}")
        execution = await self.runner.run(definition, context)
        self._executions[execution.id] = execution
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    def list_executions(self) -> list[WorkflowExecution]:
        return list(self._executions.values())
