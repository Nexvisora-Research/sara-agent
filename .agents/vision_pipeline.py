"""High-level vision pipeline for Sara Agent.

Pipeline:
image source -> vision model analysis -> structured data -> visual memory ->
response text.  The lower-level model call stays in ``tools.vision_tools`` so
CLI, TUI, gateway, and tools all use the same vision backend configuration.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from sara_constants import get_sara_home

ExtractType = Literal["text", "code", "ui", "entities", "layout", "full"]


@dataclass(frozen=True)
class VisionInput:
    source: str
    kind: Literal["url", "file", "data"]


@dataclass
class StructuredVisualData:
    summary: str = ""
    text: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    ui_elements: list[str] = field(default_factory=list)
    objects: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    layout: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    raw_analysis: str = ""


@dataclass(frozen=True)
class VisionPipelineResponse:
    image_source: str
    final_text: str
    analysis: str
    structured_data: dict[str, Any]
    memory_id: str | None = None


def _memory_dir(user_id: str) -> Path:
    safe_user = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(user_id or "default"))[:80]
    path = get_sara_home() / "visual_memories" / safe_user
    path.mkdir(parents=True, exist_ok=True)
    return path


def _memory_file(user_id: str) -> Path:
    return _memory_dir(user_id) / "memories.json"


def _load_memories(user_id: str) -> list[dict[str, Any]]:
    path = _memory_file(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_memories(user_id: str, memories: list[dict[str, Any]]) -> None:
    path = _memory_file(user_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _normalize_input(image_source: str) -> VisionInput:
    source = str(image_source or "").strip()
    if not source:
        raise ValueError("No image source provided")
    if source.startswith("data:image/"):
        return VisionInput(source=source, kind="data")
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return VisionInput(source=source, kind="url")
    if source.startswith("file://"):
        source = source[7:]
    path = Path(source).expanduser()
    if path.is_file():
        return VisionInput(source=str(path), kind="file")
    raise ValueError("Image source must be an HTTP(S) URL, data URL, or existing local file")


async def _analyze_image(vision_input: VisionInput, question: str = "") -> str:
    from tools.vision_tools import vision_analyze_tool

    prompt = (
        "Analyze this image carefully. Describe visible objects, text, people, "
        "UI elements, layout, code, diagrams, and any notable entities. "
        "Return concrete observations, not guesses."
    )
    if question:
        prompt += f"\n\nUser question: {question}"
    result = await vision_analyze_tool(image_url=vision_input.source, user_prompt=prompt)
    try:
        payload = json.loads(result)
        if isinstance(payload, dict):
            if payload.get("success") and payload.get("analysis"):
                return str(payload["analysis"])
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
    except json.JSONDecodeError:
        pass
    return str(result or "")


def _split_lines(text: str) -> list[str]:
    return [line.strip(" -\t") for line in text.splitlines() if line.strip(" -\t")]


def _extract_code_blocks(text: str) -> list[str]:
    blocks = re.findall(r"```(?:[A-Za-z0-9_+.-]+)?\s*(.*?)```", text, flags=re.DOTALL)
    inline = []
    for line in _split_lines(text):
        if re.search(r"\b(def|class|function|const|let|var|import|SELECT|CREATE|if|for|while)\b", line):
            inline.append(line)
    return [b.strip() for b in blocks if b.strip()] + inline[:10]


def _extract_quoted_text(text: str) -> list[str]:
    found = re.findall(r'"([^"\n]{2,160})"', text)
    found += re.findall(r"'([^'\n]{2,160})'", text)
    return _dedupe(found)[:30]


def _sentences_matching(text: str, patterns: list[str], limit: int = 20) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    matches = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        lower = c.lower()
        if any(p in lower for p in patterns):
            matches.append(c[:240])
    return _dedupe(matches)[:limit]


def _keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())
    stop = {
        "the", "and", "that", "this", "with", "from", "image", "visible",
        "there", "appears", "shown", "shows", "contains", "could", "would",
    }
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = re.sub(r"\s+", " ", str(item).strip()).lower()
        if key and key not in seen:
            seen.add(key)
            out.append(str(item).strip())
    return out


def extract_structured_data(analysis: str, extract_type: ExtractType = "full") -> StructuredVisualData:
    text = str(analysis or "").strip()
    lines = _split_lines(text)
    first_summary = next((line for line in lines if len(line) > 20), text[:240])
    data = StructuredVisualData(
        summary=first_summary[:500],
        raw_analysis=text,
        tags=_keywords(text),
    )

    if extract_type in {"text", "full"}:
        data.text = _extract_quoted_text(text)
        data.text += _sentences_matching(text, ["text", "reads", "label", "caption", "ocr"], limit=12)
        data.text = _dedupe(data.text)[:30]

    if extract_type in {"code", "full"}:
        data.code = _extract_code_blocks(text)

    if extract_type in {"ui", "full"}:
        data.ui_elements = _sentences_matching(
            text,
            ["button", "menu", "input", "field", "tab", "sidebar", "toolbar", "dialog", "modal", "screen", "ui"],
        )

    if extract_type in {"entities", "full"}:
        proper = re.findall(r"\b[A-Z][A-Za-z0-9_.-]*(?:\s+[A-Z][A-Za-z0-9_.-]*){0,3}\b", text)
        data.entities = _dedupe([p for p in proper if len(p) > 2])[:30]

    if extract_type in {"layout", "full"}:
        data.layout = _sentences_matching(
            text,
            ["left", "right", "top", "bottom", "center", "layout", "row", "column", "grid", "foreground", "background"],
        )

    if extract_type == "full":
        object_patterns = ["object", "person", "people", "building", "vehicle", "table", "chart", "diagram", "icon", "logo"]
        data.objects = _sentences_matching(text, object_patterns, limit=20)
        if not data.objects:
            data.objects = data.tags[:10]

    return data


def store_visual_memory(user_id: str, image_description: str, structured_data: dict[str, Any]) -> str:
    memories = _load_memories(user_id)
    memory_id = f"vis_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    tags = structured_data.get("tags") if isinstance(structured_data, dict) else []
    record = {
        "memory_id": memory_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "image_description": str(image_description or ""),
        "structured_data": structured_data,
        "tags": tags if isinstance(tags, list) else [],
    }
    memories.insert(0, record)
    _save_memories(user_id, memories[:1000])
    return memory_id


def search_visual_memories(user_id: str, query: str, max_results: int = 5) -> list[dict[str, Any]]:
    terms = [t.lower() for t in re.findall(r"[A-Za-z0-9_-]+", query or "") if len(t) > 1]
    if not terms:
        return []
    scored = []
    for memory in _load_memories(user_id):
        haystack = json.dumps(memory, ensure_ascii=False).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            scored.append((score, memory))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [memory for _, memory in scored[: max(1, int(max_results or 5))]]


def list_visual_memories(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    return _load_memories(user_id)[: max(1, int(limit or 10))]


def delete_visual_memory(user_id: str, memory_id: str) -> bool:
    memories = _load_memories(user_id)
    kept = [m for m in memories if m.get("memory_id") != memory_id]
    if len(kept) == len(memories):
        return False
    _save_memories(user_id, kept)
    return True


async def process_image(
    user_id: str,
    image_source: str,
    question: str = "",
    channel: str = "chat",
    extract_structured: bool = True,
    store_memory: bool = True,
) -> VisionPipelineResponse:
    vision_input = _normalize_input(image_source)
    analysis = await _analyze_image(vision_input, question)
    structured = (
        extract_structured_data(analysis, "full")
        if extract_structured
        else StructuredVisualData(summary=analysis[:500], raw_analysis=analysis)
    )
    structured_dict = structured.__dict__
    memory_id = None
    if store_memory:
        structured_dict = dict(structured_dict)
        structured_dict["channel"] = channel
        structured_dict["image_source"] = vision_input.source
        memory_id = store_visual_memory(user_id, analysis, structured_dict)

    final_text = analysis
    if memory_id:
        final_text = f"{analysis}\n\n[visual_memory_id: {memory_id}]"
    return VisionPipelineResponse(
        image_source=vision_input.source,
        final_text=final_text,
        analysis=analysis,
        structured_data=structured_dict,
        memory_id=memory_id,
    )

