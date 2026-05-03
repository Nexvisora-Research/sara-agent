"""
tools/register_tool.py — Master Tool Registry for Sara AI.

All tools are imported lazily from their respective modules.
execute_tool() is the single dispatch point called by agent_loop.
"""

import datetime
import importlib
import inspect
import json
import logging
import os
import platform
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests as _requests

logger = logging.getLogger(__name__)
OS = platform.system()


@dataclass(frozen=True)
class ToolPolicy:
    category: str
    requires_confirmation: bool = False
    description: str = ""


@dataclass
class PluginTool:
    name: str
    handler: Callable
    schema: dict[str, Any] | None = None
    check_fn: Callable[[], bool] | None = None
    emoji: str = ""
    toolset: str = "plugin"
    plugin: str = ""

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Core Tools (inline, no extra deps)
# ══════════════════════════════════════════════════════════════════════════════

def get_time(unused: str = "") -> str:
    now = datetime.datetime.now().strftime("%A, %d %B %Y — %I:%M %p")
    return f"🕐 Current time: {now}"


def get_system_info(unused: str = "") -> str:
    info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Python": platform.python_version(),
    }
    lines = "\n".join(f"  {k}: {v}" for k, v in info.items())
    return f"🖥️ System Info:\n{lines}"


def calculate(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "⛔ Invalid characters in expression."
        result = eval(expression, {"__builtins__": {}})
        return f"🧮 {expression} = {result}"
    except Exception as e:
        return f"❌ Calculation error: {e}"


def set_reminder(text: str) -> str:
    return f"⏰ Reminder set: '{text}'"


def get_weather(city: str) -> str:
    city = city.strip()
    if not city:
        return "❓ Please specify a city."
    try:
        resp = _requests.get(
            f"https://wttr.in/{city.replace(' ', '+')}?format=3",
            timeout=8, headers={"User-Agent": "Sara-AI/1.0"}
        )
        return f"🌤️ {resp.text.strip()}" if resp.status_code == 200 else f"❌ Could not get weather for '{city}'."
    except Exception as e:
        return f"❌ Weather error: {e}"


def tell_joke(unused: str = "") -> str:
    try:
        resp = _requests.get(
            "https://icanhazdadjoke.com/",
            headers={"Accept": "application/json", "User-Agent": "Sara-AI/1.0"},
            timeout=8,
        )
        return f"😄 {resp.json().get('joke', 'No joke found.')}" if resp.status_code == 200 else "❌ Couldn't fetch a joke."
    except Exception as e:
        return f"❌ Joke error: {e}"


def note_save(value: str, user_id: str = "") -> str:
    from memory.user_profile import save_note
    note = value.strip()
    if not note:
        return "❓ What would you like me to note?"
    save_note(user_id, note)
    return f"📝 Note saved: \"{note}\""


def note_list(unused: str = "", user_id: str = "") -> str:
    from memory.user_profile import get_notes
    notes = get_notes(user_id)
    if not notes:
        return "📭 No notes yet. Try: 'save note: ...'"
    return "📋 Your notes:\n" + "\n".join(f"  {i+1}. {n}" for i, n in enumerate(notes))


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_skill_files(include_optional: bool = False):
    roots = [("installed", _repo_root() / "skills")]
    if include_optional:
        roots.append(("optional", _repo_root() / "optional-skills"))
    for kind, root in roots:
        if not root.is_dir():
            continue
        for skill_file in sorted(root.rglob("SKILL.md")):
            rel = skill_file.parent.relative_to(root).as_posix()
            yield kind, rel, skill_file


def _skill_summary(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.lower().startswith("description:"):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "---")):
            return stripped[:180]
    return ""


def list_skills(value: str = "") -> str:
    """List installed skills, optionally including optional skill packs."""
    include_optional = value.strip().lower() in {"all", "optional", "include optional", "true", "1"}
    rows = []
    for kind, rel, skill_file in _iter_skill_files(include_optional=include_optional):
        desc = _skill_summary(skill_file)
        suffix = f" — {desc}" if desc else ""
        rows.append(f"- {rel} ({kind}){suffix}")
    if not rows:
        return "No skills found."
    heading = "Available skills"
    if include_optional:
        heading += " (installed + optional)"
    return heading + ":\n" + "\n".join(rows[:200])


def read_skill(value: str = "") -> str:
    """Read a skill by name/path from skills/ or optional-skills/."""
    query = value.strip().strip("/")
    if not query:
        return "Please provide a skill name or path, e.g. `creative/p5js`."
    matches = []
    for kind, rel, skill_file in _iter_skill_files(include_optional=True):
        if query == rel or query == rel.split("/")[-1] or query.lower() in rel.lower():
            matches.append((kind, rel, skill_file))
    if not matches:
        return f"No skill matched '{query}'. Try list_skills first."
    if len(matches) > 1:
        options = "\n".join(f"- {rel} ({kind})" for kind, rel, _ in matches[:20])
        return f"Multiple skills matched '{query}':\n{options}"
    kind, rel, skill_file = matches[0]
    try:
        text = skill_file.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Could not read {rel}: {exc}"
    max_chars = 16000
    body = text[:max_chars]
    if len(text) > max_chars:
        body += "\n\n[truncated]"
    return f"{rel} ({kind})\n\n{body}"


def read_sara_features(value: str = "") -> str:
    """Read Sara's local feature guide for capabilities, plugins, skills, and daily use."""
    guide_path = _repo_root() / ".agents" / "SARA_FEATURE_GUIDE.md"
    if not guide_path.exists():
        return "Sara feature guide is not available yet."
    try:
        text = guide_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Could not read Sara feature guide: {exc}"

    if value.strip().lower() not in {"full", "all", "complete"}:
        return """Sara has these ready feature areas:

- Chat: Telegram, Discord, and WhatsApp.
- Memory: profile facts, notes, summaries, and long-term context.
- Daily tools: time, weather, calculator, reminders, notes, files, web search, YouTube, news, knowledge search.
- Local control: apps, terminal commands, Python files, screenshots, clipboard, system stats, and media controls. Risky actions ask first.
- Communication: Telegram, WhatsApp, Discord, email, Slack, and generic channel messages.
- Automations: routines and scheduled workflows.
- Multi-agent mode: planner, researcher, builder, and reviewer.
- Plugins: Google Meet, Spotify, image generation, memory providers, platform adapters, observability, disk cleanup, and dashboard plugins.
- Skills: coding, GitHub, research, creative work, productivity, media, email, data science, MLOps, MCP, smart home, gaming, and more.

Useful things to ask:

list plugins
list skills all
agents status
use agents to plan my day
save note: ...
schedule a workflow for 9 AM daily news summary

For a new idea, Sara should tell you whether it is best as a feature, plugin, skill, config change, routine, or automation. Full guide: .agents/SARA_FEATURE_GUIDE.md"""

    max_chars = 18000
    body = text[:max_chars]
    if len(text) > max_chars:
        body += "\n\n[truncated]"
    return body


def list_plugins(value: str = "") -> str:
    """List plugin manifests and whether their tools reached the registry."""
    rows = []
    for plugin_name, module_name in _iter_plugin_module_names():
        manifest = _repo_root() / "plugins" / Path(*plugin_name.split("/")) / "plugin.yaml"
        meta = _read_plugin_manifest(manifest)
        provided = meta.get("provides_tools", [])
        registered = [tool for tool in provided if tool.strip().lower() in TOOLS]
        desc = meta.get("description", "")
        status = f"{len(registered)}/{len(provided)} tools surfaced" if provided else "no tools declared"
        suffix = f" — {desc}" if desc else ""
        rows.append(f"- {plugin_name}: {status}{suffix}")
    if not rows:
        return "No plugin manifests found."
    return "Available plugins:\n" + "\n".join(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — System Control (system_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.system_tools import (
    open_app, open_terminal, smart_open_app, open_youtube_music, close_app, shutdown_pc, restart_pc, open_folder,
    take_screenshot, read_screen, clipboard_read, clipboard_write,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Developer / Terminal (dev_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.dev_tools import run_terminal, run_python, install_package, git_clone, create_project


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — File Management (file_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.file_tools import read_file, write_file, create_folder, delete_file, list_files, export_chat


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Web / Scraping (web_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.web_tools import google_search, youtube_search, open_url, scrape_website, download_file


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — AI Content (ai_tools.py via LangChain)
# ══════════════════════════════════════════════════════════════════════════════
from tools.ai_tools import generate_text, summarize_text, analyze_document


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Browser Automation (browser_tools.py via Playwright)
# ══════════════════════════════════════════════════════════════════════════════
from tools.browser_tools import browser_open, browser_screenshot, browser_fill_form


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Knowledge System (memory/knowledge.py via ChromaDB)
# ══════════════════════════════════════════════════════════════════════════════
from memory.knowledge import knowledge_add, knowledge_search, knowledge_count


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Communication (communication_tools.py)
# Plugin registry: add any new channel with @register_channel("name")
# ══════════════════════════════════════════════════════════════════════════════
from tools.communication_tools import (
    send_telegram_message,
    send_whatsapp_message,
    send_discord_message,
    send_email,
    send_slack_message,
    send_via_channel,
    list_channels,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Voice Input (voice_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.voice_tools import listen_mic, list_audio_devices


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — Reminders with Notifications (reminder_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.reminder_tools import set_reminder, list_reminders


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — System Monitor (monitor_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.monitor_tools import (
    get_cpu_usage, get_ram_usage, get_disk_usage,
    get_top_processes, get_system_stats,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 — News (news_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.news_tools import get_news, get_trending_news
from tools.automation_tools import (
    list_scheduled_workflows,
    remove_scheduled_workflow,
    schedule_workflow,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 — Media Controls (media_tools.py)
# ══════════════════════════════════════════════════════════════════════════════
from tools.media_tools import (
    media_play_pause, media_next, media_prev,
    set_volume, get_volume, mute_volume, unmute_volume,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15 — Multi-Agent Coordination (agent/multi_agent.py)
# ══════════════════════════════════════════════════════════════════════════════
from agent.multi_agent import delegate_task, multi_agent_status


# ══════════════════════════════════════════════════════════════════════════════
# MASTER REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
TOOLS: dict[str, Callable | PluginTool] = {
    # ── Core ──────────────────────────────────────────
    "get_time":           get_time,
    "get_system_info":    get_system_info,
    "calculate":          calculate,
    "set_reminder":       set_reminder,         # real timed + toast notification
    "list_reminders":     list_reminders,
    "get_weather":        get_weather,
    "tell_joke":          tell_joke,
    "note_save":          note_save,
    "note_list":          note_list,
    "list_skills":        list_skills,
    "read_skill":         read_skill,
    "read_sara_features": read_sara_features,
    "list_plugins":       list_plugins,
    # ── System Control ────────────────────────────────
    "open_app":           open_app,
    "open_terminal":      open_terminal,
    "smart_open_app":     smart_open_app,
    "open_youtube_music": open_youtube_music,
    "close_app":          close_app,
    "shutdown_pc":        shutdown_pc,
    "restart_pc":         restart_pc,
    "open_folder":        open_folder,
    "take_screenshot":    take_screenshot,
    "read_screen":        read_screen,
    "clipboard_read":     clipboard_read,
    "clipboard_write":    clipboard_write,
    # ── Developer / Terminal ──────────────────────────
    "run_terminal":       run_terminal,
    "run_python":         run_python,
    "install_package":    install_package,
    "git_clone":          git_clone,
    "create_project":     create_project,
    # ── File Management ───────────────────────────────
    "read_file":          read_file,
    "write_file":         write_file,
    "create_folder":      create_folder,
    "delete_file":        delete_file,
    "list_files":         list_files,
    "export_chat":        export_chat,
    # ── Web ───────────────────────────────────────────
    "google_search":      google_search,
    "youtube_search":     youtube_search,
    "open_url":           open_url,
    "scrape_website":     scrape_website,
    "download_file":      download_file,
    # ── AI Content ────────────────────────────────────
    "generate_text":      generate_text,
    "summarize_text":     summarize_text,
    "analyze_document":   analyze_document,
    # ── Browser Automation ────────────────────────────
    "browser_open":       browser_open,
    "browser_screenshot": browser_screenshot,
    "browser_fill_form":  browser_fill_form,
    # ── Knowledge System ──────────────────────────────
    "knowledge_add":      knowledge_add,
    "knowledge_search":   knowledge_search,
    "knowledge_count":    knowledge_count,
    # ── Communication ─────────────────────────────────
    "send_telegram":      send_telegram_message,
    "send_whatsapp":      send_whatsapp_message,
    "send_discord":       send_discord_message,
    "send_email":         send_email,
    "send_slack":         send_slack_message,
    "send_message":       send_via_channel,
    "list_channels":      list_channels,
    # ── Voice Input ───────────────────────────────────
    "listen_mic":         listen_mic,
    "list_audio_devices": list_audio_devices,
    # ── System Monitor ────────────────────────────────
    "get_cpu_usage":      get_cpu_usage,
    "get_ram_usage":      get_ram_usage,
    "get_disk_usage":     get_disk_usage,
    "get_top_processes":  get_top_processes,
    "get_system_stats":   get_system_stats,
    # ── News ──────────────────────────────────────────
    "get_news":           get_news,
    "get_trending_news":  get_trending_news,
    "schedule_workflow":  schedule_workflow,
    "list_workflows":     list_scheduled_workflows,
    "delete_workflow":    remove_scheduled_workflow,
    # ── Media Controls ────────────────────────────────
    "media_play_pause":   media_play_pause,
    "media_next":         media_next,
    "media_prev":         media_prev,
    "set_volume":         set_volume,
    "get_volume":         get_volume,
    "mute_volume":        mute_volume,
    "unmute_volume":      unmute_volume,
    # ── Multi-Agent Coordination ───────────────────────
    "delegate_task":      delegate_task,
    "multi_agent_status": multi_agent_status,
}

TOOL_POLICIES: dict[str, ToolPolicy] = {
    # Core
    "get_time":           ToolPolicy("safe_read"),
    "get_system_info":    ToolPolicy("safe_read"),
    "calculate":          ToolPolicy("safe_read"),
    "set_reminder":       ToolPolicy("safe_write"),
    "list_reminders":     ToolPolicy("safe_read"),
    "get_weather":        ToolPolicy("safe_read"),
    "tell_joke":          ToolPolicy("safe_read"),
    "note_save":          ToolPolicy("safe_write"),
    "note_list":          ToolPolicy("safe_read"),
    "list_skills":        ToolPolicy("safe_read"),
    "read_skill":         ToolPolicy("safe_read"),
    "read_sara_features": ToolPolicy("safe_read"),
    "list_plugins":       ToolPolicy("safe_read"),
    # System control
    "open_app":           ToolPolicy("risky", True, "Opens a local application"),
    "open_terminal":      ToolPolicy("risky", True, "Opens a terminal window"),
    "smart_open_app":     ToolPolicy("risky", True, "Opens an app and may install it first"),
    "open_youtube_music": ToolPolicy("risky", True, "Opens YouTube Music in a browser"),
    "close_app":          ToolPolicy("risky", True, "Closes a running application"),
    "shutdown_pc":        ToolPolicy("risky", True, "Shuts down the computer"),
    "restart_pc":         ToolPolicy("risky", True, "Restarts the computer"),
    "open_folder":        ToolPolicy("risky", True, "Opens a local folder"),
    "take_screenshot":    ToolPolicy("risky", True, "Captures the current screen"),
    "read_screen":        ToolPolicy("safe_read"),
    "clipboard_read":     ToolPolicy("safe_read"),
    "clipboard_write":    ToolPolicy("risky", True, "Modifies the clipboard"),
    # Developer
    "run_terminal":       ToolPolicy("risky", True, "Runs a shell command"),
    "run_python":         ToolPolicy("risky", True, "Executes a local Python script"),
    "install_package":    ToolPolicy("risky", True, "Installs a package"),
    "git_clone":          ToolPolicy("risky", True, "Clones a remote repository"),
    "create_project":     ToolPolicy("safe_write"),
    # Files
    "read_file":          ToolPolicy("safe_read"),
    "write_file":         ToolPolicy("risky", True, "Creates or overwrites a file"),
    "create_folder":      ToolPolicy("safe_write"),
    "delete_file":        ToolPolicy("risky", True, "Deletes a file"),
    "list_files":         ToolPolicy("safe_read"),
    "export_chat":        ToolPolicy("safe_write"),
    # Web
    "google_search":      ToolPolicy("safe_read"),
    "youtube_search":     ToolPolicy("safe_read"),
    "open_url":           ToolPolicy("risky", True, "Opens a URL in a browser"),
    "scrape_website":     ToolPolicy("safe_read"),
    "download_file":      ToolPolicy("risky", True, "Downloads a file"),
    # AI
    "generate_text":      ToolPolicy("safe_read"),
    "summarize_text":     ToolPolicy("safe_read"),
    "analyze_document":   ToolPolicy("safe_read"),
    # Browser
    "browser_open":       ToolPolicy("risky", True, "Launches browser automation"),
    "browser_screenshot": ToolPolicy("risky", True, "Captures a webpage screenshot"),
    "browser_fill_form":  ToolPolicy("risky", True, "Submits data through browser automation"),
    # Knowledge
    "knowledge_add":      ToolPolicy("safe_write"),
    "knowledge_search":   ToolPolicy("safe_read"),
    "knowledge_count":    ToolPolicy("safe_read"),
    # Communication
    "send_telegram":      ToolPolicy("risky", True, "Sends a Telegram message"),
    "send_whatsapp":      ToolPolicy("risky", True, "Sends a WhatsApp message"),
    "send_discord":       ToolPolicy("risky", True, "Sends a Discord message"),
    "send_email":         ToolPolicy("risky", True, "Sends an email"),
    "send_slack":         ToolPolicy("risky", True, "Sends a Slack message"),
    "send_message":       ToolPolicy("risky", True, "Sends an outbound message"),
    "list_channels":      ToolPolicy("safe_read"),
    # Voice
    "listen_mic":         ToolPolicy("risky", True, "Records audio from the microphone"),
    "list_audio_devices": ToolPolicy("safe_read"),
    # Monitor
    "get_cpu_usage":      ToolPolicy("safe_read"),
    "get_ram_usage":      ToolPolicy("safe_read"),
    "get_disk_usage":     ToolPolicy("safe_read"),
    "get_top_processes":  ToolPolicy("safe_read"),
    "get_system_stats":   ToolPolicy("safe_read"),
    # News
    "get_news":           ToolPolicy("safe_read"),
    "get_trending_news":  ToolPolicy("safe_read"),
    "schedule_workflow":  ToolPolicy("safe_write"),
    "list_workflows":     ToolPolicy("safe_read"),
    "delete_workflow":    ToolPolicy("safe_write"),
    # Media
    "media_play_pause":   ToolPolicy("risky", True, "Controls system media playback"),
    "media_next":         ToolPolicy("risky", True, "Controls system media playback"),
    "media_prev":         ToolPolicy("risky", True, "Controls system media playback"),
    "set_volume":         ToolPolicy("risky", True, "Changes system volume"),
    "get_volume":         ToolPolicy("safe_read"),
    "mute_volume":        ToolPolicy("risky", True, "Changes system volume"),
    "unmute_volume":      ToolPolicy("risky", True, "Changes system volume"),
    # Multi-agent
    "delegate_task":      ToolPolicy("safe_read"),
    "multi_agent_status": ToolPolicy("safe_read"),
}


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

def _coerce_plugin_args(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    except Exception:
        return {"value": value, "text": value, "query": value}


def execute_tool(action: str, value: str, user_id: str = "") -> str:
    """Look up and call a tool by name. Passes user_id to tools that accept it."""
    tool_fn = TOOLS.get(action.strip().lower())
    if tool_fn is None:
        available = ", ".join(TOOLS.keys())
        return f"❌ Unknown tool '{action}'.\nAvailable: {available}"
    logger.info(f"Tool: {action}({value!r}) user={user_id}")
    if isinstance(tool_fn, PluginTool):
        if tool_fn.check_fn is not None:
            try:
                if not tool_fn.check_fn():
                    return f"❌ Plugin tool '{action}' is registered but its runtime requirements are not available."
            except Exception as exc:
                return f"❌ Plugin tool '{action}' availability check failed: {exc}"
        args = _coerce_plugin_args(value)
        if user_id:
            args.setdefault("user_id", user_id)
        sig = inspect.signature(tool_fn.handler)
        if "user_id" in sig.parameters or any(param.kind is inspect.Parameter.VAR_KEYWORD for param in sig.parameters.values()):
            return tool_fn.handler(args, user_id=user_id)
        return tool_fn.handler(args)
    sig = inspect.signature(tool_fn)
    if "user_id" in sig.parameters:
        return tool_fn(value, user_id=user_id)
    return tool_fn(value)


def get_tool_policy(action: str) -> ToolPolicy:
    """Return the centralized execution policy for a tool."""
    return TOOL_POLICIES.get(action.strip().lower(), ToolPolicy("risky", True, "Unknown tool"))


def get_tool_catalog() -> list[dict]:
    """Return lightweight tool metadata for planning prompts."""
    items = []
    for name, description in TOOL_DESCRIPTIONS.items():
        policy = get_tool_policy(name)
        items.append(
            {
                "name": name,
                "description": description,
                "category": policy.category,
                "requires_confirmation": policy.requires_confirmation,
            }
        )
    return items


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT DESCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

TOOL_DESCRIPTIONS: dict[str, str] = {
    # Core
    "get_time":           "get_time() — Current date and time",
    "get_system_info":    "get_system_info() — OS and hardware info",
    "calculate":          "calculate(expr) — Math e.g. '200 * 12 / 4'",
    "set_reminder":       "set_reminder(text) — Set a timed reminder with desktop notification e.g. 'drink water in 5 minutes'",
    "list_reminders":     "list_reminders() — Show all pending and completed reminders",
    "get_weather":        "get_weather(city) — Live weather e.g. 'Mumbai'",
    "tell_joke":          "tell_joke() — Random joke",
    "note_save":          "note_save(text) — Save a personal note",
    "note_list":          "note_list() — List saved notes",
    "list_skills":        "list_skills(all?) — List installed skills; pass 'all' to include optional-skills",
    "read_skill":         "read_skill(name_or_path) — Read a SKILL.md by name or path",
    "read_sara_features": "read_sara_features() — Read Sara's local guide for ready features, plugins, skills, new additions, and daily-life usage",
    "list_plugins":       "list_plugins() — List plugin manifests and surfaced plugin tools",
    # System
    "open_app":           "open_app(name) — Open an app e.g. 'chrome', 'vscode'",
    "open_terminal":      "open_terminal(cmd?) — Open a terminal, optionally running a command",
    "smart_open_app":     "smart_open_app(name) — Detect OS, install app if needed, then open it",
    "open_youtube_music": "open_youtube_music(query?) — Open YouTube Music, optionally searching a mood or playlist",
    "close_app":          "close_app(name) — Close a running app",
    "shutdown_pc":        "shutdown_pc() — Shut down the computer",
    "restart_pc":         "restart_pc() — Restart the computer",
    "open_folder":        "open_folder(path) — Open a folder in Explorer",
    "take_screenshot":    "take_screenshot(filename?) — Capture desktop screenshot",
    "read_screen":        "read_screen() — OCR screenshot to read text on screen",
    "clipboard_read":     "clipboard_read() — Read current clipboard text",
    "clipboard_write":    "clipboard_write(text) — Copy text to clipboard",
    # Dev
    "run_terminal":       "run_terminal(cmd) — Run any shell command",
    "run_python":         "run_python(file) — Run a Python script",
    "install_package":    "install_package(pkg) — pip/npm install",
    "git_clone":          "git_clone(url) — Clone a git repo",
    "create_project":     "create_project(name) — Scaffold a new project",
    # Files
    "read_file":          "read_file(path) — Read a text file",
    "write_file":         "write_file(path::content) — Write/create a file",
    "create_folder":      "create_folder(path) — Create a directory",
    "delete_file":        "delete_file(path) — Delete a file",
    "list_files":         "list_files(dir) — List files in a folder",
    "export_chat":        "export_chat() — Export conversation history to a Markdown file",
    # Web
    "google_search":      "google_search(query) — Google search",
    "youtube_search":     "youtube_search(query) — YouTube search",
    "open_url":           "open_url(url) — Open a URL in browser",
    "scrape_website":     "scrape_website(url) — Extract text from webpage",
    "download_file":      "download_file(url) — Download a file",
    # AI
    "generate_text":      "generate_text(prompt) — Write articles, code, emails",
    "summarize_text":     "summarize_text(text) — Summarize a block of text",
    "analyze_document":   "analyze_document(path) — AI analysis of a file",
    # Browser
    "browser_open":       "browser_open(url) — Open URL in headless browser",
    "browser_screenshot": "browser_screenshot(url) — Screenshot a webpage",
    "browser_fill_form":  "browser_fill_form(url::field=val) — Fill web form or use query=... with a site URL to search",
    # Knowledge
    "knowledge_add":      "knowledge_add(text) — Add to AI knowledge base",
    "knowledge_search":   "knowledge_search(query) — Semantic knowledge search",
    "knowledge_count":    "knowledge_count() — How many knowledge items stored",
    # Communication
    "send_telegram":      "send_telegram(text) — Send Telegram message to your chat",
    "send_whatsapp":      "send_whatsapp(text) — Send WhatsApp message (via WhatsApp Web)",
    "send_discord":       "send_discord(text) — Send message to Discord channel",
    "send_email":         "send_email(text OR to::subject::body) — Send email via Gmail",
    "send_slack":         "send_slack(text) — Send message to Slack channel",
    "send_message":       "send_message(channel::text) — Send via any channel e.g. 'discord::Hello!'",
    "list_channels":      "list_channels() — List all available communication channels",
    # Voice
    "listen_mic":         "listen_mic(seconds?) — Record mic and transcribe speech to text",
    "list_audio_devices": "list_audio_devices() — List available microphones",
    # System Monitor
    "get_cpu_usage":      "get_cpu_usage() — CPU usage % overall and per core",
    "get_ram_usage":      "get_ram_usage() — RAM total / used / free",
    "get_disk_usage":     "get_disk_usage(path?) — Disk usage for a drive e.g. 'C:\\' ",
    "get_top_processes":  "get_top_processes(n?) — Top N processes by CPU usage",
    "get_system_stats":   "get_system_stats() — Quick system dashboard (CPU + RAM + Disk)",
    # News
    "get_news":           "get_news(topic) — Top 5 news headlines for a topic",
    "get_trending_news":  "get_trending_news() — Current top global headlines",
    "schedule_workflow":  "schedule_workflow(text) — Create a daily automation such as '9 am top tech search and give summary'",
    "list_workflows":     "list_workflows() — Show scheduled automations",
    "delete_workflow":    "delete_workflow(id) — Delete a scheduled automation by id",
    # Media Controls
    "media_play_pause":   "media_play_pause() — Toggle play/pause on media player",
    "media_next":         "media_next() — Skip to next track",
    "media_prev":         "media_prev() — Go back to previous track",
    "set_volume":         "set_volume(0-100) — Set system volume level",
    "get_volume":         "get_volume() — Get current system volume",
    "mute_volume":        "mute_volume() — Mute system audio",
    "unmute_volume":      "unmute_volume() — Unmute system audio",
    # Multi-Agent
    "delegate_task":      "delegate_task(goal_or_json) — Run Sara's planner/researcher/builder/reviewer agents on a complex task",
    "multi_agent_status": "multi_agent_status() — Show configured Sara sub-agents and .agents config path",
}


class _PluginRegistrationContext:
    """Minimal sara-compatible context for plugin register(ctx) hooks."""

    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name

    def register_tool(
        self,
        *,
        name: str,
        handler: Callable,
        schema: dict[str, Any] | None = None,
        toolset: str = "plugin",
        check_fn: Callable[[], bool] | None = None,
        emoji: str = "",
        **_kwargs,
    ) -> None:
        key = name.strip().lower()
        if not key:
            return
        description = ""
        if isinstance(schema, dict):
            description = str(schema.get("description") or "")
        if not description:
            description = f"{key} plugin tool"
        prefix = f"{emoji} " if emoji else ""
        TOOLS[key] = PluginTool(
            name=key,
            handler=handler,
            schema=schema,
            check_fn=check_fn,
            emoji=emoji,
            toolset=toolset,
            plugin=self.plugin_name,
        )
        TOOL_POLICIES.setdefault(key, ToolPolicy("risky", True, f"{self.plugin_name} plugin tool"))
        TOOL_DESCRIPTIONS[key] = f"{prefix}{key}(json) — {description}"

    def register_cli_command(self, *args, **kwargs) -> None:
        pass

    def register_hook(self, *args, **kwargs) -> None:
        pass

    def register_memory_provider(self, *args, **kwargs) -> None:
        pass

    def register_context_engine(self, *args, **kwargs) -> None:
        pass


def _iter_plugin_module_names() -> list[tuple[str, str]]:
    plugins_root = _repo_root() / "plugins"
    if not plugins_root.is_dir():
        return []
    discovered: list[tuple[str, str]] = []
    for init_file in sorted(plugins_root.rglob("__init__.py")):
        rel_dir = init_file.parent.relative_to(plugins_root)
        parts = rel_dir.parts
        if not parts:
            continue
        if any(part in {"dashboard", "node", "realtime", "__pycache__"} for part in parts):
            continue
        if not (init_file.parent / "plugin.yaml").exists():
            continue
        module_name = "plugins." + ".".join(parts)
        plugin_name = "/".join(parts)
        discovered.append((plugin_name, module_name))
    return discovered


def _read_plugin_manifest(path: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {"provides_tools": []}
    if not path.exists():
        return meta
    current_list: str | None = None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return meta
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current_list and stripped.startswith("- "):
            meta.setdefault(current_list, []).append(stripped[2:].strip().strip("\"'"))
            continue
        current_list = None
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if value:
            meta[key] = value
        else:
            meta.setdefault(key, [])
            current_list = key
    if not isinstance(meta.get("provides_tools"), list):
        meta["provides_tools"] = []
    return meta


def _unavailable_plugin_handler(plugin_name: str, tool_name: str, reason: str) -> Callable:
    def _handler(_args: dict[str, Any], **_kwargs) -> str:
        return (
            f"❌ Plugin tool '{tool_name}' from '{plugin_name}' is declared but not runnable "
            f"in this Sara runtime. Reason: {reason}"
        )

    return _handler


def _surface_manifest_tools(plugin_name: str, reason: str) -> None:
    manifest = _repo_root() / "plugins" / Path(*plugin_name.split("/")) / "plugin.yaml"
    meta = _read_plugin_manifest(manifest)
    description = str(meta.get("description") or f"{plugin_name} plugin tool")
    for raw_name in meta.get("provides_tools", []):
        key = str(raw_name).strip().lower()
        if not key or key in TOOLS:
            continue
        TOOLS[key] = PluginTool(
            name=key,
            handler=_unavailable_plugin_handler(plugin_name, key, reason),
            schema={"description": description},
            plugin=plugin_name,
        )
        TOOL_POLICIES.setdefault(key, ToolPolicy("risky", True, f"{plugin_name} plugin tool"))
        TOOL_DESCRIPTIONS[key] = f"{key}(json) — {description} [plugin unavailable: {reason}]"


def _load_plugin_tools() -> None:
    for plugin_name, module_name in _iter_plugin_module_names():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            logger.debug("Plugin import skipped for %s: %s", module_name, exc)
            _surface_manifest_tools(plugin_name, str(exc))
            continue
        register = getattr(module, "register", None)
        if not callable(register):
            _surface_manifest_tools(plugin_name, "plugin has no register(ctx) hook")
            continue
        before = set(TOOLS)
        try:
            register(_PluginRegistrationContext(plugin_name))
        except Exception as exc:
            logger.debug("Plugin register skipped for %s: %s", module_name, exc)
            _surface_manifest_tools(plugin_name, str(exc))
            continue
        if set(TOOLS) == before:
            _surface_manifest_tools(plugin_name, "plugin registered no tools")


_load_plugin_tools()


def get_tools_description() -> str:
    return "\n".join(f"- {v}" for v in TOOL_DESCRIPTIONS.values())
