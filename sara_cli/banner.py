"""Welcome banner, ASCII art, skills summary, and update check for the CLI.

Pure display functions with no SaraCLI state dependency.
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from sara_constants import get_sara_home
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import print_formatted_text as _pt_print
from prompt_toolkit.formatted_text import ANSI as _PT_ANSI

logger = logging.getLogger(__name__)


# =========================================================================
# ANSI building blocks
# =========================================================================

_GOLD = "\033[1;38;2;255;215;0m"  # True-color #FFD700 bold
_BOLD = "\033[1m"
_DIM  = "\033[2m"
_RST  = "\033[0m"


def cprint(text: str) -> None:
    """Print ANSI-colored text through prompt_toolkit's renderer."""
    _pt_print(_PT_ANSI(text))


# =========================================================================
# Skin-aware color helpers
# =========================================================================

def _skin_color(key: str, fallback: str) -> str:
    """Return a color from the active skin, or *fallback*."""
    try:
        from sara_cli.skin_engine import get_active_skin
        return get_active_skin().get_color(key, fallback)
    except Exception:
        return fallback


def _skin_branding(key: str, fallback: str) -> str:
    """Return a branding string from the active skin, or *fallback*."""
    try:
        from sara_cli.skin_engine import get_active_skin
        return get_active_skin().get_branding(key, fallback)
    except Exception:
        return fallback


# =========================================================================
# ASCII art & branding
# =========================================================================

from sara_cli import __version__ as VERSION, __release_date__ as RELEASE_DATE

SARA_AGENT_LOGO = """\
[bold #7DD3FC]  ╭────────────────────────────────────────────────────────────╮[/]
[#E6EDF3]     S A R A  A G E N T[/]   [#F78C6C]local-first AI chat console[/]
[dim #8EA8A6]     tools · skills · memory · automation[/]
[bold #7DD3FC]  ╰────────────────────────────────────────────────────────────╯[/]"""

SARA_CADUCEUS = """\
[#7DD3FC]            ╭────────────╮[/]
[#7DD3FC]        ╭───┤    S A     ├───╮[/]
[#E6EDF3]        │   ╰─────┬──────╯   │[/]
[#E6EDF3]        │      SARA AGENT     │[/]
[#8EA8A6]        │   chat · tools · os │[/]
[#F78C6C]        ╰───────╮     ╭───────╯[/]
[#F78C6C]                │  ◇  │[/]
[#8EA8A6]                │     │[/]
[#8EA8A6]                │     │[/]
[#7DD3FC]              ╭─╯     ╰─╮[/]
[#7DD3FC]              ╰─────────╯[/]"""


# =========================================================================
# Skills scanning
# =========================================================================

def get_available_skills() -> Dict[str, List[str]]:
    """Return skills grouped by category, filtered by platform and disabled state.

    Delegates to ``_find_all_skills()`` from ``tools/skills_tool``, which
    already handles platform gating (``platforms:`` frontmatter) and respects
    the user's ``skills.disabled`` config list.
    """
    try:
        from tools.skills_tool import _find_all_skills
        all_skills = _find_all_skills()
    except Exception:
        return {}

    skills_by_category: Dict[str, List[str]] = {}
    for skill in all_skills:
        category = skill.get("category") or "general"
        skills_by_category.setdefault(category, []).append(skill["name"])
    return skills_by_category


# =========================================================================
# Update check
# =========================================================================

# Cache update-check results for 6 hours to avoid repeated git fetches.
_UPDATE_CHECK_CACHE_SECONDS = 6 * 3600

# Sentinel returned when we know an update exists but can't count commits
# (e.g. nix-built sara — no local git history to count against).
UPDATE_AVAILABLE_NO_COUNT = -1

_UPSTREAM_REPO_URL = "https://github.com/NexvisoraResearch/sara-agent.git"


def _check_via_rev(local_rev: str) -> Optional[int]:
    """Compare an embedded git revision to upstream main via ls-remote.

    Returns 0 if up-to-date, ``UPDATE_AVAILABLE_NO_COUNT`` if behind,
    or ``None`` on failure.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", _UPSTREAM_REPO_URL, "refs/heads/main"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    upstream_rev = result.stdout.split()[0]
    return 0 if upstream_rev == local_rev else UPDATE_AVAILABLE_NO_COUNT


def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Count commits behind origin/main in a local checkout."""
    try:
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            capture_output=True, timeout=10, cwd=str(repo_dir),
        )
    except Exception:
        pass  # Offline or timeout — use stale refs, that's fine

    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            capture_output=True, text=True, timeout=5, cwd=str(repo_dir),
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return None


def check_for_updates() -> Optional[int]:
    """Check whether a Sara update is available.

    Two paths: if ``SARA_REVISION`` is set (nix builds embed it), compare it
    to upstream main via ``git ls-remote``. Otherwise look for a local git
    checkout and count commits behind ``origin/main``.

    Returns the number of commits behind, ``UPDATE_AVAILABLE_NO_COUNT`` (-1)
    if behind but the count is unknown, ``0`` if up-to-date, or ``None`` if
    the check failed or doesn't apply. Cached for 6 hours.
    """
    sara_home = get_sara_home()
    cache_file = sara_home / ".update_check"
    embedded_rev = os.environ.get("SARA_REVISION") or None

    now = time.time()
    try:
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if (
                now - cached.get("ts", 0) < _UPDATE_CHECK_CACHE_SECONDS
                and cached.get("rev") == embedded_rev
            ):
                return cached.get("behind")
    except Exception:
        pass

    if embedded_rev:
        behind = _check_via_rev(embedded_rev)
    else:
        repo_dir = _resolve_repo_dir()
        if repo_dir is None:
            return None
        behind = _check_via_local_git(repo_dir)

    try:
        cache_file.write_text(json.dumps({"ts": now, "behind": behind, "rev": embedded_rev}))
    except Exception:
        pass

    return behind


def _resolve_repo_dir() -> Optional[Path]:
    """Return the active Sara git checkout, or None if not a git install."""
    sara_home = get_sara_home()
    for candidate in (sara_home / "sara-agent", Path(__file__).parent.parent.resolve()):
        if (candidate / ".git").exists():
            return candidate
    return None


def _git_short_hash(repo_dir: Path, rev: str) -> Optional[str]:
    """Resolve a git revision to an 8-character short hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", rev],
            capture_output=True, text=True, timeout=5, cwd=str(repo_dir),
        )
    except Exception:
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    """Return upstream/local git hashes for the startup banner."""
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        return None

    upstream = _git_short_hash(repo_dir, "origin/main")
    local    = _git_short_hash(repo_dir, "HEAD")
    if not upstream or not local:
        return None

    ahead = 0
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(repo_dir),
        )
        if result.returncode == 0:
            ahead = int(result.stdout.strip() or "0")
    except Exception:
        pass

    return {"upstream": upstream, "local": local, "ahead": max(ahead, 0)}


_RELEASE_URL_BASE = "https://github.com/NexvisoraResearch/sara-agent/releases/tag"
_latest_release_cache: Optional[tuple] = None  # (tag, url) once resolved


def get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]:
    """Return ``(tag, release_url)`` for the latest git tag, or None.

    Local-only — runs ``git describe --tags --abbrev=0`` against the Sara
    checkout. Cached per-process. Release URL always points at the canonical
    NexvisoraResearch/sara-agent repo (forks don't get a link).
    """
    global _latest_release_cache
    if _latest_release_cache is not None:
        return _latest_release_cache or None

    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        _latest_release_cache = ()
        return None

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=3, cwd=str(repo_dir),
        )
    except Exception:
        _latest_release_cache = ()
        return None

    tag = (result.stdout or "").strip()
    if result.returncode != 0 or not tag:
        _latest_release_cache = ()
        return None

    _latest_release_cache = (tag, f"{_RELEASE_URL_BASE}/{tag}")
    return _latest_release_cache


def format_banner_version_label() -> str:
    """Return the version label shown in the startup banner title."""
    base  = f"Sara Agent v{VERSION} ({RELEASE_DATE})"
    state = get_git_banner_state()
    if not state:
        return base

    upstream = state["upstream"]
    local    = state["local"]
    ahead    = int(state.get("ahead") or 0)

    if ahead <= 0 or upstream == local:
        return f"{base} · upstream {upstream}"

    word = "commit" if ahead == 1 else "commits"
    return f"{base} · upstream {upstream} · local {local} (+{ahead} carried {word})"


# =========================================================================
# Non-blocking update check
# =========================================================================

_update_result: Optional[int] = None
_update_check_done = threading.Event()


def prefetch_update_check() -> None:
    """Kick off the update check in a background daemon thread."""
    def _run() -> None:
        global _update_result
        _update_result = check_for_updates()
        _update_check_done.set()

    threading.Thread(target=_run, daemon=True).start()


def get_update_result(timeout: float = 0.5) -> Optional[int]:
    """Return the prefetched update result, or None if not yet ready."""
    _update_check_done.wait(timeout=timeout)
    return _update_result


# =========================================================================
# Banner helpers
# =========================================================================

def _format_context_length(tokens: int) -> str:
    """Format a token count for display (e.g. 128000 → '128K', 1048576 → '1M')."""
    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        return f"{round(val)}M" if abs(val - round(val)) < 0.05 else f"{val:.1f}M"
    if tokens >= 1_000:
        val = tokens / 1_000
        return f"{round(val)}K" if abs(val - round(val)) < 0.05 else f"{val:.1f}K"
    return str(tokens)


def _display_toolset_name(toolset_name: str) -> str:
    """Normalize internal/legacy toolset identifiers for banner display."""
    if not toolset_name:
        return "unknown"
    return toolset_name.removesuffix("_tools")


def _truncate_tool_list(tool_names: List[str], max_len: int = 42) -> List[str]:
    """Return a display-capped list of tool names, appending '...' if cut."""
    out, length = [], 0
    for name in tool_names:
        if length + len(name) + 2 > max_len:
            out.append("...")
            break
        out.append(name)
        length += len(name) + 2
    return out


def _colorize_tool_names(
    names: List[str],
    text_color: str,
    disabled: set,
    lazy: set,
) -> List[str]:
    result = []
    for name in names:
        if name == "...":
            result.append("[dim]...[/]")
        elif name in disabled:
            result.append(f"[red]{name}[/]")
        elif name in lazy:
            result.append(f"[yellow]{name}[/]")
        else:
            result.append(f"[{text_color}]{name}[/]")
    return result


# =========================================================================
# Welcome banner
# =========================================================================

def build_welcome_banner(
    console: Console,
    model: str,
    cwd: str,
    tools: List[dict] = None,
    enabled_toolsets: List[str] = None,
    session_id: str = None,
    get_toolset_for_tool=None,
    context_length: int = None,
) -> None:
    """Build and print the welcome banner (caduceus left, info right).

    Args:
        console:              Rich Console instance.
        model:                Current model name.
        cwd:                  Current working directory.
        tools:                List of tool definitions.
        enabled_toolsets:     List of enabled toolset names.
        session_id:           Session identifier.
        get_toolset_for_tool: Callable mapping tool name → toolset name.
        context_length:       Model's context window size in tokens.
    """
    from model_tools import check_tool_availability, TOOLSET_REQUIREMENTS
    if get_toolset_for_tool is None:
        from model_tools import get_toolset_for_tool

    tools             = tools or []
    enabled_toolsets  = enabled_toolsets or []

    # ── Disabled / lazy tool sets ────────────────────────────────────
    _, unavailable_toolsets = check_tool_availability(quiet=True)
    disabled_tools: set = set()
    lazy_tools: set     = set()
    for item in unavailable_toolsets:
        ts_req       = TOOLSET_REQUIREMENTS.get(item.get("name", ""), {})
        tools_in_ts  = item.get("tools", [])
        if ts_req.get("check_fn"):
            lazy_tools.update(tools_in_ts)
        else:
            disabled_tools.update(tools_in_ts)

    # ── Skin tokens ──────────────────────────────────────────────────
    accent         = _skin_color("banner_accent",  "#7DD3FC")
    dim            = _skin_color("banner_dim",      "#8EA8A6")
    text           = _skin_color("banner_text",     "#E6EDF3")
    session_color  = _skin_color("session_border",  "#64748B")
    title_color    = _skin_color("banner_title",    "#E6EDF3")
    border_color   = _skin_color("banner_border",   "#2DD4BF")

    # ── Skin art ─────────────────────────────────────────────────────
    try:
        from sara_cli.skin_engine import get_active_skin
        _skin = get_active_skin()
    except Exception:
        _skin = None

    hero_art = (
        getattr(_skin, "banner_hero", None) or SARA_CADUCEUS
    )
    logo_art = (
        getattr(_skin, "banner_logo", None) or SARA_AGENT_LOGO
    )

    # ── Left column (caduceus + model info) ──────────────────────────
    model_short = model.split("/")[-1].removesuffix(".gguf")
    if len(model_short) > 28:
        model_short = model_short[:25] + "..."

    ctx_str = (
        f" [dim {dim}]·[/] [dim {dim}]{_format_context_length(context_length)} context[/]"
        if context_length else ""
    )
    left_lines = [
        f"[bold {title_color}]Sara Agent[/] [dim {dim}]by Nexvisora Research[/]",
        "",
        hero_art,
        "",
        f"[bold {accent}]{model_short}[/]{ctx_str}",
        f"[dim {dim}]{cwd}[/]",
    ]
    if session_id:
        left_lines.append(f"[dim {session_color}]Session: {session_id}[/]")

    # ── Right column (tools, MCP, skills, summary) ───────────────────
    right_lines = [f"[bold {accent}]Tools Ready[/]"]

    # Build toolsets dict
    toolsets_dict: Dict[str, list] = {}
    for tool in tools:
        tool_name = tool["function"]["name"]
        ts = _display_toolset_name(get_toolset_for_tool(tool_name) or "other")
        toolsets_dict.setdefault(ts, []).append(tool_name)
    for item in unavailable_toolsets:
        ts = _display_toolset_name(item.get("id", item.get("name", "unknown")))
        for tool_name in item.get("tools", []):
            if tool_name not in toolsets_dict.get(ts, []):
                toolsets_dict.setdefault(ts, []).append(tool_name)

    sorted_toolsets   = sorted(toolsets_dict)
    display_toolsets  = sorted_toolsets[:8]
    remaining_count   = len(sorted_toolsets) - 8

    for ts in display_toolsets:
        sorted_names = sorted(toolsets_dict[ts])
        display_names = (
            _truncate_tool_list(sorted_names)
            if len(", ".join(sorted_names)) > 45
            else sorted_names
        )
        colored = _colorize_tool_names(display_names, text, disabled_tools, lazy_tools)
        right_lines.append(f"[bold {dim}]{ts}[/] [dim {dim}]→[/] {', '.join(colored)}")

    if remaining_count > 0:
        right_lines.append(f"[dim {dim}]+ {remaining_count} more toolsets[/]")

    # MCP servers
    try:
        from tools.mcp_tool import get_mcp_status
        mcp_status = get_mcp_status()
    except Exception:
        mcp_status = []

    if mcp_status:
        right_lines += ["", f"[bold {accent}]MCP Servers[/]"]
        for srv in mcp_status:
            if srv["connected"]:
                right_lines.append(
                    f"[dim {dim}]{srv['name']}[/] [{text}]({srv['transport']})[/] "
                    f"[dim {dim}]—[/] [{text}]{srv['tools']} tool(s)[/]"
                )
            else:
                right_lines.append(
                    f"[red]{srv['name']}[/] [dim]({srv['transport']})[/] [red]— failed[/]"
                )

    # Skills
    right_lines += ["", f"[bold {accent}]Skills Loaded[/]"]
    skills_by_category = get_available_skills()
    total_skills = sum(len(s) for s in skills_by_category.values())

    if skills_by_category:
        sorted_categories = sorted(skills_by_category)
        display_categories = sorted_categories[:10]
        remaining_categories = len(sorted_categories) - len(display_categories)
        for category in display_categories:
            skill_names  = sorted(skills_by_category[category])
            display_part = skill_names[:8]
            skills_str   = ", ".join(display_part)
            if len(skill_names) > 8:
                skills_str += f" +{len(skill_names) - 8} more"
            if len(skills_str) > 50:
                skills_str = skills_str[:47] + "..."
            right_lines.append(f"[bold {dim}]{category}[/] [dim {dim}]→[/] [{text}]{skills_str}[/]")
        if remaining_categories > 0:
            right_lines.append(f"[dim {dim}]+ {remaining_categories} more skill categories[/]")
    else:
        right_lines.append(f"[dim {dim}]No skills installed[/]")

    # Active profile (omit when 'default')
    right_lines.append("")
    try:
        from sara_cli.profiles import get_active_profile_name
        profile = get_active_profile_name()
        if profile and profile != "default":
            right_lines.append(f"[bold {accent}]Profile:[/] [{text}]{profile}[/]")
    except Exception:
        pass

    # Summary line
    mcp_connected  = sum(1 for s in mcp_status if s["connected"]) if mcp_status else 0
    summary_parts  = [f"{len(tools)} tools", f"{total_skills} skills"]
    if mcp_connected:
        summary_parts.append(f"{mcp_connected} MCP servers")
    summary_parts.append("/help")
    right_lines.append(f"[bold {accent}]{'  ·  '.join(summary_parts)}[/]")

    # Update notice
    try:
        behind = get_update_result(timeout=0.5)
        if behind is not None and behind != 0:
            from sara_cli.config import get_managed_update_command, recommended_update_command
            if behind > 0:
                word = "commit" if behind == 1 else "commits"
                right_lines.append(
                    f"[bold yellow]⚠ {behind} {word} behind[/]"
                    f"[dim yellow] — run [bold]{recommended_update_command()}[/bold] to update[/]"
                )
            else:
                # UPDATE_AVAILABLE_NO_COUNT: nix-built Sara; update exists but
                # count is unknown and install method is unclear.
                managed_cmd = get_managed_update_command()
                line = "[bold yellow]⚠ update available[/]"
                if managed_cmd:
                    line += f"[dim yellow] — run [bold]{managed_cmd}[/bold][/]"
                right_lines.append(line)
    except Exception:
        pass  # Never break the banner over an update check

    # ── Assemble layout ───────────────────────────────────────────────
    layout_table = Table.grid(padding=(0, 2))
    layout_table.add_column("left",  justify="center")
    layout_table.add_column("right", justify="left")
    layout_table.add_row("\n".join(left_lines), "\n".join(right_lines))

    version_label = format_banner_version_label()
    release_info  = get_latest_release_tag()
    if release_info:
        tag, url     = release_info
        title_markup = f"[bold {title_color}][link={url}]{version_label}[/link][/]"
    else:
        title_markup = f"[bold {title_color}]{version_label}[/]"

    outer_panel = Panel(
        layout_table,
        title=title_markup,
        border_style=border_color,
        padding=(0, 2),
    )

    console.print()
    if shutil.get_terminal_size().columns >= 95:
        console.print(logo_art)
        console.print()
    console.print(outer_panel)
