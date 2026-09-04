"""
agent/planner.py — Structured planner / worker coordinator for Sara AI vNext.

Complex turns are upgraded from free-form multi-tool execution into:
  planner -> workers -> reviewer

This module owns the shared execution plan data structures and the worker-side
plan execution. The reviewer lives in agent/observer.py.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from brain.llm_engine import ask_ai_smart
from tools.register_tool import execute_tool, get_tool_catalog, get_tool_policy

logger = logging.getLogger(__name__)

MAX_SUBTASKS = 4
MAX_PARALLEL_WORKERS = 2
MAX_TOOL_CALLS_PER_SUBTASK = 3


@dataclass
class ToolCall:
    action: str
    input: str = ""


@dataclass
class Subtask:
    id: str
    goal: str
    depends_on: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    risk_level: str = "safe_read"
    expected_output: str = ""
    parallelizable: bool = True


@dataclass
class ExecutionPlan:
    user_goal: str
    subtasks: list[Subtask]
    planner_notes: str = ""


@dataclass
class WorkerResult:
    subtask_id: str
    goal: str
    success: bool
    outputs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    action_summaries: list[str] = field(default_factory=list)
    attempts: int = 1
    skipped: bool = False
    risk_level: str = "safe_read"


@dataclass
class ReviewResult:
    status: str
    final_text: str
    action_summaries: list[str] = field(default_factory=list)
    pending_confirmation: dict | None = None
    progress_updates: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    status: str
    final_text: str
    progress_updates: list[str] = field(default_factory=list)
    confirmation: dict | None = None
    action_summaries: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def requires_confirmation(self) -> bool:
        return self.confirmation is not None

    def render_text(self) -> str:
        return self.final_text


def plan_complex_task(user_id: str, user_input: str, context: str = "") -> ExecutionPlan:
    """Create a structured execution plan for a complex request."""
    plan = _plan_with_llm(user_input=user_input, context=context)
    if plan is None:
        plan = _heuristic_plan(user_input)
    return _normalize_plan(plan, user_input)


def execute_plan(
    user_id: str,
    plan: ExecutionPlan,
    *,
    allow_risky: bool = False,
) -> tuple[list[WorkerResult], list[Subtask], list[str], bool]:
    """
    Execute all ready subtasks while respecting dependencies and confirmation policy.

    Returns (worker_results, pending_confirmation_subtasks, progress_updates, partial_completion).
    """
    remaining = {subtask.id: subtask for subtask in plan.subtasks}
    completed: set[str] = set()
    failed: set[str] = set()
    results: list[WorkerResult] = []
    progress_updates: list[str] = []
    pending_confirmation: list[Subtask] = []
    partial_completion = False

    while remaining:
        ready = [
            subtask
            for subtask in remaining.values()
            if all(dep in completed for dep in subtask.depends_on)
        ]

        if not ready:
            partial_completion = bool(completed)
            for subtask in list(remaining.values()):
                result = WorkerResult(
                    subtask_id=subtask.id,
                    goal=subtask.goal,
                    success=False,
                    errors=["Skipped because dependencies failed or could not be resolved."],
                    skipped=True,
                    risk_level=subtask.risk_level,
                )
                results.append(result)
                failed.add(subtask.id)
                remaining.pop(subtask.id, None)
            break

        blocked = []
        executable = []
        for subtask in ready:
            if subtask.depends_on and any(dep in failed for dep in subtask.depends_on):
                result = WorkerResult(
                    subtask_id=subtask.id,
                    goal=subtask.goal,
                    success=False,
                    errors=["Skipped because a dependency failed."],
                    skipped=True,
                    risk_level=subtask.risk_level,
                )
                results.append(result)
                failed.add(subtask.id)
                remaining.pop(subtask.id, None)
                continue
            if _requires_confirmation(subtask) and not allow_risky:
                blocked.append(subtask)
            else:
                executable.append(subtask)

        if blocked:
            pending_confirmation.extend(sorted(blocked, key=lambda item: item.id))
            partial_completion = bool(completed)
            break

        if not executable:
            partial_completion = bool(completed)
            break

        batch = _choose_batch(executable)
        for subtask in batch:
            remaining.pop(subtask.id, None)

        if len(batch) == 1:
            batch_results = [_execute_subtask(user_id, batch[0])]
        else:
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_WORKERS, len(batch))) as pool:
                batch_results = list(pool.map(lambda item: _execute_subtask(user_id, item), batch))

        for result in batch_results:
            results.append(result)
            if result.success:
                completed.add(result.subtask_id)
                progress_updates.append(f"Completed {result.subtask_id}: {result.goal}")
            else:
                failed.add(result.subtask_id)
                progress_updates.append(f"Failed {result.subtask_id}: {result.goal}")

    return results, pending_confirmation, progress_updates, partial_completion


def _choose_batch(ready: list[Subtask]) -> list[Subtask]:
    """Pick up to two ready subtasks, preserving sequential work when needed."""
    ready = sorted(ready, key=lambda item: item.id)
    first = ready[0]
    if not first.parallelizable:
        return [first]

    batch = [first]
    for subtask in ready[1:]:
        if not subtask.parallelizable:
            break
        batch.append(subtask)
        if len(batch) >= MAX_PARALLEL_WORKERS:
            break
    return batch


def _execute_subtask(user_id: str, subtask: Subtask) -> WorkerResult:
    """Run the tool calls for one subtask, with one repair retry."""
    attempts = 0
    outputs: list[str] = []
    errors: list[str] = []
    action_summaries: list[str] = []

    while attempts < 2:
        attempts += 1
        outputs.clear()
        errors.clear()
        action_summaries.clear()

        if not subtask.tool_calls:
            errors.append("No executable tool calls were planned for this subtask.")
            break

        for tool_call in subtask.tool_calls[:MAX_TOOL_CALLS_PER_SUBTASK]:
            try:
                result = execute_tool(tool_call.action, tool_call.input, user_id=user_id)
            except Exception as exc:  # pragma: no cover - defensive fallback
                result = f"⚠️ Tool '{tool_call.action}' failed: {exc}"
            outputs.append(result)
            action_summaries.append(f"{tool_call.action}({tool_call.input})")
            if _looks_like_failure(result):
                errors.append(result)
                break

        if not errors:
            return WorkerResult(
                subtask_id=subtask.id,
                goal=subtask.goal,
                success=True,
                outputs=list(outputs),
                action_summaries=action_summaries,
                attempts=attempts,
                risk_level=subtask.risk_level,
            )

    return WorkerResult(
        subtask_id=subtask.id,
        goal=subtask.goal,
        success=False,
        outputs=list(outputs),
        errors=list(errors),
        action_summaries=action_summaries,
        attempts=attempts,
        risk_level=subtask.risk_level,
    )


def _requires_confirmation(subtask: Subtask) -> bool:
    for tool_call in subtask.tool_calls:
        policy = get_tool_policy(tool_call.action)
        if not policy.requires_confirmation:
            continue
        if tool_call.action == "browser_fill_form" and _is_browser_search_shortcut(tool_call.input):
            continue
        return True
    return False


def _is_browser_search_shortcut(tool_input: str) -> bool:
    """Return True when browser_fill_form is being used as a site search shortcut."""
    text = (tool_input or "").strip()
    if not text or "::" in text:
        return False

    parsed: dict[str, str] = {}
    for chunk in re.split(r"[;,]", text):
        chunk = chunk.strip()
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        parsed[key.strip().lower()] = value.strip()

    if not parsed or "url" not in parsed:
        return False

    allowed_keys = {"url", "site", "website", "query", "q", "search"}
    keys = set(parsed.keys())
    return bool(keys & {"query", "q", "search"}) and keys.issubset(allowed_keys)


def _looks_like_failure(text: str) -> bool:
    lowered = (text or "").lower().strip()
    return lowered.startswith(("❌", "⚠️", "⛔")) or "error" in lowered


def _plan_with_llm(user_input: str, context: str) -> ExecutionPlan | None:
    catalog = json.dumps(get_tool_catalog(), ensure_ascii=False, indent=2)
    prompt = f"""You are Sara AI's task planner.

Create a compact JSON execution plan for the user's request.
Only include subtasks that materially help complete the task.
Use at most 4 subtasks and at most 3 tool calls per subtask.
Respect tool safety metadata. Risky tools should stay in the plan but be marked risky.
Output JSON only.

Available tools:
{catalog}

Recent context:
{context or "(none)"}

Schema:
{{
  "user_goal": "short restatement",
  "planner_notes": "short note",
  "subtasks": [
    {{
      "id": "task_1",
      "goal": "what this subtask does",
      "depends_on": [],
      "tool_calls": [
        {{"action": "tool_name", "input": "value"}}
      ],
      "risk_level": "safe_read|safe_write|risky",
      "expected_output": "what should come back",
      "parallelizable": true
    }}
  ]
}}

User request:
{user_input}
"""
    raw = ask_ai_smart(prompt).strip()
    if not raw or raw.startswith("⚠️"):
        return None

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return _coerce_plan(parsed)


def _coerce_plan(data: dict) -> ExecutionPlan:
    subtasks = []
    for item in data.get("subtasks", [])[:MAX_SUBTASKS]:
        tool_calls = []
        for tool_call in item.get("tool_calls", [])[:MAX_TOOL_CALLS_PER_SUBTASK]:
            action = str(tool_call.get("action", "")).strip()
            if not action:
                continue
            tool_calls.append(ToolCall(action=action, input=str(tool_call.get("input", ""))))
        subtasks.append(
            Subtask(
                id=str(item.get("id", f"task_{len(subtasks) + 1}")),
                goal=str(item.get("goal", "")).strip() or f"Subtask {len(subtasks) + 1}",
                depends_on=[str(dep) for dep in item.get("depends_on", [])],
                tool_calls=tool_calls,
                risk_level=str(item.get("risk_level", "safe_read")),
                expected_output=str(item.get("expected_output", "")).strip(),
                parallelizable=bool(item.get("parallelizable", True)),
            )
        )
    return ExecutionPlan(
        user_goal=str(data.get("user_goal", "")).strip(),
        planner_notes=str(data.get("planner_notes", "")).strip(),
        subtasks=subtasks,
    )


def _normalize_plan(plan: ExecutionPlan, user_input: str) -> ExecutionPlan:
    normalized = []
    for index, subtask in enumerate(plan.subtasks[:MAX_SUBTASKS], start=1):
        action_calls = []
        for tool_call in subtask.tool_calls[:MAX_TOOL_CALLS_PER_SUBTASK]:
            if tool_call.action.strip():
                action_calls.append(ToolCall(tool_call.action.strip().lower(), tool_call.input))

        if not action_calls:
            continue

        derived_level = _derive_risk_level(action_calls)
        normalized.append(
            Subtask(
                id=subtask.id or f"task_{index}",
                goal=subtask.goal or f"Subtask {index}",
                depends_on=[dep for dep in subtask.depends_on if dep],
                tool_calls=action_calls,
                risk_level=derived_level,
                expected_output=subtask.expected_output,
                parallelizable=bool(subtask.parallelizable),
            )
        )

    if not normalized:
        fallback = _heuristic_plan(user_input)
        return fallback

    return ExecutionPlan(
        user_goal=plan.user_goal or user_input,
        planner_notes=plan.planner_notes,
        subtasks=normalized,
    )


def _derive_risk_level(tool_calls: list[ToolCall]) -> str:
    if any(get_tool_policy(call.action).category == "risky" for call in tool_calls):
        return "risky"
    if any(get_tool_policy(call.action).category == "safe_write" for call in tool_calls):
        return "safe_write"
    return "safe_read"


def _heuristic_plan(user_input: str) -> ExecutionPlan:
    segments = _split_segments(user_input)
    subtasks = []
    for index, segment in enumerate(segments[:MAX_SUBTASKS], start=1):
        tool_calls = _infer_tool_calls(segment)
        if not tool_calls:
            tool_calls = [ToolCall("generate_text", segment)]
        subtasks.append(
            Subtask(
                id=f"task_{index}",
                goal=segment,
                depends_on=[] if index == 1 else [],
                tool_calls=tool_calls,
                risk_level=_derive_risk_level(tool_calls),
                expected_output=f"Useful result for: {segment}",
                parallelizable=" then " not in user_input.lower(),
            )
        )
    return ExecutionPlan(user_goal=user_input, subtasks=subtasks, planner_notes="heuristic planner fallback")


def _split_segments(text: str) -> list[str]:
    parts = re.split(r"\bthen\b|,", text, flags=re.IGNORECASE)
    cleaned = [part.strip(" .") for part in parts if part.strip(" .")]
    return cleaned or [text.strip()]


def _infer_tool_calls(text: str) -> list[ToolCall]:
    lower = text.lower().strip()

    if re.fullmatch(r"(?:please\s+)?(?:shutdown|shut\s*down|power\s*off)(?:\s+(?:pc|computer|system|laptop|machine))?(?:\s+please)?[\s!.]*", lower):
        return [ToolCall("shutdown_pc", "")]

    if re.fullmatch(r"(?:please\s+)?(?:restart|reboot)(?:\s+(?:pc|computer|system|laptop|machine))?(?:\s+please)?[\s!.]*", lower):
        return [ToolCall("restart_pc", "")]

    if lower in {"time", "what's the time", "what is the time"}:
        return [ToolCall("get_time", "")]

    if "weather in " in lower:
        city = lower.split("weather in ", 1)[1].strip()
        return [ToolCall("get_weather", city)]

    if lower.startswith("weather "):
        return [ToolCall("get_weather", text[8:].strip())]

    if "joke" in lower:
        return [ToolCall("tell_joke", "")]

    if lower.startswith("save note:"):
        return [ToolCall("note_save", text.split(":", 1)[1].strip())]

    if lower.startswith("remember:"):
        return [ToolCall("note_save", text.split(":", 1)[1].strip())]

    if re.fullmatch(r"[\d\s+\-*/().]+", lower):
        return [ToolCall("calculate", text)]

    if lower.startswith("calculate "):
        return [ToolCall("calculate", text[len("calculate "):].strip())]

    if "youtube" in lower:
        query = re.sub(r"^(search\s+youtube\s+for|youtube|open youtube|play youtube)\s+", "", text, flags=re.IGNORECASE).strip()
        return [ToolCall("youtube_search", query or text)]

    if lower.startswith("google ") or lower.startswith("search "):
        query = re.sub(r"^(google|search)\s+", "", text, flags=re.IGNORECASE).strip()
        return [ToolCall("google_search", query)]

    if lower.startswith("open terminal"):
        remainder = text[len("open terminal"):].strip()
        remainder = re.sub(r"^(?:and\s+)?(?:run|execute)(?:\s+command)?\s*[:\-]?\s+", "", remainder, flags=re.IGNORECASE).strip()
        return [ToolCall("open_terminal", remainder)]

    run_match = re.match(r"^(?:run|execute)(?:\s+(?:terminal|shell|cmd))?(?:\s+command)?\s*[:\-]?\s+(.+)$", text, flags=re.IGNORECASE)
    if run_match:
        return [ToolCall("run_terminal", run_match.group(1).strip())]

    if lower.startswith("open "):
        target = re.sub(r"^(?:the\s+)?(?:app|application|program|software)\s+", "", text[5:].strip(), flags=re.IGNORECASE)
        return [ToolCall("open_app", target)]

    install_app_match = re.match(
        r"^(?:install|setup|set\s+up)(?:\s+(?:the|an|a))?\s+(?:app|application|program|software)\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if install_app_match:
        return [ToolCall("smart_open_app", install_app_match.group(1).strip())]

    if lower.startswith("install "):
        return [ToolCall("install_package", text[8:].strip())]

    if lower.startswith("read file "):
        return [ToolCall("read_file", text[10:].strip())]

    if lower.startswith("list files"):
        folder = text[10:].strip() or "."
        return [ToolCall("list_files", folder)]

    if lower.startswith("create folder "):
        return [ToolCall("create_folder", text[14:].strip())]

    if lower.startswith("create project "):
        return [ToolCall("create_project", text[15:].strip())]

    multi_agent_match = re.match(
        r"^(?:use\s+)?(?:multi[-\s]?agents?|agents?|delegate)(?:\s+(?:to|for|on))?\s*[:\-]?\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if multi_agent_match:
        return [ToolCall("delegate_task", multi_agent_match.group(1).strip())]

    return []
