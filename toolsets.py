"""Compatibility toolset registry for sara Agent.

This module provides the small API surface expected by the CLI and setup
wizard. It keeps toolset resolution available even when the richer registry
generation path is unavailable in a stripped-down checkout.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from sara_cli.platforms import get_all_platforms


_TOOLSET_TOOL_MAP: Dict[str, List[str]] = {
    "web": ["web_search", "web_extract"],
    "browser": ["navigate", "click", "type", "scroll"],
    "terminal": ["terminal", "process"],
    "file": ["read", "write", "patch", "search"],
    "code_execution": ["execute_code"],
    "vision": ["vision_analyze"],
    "image_gen": ["image_generate"],
    "moa": ["mixture_of_agents"],
    "tts": ["text_to_speech"],
    "skills": ["list_skills", "read_skill", "manage_skills"],
    "todo": ["todo"],
    "memory": ["memory_add", "memory_search", "memory_list", "memory_delete"],
    "session_search": ["search_sessions"],
    "clarify": ["clarify"],
    "delegation": ["delegate_task"],
    "cronjob": ["create_job", "list_jobs", "update_job", "pause_job", "resume_job", "run_job"],
    "messaging": ["send_message", "broadcast_message"],
    "rl": ["rl_train"],
    "homeassistant": ["homeassistant_control"],
    "spotify": ["spotify_search", "spotify_playback", "spotify_playlists", "spotify_library"],
    "discord": ["discord_fetch_messages", "discord_search_members", "discord_create_thread"],
    "discord_admin": ["discord_list_channels", "discord_list_roles", "discord_pin_message", "discord_assign_role"],
    "yuanbao": ["yuanbao_group_info", "yuanbao_member_queries", "yuanbao_dm"],
}


def _build_default_composite() -> List[str]:
    tools: List[str] = []
    for tool_names in _TOOLSET_TOOL_MAP.values():
        for tool_name in tool_names:
            if tool_name not in tools:
                tools.append(tool_name)
    return tools


_DEFAULT_COMPOSITE_TOOLS = _build_default_composite()


def _registered_toolsets() -> Dict[str, Dict[str, object]]:
    try:
        from tools.registry import registry
        return registry.get_available_toolsets()
    except Exception:
        return {}


def _registered_tool_names() -> List[str]:
    try:
        from tools.registry import registry
        return registry.get_all_tool_names()
    except Exception:
        return []

TOOLSETS: Dict[str, Dict[str, object]] = {
    name: {
        "description": f"{name} toolset",
        "resolved_tools": list(tool_names),
        "tool_count": len(tool_names),
        "includes": [],
    }
    for name, tool_names in _TOOLSET_TOOL_MAP.items()
}

TOOLSETS["sara-cli"] = {
    "description": "Default CLI toolset",
    "resolved_tools": list(_DEFAULT_COMPOSITE_TOOLS),
    "tool_count": len(_DEFAULT_COMPOSITE_TOOLS),
    "includes": list(_TOOLSET_TOOL_MAP.keys()),
}

for platform_name in get_all_platforms().keys():
    default_toolset = f"sara-{platform_name}"
    TOOLSETS.setdefault(
        default_toolset,
        {
            "description": f"Default toolset for {platform_name}",
            "resolved_tools": list(_DEFAULT_COMPOSITE_TOOLS),
            "tool_count": len(_DEFAULT_COMPOSITE_TOOLS),
            "includes": list(_TOOLSET_TOOL_MAP.keys()),
        },
    )


def resolve_toolset(toolset_name: str) -> List[str]:
    if not toolset_name:
        return []
    registered_toolsets = _registered_toolsets()
    registered_tools = _registered_tool_names()
    if toolset_name == "all":
        if registered_tools:
            return registered_tools
        return list(_DEFAULT_COMPOSITE_TOOLS)
    if toolset_name == "*":
        if registered_tools:
            return registered_tools
        return list(_DEFAULT_COMPOSITE_TOOLS)
    registered_info = registered_toolsets.get(toolset_name)
    if registered_info is not None:
        return list(registered_info.get("resolved_tools") or [])
    info = TOOLSETS.get(toolset_name)
    if info is not None:
        return list(info["resolved_tools"])
    if toolset_name.startswith("sara-"):
        if registered_tools:
            return registered_tools
        return list(_DEFAULT_COMPOSITE_TOOLS)
    return [toolset_name]


def validate_toolset(toolset_name: str) -> bool:
    if not toolset_name:
        return False
    return (
        toolset_name in TOOLSETS
        or toolset_name in _registered_toolsets()
        or toolset_name in {"all", "*"}
        or toolset_name.startswith("sara-")
    )


def get_toolset_info(toolset_name: str):
    tools = resolve_toolset(toolset_name)
    if not tools:
        return None
    info = TOOLSETS.get(toolset_name, {})
    return {
        "name": toolset_name,
        "description": str(info.get("description") or f"{toolset_name} toolset"),
        "tool_count": len(tools),
        "resolved_tools": tools,
        "includes": list(info.get("includes") or []),
    }


def get_all_toolsets() -> Dict[str, Dict[str, object]]:
    all_toolsets = {name: get_toolset_info(name) for name in TOOLSETS.keys()}
    all_toolsets.update(_registered_toolsets())
    return all_toolsets
