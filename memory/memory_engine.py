"""
memory/memory_engine.py — Sara vNext layered memory engine.

This layer keeps:
  - profile signals (topics, mood, goals, habits)
  - a rolling conversation summary
  - episodic memories for stable preferences, goals, corrections, and tasks
  - query-aware retrieval backed by semantic search when available
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUMMARY_FILE = "summary.json"
EPISODIC_FILE = "episodic_memory.json"
SUMMARY_MAX_LINES = 14
EPISODIC_MAX_RECORDS = 100

TOPIC_PATTERNS = {
    "coding": r"\b(code|coding|python|javascript|js|react|flask|django|html|css|api|bug|error|debug|github|git|function|class|program|script|algorithm|database|sql|deploy|docker)\b",
    "music": r"\b(music|song|playlist|spotify|album|artist|guitar|piano|beats|rap|rock|pop|jazz|classical|listen)\b",
    "fitness": r"\b(gym|workout|exercise|run|running|fitness|health|diet|calories|weight|yoga|cycling|protein)\b",
    "gaming": r"\b(game|gaming|play|player|steam|xbox|playstation|pc|fps|rpg|esports|minecraft|fortnite)\b",
    "food": r"\b(food|eat|cook|recipe|restaurant|pizza|coffee|tea|lunch|dinner|breakfast|snack|vegetarian|vegan)\b",
    "travel": r"\b(travel|trip|flight|hotel|city|country|visit|passport|vacation|holiday|tour|backpack)\b",
    "study": r"\b(study|learn|course|university|college|school|exam|degree|book|read|knowledge|tutorial|class)\b",
    "work": r"\b(work|job|office|meeting|project|deadline|client|boss|salary|freelance|startup|business|career)\b",
    "finance": r"\b(money|invest|stock|crypto|bitcoin|savings|budget|loan|bank|income|expense|profit)\b",
    "ai": r"\b(ai|llm|gpt|chatgpt|machine learning|neural|model|prompt|gemini|claude|ollama|groq|tensorflow|pytorch)\b",
    "family": r"\b(family|mom|dad|parent|brother|sister|child|kids|wife|husband|friend|relationship|love)\b",
    "movies": r"\b(movie|film|netflix|show|series|watch|cinema|actor|director|episode|season|anime)\b",
}

STOP_WORDS = {
    "i", "me", "my", "the", "a", "an", "is", "it", "to", "of", "and", "or", "but", "in", "on",
    "at", "for", "do", "did", "are", "was", "be", "have", "has", "will", "you", "we", "they",
    "not", "no", "yes", "ok", "hi", "hey", "just", "very", "also", "more", "some", "about",
    "with", "from", "get", "use", "need", "want", "know", "like", "good", "now", "can",
}

POSITIVE_WORDS = {
    "happy", "great", "love", "awesome", "excellent", "good", "nice", "fantastic", "amazing",
    "wonderful", "brilliant", "excited", "joy", "glad", "thanks", "perfect", "cool", "fun",
    "enjoy", "best", "hope", "yes", "yay", "wow", "done", "success", "fixed", "works",
}

NEGATIVE_WORDS = {
    "sad", "bad", "hate", "terrible", "awful", "horrible", "angry", "upset", "annoyed",
    "frustrated", "broken", "failed", "error", "bug", "crash", "problem", "issue", "wrong",
    "fix", "help", "stuck", "weird", "slow", "confused", "lost", "tired", "bored", "cant",
    "cannot", "fail", "broke",
}

GOAL_PATTERNS = [
    (r"i want to (.{5,80})", "Wants to "),
    (r"i am trying to (.{5,80})", "Trying to "),
    (r"i plan to (.{5,80})", "Plans to "),
    (r"i need to (.{5,80})", "Needs to "),
    (r"my goal is (.{5,80})", "Goal: "),
    (r"i hope to (.{5,80})", "Hopes to "),
    (r"i'm learning (.{5,80})", "Learning "),
    (r"i am learning (.{5,80})", "Learning "),
]

HABIT_PATTERNS = [
    (r"i always (.{5,80})", "Always "),
    (r"every (morning|evening|day|night|week) i (.{5,80})", "Habit: "),
    (r"i usually (.{5,80})", "Usually "),
    (r"i often (.{5,80})", "Often "),
]

PREFERENCE_PATTERNS = [
    (r"\b(step by step|steps)\b", "prefers step-by-step help"),
    (r"\b(short|brief|concise)\b", "prefers concise answers"),
    (r"\b(detailed|deep|in detail)\b", "prefers detailed answers"),
    (r"\b(simple|easy to understand)\b", "prefers simple explanations"),
]


@dataclass
class MemoryRecord:
    content: str
    memory_type: str
    source: str
    timestamp: str
    metadata: dict = field(default_factory=dict)


@dataclass
class UnderstandingFrame:
    user_goal: str = ""
    constraints: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)


def _user_dir(user_id: str) -> str:
    user_dir = os.path.join(DATA_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _profile_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), "profile.json")


def _summary_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), SUMMARY_FILE)


def _episodic_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), EPISODIC_FILE)


def _load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Could not load %s: %s", path, exc)
    return default


def _save_json(path: str, value) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("Could not save %s: %s", path, exc)


def _load_profile(user_id: str) -> dict:
    return _load_json(_profile_path(user_id), {})


def _save_profile(user_id: str, profile: dict) -> None:
    _save_json(_profile_path(user_id), profile)


def _load_summary(user_id: str) -> dict:
    return _load_json(
        _summary_path(user_id),
        {"summary": "", "summary_lines": [], "message_count": 0, "last_updated": None},
    )


def _save_summary(user_id: str, summary: dict) -> None:
    _save_json(_summary_path(user_id), summary)


def _load_episodic_memories(user_id: str) -> list[dict]:
    return _load_json(_episodic_path(user_id), [])


def _save_episodic_memories(user_id: str, records: list[dict]) -> None:
    _save_json(_episodic_path(user_id), records[-EPISODIC_MAX_RECORDS:])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_topics(text: str) -> list[str]:
    """Return a list of detected topic labels from text."""
    text_lower = text.lower()
    found = []
    for topic, pattern in TOPIC_PATTERNS.items():
        if re.search(pattern, text_lower):
            found.append(topic)
    if not found:
        words = re.findall(r"[a-z]{4,}", text_lower)
        found = [w for w in words if w not in STOP_WORDS][:3]
    return found


def detect_emotion(text: str) -> str:
    """Return 'positive', 'neutral', or 'negative' based on simple word matching."""
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    pos_score = len(tokens & POSITIVE_WORDS)
    neg_score = len(tokens & NEGATIVE_WORDS)
    if pos_score > neg_score:
        return "positive"
    if neg_score > pos_score:
        return "negative"
    return "neutral"


def _extract_goals(text: str) -> list[str]:
    goals = []
    lower = text.lower()
    for pattern, prefix in GOAL_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            tail = match.group(match.lastindex or 1).strip(" .,!")
            if 4 < len(tail) < 100:
                goals.append(prefix + tail)
    return goals


def _extract_habits(text: str) -> list[str]:
    habits = []
    lower = text.lower()
    for pattern, prefix in HABIT_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            tail = match.group(match.lastindex or 1).strip(" .,!")
            if 4 < len(tail) < 100:
                habits.append(prefix + tail)
    return habits


def _extract_constraints(text: str) -> list[str]:
    constraints = []
    patterns = [
        r"\bwithout ([^.,;!?]+)",
        r"\bonly ([^.,;!?]+)",
        r"\busing ([^.,;!?]+)",
        r"\bdon't ([^.,;!?]+)",
        r"\bdo not ([^.,;!?]+)",
    ]
    lower = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lower):
            value = match.group(0).strip(" .,!")
            if value and value not in constraints:
                constraints.append(value)
    return constraints[:4]


def _extract_preferences(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for pattern, label in PREFERENCE_PATTERNS:
        if re.search(pattern, lower) and label not in found:
            found.append(label)
    if "in hindi" in lower:
        found.append("prefers Hindi when requested")
    return found[:4]


def _extract_entities(text: str) -> list[str]:
    entities = []
    for token in re.findall(r"\b[A-Z][a-zA-Z0-9_+-]{2,}\b", text):
        if token not in entities:
            entities.append(token)
    for topic in extract_topics(text):
        if topic not in entities:
            entities.append(topic)
    return entities[:6]


def extract_understanding_frame(text: str) -> UnderstandingFrame:
    """Build a structured understanding frame from the user's latest turn."""
    cleaned = " ".join(text.strip().split())
    lower = cleaned.lower()
    user_goal = ""

    goal_patterns = [
        r"(?:can you|could you|please|help me|i need to|i want to)\s+(.+)",
        r"(?:build|create|make|write|find|open|search|show|explain)\s+(.+)",
    ]
    for pattern in goal_patterns:
        match = re.search(pattern, lower)
        if match:
            user_goal = match.group(1).strip(" .?!")
            break

    if not user_goal:
        user_goal = cleaned[:120]

    unresolved = []
    if "?" in cleaned:
        unresolved.append(cleaned)

    return UnderstandingFrame(
        user_goal=user_goal,
        constraints=_extract_constraints(cleaned),
        preferences=_extract_preferences(cleaned),
        entities=_extract_entities(cleaned),
        unresolved_questions=unresolved[:2],
    )


def _maybe_store_memory(user_id: str, record: MemoryRecord, *, semantic: bool = True) -> None:
    records = _load_episodic_memories(user_id)
    dedupe_key = (record.memory_type, record.content.lower())
    existing = {
        (item.get("memory_type", ""), item.get("content", "").lower())
        for item in records[-20:]
        if isinstance(item, dict)
    }
    if dedupe_key in existing:
        return

    records.append(asdict(record))
    _save_episodic_memories(user_id, records)

    if semantic:
        try:
            from memory.knowledge import knowledge_add

            knowledge_add(
                record.content,
                user_id=user_id,
                memory_type=record.memory_type,
                source=record.source,
            )
        except Exception as exc:
            logger.debug("Semantic memory save skipped: %s", exc)


def auto_update_profile(user_id: str, user_text: str) -> None:
    """
    Update profile signals and understanding after every user message.

    This remains lightweight and deterministic so it can run on every turn.
    """
    if not user_text or len(user_text.strip()) < 3:
        return

    profile = _load_profile(user_id)
    changed = False

    topics = extract_topics(user_text)
    if topics:
        freq = profile.setdefault("topic_frequency", {})
        for topic in topics:
            freq[topic] = freq.get(topic, 0) + 1
        changed = True

    emotion = detect_emotion(user_text)
    mood_history = profile.setdefault("mood_history", [])
    mood_history.append({"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "emotion": emotion})
    profile["mood_history"] = mood_history[-30:]
    changed = True

    goals = _extract_goals(user_text)
    if goals:
        existing = set(profile.get("goals", []))
        for goal in goals:
            if goal not in existing:
                profile.setdefault("goals", []).append(goal)
                _maybe_store_memory(
                    user_id,
                    MemoryRecord(goal, "goal", "chat", _now_iso(), {"emotion": emotion}),
                )
                changed = True

    habits = _extract_habits(user_text)
    if habits:
        existing = set(profile.get("habits", []))
        for habit in habits:
            if habit not in existing:
                profile.setdefault("habits", []).append(habit)
                _maybe_store_memory(
                    user_id,
                    MemoryRecord(habit, "habit", "chat", _now_iso(), {"emotion": emotion}),
                )
                changed = True

    frame = extract_understanding_frame(user_text)
    profile["last_understanding"] = asdict(frame)
    changed = True

    preferences = frame.preferences
    if preferences:
        pref_store = profile.setdefault("preferences", {})
        style_pref = None
        if any("concise" in pref for pref in preferences):
            style_pref = "concise"
        elif any("detailed" in pref for pref in preferences):
            style_pref = "detailed"
        elif any("step-by-step" in pref for pref in preferences):
            style_pref = "step_by_step"
        elif any("simple" in pref for pref in preferences):
            style_pref = "simple"
        if style_pref and pref_store.get("response_style") != style_pref:
            pref_store["response_style"] = style_pref
            _maybe_store_memory(
                user_id,
                MemoryRecord(f"User preference: {style_pref}", "preference", "chat", _now_iso()),
            )
            changed = True

    profile["conversation_count"] = profile.get("conversation_count", 0) + 1
    changed = True

    if changed:
        _save_profile(user_id, profile)


def finalize_turn_memory(
    user_id: str,
    user_text: str,
    assistant_text: str = "",
    *,
    action_summaries: list[str] | None = None,
) -> None:
    """Update rolling summaries and high-value episodic memories once a turn is complete."""
    summary = _load_summary(user_id)
    lines = summary.get("summary_lines", [])

    user_line = f"User: {_compress(user_text)}"
    if user_line not in lines[-4:]:
        lines.append(user_line)

    if assistant_text:
        assistant_line = f"Sara: {_compress(assistant_text)}"
        if assistant_line not in lines[-4:]:
            lines.append(assistant_line)

    summary["summary_lines"] = lines[-SUMMARY_MAX_LINES:]
    summary["summary"] = " | ".join(summary["summary_lines"][-6:])
    summary["message_count"] = summary.get("message_count", 0) + 1
    summary["last_updated"] = _now_iso()
    _save_summary(user_id, summary)

    lowered = user_text.lower().strip()
    if lowered.startswith(("actually", "no,", "no ", "that's wrong", "that is wrong")):
        _maybe_store_memory(
            user_id,
            MemoryRecord(f"Correction from user: {_compress(user_text, 160)}", "correction", "chat", _now_iso()),
        )

    if action_summaries:
        detail = ", ".join(action_summaries[:4])
        _maybe_store_memory(
            user_id,
            MemoryRecord(
                f"Completed task for user: {_compress(user_text, 100)} | Actions: {detail}",
                "task",
                "execution",
                _now_iso(),
            ),
            semantic=True,
        )


def retrieve_relevant_memories(user_id: str, query: str, limit: int = 3) -> list[MemoryRecord]:
    """Return relevant episodic memories for the current query."""
    query = (query or "").strip()
    if not query:
        return []

    try:
        from memory.knowledge import search_knowledge_records

        semantic_items = search_knowledge_records(query, user_id=user_id, limit=limit)
        if semantic_items:
            records = []
            for item in semantic_items:
                meta = item.get("metadata", {})
                records.append(
                    MemoryRecord(
                        content=item["document"],
                        memory_type=meta.get("memory_type", "semantic"),
                        source=meta.get("source", "semantic"),
                        timestamp=meta.get("timestamp", ""),
                        metadata=meta,
                    )
                )
            return records[:limit]
    except Exception as exc:
        logger.debug("Semantic retrieval unavailable: %s", exc)

    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for item in _load_episodic_memories(user_id):
        content = item.get("content", "")
        tokens = set(re.findall(r"[a-z0-9]+", content.lower()))
        overlap = len(query_tokens & tokens)
        if overlap:
            scored.append((overlap, item))
    scored.sort(key=lambda row: row[0], reverse=True)

    results = []
    for _, item in scored[:limit]:
        results.append(
            MemoryRecord(
                content=item.get("content", ""),
                memory_type=item.get("memory_type", "episodic"),
                source=item.get("source", "chat"),
                timestamp=item.get("timestamp", ""),
                metadata=item.get("metadata", {}),
            )
        )
    return results


def get_memory_summary(user_id: str) -> str:
    """Return a readable summary of layered memory state."""
    profile = _load_profile(user_id)
    summary = _load_summary(user_id)
    episodes = _load_episodic_memories(user_id)

    if not profile and not summary.get("summary") and not episodes:
        return "🧠 Sara hasn't learned much about you yet. Start chatting!"

    lines = ["🧠 *What Sara Remembers About You*\n"]

    name = profile.get("name")
    if name:
        lines.append(f"👤 Name: *{name}*")

    lang = profile.get("language", "en")
    tz = profile.get("timezone")
    if tz:
        lines.append(f"🌍 Location/TZ: `{tz}` | Language: `{lang}`")

    interests = profile.get("interests", [])
    if interests:
        lines.append(f"❤️ Interests: {', '.join(interests[:6])}")

    freq = profile.get("topic_frequency", {})
    if freq:
        top = sorted(freq.items(), key=lambda item: item[1], reverse=True)[:5]
        lines.append("🔥 Top topics: " + ", ".join(f"{topic} ({count}x)" for topic, count in top))

    facts = profile.get("facts", [])[-5:]
    if facts:
        lines.append(f"📌 Facts: {'; '.join(facts)}")

    goals = profile.get("goals", [])[-3:]
    if goals:
        lines.append(f"🎯 Goals: {'; '.join(goals)}")

    habits = profile.get("habits", [])[-3:]
    if habits:
        lines.append(f"🔄 Habits: {'; '.join(habits)}")

    understanding = profile.get("last_understanding", {})
    if understanding.get("user_goal"):
        lines.append(f"🧭 Current intent pattern: {understanding['user_goal']}")

    if summary.get("summary"):
        lines.append(f"📝 Rolling summary: {_compress(summary['summary'], 180)}")

    if episodes:
        recent = [item.get("content", "") for item in episodes[-3:]]
        lines.append("🗂️ Recent memories: " + " | ".join(_compress(item, 70) for item in recent if item))

    mood_history = profile.get("mood_history", [])
    if mood_history:
        recent = [item["emotion"] for item in mood_history[-10:]]
        dominant = Counter(recent).most_common(1)[0][0]
        lines.append(f"💬 Recent mood pattern: {dominant}")

    convo_count = profile.get("conversation_count", 0)
    if convo_count:
        lines.append(f"📊 Messages exchanged: {convo_count}")

    lines.append("\n_Sara now keeps layered memory: history, summaries, and relevant past tasks._")
    return "\n".join(lines)


def get_rich_context_string(user_id: str, query: str = "") -> str:
    """
    Build an enriched context block to inject into prompts.

    Includes rolling summary, understanding, stable profile signals, and query-aware retrieval.
    """
    profile = _load_profile(user_id)
    summary = _load_summary(user_id)
    lines = []

    if summary.get("summary"):
        lines.append(f"- Rolling summary: {summary['summary']}")

    understanding = profile.get("last_understanding", {})
    if understanding.get("user_goal"):
        lines.append(f"- Last understood goal: {understanding['user_goal']}")
    if understanding.get("constraints"):
        lines.append(f"- Common constraints: {', '.join(understanding['constraints'][:3])}")
    if understanding.get("preferences"):
        lines.append(f"- Style hints: {', '.join(understanding['preferences'][:3])}")

    freq = profile.get("topic_frequency", {})
    if freq:
        top_topics = sorted(freq.items(), key=lambda item: item[1], reverse=True)[:3]
        lines.append(f"- Frequently talks about: {', '.join(topic for topic, _ in top_topics)}")

    goals = profile.get("goals", [])[-2:]
    if goals:
        lines.append(f"- Recent goals: {'; '.join(goals)}")

    habits = profile.get("habits", [])[-2:]
    if habits:
        lines.append(f"- Known habits: {'; '.join(habits)}")

    relevant = retrieve_relevant_memories(user_id, query or understanding.get("user_goal", ""), limit=3)
    if relevant:
        lines.append("- Relevant memories:")
        for item in relevant:
            lines.append(f"  * [{item.memory_type}] {_compress(item.content, 120)}")

    return "\n".join(lines)


def _compress(text: str, limit: int = 120) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."
