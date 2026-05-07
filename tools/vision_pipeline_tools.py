#!/usr/bin/env python3
"""
tools/vision_pipeline_tools.py - Vision Pipeline Tools for Sara AI Tool Registry.

Registers high-level vision tools that use the vision_pipeline module:
- vision_process: Full pipeline (image -> structured data -> memory -> response)
- vision_extract: Extract specific data from an image (text, code, UI, entities)
- vision_remember: Store a visual memory
- vision_recall: Search visual memories
- vision_memories: List visual memories

These tools let the agent use vision capabilities through the normal tool system.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Awaitable, Dict

from tools.registry import registry, tool_error

logger = logging.getLogger(__name__)


# ─── Tool: vision_process (full pipeline) ─────────────────────────────────────

VISION_PROCESS_SCHEMA = {
    "name": "vision_process",
    "description": (
        "Process an image through the full vision pipeline: analyze with AI vision, "
        "extract structured data (text, code, UI elements, objects, entities), "
        "store in visual memory, and return a comprehensive response. "
        "Use this when the user sends an image and wants to understand it, "
        "or when you need to analyze a screenshot, photo, diagram, or any visual content. "
        "Accepts image URLs or local file paths."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "Image URL (http/https) or local file path."
            },
            "question": {
                "type": "string",
                "description": "What to ask about the image. Empty = general analysis."
            },
            "channel": {
                "type": "string",
                "description": "Source channel: telegram, discord, or chat (default: chat)."
            },
        },
        "required": ["image_url"],
    },
}


async def _handle_vision_process(args: Dict[str, Any], **kw: Any) -> str:
    image_url = args.get("image_url", "")
    question = args.get("question", "")
    channel = args.get("channel", "chat")
    user_id = kw.get("user_id", "default")

    if not image_url:
        return tool_error("No image_url provided")

    try:
        from agent.vision_pipeline import process_image
        response = await process_image(
            user_id=user_id,
            image_source=image_url,
            question=question,
            channel=channel,
            extract_structured=True,
            store_memory=True,
        )
        return response.final_text
    except ImportError:
        return tool_error("vision_pipeline module not available")
    except Exception as e:
        logger.error("vision_process error: %s", e, exc_info=True)
        return tool_error("Vision processing failed: " + str(e))


# ─── Tool: vision_extract (targeted extraction) ──────────────────────────────

VISION_EXTRACT_SCHEMA = {
    "name": "vision_extract",
    "description": (
        "Extract specific structured data from an image. "
        "Use when you need targeted extraction: just text (OCR), just code, "
        "just UI elements, just entities, or just layout info. "
        "More efficient than full pipeline when you only need one type of data."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "Image URL or local file path."
            },
            "extract_type": {
                "type": "string",
                "description": "What to extract: text, code, ui, entities, layout, or full (default: full).",
                "enum": ["text", "code", "ui", "entities", "layout", "full"],
            },
        },
        "required": ["image_url"],
    },
}


async def _handle_vision_extract(args: Dict[str, Any], **kw: Any) -> str:
    image_url = args.get("image_url", "")
    extract_type = args.get("extract_type", "full")

    if not image_url:
        return tool_error("No image_url provided")

    try:
        from agent.vision_pipeline import _normalize_input, _analyze_image, extract_structured_data
        vision_input = _normalize_input(image_url)
        vision_output = await _analyze_image(vision_input, "")
        if not vision_output:
            return tool_error("Could not analyze image")
        data = extract_structured_data(vision_output, extract_type)
        return json.dumps(data.__dict__, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("vision_extract error: %s", e, exc_info=True)
        return tool_error("Extraction failed: " + str(e))


# ─── Tool: vision_remember ───────────────────────────────────────────────────

VISION_REMEMBER_SCHEMA = {
    "name": "vision_remember",
    "description": (
        "Store a visual memory manually. Use when the user says "
        '"remember this image" or "save this to visual memory".'
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "Image URL or local file path."
            },
            "description": {
                "type": "string",
                "description": "Custom description of the image (optional, auto-generated if empty)."
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags to associate with this memory (optional)."
            },
        },
        "required": ["image_url"],
    },
}


async def _handle_vision_remember(args: Dict[str, Any], **kw: Any) -> str:
    image_url = args.get("image_url", "")
    custom_desc = args.get("description", "")
    tags = args.get("tags", [])
    user_id = kw.get("user_id", "default")

    if not image_url:
        return tool_error("No image_url provided")

    try:
        from agent.vision_pipeline import _normalize_input, _analyze_image, extract_structured_data, store_visual_memory
        vision_input = _normalize_input(image_url)
        if custom_desc:
            structured = extract_structured_data(custom_desc, "full")
            structured.objects.extend(tags)
            mid = store_visual_memory(user_id, custom_desc, structured.__dict__)
        else:
            vision_output = await _analyze_image(vision_input, "")
            structured = extract_structured_data(vision_output, "full")
            mid = store_visual_memory(user_id, vision_output, structured.__dict__)
        return json.dumps({"success": True, "memory_id": mid, "message": "Visual memory stored"})
    except Exception as e:
        logger.error("vision_remember error: %s", e, exc_info=True)
        return tool_error("Failed to store memory: " + str(e))


# ─── Tool: vision_recall ─────────────────────────────────────────────────────

VISION_RECALL_SCHEMA = {
    "name": "vision_recall",
    "description": (
        "Search visual memories by query. Use when the user asks about "
        "something they showed before, or when you need to find related "
        "visual memories."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to find relevant visual memories."
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default: 5).",
            },
        },
        "required": ["query"],
    },
}


def _handle_vision_recall(args: Dict[str, Any], **kw: Any) -> str:
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    user_id = kw.get("user_id", "default")

    if not query:
        return tool_error("No query provided")

    try:
        from agent.vision_pipeline import search_visual_memories
        results = search_visual_memories(user_id, query, max_results)
        if not results:
            return json.dumps({"success": True, "count": 0, "message": "No matching visual memories found."})
        return json.dumps({"success": True, "count": len(results), "memories": results}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("vision_recall error: %s", e, exc_info=True)
        return tool_error("Search failed: " + str(e))


# ─── Tool: vision_memories (list) ────────────────────────────────────────────

VISION_MEMORIES_SCHEMA = {
    "name": "vision_memories",
    "description": "List recent visual memories for the current user.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of memories to list (default: 10).",
            },
        },
    },
}


def _handle_vision_memories(args: Dict[str, Any], **kw: Any) -> str:
    limit = args.get("limit", 10)
    user_id = kw.get("user_id", "default")

    try:
        from agent.vision_pipeline import list_visual_memories
        mems = list_visual_memories(user_id, limit)
        if not mems:
            return "No visual memories stored yet."
        lines = ["Visual Memories (" + str(len(mems)) + "):"]
        for m in mems:
            mid = m.get("memory_id", "?")
            ts = m.get("timestamp", "?")[:16]
            desc = m.get("image_description", "")[:80]
            tags = ", ".join(m.get("tags", [])[:5])
            lines.append("  [" + mid + "] " + ts + " - " + desc + " (tags: " + tags + ")")
        return "\n".join(lines)
    except Exception as e:
        logger.error("vision_memories error: %s", e, exc_info=True)
        return tool_error("Failed to list memories: " + str(e))


# ─── Tool: vision_forget ─────────────────────────────────────────────────────

VISION_FORGET_SCHEMA = {
    "name": "vision_forget",
    "description": "Delete a visual memory by its ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "string",
                "description": "The ID of the visual memory to delete."
            },
        },
        "required": ["memory_id"],
    },
}


def _handle_vision_forget(args: Dict[str, Any], **kw: Any) -> str:
    memory_id = args.get("memory_id", "")
    user_id = kw.get("user_id", "default")

    if not memory_id:
        return tool_error("No memory_id provided")

    try:
        from agent.vision_pipeline import delete_visual_memory
        if delete_visual_memory(user_id, memory_id):
            return "Visual memory " + memory_id + " deleted."
        return "Memory " + memory_id + " not found."
    except Exception as e:
        logger.error("vision_forget error: %s", e, exc_info=True)
        return tool_error("Failed to delete: " + str(e))


# ─── Registration ─────────────────────────────────────────────────────────────

def _check_vision_available() -> bool:
    """Check if vision pipeline is available."""
    try:
        from agent.vision_pipeline import process_image
        return True
    except ImportError:
        return False


registry.register(
    name="vision_process",
    toolset="vision",
    schema=VISION_PROCESS_SCHEMA,
    handler=_handle_vision_process,
    check_fn=_check_vision_available,
    is_async=True,
    emoji="👁️",
)

registry.register(
    name="vision_extract",
    toolset="vision",
    schema=VISION_EXTRACT_SCHEMA,
    handler=_handle_vision_extract,
    check_fn=_check_vision_available,
    is_async=True,
    emoji="🔍",
)

registry.register(
    name="vision_remember",
    toolset="vision",
    schema=VISION_REMEMBER_SCHEMA,
    handler=_handle_vision_remember,
    check_fn=_check_vision_available,
    is_async=True,
    emoji="💾",
)

registry.register(
    name="vision_recall",
    toolset="vision",
    schema=VISION_RECALL_SCHEMA,
    handler=_handle_vision_recall,
    check_fn=_check_vision_available,
    emoji="🔎",
)

registry.register(
    name="vision_memories",
    toolset="vision",
    schema=VISION_MEMORIES_SCHEMA,
    handler=_handle_vision_memories,
    check_fn=_check_vision_available,
    emoji="📋",
)

registry.register(
    name="vision_forget",
    toolset="vision",
    schema=VISION_FORGET_SCHEMA,
    handler=_handle_vision_forget,
    check_fn=_check_vision_available,
    emoji="🗑️",
)
