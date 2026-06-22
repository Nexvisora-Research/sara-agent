"""Tests for the Model Router subsystem."""

import pytest

from maestro.router import (
    ModelRouter,
    ModelRegistry,
    CapabilityScorer,
    FallbackManager,
)
from maestro.models import ModelRoute, ModelCapability


class TestModelRegistry:
    def test_register_and_find(self):
        reg = ModelRegistry()
        route = ModelRoute(provider="test", model_name="test-model", capabilities=[ModelCapability.CODE])
        reg.register(route)
        assert reg.get(route.id) is route
        assert len(reg.find_by_capability(ModelCapability.CODE)) == 1
        assert len(reg.find_by_capability(ModelCapability.VISION)) == 0

    def test_load_defaults(self):
        reg = ModelRegistry()
        reg.load_defaults()
        assert len(reg.list()) >= 4
        assert any(r.provider == "ollama" for r in reg.list())


class TestCapabilityScorer:
    def test_score_matching(self):
        scorer = CapabilityScorer()
        route = ModelRoute(
            provider="test", model_name="m",
            capabilities=[ModelCapability.CODE, ModelCapability.REASONING],
            priority=8, cost_per_1k_tokens=0.0, latency_p50_ms=100,
        )
        score = scorer.score(route, [ModelCapability.CODE])
        assert 0 < score <= 1.0

    def test_score_cost_penalty(self):
        scorer = CapabilityScorer()
        cheap = ModelRoute(provider="a", model_name="cheap", capabilities=[ModelCapability.CODE], cost_per_1k_tokens=0.0, latency_p50_ms=100, priority=5)
        expensive = ModelRoute(provider="b", model_name="expensive", capabilities=[ModelCapability.CODE], cost_per_1k_tokens=0.1, latency_p50_ms=100, priority=5)
        cheap_score = scorer.score(cheap, [ModelCapability.CODE])
        expensive_score = scorer.score(expensive, [ModelCapability.CODE])
        assert cheap_score > expensive_score


class TestFallbackManager:
    def test_fallback_chain(self):
        reg = ModelRegistry()
        reg.load_defaults()
        mgr = FallbackManager(reg)
        mgr.set_fallback_chain("openai/gpt-4o", ["ollama/qwen2.5-coder"])
        chain = mgr.get_chain("openai/gpt-4o")
        assert len(chain) == 2


class TestModelRouter:
    def test_select_by_capability(self):
        router = ModelRouter()
        router.registry.load_defaults()
        route = router.select([ModelCapability.CODE])
        assert route is not None
        assert ModelCapability.CODE in route.capabilities

    def test_select_for_task(self):
        router = ModelRouter()
        router.registry.load_defaults()
        route = router.select_for_task("coding")
        assert route is not None

    def test_select_with_fallback(self):
        router = ModelRouter()
        router.registry.load_defaults()
        routes = router.select_with_fallback([ModelCapability.CODE])
        assert len(routes) >= 1

    def test_select_none_for_unknown(self):
        router = ModelRouter()
        route = router.select([ModelCapability.CODE])  # empty registry
        assert route is None
