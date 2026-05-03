"""
agent/multi_agent.py — lightweight multi-agent coordinator for Sara AI.

The checked-in .agents/ folder contains transport and provider code from a
larger agent runtime. Sara's current package already uses agent/ for its own
turn loop, so this module gives Sara a small native coordinator while using
.agents/ as the local agent-home/config surface.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brain.llm_engine import ask_ai_creative, ask_ai_smart

logger = logging.getLogger(__name__)

MAX_WORKERS = 4
DEFAULT_AGENT_HOME = Path(__file__).resolve().parent.parent / ".agents"
DEFAULT_CONFIG_PATH = DEFAULT_AGENT_HOME / "sara_agents.json"


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    instructions: str
    tier: str = "smart"


@dataclass
class AgentWorkItem:
    id: str
    agent: str
    goal: str
    context: str = ""


@dataclass
class AgentWorkResult:
    id: str
    agent: str
    goal: str
    success: bool
    output: str
    error: str = ""


@dataclass
class MultiAgentRuntime:
    home: Path = DEFAULT_AGENT_HOME
    config_path: Path = DEFAULT_CONFIG_PATH
    agents: dict[str, AgentSpec] = field(default_factory=dict)
    initialized: bool = False

    def initialize(self) -> None:
        try:
            self.home.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.debug("Could not create multi-agent home %s: %s", self.home, exc)
        self.agents = self._load_agents()
        self.initialized = True
        logger.info("Sara multi-agent runtime ready with %s agents", len(self.agents))

    def status_text(self) -> str:
        if not self.initialized:
            self.initialize()
        rows = [
            f"- {spec.name}: {spec.role} ({spec.tier})"
            for spec in sorted(self.agents.values(), key=lambda item: item.name)
        ]
        return (
            "Multi-agent runtime: ready\n"
            f"Agent home: {self.home}\n"
            f"Config: {self.config_path}\n"
            "Agents:\n"
            + "\n".join(rows)
        )

    def delegate(self, goal: str, *, user_id: str = "", context: str = "") -> str:
        if not self.initialized:
            self.initialize()
        goal = goal.strip()
        if not goal:
            return "Please provide a task to delegate."

        work_items = self._plan_work(goal, context=context)
        if not work_items:
            work_items = [AgentWorkItem("task_1", "researcher", goal, context)]

        workers = min(MAX_WORKERS, max(1, len(work_items)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda item: self._run_agent(item, goal, user_id), work_items))

        return self._review(goal, results, context=context)

    def _default_config(self) -> dict[str, Any]:
        return {
            "version": 1,
            "agents": [
                {
                    "name": "planner",
                    "role": "Break complex requests into clear, ordered work.",
                    "tier": "smart",
                    "instructions": "Find dependencies, risks, and the smallest useful execution path.",
                },
                {
                    "name": "researcher",
                    "role": "Gather facts, options, and relevant context.",
                    "tier": "smart",
                    "instructions": "Be precise. Separate known facts from assumptions.",
                },
                {
                    "name": "builder",
                    "role": "Design implementation steps and concrete changes.",
                    "tier": "smart",
                    "instructions": "Prefer practical, repo-aware work. Keep scope tight.",
                },
                {
                    "name": "reviewer",
                    "role": "Review outputs for bugs, gaps, risks, and missing verification.",
                    "tier": "creative",
                    "instructions": "Challenge weak assumptions and summarize the safest final answer.",
                },
            ],
        }

    def _load_agents(self) -> dict[str, AgentSpec]:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Could not load multi-agent config: %s", exc)
                data = self._default_config()
        else:
            data = self._default_config()

        agents: dict[str, AgentSpec] = {}
        for item in data.get("agents", []):
            name = str(item.get("name", "")).strip().lower()
            if not name:
                continue
            agents[name] = AgentSpec(
                name=name,
                role=str(item.get("role", "")).strip() or name,
                instructions=str(item.get("instructions", "")).strip(),
                tier=str(item.get("tier", "smart")).strip().lower() or "smart",
            )

        return agents or self._agents_from_config(self._default_config())

    def _agents_from_config(self, data: dict[str, Any]) -> dict[str, AgentSpec]:
        agents: dict[str, AgentSpec] = {}
        for item in data.get("agents", []):
            name = str(item.get("name", "")).strip().lower()
            if not name:
                continue
            agents[name] = AgentSpec(
                name=name,
                role=str(item.get("role", "")).strip() or name,
                instructions=str(item.get("instructions", "")).strip(),
                tier=str(item.get("tier", "smart")).strip().lower() or "smart",
            )
        return agents

    def _plan_work(self, goal: str, *, context: str = "") -> list[AgentWorkItem]:
        available = "\n".join(f"- {name}: {spec.role}" for name, spec in self.agents.items())
        prompt = f"""You are Sara AI's multi-agent coordinator.

Split the user's goal into 2-4 independent work items for the available agents.
Use only these agent names:
{available}

Return JSON only:
{{
  "tasks": [
    {{"id": "task_1", "agent": "researcher", "goal": "specific subtask", "context": "brief context"}}
  ]
}}

Recent context:
{context or "(none)"}

User goal:
{goal}
"""
        raw = ask_ai_smart(prompt).strip()
        if not raw or raw.startswith("⚠️"):
            return self._fallback_plan(goal, context)

        raw = raw.removeprefix("```json").removeprefix("```").strip()
        raw = raw.removesuffix("```").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return self._fallback_plan(goal, context)

        items: list[AgentWorkItem] = []
        for index, task in enumerate(data.get("tasks", [])[:MAX_WORKERS], start=1):
            agent = str(task.get("agent", "")).strip().lower()
            if agent not in self.agents:
                agent = self._best_agent_for_goal(str(task.get("goal", goal)))
            items.append(
                AgentWorkItem(
                    id=str(task.get("id", f"task_{index}")),
                    agent=agent,
                    goal=str(task.get("goal", goal)).strip() or goal,
                    context=str(task.get("context", context)).strip(),
                )
            )
        return items or self._fallback_plan(goal, context)

    def _fallback_plan(self, goal: str, context: str) -> list[AgentWorkItem]:
        return [
            AgentWorkItem("task_1", "planner", f"Plan the best approach for: {goal}", context),
            AgentWorkItem("task_2", "researcher", f"Find key facts and constraints for: {goal}", context),
            AgentWorkItem("task_3", "builder", f"Propose concrete implementation or action steps for: {goal}", context),
            AgentWorkItem("task_4", "reviewer", f"Review risks, gaps, and verification for: {goal}", context),
        ]

    def _best_agent_for_goal(self, goal: str) -> str:
        lower = goal.lower()
        if any(word in lower for word in {"review", "risk", "test", "verify", "bug"}):
            return "reviewer" if "reviewer" in self.agents else next(iter(self.agents))
        if any(word in lower for word in {"build", "implement", "code", "fix", "create"}):
            return "builder" if "builder" in self.agents else next(iter(self.agents))
        if any(word in lower for word in {"research", "find", "compare", "look up"}):
            return "researcher" if "researcher" in self.agents else next(iter(self.agents))
        return "planner" if "planner" in self.agents else next(iter(self.agents))

    def _run_agent(self, item: AgentWorkItem, parent_goal: str, user_id: str) -> AgentWorkResult:
        spec = self.agents.get(item.agent) or next(iter(self.agents.values()))
        prompt = f"""You are Sara AI sub-agent: {spec.name}.
Role: {spec.role}
Instructions: {spec.instructions}

Parent user goal:
{parent_goal}

Your assigned task:
{item.goal}

Context:
{item.context or "(none)"}

Return a concise, useful result. Include assumptions and blockers if any.
"""
        try:
            caller = ask_ai_creative if spec.tier == "creative" else ask_ai_smart
            output = caller(prompt).strip()
            success = bool(output) and not output.startswith("⚠️")
            return AgentWorkResult(item.id, spec.name, item.goal, success, output)
        except Exception as exc:  # pragma: no cover - defensive
            return AgentWorkResult(item.id, spec.name, item.goal, False, "", str(exc))

    def _review(self, goal: str, results: list[AgentWorkResult], *, context: str = "") -> str:
        packed = json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2)
        reviewer = self.agents.get("reviewer")
        reviewer_prompt = f"""You are Sara AI's lead reviewer.

Synthesize the sub-agent results into one final answer for the user.
Be direct. Mention important risks or blockers. Do not invent completed actions.

User goal:
{goal}

Sub-agent results:
{packed}
"""
        try:
            final = ask_ai_creative(reviewer_prompt).strip()
            if final and not final.startswith("⚠️"):
                return final
        except Exception:
            pass

        lines = [f"Multi-agent result for: {goal}", ""]
        for result in results:
            status = "ok" if result.success else "failed"
            lines.append(f"{result.agent} [{status}]: {result.goal}")
            lines.append(result.output or result.error or "No output.")
            lines.append("")
        return "\n".join(lines).strip()


_runtime = MultiAgentRuntime()


def initialize_multi_agent_runtime() -> None:
    _runtime.initialize()


def multi_agent_status(_value: str = "") -> str:
    return _runtime.status_text()


def delegate_task(value: str, user_id: str = "") -> str:
    """Delegate a task to Sara's planner/researcher/builder/reviewer agents."""
    context = ""
    try:
        payload = json.loads(value) if value.strip().startswith("{") else None
    except Exception:
        payload = None
    if isinstance(payload, dict):
        goal = str(payload.get("goal") or payload.get("task") or payload.get("value") or "").strip()
        context = str(payload.get("context") or "").strip()
    else:
        goal = value.strip()
    return _runtime.delegate(goal, user_id=user_id, context=context)
