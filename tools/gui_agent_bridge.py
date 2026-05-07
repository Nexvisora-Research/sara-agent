#!/usr/bin/env python3
"""Lightweight bridge for Sara Agent GUI -> core agent loop.

Reads a JSON payload from argv[1] or stdin:
{
  "user_id": "gui_user",
  "message": "hello",
  "channel": "sara-agent"
}

Writes JSON to stdout:
{
  "ok": true,
  "status": "final",
  "reply": "...",
  "action_summaries": [...]
}
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path


def _load_payload() -> dict:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return json.loads(sys.argv[1])

    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def _print_json(data: dict, exit_code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=True), flush=True)
    raise SystemExit(exit_code)


def _knowledge_status() -> str:
    try:
        from memory.knowledge import _check_deps, _get_collection, fallback_count

        err = _check_deps()
        if err:
            return f"Vector memory: active via local JSON fallback ({fallback_count()} stored chunks). Install chromadb + sentence-transformers later for Chroma semantic search."
        collection = _get_collection()
        return f"Vector memory: active ({collection.count()} stored chunks)."
    except Exception as exc:
        return f"Vector memory: unavailable ({exc})."


def _handle_gui_command(user_id: str, message: str) -> dict | None:
    text = message.strip()
    lower = text.lower()

    if lower in {"/memory", "memory", "show memory", "memory status"}:
        from memory.memory_engine import get_memory_summary

        return {
            "ok": True,
            "status": "final",
            "reply": get_memory_summary(user_id) + "\n\n" + _knowledge_status(),
            "action_summaries": ["memory_summary"],
        }

    if lower in {"/tools", "tools", "list tools", "show tools"}:
        from tools.register_tool import get_tools_description

        return {
            "ok": True,
            "status": "final",
            "reply": "Available Sara tools:\n\n" + get_tools_description(),
            "action_summaries": ["list_tools"],
        }

    if lower in {"/skills", "skills", "list skills", "show skills"}:
        from tools.register_tool import execute_tool

        return {
            "ok": True,
            "status": "final",
            "reply": execute_tool("list_skills", "", user_id=user_id),
            "action_summaries": ["list_skills"],
        }

    if lower in {"/skills all", "all skills", "show all skills"}:
        from tools.register_tool import execute_tool

        return {
            "ok": True,
            "status": "final",
            "reply": execute_tool("list_skills", "all", user_id=user_id),
            "action_summaries": ["list_skills(all)"],
        }

    if lower in {"/features", "features", "/help", "help"}:
        from tools.register_tool import execute_tool

        return {
            "ok": True,
            "status": "final",
            "reply": execute_tool("read_sara_features", "", user_id=user_id),
            "action_summaries": ["read_sara_features"],
        }

    if lower.startswith("/remember "):
        from memory.knowledge import knowledge_add

        content = text[len("/remember "):].strip()
        return {
            "ok": True,
            "status": "final",
            "reply": knowledge_add(content, user_id=user_id, memory_type="user_note", source="gui"),
            "action_summaries": ["knowledge_add"],
        }

    if lower.startswith("/recall "):
        from memory.knowledge import knowledge_search

        query = text[len("/recall "):].strip()
        return {
            "ok": True,
            "status": "final",
            "reply": knowledge_search(query, user_id=user_id),
            "action_summaries": ["knowledge_search"],
        }

    return None


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        with redirect_stdout(sys.stderr):
            from sara_cli.env_loader import load_sara_dotenv
            from sara_constants import get_sara_home

            load_sara_dotenv(sara_home=get_sara_home(), project_env=repo_root / '.env')
    except Exception:
        pass

    try:
        payload = _load_payload()
        user_id = str(payload.get('user_id') or 'gui_user')
        message = str(payload.get('message') or '').strip()
        channel = str(payload.get('channel') or 'gui')

        if not message:
            _print_json({
                'ok': False,
                'error': 'empty_message',
                'reply': 'Please type a message.',
            }, exit_code=1)

        with redirect_stdout(sys.stderr):
            command_response = _handle_gui_command(user_id, message)
        if command_response:
            _print_json(command_response)

        with redirect_stdout(sys.stderr):
            from agent.agent_loop import process_turn

            response = process_turn(user_id, message, channel=channel)
        reply = getattr(response, 'final_text', '') or ''
        status = getattr(response, 'status', 'final')
        action_summaries = getattr(response, 'action_summaries', []) or []

        _print_json({
            'ok': True,
            'status': status,
            'reply': reply,
            'action_summaries': action_summaries,
        })
    except Exception as exc:
        _print_json({
            'ok': False,
            'error': str(exc),
            'reply': 'Sara Agent backend is unavailable right now.',
        }, exit_code=1)


if __name__ == '__main__':
    main()
