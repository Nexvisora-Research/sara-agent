"""Model Router — intelligent model selection based on task capability and cost."""

from __future__ import annotations

import logging
import os
from typing import Any

from .models import ModelCapability, ModelRoute, new_id, utc_now

logger = logging.getLogger("sara.maestro.router")

DEFAULT_ROUTES: list[dict[str, Any]] = [
    {
        "provider": "ollama",
        "model_name": "qwen2.5-coder",
        "capabilities": ["code"],
        "priority": 10,
        "cost_per_1k_tokens": 0.0,
        "latency_p50_ms": 500,
        "max_context_tokens": 32768,
    },
    {
        "provider": "ollama",
        "model_name": "deepseek-r1",
        "capabilities": ["reasoning"],
        "priority": 10,
        "cost_per_1k_tokens": 0.0,
        "latency_p50_ms": 1000,
        "max_context_tokens": 65536,
    },
    {
        "provider": "openai",
        "model_name": "gpt-4o",
        "capabilities": ["code", "reasoning", "research", "conversation", "vision", "function_calling"],
        "priority": 5,
        "cost_per_1k_tokens": 0.01,
        "latency_p50_ms": 800,
        "max_context_tokens": 128000,
    },
    {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "capabilities": ["conversation", "fast", "cheap", "function_calling"],
        "priority": 8,
        "cost_per_1k_tokens": 0.0015,
        "latency_p50_ms": 400,
        "max_context_tokens": 128000,
    },
    {
        "provider": "openrouter",
        "model_name": "anthropic/claude-3.5-sonnet",
        "capabilities": ["code", "reasoning", "research", "long_context"],
        "priority": 4,
        "cost_per_1k_tokens": 0.015,
        "latency_p50_ms": 1200,
        "max_context_tokens": 200000,
    },
    {
        "provider": "ollama",
        "model_name": "llama3.2",
        "capabilities": ["conversation", "fast"],
        "priority": 9,
        "cost_per_1k_tokens": 0.0,
        "latency_p50_ms": 200,
        "max_context_tokens": 8192,
    },
]


class ModelRegistry:
    """Registry of available model routes."""

    def __init__(self) -> None:
        self._routes: dict[str, ModelRoute] = {}

    def register(self, route: ModelRoute) -> None:
        self._routes[route.id] = route
        key = f"{route.provider}/{route.model_name}"
        self._routes[key] = route

    def get(self, name_or_id: str) -> ModelRoute | None:
        return self._routes.get(name_or_id)

    def list(self) -> list[ModelRoute]:
        return list({r.id: r for r in self._routes.values()}.values())

    def find_by_capability(self, capability: ModelCapability) -> list[ModelRoute]:
        return sorted(
            [r for r in self.list() if capability in r.capabilities and r.enabled],
            key=lambda r: r.priority,
            reverse=True,
        )

    def load_defaults(self) -> None:
        for data in DEFAULT_ROUTES:
            route = ModelRoute(**data, id=new_id())
            self.register(route)

    def discover_local(self) -> None:
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[1:]:
                    parts = line.split()
                    if parts:
                        name = parts[0]
                        self._infer_and_register_local(name)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.debug("Ollama not available for local discovery")

    def _infer_and_register_local(self, model_name: str) -> None:
        name_lower = model_name.lower()
        caps: list[ModelCapability] = [ModelCapability.CONVERSATION]

        if any(k in name_lower for k in ["coder", "code"]):
            caps.append(ModelCapability.CODE)
        if any(k in name_lower for k in ["reason", "r1", "think"]):
            caps.append(ModelCapability.REASONING)
        if any(k in name_lower for k in ["deepseek", "qwen", "yi"]):
            caps.append(ModelCapability.REASONING)
        if "vision" in name_lower or "llava" in name_lower:
            caps.append(ModelCapability.VISION)
        if any(k in name_lower for k in ["tiny", "small", "3b", "1b", "7b"]):
            caps.append(ModelCapability.FAST)

        route = ModelRoute(
            provider="ollama",
            model_name=model_name,
            capabilities=caps,
            priority=7,
            cost_per_1k_tokens=0.0,
            latency_p50_ms=300,
        )
        self.register(route)


class CapabilityScorer:
    """Score and rank models by capability match, cost, and latency."""

    WEIGHTS = {
        "capability_match": 0.5,
        "cost_penalty": 0.2,
        "latency_penalty": 0.15,
        "priority_bonus": 0.15,
    }

    def score(
        self,
        route: ModelRoute,
        required_capabilities: list[ModelCapability],
        max_cost: float | None = None,
        max_latency: float | None = None,
    ) -> float:
        score = 0.0

        matched = sum(1 for c in required_capabilities if c in route.capabilities)
        capability_score = matched / max(len(required_capabilities), 1)
        score += capability_score * self.WEIGHTS["capability_match"]

        if max_cost is not None and route.cost_per_1k_tokens > max_cost:
            score -= 0.3

        cost_score = 1.0 / (1.0 + route.cost_per_1k_tokens * 100)
        score += cost_score * self.WEIGHTS["cost_penalty"]

        if max_latency is not None and route.latency_p50_ms > max_latency:
            score -= 0.2

        latency_score = 1.0 / (1.0 + route.latency_p50_ms / 1000)
        score += latency_score * self.WEIGHTS["latency_penalty"]

        priority_score = route.priority / 10.0
        score += priority_score * self.WEIGHTS["priority_bonus"]

        return score


class FallbackManager:
    """Manage fallback chains when the primary model is unavailable."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self._fallback_chains: dict[str, list[str]] = {}

    def set_fallback_chain(self, primary: str, fallbacks: list[str]) -> None:
        self._fallback_chains[primary] = fallbacks

    def get_chain(self, primary: str) -> list[str]:
        return [primary] + self._fallback_chains.get(primary, [])

    async def try_each(
        self,
        route_names: list[str],
        invoke_fn: Any,
    ) -> Any:
        last_error: Exception | None = None
        for name in route_names:
            route = self.registry.get(name)
            if not route or not route.enabled:
                continue
            try:
                return await invoke_fn(route)
            except Exception as e:
                last_error = e
                logger.warning("Fallback %s failed: %s", name, e)
        if last_error:
            raise last_error


class ModelRouter:
    """Intelligent model selection and routing."""

    def __init__(
        self,
        registry: ModelRegistry | None = None,
        scorer: CapabilityScorer | None = None,
        fallback: FallbackManager | None = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.scorer = scorer or CapabilityScorer()
        self.fallback = fallback or FallbackManager(self.registry)
        self._logger = logging.getLogger("sara.maestro.router")

    def select(
        self,
        capabilities: list[ModelCapability],
        max_cost: float | None = None,
        max_latency: float | None = None,
    ) -> ModelRoute | None:
        seen: set[str] = set()
        candidates: list[ModelRoute] = []
        for cap in capabilities:
            for route in self.registry.find_by_capability(cap):
                if route.id not in seen:
                    seen.add(route.id)
                    candidates.append(route)

        if not candidates:
            self._logger.warning("No models found for capabilities %s", capabilities)
            return None

        scored = [
            (self.scorer.score(r, capabilities, max_cost, max_latency), r)
            for r in candidates
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        best = scored[0][1]
        self._logger.info(
            "Selected %s/%s (score=%.2f) for %s",
            best.provider, best.model_name, scored[0][0],
            [c.value for c in capabilities],
        )
        return best

    def select_for_task(self, task_type: str) -> ModelRoute | None:
        type_to_caps: dict[str, list[ModelCapability]] = {
            "coding": [ModelCapability.CODE, ModelCapability.REASONING],
            "reasoning": [ModelCapability.REASONING, ModelCapability.LONG_CONTEXT],
            "research": [ModelCapability.RESEARCH, ModelCapability.LONG_CONTEXT],
            "conversation": [ModelCapability.CONVERSATION, ModelCapability.FAST],
            "vision": [ModelCapability.VISION, ModelCapability.REASONING],
        }
        caps = type_to_caps.get(task_type, [ModelCapability.CONVERSATION])
        return self.select(caps)

    def select_with_fallback(
        self,
        capabilities: list[ModelCapability],
    ) -> list[ModelRoute]:
        primary = self.select(capabilities)
        if not primary:
            return []
        key = f"{primary.provider}/{primary.model_name}"
        chain = self.fallback.get_chain(key)
        return [r for name in chain if (r := self.registry.get(name))]
