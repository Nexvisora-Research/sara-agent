"""
agent/build_workflow.py — Sara AI 5-stage Project Builder State Machine.

Flow:
  IDLE → DISCUSSING → PLANNING → AWAITING_APPROVAL → BUILDING → DONE

Trigger: user says "build a website", "create an app", "make a bot", etc.
The Telegram bot intercepts and routes all subsequent messages here
until the session reaches DONE or is cancelled.
"""

import json
import logging
import os
import re
import subprocess
from enum import Enum
from typing import Optional

from brain.llm_engine import ask_ai_smart

logger = logging.getLogger(__name__)

# ── Default project output directory ─────────────────────────────────────────
DEFAULT_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), "sara_projects")


# ══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE
# ══════════════════════════════════════════════════════════════════════════════

class BuildState(str, Enum):
    IDLE              = "IDLE"
    DISCUSSING        = "DISCUSSING"
    PLANNING          = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BUILDING          = "BUILDING"
    DONE              = "DONE"


# In-memory sessions: { user_id: session_dict }
_sessions: dict = {}


# ── Intent detection ──────────────────────────────────────────────────────────

_BUILD_INTENT = re.compile(
    r"\b(build|create|make|develop|write|scaffold|generate|code)\b.{0,40}"
    r"\b(website|web\s*app|app|application|bot|tool|script|project|program|"
    r"portfolio|dashboard|api|cli|plugin|extension|game|landing\s*page)\b",
    re.IGNORECASE,
)


def is_build_intent(text: str) -> bool:
    """Return True if the user's message is a project-build request."""
    return bool(_BUILD_INTENT.search(text))


# ── Session management ────────────────────────────────────────────────────────

def get_session(user_id: str) -> Optional[dict]:
    """Return the current build session for a user, or None."""
    s = _sessions.get(user_id)
    if s and s["state"] != BuildState.IDLE:
        return s
    return None


def reset_session(user_id: str) -> None:
    """Clear the build session for a user."""
    _sessions.pop(user_id, None)
    logger.info(f"[{user_id}] Build session reset.")


def start_session(user_id: str, intent: str) -> str:
    """Initialise a new build session and return the first question."""
    _sessions[user_id] = {
        "state":          BuildState.DISCUSSING,
        "intent":         intent,
        "questions_asked": 0,
        "answers":        [],
        "plan":           {},
        "build_steps":    [],
        "current_step":   0,
        "project_dir":    "",
        "change_request": "",
    }
    logger.info(f"[{user_id}] Build session started: {intent!r}")
    return _ask_next_question(user_id)


# ══════════════════════════════════════════════════════════════════════════════
# STAGE HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

# Questions Sara asks to gather context
_QUESTIONS = [
    "🎯 What's the *main purpose* of this project? _(e.g. showcase work, sell products, track expenses)_",
    "👥 Who are the *target users*? _(e.g. recruiters, customers, just me)_",
    "⚙️ Do you have a *tech preference*? _(e.g. React, Python, plain HTML — or I'll choose the best fit)_",
]


def _ask_next_question(user_id: str) -> str:
    s = _sessions[user_id]
    q_idx = s["questions_asked"]
    if q_idx < len(_QUESTIONS):
        s["questions_asked"] += 1
        # Add a header only on the first question
        prefix = (
            f"🚀 *Project Builder activated!*\n"
            f"Let me ask a couple of quick questions so I can plan this perfectly.\n\n"
            if q_idx == 0 else ""
        )
        return prefix + _QUESTIONS[q_idx]
    # All questions done → move to planning
    return _transition_to_planning(user_id)


def _do_discussing(user_id: str, text: str) -> str:
    """Collect an answer and ask the next question (or advance to PLANNING)."""
    s = _sessions[user_id]
    s["answers"].append(text)
    return _ask_next_question(user_id)


def _transition_to_planning(user_id: str) -> str:
    """Move to PLANNING state and generate the structured plan."""
    s = _sessions[user_id]
    s["state"] = BuildState.PLANNING

    intent   = s["intent"]
    answers  = s["answers"]
    q_labels = ["Purpose", "Target users", "Tech preference"]
    qa_text  = "\n".join(
        f"- {q_labels[i]}: {answers[i]}" for i in range(min(len(answers), len(q_labels)))
    )

    prompt = f"""You are an expert software architect helping a developer plan a new project.

User wants to: {intent}

Gathered context:
{qa_text}

Produce a JSON project plan — NO extra text, ONLY the JSON object:

{{
  "name": "<short project name, no spaces>",
  "description": "<one-sentence description>",
  "framework": "<primary framework or language>",
  "stack": ["<tech1>", "<tech2>", ...],
  "pages": ["<page1>", "<page2>", ...],
  "features": ["<feature1>", "<feature2>", ...],
  "build_steps": [
    {{"step": 1, "type": "scaffold", "cmd": "<shell command>", "description": "<what this does>"}},
    {{"step": 2, "type": "generate", "file": "<relative path>", "prompt": "<what to write>", "description": "<what this does>"}},
    {{"step": 3, "type": "install",  "cmd": "<install command>", "description": "<why>"}},
    {{"step": 4, "type": "run",      "cmd": "<run command>",     "description": "<what starts>"}}
  ]
}}

Rules:
- build_steps MUST include at minimum: one scaffold step, one or more generate steps, and optionally install/run steps.
- Keep build_steps between 3-6 total.
- Use practical, real commands only (npx, pip, python, etc.).
- Output ONLY the JSON. No markdown fences, no explanation.
"""

    raw = ""
    try:
        raw = ask_ai_smart(prompt).strip()
        # Strip markdown fences if the LLM added them anyway
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)
        plan = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Plan generation failed: {e}\nRaw: {raw!r}")
        # Fallback minimal plan
        plan = {
            "name":        "MyProject",
            "description": intent,
            "framework":   "Python",
            "stack":       ["Python"],
            "pages":       [],
            "features":    [],
            "build_steps": [
                {"step": 1, "type": "scaffold", "cmd": "mkdir MyProject", "description": "Create project folder"},
                {"step": 2, "type": "generate", "file": "main.py", "prompt": f"Write a basic Python script for: {intent}", "description": "Main script"},
            ],
        }

    s["plan"] = plan
    s["build_steps"] = plan.get("build_steps", [])
    s["state"] = BuildState.AWAITING_APPROVAL

    return format_plan_card(plan)


def _do_planning_changes(user_id: str, change_request: str) -> str:
    """User wants to change something — re-generate plan with change request."""
    s = _sessions[user_id]
    s["change_request"] = change_request
    s["state"] = BuildState.PLANNING

    intent  = s["intent"]
    answers = s["answers"]
    q_labels = ["Purpose", "Target users", "Tech preference"]
    qa_text  = "\n".join(
        f"- {q_labels[i]}: {answers[i]}" for i in range(min(len(answers), len(q_labels)))
    )

    prompt = f"""You are an expert software architect helping revise a project plan.

Original request: {intent}
Context:
{qa_text}

The user reviewed the plan and asked for this change:
"{change_request}"

Produce a REVISED JSON project plan with this change applied.
Output ONLY the JSON object (same schema as before). No markdown, no explanation.

Schema:
{{
  "name": "...", "description": "...", "framework": "...",
  "stack": [...], "pages": [...], "features": [...],
  "build_steps": [{{"step": 1, "type": "scaffold|generate|install|run", "cmd": "...", "description": "..."}}]
}}
"""

    try:
        raw = ask_ai_smart(prompt).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)
        plan = json.loads(raw)
    except Exception as e:
        logger.error(f"Plan revision failed: {e}")
        return "⚠️ Couldn't revise the plan. Please describe the change differently."

    s["plan"] = plan
    s["build_steps"] = plan.get("build_steps", [])
    s["state"] = BuildState.AWAITING_APPROVAL
    s["change_request"] = ""

    return "✏️ *Plan updated!* Here's the revised version:\n\n" + format_plan_card(plan)


# ══════════════════════════════════════════════════════════════════════════════
# BUILDING
# ══════════════════════════════════════════════════════════════════════════════

def start_building(user_id: str) -> str:
    """Advance from AWAITING_APPROVAL → BUILDING. Returns the first progress message."""
    s = _sessions[user_id]
    s["state"] = BuildState.BUILDING
    s["current_step"] = 0

    plan = s["plan"]
    project_name = re.sub(r"[^\w\-]", "_", plan.get("name", "MyProject"))
    project_dir  = os.path.join(DEFAULT_PROJECTS_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)
    s["project_dir"] = project_dir

    total = len(s["build_steps"])
    logger.info(f"[{user_id}] Building '{project_name}' — {total} steps → {project_dir}")

    return (
        f"🔨 *Building {plan.get('name', 'your project')}...*\n"
        f"📁 Output: `{project_dir}`\n"
        f"🪜 {total} steps to go. I'll update you after each one!\n\n"
        f"Type /build_status to check progress anytime."
    )


def execute_next_step(user_id: str) -> str:
    """Execute the next build step and return a progress message."""
    s = _sessions[user_id]
    steps = s["build_steps"]
    idx   = s["current_step"]

    if idx >= len(steps):
        return _finish_build(user_id)

    step         = steps[idx]
    step_num     = step.get("step", idx + 1)
    total        = len(steps)
    description  = step.get("description", "")
    step_type    = step.get("type", "")
    project_dir  = s["project_dir"]

    s["current_step"] += 1

    # ── scaffold / install / run ─────────────────────────────────────────────
    if step_type in ("scaffold", "install", "run"):
        cmd = step.get("cmd", "").strip()
        if not cmd:
            return f"⚠️ Step {step_num}: Empty command — skipping."
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_dir,
            )
            ok = result.returncode == 0
            icon = "✅" if ok else "⚠️"
            out  = (result.stdout or result.stderr or "").strip()[:300]
            return (
                f"{icon} *Step {step_num}/{total}* — {description}\n"
                f"`$ {cmd}`\n"
                + (f"\n```\n{out}\n```" if out else "")
            )
        except subprocess.TimeoutExpired:
            return f"⚠️ Step {step_num}: Command timed out — `{cmd}`"
        except Exception as e:
            return f"⚠️ Step {step_num}: Error — {e}"

    # ── generate (write a file via LLM) ─────────────────────────────────────
    if step_type == "generate":
        file_path = step.get("file", "output.txt")
        gen_prompt = step.get("prompt", f"Write code for: {s['intent']}")
        plan       = s["plan"]

        full_prompt = (
            f"You are writing code for a '{plan.get('framework', 'Python')}' project.\n"
            f"Project: {plan.get('description', s['intent'])}\n"
            f"Stack: {', '.join(plan.get('stack', []))}\n\n"
            f"Task: {gen_prompt}\n\n"
            "Output ONLY the file content. No explanations, no markdown fences."
        )
        try:
            code = ask_ai_smart(full_prompt).strip()
            # Strip fences if LLM adds them
            code = re.sub(r"^```\w*\n?", "", code)
            code = re.sub(r"\n?```$",    "", code)

            abs_path = os.path.join(project_dir, file_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(code)

            lines = len(code.splitlines())
            return (
                f"✅ *Step {step_num}/{total}* — {description}\n"
                f"📄 Generated `{file_path}` ({lines} lines)"
            )
        except Exception as e:
            return f"⚠️ Step {step_num}: File generation failed — {e}"

    return f"⚠️ Step {step_num}: Unknown step type '{step_type}' — skipping."


def _finish_build(user_id: str) -> str:
    """All steps done — mark DONE and return summary."""
    s = _sessions[user_id]
    s["state"] = BuildState.DONE
    plan = s["plan"]
    project_dir = s["project_dir"]

    summary = (
        f"🎉 *Done! {plan.get('name', 'Your project')} is ready!*\n\n"
        f"📁 *Location:* `{project_dir}`\n"
        f"🔧 *Framework:* {plan.get('framework', '—')}\n"
        f"✨ *Features:* {', '.join(plan.get('features', [])) or '—'}\n\n"
        f"Open the folder and explore your project! 🚀\n"
        f"_(This session is now closed. Say 'build another' to start fresh.)_"
    )
    reset_session(user_id)
    return summary


def get_build_status(user_id: str) -> str:
    """Return a short status message for /build_status."""
    s = _sessions.get(user_id)
    if not s or s["state"] == BuildState.IDLE:
        return "🏗️ No active build session."
    state  = s["state"]
    total  = len(s["build_steps"])
    done   = s["current_step"]
    plan   = s["plan"]
    return (
        f"🔨 *Build Status*\n"
        f"Project: *{plan.get('name', '...')}*\n"
        f"State:   `{state}`\n"
        f"Progress: {done}/{total} steps complete"
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

def handle_input(user_id: str, text: str) -> str:
    """
    Main entry point called by agent_loop / telegram_bot.
    Routes input to the correct stage handler based on session state.
    """
    s = _sessions.get(user_id)
    if not s:
        # Shouldn't happen — call start_session() first
        return "⚠️ No active build session. Say 'build me something' to start!"

    state = s["state"]

    # ── DISCUSSING: collect answers ──────────────────────────────────────────
    if state == BuildState.DISCUSSING:
        return _do_discussing(user_id, text)

    # ── AWAITING_APPROVAL: only inline buttons move things forward ───────────
    if state == BuildState.AWAITING_APPROVAL:
        # If the user types instead of clicking a button, remind them
        lower = text.lower().strip()
        if any(w in lower for w in ("yes", "ok", "go", "build", "approve", "looks good", "good", "great")):
            # Accept text approval too
            return _text_approved(user_id)
        if any(w in lower for w in ("cancel", "stop", "no", "abort")):
            reset_session(user_id)
            return "❌ Build session cancelled. Say 'build' anytime to start a new project!"
        return (
            "⏳ *Waiting for your decision* on the plan above.\n"
            "Tap *✅ Looks great! Build it* to start, "
            "*✏️ Change something* to revise, or "
            "*❌ Cancel* to exit."
        )

    # ── BUILDING: acknowledge but keep building ──────────────────────────────
    if state == BuildState.BUILDING:
        return (
            "⚙️ *Build in progress...* I'll let you know when each step completes.\n"
            "Use /build_status to check progress."
        )

    # ── PLANNING state is internal — shouldn't receive user input ───────────
    if state == BuildState.PLANNING:
        return "⏳ Planning your project... one moment!"

    return "⚠️ Unexpected state. Type /cancel_build to reset."


def _text_approved(user_id: str) -> str:
    """Handle text-based approval (same as tapping the approve button)."""
    msg = start_building(user_id)
    return msg


# ── Waiting for change description ───────────────────────────────────────────
# This state flag is set by the Telegram callback handler
_awaiting_change: set = set()


def mark_awaiting_change(user_id: str) -> None:
    """Mark that the next message from this user is a change description."""
    _awaiting_change.add(user_id)


def is_awaiting_change(user_id: str) -> bool:
    return user_id in _awaiting_change


def consume_change_input(user_id: str, text: str) -> str:
    """Called when user sends their change description."""
    _awaiting_change.discard(user_id)
    return _do_planning_changes(user_id, text)


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTING
# ══════════════════════════════════════════════════════════════════════════════

def format_plan_card(plan: dict) -> str:
    """Format the plan as a clean Telegram Markdown message (shown before approval buttons)."""
    name        = plan.get("name",        "MyProject")
    description = plan.get("description", "")
    framework   = plan.get("framework",   "—")
    stack       = ", ".join(plan.get("stack",    [])) or "—"
    pages       = ", ".join(plan.get("pages",    [])) or "—"
    features    = plan.get("features", [])
    steps       = plan.get("build_steps", [])

    feature_lines = "\n".join(f"  • {f}" for f in features) if features else "  —"
    step_lines    = "\n".join(
        f"  {s.get('step','?')}. [{s.get('type','?').upper()}] {s.get('description', s.get('cmd',''))}"
        for s in steps
    )

    return (
        f"🏗️ *Here's your project plan:*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 *{name}*\n"
        f"_{description}_\n\n"
        f"⚙️ *Framework:* {framework}\n"
        f"🔧 *Stack:* {stack}\n"
        f"📄 *Pages:* {pages}\n\n"
        f"✨ *Features:*\n{feature_lines}\n\n"
        f"🪜 *Build Steps ({len(steps)} total):*\n{step_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"What would you like to do?"
    )
