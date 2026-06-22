"""Tests for the Reflection & Self-Correction subsystem."""

import pytest

from maestro.reflection import (
    CriticAgent,
    ConfidenceScorer,
    ImprovementEngine,
    ReflectionAgent,
)
from maestro.models import CritiqueAspect


class TestConfidenceScorer:
    def test_score_no_critiques(self):
        scorer = ConfidenceScorer()
        score = scorer.score([])
        assert score == 0.5

    def test_score_high_quality(self):
        scorer = ConfidenceScorer()
        from maestro.models import CritiqueResult
        critiques = [
            CritiqueResult(task_id="t1", agent_id="a1", aspect=CritiqueAspect.CORRECTNESS, score=1.0),
            CritiqueResult(task_id="t1", agent_id="a1", aspect=CritiqueAspect.COMPLETENESS, score=0.9),
        ]
        score = scorer.score(critiques)
        assert 0.5 <= score <= 1.0

    def test_retry_penalty(self):
        scorer = ConfidenceScorer()
        from maestro.models import CritiqueResult
        critiques = [CritiqueResult(task_id="t1", agent_id="a1", aspect=CritiqueAspect.CORRECTNESS, score=1.0)]
        score_no_retry = scorer.score(critiques, retry_count=0)
        score_retry = scorer.score(critiques, retry_count=5)
        assert score_no_retry >= score_retry


class TestCriticAgent:
    @pytest.mark.asyncio
    async def test_evaluate_correctness(self):
        critic = CriticAgent()
        results = await critic.evaluate(
            "t1", "a1",
            "def foo():\n    pass  # TODO: implement",
            aspects=[CritiqueAspect.CORRECTNESS],
        )
        assert len(results) == 1
        assert results[0].score < 1.0

    @pytest.mark.asyncio
    async def test_evaluate_security(self):
        critic = CriticAgent()
        results = await critic.evaluate(
            "t1", "a1",
            "api_key = 'sk-12345'",
            aspects=[CritiqueAspect.SECURITY],
        )
        assert len(results) == 1
        assert results[0].score < 1.0

    @pytest.mark.asyncio
    async def test_evaluate_all_aspects(self):
        critic = CriticAgent()
        results = await critic.evaluate("t1", "a1", "print('hello world')")
        assert len(results) == len(CritiqueAspect)


class TestImprovementEngine:
    def test_generate_prompt(self):
        engine = ImprovementEngine()
        from maestro.models import CritiqueResult
        critiques = [
            CritiqueResult(
                task_id="t1", agent_id="a1",
                aspect=CritiqueAspect.CORRECTNESS,
                score=0.4,
                issues=["Missing error handling"],
                suggestions=["Add try/except"],
            )
        ]
        prompt = engine.generate_improvement_prompt("Build a function", critiques)
        assert "Missing error handling" in prompt
        assert "Add try/except" in prompt

    def test_should_retry(self):
        engine = ImprovementEngine(max_retries=3)
        from maestro.models import ReflectionReport
        report = ReflectionReport(
            task_id="t1", agent_id="a1",
            overall_score=0.3,
            confidence=0.3,
            should_retry=True,
            retry_count=1,
        )
        assert engine.should_retry(report)

        report2 = ReflectionReport(
            task_id="t1", agent_id="a1",
            overall_score=0.3,
            confidence=0.3,
            should_retry=True,
            retry_count=5,
        )
        assert not engine.should_retry(report2)


class TestReflectionAgent:
    @pytest.mark.asyncio
    async def test_reflect(self):
        agent = ReflectionAgent()
        report = await agent.reflect(
            task_id="t1",
            agent_id="a1",
            task_description="Write a function",
            output="def f(): pass",
        )
        assert len(report.critiques) > 0
        assert 0 <= report.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_reflect_and_improve(self):
        agent = ReflectionAgent()

        async def executor(task: str) -> str:
            return "Improved: " + task

        report, output = await agent.reflect_and_improve(
            task_id="t1",
            agent_id="a1",
            task_description="Write quality code",
            executor=executor,
            max_retries=1,
        )
        assert output
        assert report.task_id == "t1"
