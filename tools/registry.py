"""Central runtime registry for tool definitions.

Provides a lightweight API used across tool modules:
- `registry.register(...)`
- `registry.dispatch(...)`
- metadata getters (`get_schema`, `get_entry`, ...)
- utility helpers (`tool_result`, `tool_error`)
"""

from __future__ import annotations

import json
import logging
import ast
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolEntry:
    name: str
    toolset: str
    schema: dict[str, Any]
    handler: Callable[..., Any]
    check_fn: Optional[Callable[[], bool]] = None
    requires_env: Optional[list] = None
    is_async: bool = False
    description: str = ""
    emoji: str = ""
    max_result_size_chars: Optional[int] = None


def _json_default(value: Any) -> Any:
    if isinstance(value, Exception):
        return str(value)
    return repr(value)


def tool_result(data: Any = None, *, success: bool = True, **extra: Any) -> str:
    payload: Dict[str, Any] = {"success": bool(success)}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


def tool_error(message: str, *, success: bool = False, **extra: Any) -> str:
    payload: Dict[str, Any] = {
        "success": bool(success),
        "error": str(message),
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolEntry] = {}
        self._toolset_aliases: dict[str, str] = {}
        self._generation = 0

    def register(
        self,
        *,
        name: str,
        toolset: str,
        schema: dict[str, Any],
        handler: Callable[..., Any],
        check_fn: Optional[Callable[[], bool]] = None,
        requires_env: Optional[list] = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        max_result_size_chars: Optional[int] = None,
    ) -> None:
        self._tools[name] = ToolEntry(
            name=name,
            toolset=toolset,
            schema=schema or {},
            handler=handler,
            check_fn=check_fn,
            requires_env=requires_env,
            is_async=bool(is_async),
            description=description,
            emoji=emoji,
            max_result_size_chars=max_result_size_chars,
        )
        self._generation += 1

    def deregister(self, name: str) -> None:
        if name in self._tools:
            self._tools.pop(name, None)
            self._generation += 1

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[dict[str, Any]]:
        entry = self._tools.get(name)
        return entry.schema if entry else None

    def get_all_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def get_emoji(self, name: str, default: str = "") -> str:
        entry = self._tools.get(name)
        return entry.emoji if entry and entry.emoji else default

    def get_toolset_for_tool(self, name: str) -> Optional[str]:
        entry = self._tools.get(name)
        return entry.toolset if entry else None

    def register_toolset_alias(self, alias: str, toolset_name: str) -> None:
        self._toolset_aliases[str(alias)] = str(toolset_name)
        self._generation += 1

    def get_toolset_alias_target(self, alias: str) -> Optional[str]:
        return self._toolset_aliases.get(str(alias))

    def get_max_result_size(self, name: str, default: int = 100_000) -> int:
        entry = self._tools.get(name)
        if entry and isinstance(entry.max_result_size_chars, int) and entry.max_result_size_chars > 0:
            return entry.max_result_size_chars
        return default

    def get_definitions(self, names: Optional[set[str]] = None, quiet: bool = False) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = []
        include = set(names) if names is not None else None

        for name in sorted(self._tools.keys()):
            if include is not None and name not in include:
                continue
            entry = self._tools[name]
            if entry.check_fn is not None:
                try:
                    if not bool(entry.check_fn()):
                        continue
                except Exception as exc:
                    if not quiet:
                        logger.debug("Tool check failed for %s: %s", name, exc)
                    continue

            schema = dict(entry.schema or {})
            schema.setdefault("name", name)
            definitions.append({"type": "function", "function": schema})

        return definitions

    def get_tool_to_toolset_map(self) -> dict[str, str]:
        return {name: entry.toolset for name, entry in self._tools.items()}

    def get_toolset_requirements(self) -> dict[str, dict[str, Any]]:
        requirements: dict[str, dict[str, Any]] = {}
        for entry in self._tools.values():
            info = requirements.setdefault(
                entry.toolset,
                {"requires_env": [], "tools": []},
            )
            info["tools"].append(entry.name)
            for env_name in entry.requires_env or []:
                if env_name not in info["requires_env"]:
                    info["requires_env"].append(env_name)
        return requirements

    def get_available_toolsets(self) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for entry in self._tools.values():
            info = grouped.setdefault(
                entry.toolset,
                {
                    "name": entry.toolset,
                    "description": f"{entry.toolset} toolset",
                    "resolved_tools": [],
                    "tool_count": 0,
                    "available": True,
                },
            )
            info["resolved_tools"].append(entry.name)
            info["tool_count"] = len(info["resolved_tools"])
            if entry.check_fn is not None:
                try:
                    info["available"] = bool(info["available"] and entry.check_fn())
                except Exception:
                    info["available"] = False
        return grouped

    def check_toolset_requirements(self) -> dict[str, bool]:
        availability: dict[str, bool] = {}
        for name, info in self.get_available_toolsets().items():
            availability[name] = bool(info.get("available", True))
        return availability

    def check_tool_availability(self, quiet: bool = False) -> tuple[list[str], list[dict[str, Any]]]:
        available_toolsets: list[str] = []
        unavailable: list[dict[str, Any]] = []
        for name, info in self.get_available_toolsets().items():
            if info.get("available", True):
                available_toolsets.append(name)
            else:
                unavailable.append({"toolset": name, "reason": "requirement check failed"})
                if not quiet:
                    logger.info("Toolset unavailable: %s", name)
        return sorted(available_toolsets), unavailable

    def dispatch(self, name: str, args: dict[str, Any], **kwargs: Any) -> str:
        entry = self._tools.get(name)
        if not entry:
            return tool_error(f"Unknown tool: {name}")

        if entry.check_fn is not None:
            try:
                if not bool(entry.check_fn()):
                    return tool_error(f"Tool not available: {name}")
            except Exception as exc:
                return tool_error(f"Tool check failed for {name}: {exc}")

        try:
            result = entry.handler(args or {}, **kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=_json_default)
        except Exception as exc:
            logger.exception("Tool '%s' failed", name)
            return tool_error(str(exc))


registry = ToolRegistry()


def _module_registers_tools(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Could not inspect tool module %s: %s", path, exc)
        return False

    for node in tree.body:
        call = node.value if isinstance(node, ast.Expr) else None
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "register"
            and isinstance(func.value, ast.Name)
            and func.value.id == "registry"
        ):
            return True
    return False


def discover_builtin_tools(tools_dir: Optional[str | Path] = None) -> list[str]:
    tools_path = Path(tools_dir) if tools_dir else Path(__file__).parent
    package = __package__ or "tools"
    before = set(registry.get_all_tool_names())

    for path in sorted(tools_path.glob("*.py")):
        if path.name in {"__init__.py", "registry.py", "mcp_tool.py"}:
            continue
        if not _module_registers_tools(path):
            continue
        module_name = f"{package}.{path.stem}"
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            logger.debug("Skipping tool module %s: %s", module_name, exc)

    after = set(registry.get_all_tool_names())
    return sorted(after - before)
