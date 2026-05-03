"""
tools/automation_tools.py — Natural-language automation helpers for Sara AI.
"""

from __future__ import annotations

import os
import re

from memory.automation_engine import (
    add_automation,
    delete_automation,
    format_automation,
    parse_automation_creation,
    render_automations_text,
)


def schedule_workflow(value: str, user_id: str = "") -> str:
    if not user_id:
        return "❌ Missing user context for scheduling."

    automation = parse_automation_creation(user_id, value)
    if not automation:
        return (
            "❓ I couldn't parse that schedule.\n"
            "Try: `9 am top tech search and give summary` or `every day 8 pm gaming time`"
        )

    saved = add_automation(user_id, automation)
    note = ""
    if saved.get("type") == "git_commit":
        repo_path = str(saved.get("config", {}).get("repo_path") or "")
        note = "\nThis one will run `git add -A` and `git commit` in the current project folder."
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            note += "\nWarning: the current folder is not a Git repository right now, so this workflow will fail until you point Sara at a real repo."
    elif saved.get("type") == "routine_run":
        note = "\nThis will run the named routine automatically at the scheduled time."
    return f"✅ Automation scheduled: {format_automation(saved)}{note}"


def list_scheduled_workflows(unused: str = "", user_id: str = "") -> str:
    if not user_id:
        return "❌ Missing user context."
    return render_automations_text(user_id)


def remove_scheduled_workflow(value: str, user_id: str = "") -> str:
    if not user_id:
        return "❌ Missing user context."

    match = re.search(r"(\d+)", value)
    if not match:
        return "❓ Tell me which automation to delete, for example: `delete automation 2`"

    automation_id = int(match.group(1))
    if delete_automation(user_id, automation_id):
        return f"🗑️ Deleted automation {automation_id}."
    return f"❌ I couldn't find automation {automation_id}."


def try_handle_automation_request(user_id: str, user_input: str) -> str | None:
    text = user_input.strip()
    lower = text.lower()

    if lower in {"list automations", "show automations", "my automations", "list workflows"}:
        return list_scheduled_workflows("", user_id=user_id)

    if lower.startswith("delete automation") or lower.startswith("remove automation"):
        return remove_scheduled_workflow(text, user_id=user_id)

    if parse_automation_creation(user_id, text):
        return schedule_workflow(text, user_id=user_id)

    return None
