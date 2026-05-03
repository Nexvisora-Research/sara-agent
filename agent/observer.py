"""
agent/observer.py — Reviewer / response composer for Sara AI vNext.

Takes structured worker results plus pending confirmation needs and turns them
into a user-facing response envelope.
"""

from __future__ import annotations

from dataclasses import asdict

from agent.planner import AgentResponse, ExecutionPlan, ReviewResult, Subtask, WorkerResult


def review_execution(
    *,
    user_input: str,
    plan: ExecutionPlan,
    worker_results: list[WorkerResult],
    pending_confirmation: list[Subtask],
) -> ReviewResult:
    """Review worker output and compose the next response step."""
    completed = [result for result in worker_results if result.success]
    failed = [result for result in worker_results if not result.success and not result.skipped]
    skipped = [result for result in worker_results if result.skipped]
    action_summaries = _collect_action_summaries(worker_results)

    if pending_confirmation:
        prompt = _build_confirmation_prompt(user_input, completed, pending_confirmation)
        return ReviewResult(
            status="confirmation",
            final_text=prompt,
            action_summaries=action_summaries,
            pending_confirmation={
                "user_goal": plan.user_goal,
                "completed_results": [asdict(item) for item in completed],
                "pending_subtasks": [asdict(item) for item in pending_confirmation],
            },
            progress_updates=[f"Awaiting approval for {len(pending_confirmation)} risky step(s)."],
        )

    if failed and completed:
        return ReviewResult(
            status="partial",
            final_text=_build_partial_reply(user_input, completed, failed),
            action_summaries=action_summaries,
            progress_updates=["Completed with partial failures."],
            meta={"failed": len(failed), "completed": len(completed), "skipped": len(skipped)},
        )

    if failed and not completed:
        return ReviewResult(
            status="error",
            final_text=_build_failure_reply(user_input, failed),
            action_summaries=action_summaries,
            progress_updates=["No safe execution path succeeded."],
            meta={"failed": len(failed), "completed": 0, "skipped": len(skipped)},
        )

    return ReviewResult(
        status="final",
        final_text=_build_success_reply(user_input, completed),
        action_summaries=action_summaries,
        progress_updates=["Completed successfully."],
        meta={"failed": 0, "completed": len(completed), "skipped": len(skipped)},
    )


def to_agent_response(review: ReviewResult) -> AgentResponse:
    """Convert a review result into the shared response envelope."""
    return AgentResponse(
        status=review.status,
        final_text=review.final_text,
        progress_updates=review.progress_updates,
        confirmation=review.pending_confirmation,
        action_summaries=review.action_summaries,
        meta=review.meta,
    )


def _collect_action_summaries(worker_results: list[WorkerResult]) -> list[str]:
    seen = []
    for result in worker_results:
        for action in result.action_summaries:
            if action not in seen:
                seen.append(action)
    return seen


def _build_confirmation_prompt(
    user_input: str,
    completed: list[WorkerResult],
    pending_confirmation: list[Subtask],
) -> str:
    lines = [f"I understood this as: {user_input}"]
    if completed:
        lines.append("")
        lines.append("Finished the safe parts already:")
        for result in completed[:3]:
            lines.append(f"- {result.goal}")

    lines.append("")
    lines.append("I need your approval before I do these risky actions:")
    for subtask in pending_confirmation[:3]:
        tool_summaries = [_format_tool_call_for_approval(call.action, call.input) for call in subtask.tool_calls]
        tool_text = "; ".join(summary for summary in tool_summaries if summary) or "unknown tool"
        lines.append(f"- {subtask.goal}. Planned: {tool_text}")
    lines.append("")
    lines.append("Reply with `yes` to continue or `no` to stop here.")
    return "\n".join(lines)


def _format_tool_call_for_approval(action: str, tool_input: str) -> str:
    cleaned = (tool_input or "").strip()
    if action in {"open_terminal", "run_terminal"}:
        if cleaned:
            return f"{action} — run `{_trim(cleaned, 120)}`"
        return f"{action} — open terminal"
    if cleaned:
        return f"{action} — input `{_trim(cleaned, 120)}`"
    return action


def _build_success_reply(user_input: str, completed: list[WorkerResult]) -> str:
    lines = [f"I understood this as: {user_input}", "", "Done:"]
    for result in completed[:4]:
        lines.append(f"- {result.goal}")
        if result.outputs:
            lines.append(_summarize_output(result.outputs[-1]))
    return "\n".join(lines).strip()


def _build_partial_reply(
    user_input: str,
    completed: list[WorkerResult],
    failed: list[WorkerResult],
) -> str:
    lines = [f"I understood this as: {user_input}", "", "Completed:"]
    for result in completed[:4]:
        lines.append(f"- {result.goal}")
    lines.append("")
    lines.append("I could not finish:")
    for result in failed[:3]:
        detail = result.errors[-1] if result.errors else "Unknown error"
        lines.append(f"- {result.goal}: {_trim(detail)}")
    return "\n".join(lines)


def _build_failure_reply(user_input: str, failed: list[WorkerResult]) -> str:
    lines = [f"I understood this as: {user_input}", "", "I couldn't complete the requested actions."]
    for result in failed[:3]:
        detail = result.errors[-1] if result.errors else "Unknown error"
        lines.append(f"- {result.goal}: {_trim(detail)}")
    return "\n".join(lines)


def _summarize_output(text: str) -> str:
    trimmed = _trim(text)
    if not trimmed:
        return "- Returned no output."
    if trimmed.startswith(("✅", "🕐", "🌤️", "😄", "📄", "📂", "🧠", "📝", "💾")):
        return trimmed
    return f"- {_trim(trimmed)}"


def _trim(text: str, limit: int = 220) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
