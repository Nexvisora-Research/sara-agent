"""Reflection & Self-Correction — critique, confidence scoring, and improvement loops."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from .models import (
    CritiqueAspect,
    CritiqueResult,
    ReflectionReport,
    utc_now,
)

logger = logging.getLogger("sara.maestro.reflection")

TaskOutput = Any
TaskExecutor = Callable[[str], Awaitable[TaskOutput]]


class ConfidenceScorer:
    """Score confidence in a task output based on multiple signals."""

    WEIGHTS = {
        "critique_avg": 0.5,
        "retry_history": 0.2,
        "completion_speed": 0.1,
        "complexity": 0.2,
    }

    def score(
        self,
        critiques: list[CritiqueResult],
        retry_count: int = 0,
        duration_seconds: float = 0.0,
        complexity: float = 0.5,
    ) -> float:
        if not critiques:
            return 0.5

        avg_critique = sum(c.score for c in critiques) / len(critiques)
        retry_penalty = max(0, 1.0 - retry_count * 0.15)
        speed_score = max(0, 1.0 - duration_seconds / 300.0)
        complexity_score = 1.0 - complexity * 0.3

        score = (
            avg_critique * self.WEIGHTS["critique_avg"]
            + retry_penalty * self.WEIGHTS["retry_history"]
            + speed_score * self.WEIGHTS["completion_speed"]
            + complexity_score * self.WEIGHTS["complexity"]
        )
        return max(0.0, min(1.0, score))


class CriticAgent:
    """Evaluate task outputs across multiple quality aspects."""

    def __init__(self, confidence_scorer: ConfidenceScorer | None = None) -> None:
        self.scorer = confidence_scorer or ConfidenceScorer()
        self._logger = logging.getLogger("sara.maestro.reflection.critic")

    async def evaluate(
        self,
        task_id: str,
        agent_id: str,
        output: str,
        aspects: list[CritiqueAspect] | None = None,
    ) -> list[CritiqueResult]:
        aspects = aspects or list(CritiqueAspect)
        critiques: list[CritiqueResult] = []

        for aspect in aspects:
            result = await self._evaluate_aspect(task_id, agent_id, aspect, output)
            critiques.append(result)

        return critiques

    async def _evaluate_aspect(
        self,
        task_id: str,
        agent_id: str,
        aspect: CritiqueAspect,
        output: str,
    ) -> CritiqueResult:
        issues, suggestions, score = self._analyze(aspect, output)
        return CritiqueResult(
            task_id=task_id,
            agent_id=agent_id,
            aspect=aspect,
            score=score,
            issues=issues,
            suggestions=suggestions,
            summary=f"{aspect.value}: score={score:.2f}, {len(issues)} issues found",
        )

    def _analyze(
        self,
        aspect: CritiqueAspect,
        output: str,
    ) -> tuple[list[str], list[str], float]:
        output_lower = output.lower()
        issues: list[str] = []
        suggestions: list[str] = []
        score = 1.0

        if aspect == CritiqueAspect.CORRECTNESS:
            if "error" in output_lower or "exception" in output_lower:
                issues.append("Output contains error references")
                score -= 0.3
            if "todo" in output_lower or "fixme" in output_lower:
                issues.append("Output contains unresolved TODOs")
                score -= 0.2
            if "untested" in output_lower:
                issues.append("Untested code paths")
                score -= 0.1

        elif aspect == CritiqueAspect.COMPLETENESS:
            if len(output) < 100:
                issues.append("Output is very short")
                score -= 0.2
            if "pass" not in output_lower and "implement" in output_lower:
                issues.append("Implementation may be incomplete")
                score -= 0.2
            suggestions.append("Verify all requirements are addressed")

        elif aspect == CritiqueAspect.EFFICIENCY:
            if any(w in output_lower for w in ["nested loop", "brute force", "inefficient"]):
                issues.append("Potentially inefficient algorithm")
                score -= 0.2
            suggestions.append("Consider time/space complexity")

        elif aspect == CritiqueAspect.STYLE:
            if len(output) > 0:
                score -= 0.05

        elif aspect == CritiqueAspect.SECURITY:
            if any(w in output_lower for w in ["password", "secret", "api_key", "token"]):
                if "input" not in output_lower and "env" not in output_lower:
                    issues.append("Possible hardcoded credential")
                    score -= 0.3
            if "eval(" in output_lower or "exec(" in output_lower:
                issues.append("Use of dangerous functions")
                score -= 0.3

        elif aspect == CritiqueAspect.BEST_PRACTICES:
            if "type: ignore" in output or "# noqa" in output:
                issues.append("Type/quality ignores present")
                score -= 0.1
            if len(output.split("\n")) > 200:
                suggestions.append("Consider splitting into smaller modules")

        return issues, suggestions, max(0.0, score)


class ImprovementEngine:
    """Generate and apply improvement suggestions from critique results."""

    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    def generate_improvement_prompt(
        self,
        original_task: str,
        critiques: list[CritiqueResult],
    ) -> str:
        lines = [f"Original task: {original_task}", "", "Critique feedback:"]
        for c in critiques:
            lines.append(f"  - [{c.aspect.value}] score={c.score:.2f}")
            for issue in c.issues:
                lines.append(f"    * Issue: {issue}")
            for suggestion in c.suggestions:
                lines.append(f"    * Suggestion: {suggestion}")
        lines.extend(["", "Please revise the output addressing all issues above."])
        return "\n".join(lines)

    def should_retry(self, report: ReflectionReport) -> bool:
        return (
            report.should_retry
            and report.retry_count < min(self.max_retries, report.max_retries)
        )


class ReflectionAgent:
    """Full reflection pipeline: evaluate, score, suggest, retry."""

    def __init__(
        self,
        critic: CriticAgent | None = None,
        scorer: ConfidenceScorer | None = None,
        improvement: ImprovementEngine | None = None,
    ) -> None:
        self.critic = critic or CriticAgent()
        self.scorer = scorer or ConfidenceScorer()
        self.improvement = improvement or ImprovementEngine()
        self._logger = logging.getLogger("sara.maestro.reflection.agent")

    async def reflect(
        self,
        task_id: str,
        agent_id: str,
        task_description: str,
        output: str,
        aspects: list[CritiqueAspect] | None = None,
        retry_count: int = 0,
        duration_seconds: float = 0.0,
    ) -> ReflectionReport:
        critiques = await self.critic.evaluate(task_id, agent_id, output, aspects)
        confidence = self.scorer.score(critiques, retry_count, duration_seconds)
        suggestions = []
        for c in critiques:
            suggestions.extend(c.suggestions)
        suggestions = list(set(suggestions))

        should_retry = confidence < 0.5 and retry_count < 3

        report = ReflectionReport(
            task_id=task_id,
            agent_id=agent_id,
            critiques=critiques,
            overall_score=sum(c.score for c in critiques) / len(critiques) if critiques else 0.5,
            confidence=confidence,
            improvement_suggestions=suggestions,
            should_retry=should_retry,
            retry_count=retry_count + 1 if should_retry else retry_count,
        )
        return report

    async def reflect_and_improve(
        self,
        task_id: str,
        agent_id: str,
        task_description: str,
        executor: TaskExecutor,
        max_retries: int = 3,
    ) -> tuple[ReflectionReport, str]:
        output = await executor(task_description)
        retry_count = 0

        while retry_count < max_retries:
            report = await self.reflect(
                task_id=task_id,
                agent_id=agent_id,
                task_description=task_description,
                output=output,
                retry_count=retry_count,
            )

            if report.confidence >= 0.5:
                self._logger.info(
                    "Task %s passed reflection (confidence=%.2f)", task_id, report.confidence
                )
                report.should_retry = False
                return report, output

            if not self.improvement.should_retry(report):
                return report, output

            prompt = self.improvement.generate_improvement_prompt(task_description, report.critiques)
            self._logger.info("Retrying task %s (attempt %d)", task_id, retry_count + 1)
            output = await executor(prompt)
            retry_count += 1

        final_report = await self.reflect(
            task_id=task_id,
            agent_id=agent_id,
            task_description=task_description,
            output=output,
            retry_count=retry_count,
        )
        return final_report, output
