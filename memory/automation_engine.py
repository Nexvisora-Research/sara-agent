"""
memory/automation_engine.py — Persistent daily workflow scheduler for Sara AI.

Automations are stored per user under memory/data/<user_id>/automations.json
and executed by a lightweight background thread while Sara is running.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from memory.user_profile import get_profile
from tools.news_tools import fetch_news_items
from tools.routine_tools import get_routine_steps

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AUTOMATIONS_FILE = "automations.json"

_scheduler_started = False
_scheduler_lock = threading.Lock()
_storage_lock = threading.Lock()

_STOP_WORDS = {
    "a", "about", "and", "for", "from", "give", "news", "of", "on", "search",
    "summary", "summanry", "the", "this", "top", "update", "updates", "with",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_dir(user_id: str) -> str:
    path = os.path.join(DATA_DIR, user_id)
    os.makedirs(path, exist_ok=True)
    return path


def _automations_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), AUTOMATIONS_FILE)


def _load_automations(user_id: str) -> list[dict[str, Any]]:
    path = _automations_path(user_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Could not load automations for %s: %s", user_id, exc)
        return []


def _save_automations(user_id: str, automations: list[dict[str, Any]]) -> None:
    try:
        with open(_automations_path(user_id), "w", encoding="utf-8") as f:
            json.dump(automations, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("Could not save automations for %s: %s", user_id, exc)


def list_automations(user_id: str) -> list[dict[str, Any]]:
    with _storage_lock:
        return _load_automations(user_id)


def add_automation(user_id: str, automation: dict[str, Any]) -> dict[str, Any]:
    with _storage_lock:
        items = _load_automations(user_id)
        next_id = max((int(item.get("id", 0)) for item in items), default=0) + 1
        automation["id"] = next_id
        items.append(automation)
        _save_automations(user_id, items)
        return automation


def delete_automation(user_id: str, automation_id: int) -> bool:
    with _storage_lock:
        items = _load_automations(user_id)
        kept = [item for item in items if int(item.get("id", -1)) != automation_id]
        if len(kept) == len(items):
            return False
        _save_automations(user_id, kept)
        return True


def set_automation_active(user_id: str, automation_id: int, active: bool) -> bool:
    """Pause or resume one automation without deleting its configuration."""
    with _storage_lock:
        items = _load_automations(user_id)
        for item in items:
            if int(item.get("id", -1)) == automation_id:
                item["active"] = bool(active)
                item["updated_at"] = _now_iso()
                _save_automations(user_id, items)
                return True
    return False


def get_automation_history(user_id: str, automation_id: int) -> list[dict[str, Any]]:
    """Return the newest execution records for one automation."""
    for item in list_automations(user_id):
        if int(item.get("id", -1)) == automation_id:
            history = item.get("run_history", [])
            return list(reversed(history)) if isinstance(history, list) else []
    return []


def clear_automation_history(user_id: str, automation_id: int) -> bool:
    """Remove execution records while keeping the automation itself."""
    with _storage_lock:
        items = _load_automations(user_id)
        for item in items:
            if int(item.get("id", -1)) == automation_id:
                item.pop("run_history", None)
                item.pop("last_status", None)
                item.pop("last_result", None)
                _save_automations(user_id, items)
                return True
    return False


def _record_automation_run(
    user_id: str,
    automation_id: int,
    result: str,
    status: str,
) -> None:
    with _storage_lock:
        items = _load_automations(user_id)
        for item in items:
            if int(item.get("id", -1)) == automation_id:
                history = item.setdefault("run_history", [])
                history.append(
                    {
                        "timestamp": _now_iso(),
                        "status": status,
                        "result": result[:1000],
                    }
                )
                item["run_history"] = history[-20:]
                item["last_status"] = status
                item["last_result"] = result[:1000]
                _save_automations(user_id, items)
                return


def run_automation_now(user_id: str, automation_id: int) -> tuple[bool, str]:
    """Execute one saved automation immediately, even if it is paused."""
    automation = next(
        (
            item
            for item in list_automations(user_id)
            if int(item.get("id", -1)) == automation_id
        ),
        None,
    )
    if automation is None:
        return False, f"I couldn't find automation {automation_id}."
    result, status = _execute_automation(user_id, automation)
    _record_automation_run(user_id, automation_id, result, status)
    _deliver_result(user_id, automation, result)
    return status == "completed", result


def _get_user_timezone(user_id: str) -> str:
    profile = get_profile(user_id)
    tz = str(profile.get("timezone") or "Asia/Kolkata").strip()
    try:
        ZoneInfo(tz)
        return tz
    except Exception:
        return "Asia/Kolkata"


def _parse_clock_time(raw: str) -> tuple[str, str]:
    text = raw.strip().lower()
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        meridiem = match.group(3)
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12
        return f"{hour:02d}:{minute:02d}", raw.strip()

    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", text)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}", raw.strip()

    raise ValueError(f"Unsupported time format: {raw}")


def _extract_news_query(text: str) -> str:
    lower = text.lower()
    if "tech" in lower or "technology" in lower:
        return "technology"
    if re.search(r"\bai\b|artificial intelligence", lower):
        return "AI"

    cleaned = re.sub(r"[^a-z0-9\s]", " ", lower)
    words = [word for word in cleaned.split() if word not in _STOP_WORDS]
    return " ".join(words[:4]) or "technology"


def _extract_routine_name(user_id: str, text: str) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if get_routine_steps(user_id, lowered):
        return lowered

    match = re.match(r"^(?:run|start|open)\s+routine\s+(.+)$", stripped, re.IGNORECASE)
    if not match:
        return None
    candidate = match.group(1).strip().lower()
    if get_routine_steps(user_id, candidate):
        return candidate
    return None


def _infer_workflow(user_id: str, user_input: str) -> tuple[str, dict[str, Any]]:
    lower = user_input.lower()
    routine_name = _extract_routine_name(user_id, user_input)
    if routine_name:
        return (
            "routine_run",
            {
                "routine_name": routine_name,
            },
        )
    if "git commit" in lower:
        return (
            "git_commit",
            {
                "repo_path": os.getcwd(),
                "commit_message": "Scheduled commit by Sara AI",
            },
        )

    return (
        "news_summary",
        {
            "query": _extract_news_query(user_input),
            "max_items": 5,
        },
    )


def parse_automation_creation(user_id: str, user_input: str) -> dict[str, Any] | None:
    text = user_input.strip()
    match = re.match(
        r"^(?:(?:every day|daily)\s+)?(?:at\s+)?"
        r"((?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:am|pm)|(?:[01]?\d|2[0-3]):[0-5]\d)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    schedule_time, remainder = match.groups()
    normalized_time, display_time = _parse_clock_time(schedule_time)
    workflow_type, config = _infer_workflow(user_id, remainder)
    return {
        "type": workflow_type,
        "config": config,
        "schedule": {
            "kind": "daily",
            "time": normalized_time,
            "display_time": display_time,
            "timezone": _get_user_timezone(user_id),
        },
        "source_text": text,
        "active": True,
        "created_at": _now_iso(),
        "last_run_at": None,
        "last_run_local_date": None,
    }


def format_automation(automation: dict[str, Any]) -> str:
    details = automation.get("config", {})
    label = automation.get("type", "workflow").replace("_", " ")
    if automation.get("type") == "news_summary":
        label = f"news summary for '{details.get('query', 'technology')}'"
    elif automation.get("type") == "git_commit":
        label = f"git commit in {details.get('repo_path', os.getcwd())}"
    elif automation.get("type") == "routine_run":
        label = f"run routine '{details.get('routine_name', 'unknown')}'"

    schedule = automation.get("schedule", {})
    status = "active" if automation.get("active", True) else "paused"
    return (
        f"[{automation.get('id', '?')}] {label} "
        f"at {schedule.get('display_time', schedule.get('time', '?'))} "
        f"({schedule.get('timezone', 'UTC')}) - {status}"
    )


def render_automations_text(user_id: str) -> str:
    items = list_automations(user_id)
    if not items:
        return (
            "No automations yet.\n"
            "Try: `9 am top tech search and give summary`"
        )
    return "Scheduled automations:\n" + "\n".join(format_automation(item) for item in items)


def _headline_summary(query: str, items: list[dict[str, Any]]) -> str:
    titles = [str(item.get("title", "")).strip() for item in items if item.get("title")]
    if not titles:
        return f"Daily {query} update: no headlines found."

    token_counts: dict[str, int] = {}
    for title in titles:
        for token in re.findall(r"[a-zA-Z]{4,}", title.lower()):
            if token in _STOP_WORDS:
                continue
            token_counts[token] = token_counts.get(token, 0) + 1

    themes = ", ".join(word for word, _ in sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))[:3])
    lines = [f"Daily {query} summary"]
    if themes:
        lines.append(f"Main themes: {themes}")
    for index, title in enumerate(titles[:5], start=1):
        lines.append(f"{index}. {title}")
    return "\n".join(lines)


def _send_telegram_message(chat_id: str, text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or not chat_id:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        data = response.json()
        return bool(data.get("ok"))
    except Exception as exc:
        logger.warning("Could not send automation message to Telegram: %s", exc)
        return False


def _deliver_result(user_id: str, automation: dict[str, Any], text: str) -> None:
    profile = get_profile(user_id)
    chat_id = str(profile.get("telegram_chat_id") or "").strip()
    if _send_telegram_message(chat_id, text):
        return
    logger.info("Automation result for %s [%s]: %s", user_id, automation.get("id"), text)


def _run_news_summary(user_id: str, automation: dict[str, Any]) -> str:
    config = automation.get("config", {})
    query = str(config.get("query") or "technology")
    max_items = int(config.get("max_items") or 5)
    items = fetch_news_items(query, max_items=max_items)
    return _headline_summary(query, items)


def _run_git_commit(user_id: str, automation: dict[str, Any]) -> str:
    config = automation.get("config", {})
    repo_path = str(config.get("repo_path") or os.getcwd())
    commit_message = str(config.get("commit_message") or "Scheduled commit by Sara AI")

    try:
        status = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if status.returncode != 0:
            return f"Scheduled git commit failed in {repo_path}: {status.stderr.strip() or status.stdout.strip() or 'git status error'}"
        if not status.stdout.strip():
            return f"Scheduled git commit skipped for {repo_path}: no changes to commit."

        add_result = subprocess.run(
            ["git", "-C", repo_path, "add", "-A"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if add_result.returncode != 0:
            return f"Scheduled git add failed in {repo_path}: {add_result.stderr.strip() or add_result.stdout.strip() or 'git add error'}"

        stamped_message = f"{commit_message} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        commit_result = subprocess.run(
            ["git", "-C", repo_path, "commit", "-m", stamped_message],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if commit_result.returncode != 0:
            details = commit_result.stderr.strip() or commit_result.stdout.strip() or "git commit error"
            return f"Scheduled git commit failed in {repo_path}: {details}"
        summary = commit_result.stdout.strip().splitlines()[0]
        return f"Scheduled git commit completed in {repo_path}: {summary}"
    except Exception as exc:
        return f"Scheduled git commit failed in {repo_path}: {exc}"


def _run_routine_automation(user_id: str, automation: dict[str, Any]) -> str:
    config = automation.get("config", {})
    routine_name = str(config.get("routine_name") or "").strip().lower()
    steps = get_routine_steps(user_id, routine_name)
    if not steps:
        return f"Scheduled routine '{routine_name}' could not run because it no longer exists."

    from tools.register_tool import execute_tool

    lines = [f"Scheduled routine '{routine_name}' completed:"]
    for index, step in enumerate(steps, start=1):
        action = str(step.get("action") or "").strip().lower()
        value = str(step.get("input") or "")
        goal = str(step.get("goal") or f"step {index}")
        if not action:
            lines.append(f"{index}. {goal}: skipped (missing action)")
            continue
        result = execute_tool(action, value, user_id=user_id)
        first_line = result.strip().splitlines()[0] if result.strip() else "done"
        lines.append(f"{index}. {goal}: {first_line}")
    return "\n".join(lines)


def _execute_automation(user_id: str, automation: dict[str, Any]) -> tuple[str, str]:
    try:
        automation_type = automation.get("type")
        if automation_type == "git_commit":
            result = _run_git_commit(user_id, automation)
        elif automation_type == "routine_run":
            result = _run_routine_automation(user_id, automation)
        else:
            result = _run_news_summary(user_id, automation)
        status = "failed" if "failed" in result.lower() else "completed"
        return result, status
    except Exception as exc:
        logger.warning("Automation %s for %s failed: %s", automation.get("id"), user_id, exc)
        return f"Automation {automation.get('id')} failed: {exc}", "failed"


def _mark_run(user_id: str, automation_id: int, local_date: str) -> None:
    with _storage_lock:
        items = _load_automations(user_id)
        for item in items:
            if int(item.get("id", -1)) == automation_id:
                item["last_run_at"] = _now_iso()
                item["last_run_local_date"] = local_date
                break
        _save_automations(user_id, items)


def _due_automations_for_user(user_id: str) -> list[tuple[dict[str, Any], str]]:
    results: list[tuple[dict[str, Any], str]] = []
    for automation in list_automations(user_id):
        if not automation.get("active", True):
            continue
        schedule = automation.get("schedule", {})
        if schedule.get("kind") != "daily":
            continue
        time_str = str(schedule.get("time") or "")
        tz_name = str(schedule.get("timezone") or "Asia/Kolkata")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("Asia/Kolkata")
        now_local = datetime.now(tz)
        current_hm = now_local.strftime("%H:%M")
        local_date = now_local.strftime("%Y-%m-%d")
        if current_hm < time_str:
            continue
        if automation.get("last_run_local_date") == local_date:
            continue
        results.append((automation, local_date))
    return results


def run_due_automations() -> None:
    if not os.path.isdir(DATA_DIR):
        return
    for user_id in os.listdir(DATA_DIR):
        user_path = os.path.join(DATA_DIR, user_id)
        if not os.path.isdir(user_path):
            continue
        for automation, local_date in _due_automations_for_user(user_id):
            _mark_run(user_id, int(automation.get("id", -1)), local_date)
            result, status = _execute_automation(user_id, automation)
            _record_automation_run(user_id, int(automation.get("id", -1)), result, status)
            _deliver_result(user_id, automation, result)


def _scheduler_loop() -> None:
    while True:
        try:
            run_due_automations()
        except Exception as exc:
            logger.exception("Automation scheduler loop error: %s", exc)
        time.sleep(30)


def start_scheduler() -> None:
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        thread = threading.Thread(target=_scheduler_loop, daemon=True, name="sara-automation-scheduler")
        thread.start()
        _scheduler_started = True
        logger.info("Automation scheduler started.")
