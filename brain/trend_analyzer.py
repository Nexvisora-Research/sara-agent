"""
brain/trend_analyzer.py — Sara v2 User Trend Analyser.

Reads the user's enriched conversation history and produces
statistics that help:
  1. The user understand their own patterns (/my_trends command)
  2. Sara personalise responses even better

No external dependencies — uses only stdlib.

Public API:
  get_user_trends(user_id)          -> dict
  format_trends_for_user(user_id)   -> str (Telegram-ready)
"""

import json
import os
import re
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "memory", "data")


# ── Common stop-words to ignore when counting topics ─────────────────────────

STOP_WORDS = {
    "i", "me", "my", "the", "a", "an", "is", "it", "its", "in", "on", "at",
    "to", "of", "for", "and", "or", "but", "so", "if", "do", "did", "does",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "will",
    "would", "could", "should", "can", "may", "might", "shall", "you", "your",
    "we", "our", "they", "their", "he", "she", "his", "her", "what", "how",
    "why", "when", "where", "which", "that", "this", "these", "those", "not",
    "no", "yes", "ok", "okay", "hi", "hey", "hello", "thanks", "thank", "please",
    "just", "also", "about", "with", "from", "as", "by", "up", "out", "get",
    "make", "use", "need", "want", "know", "think", "look", "see", "go", "got",
    "like", "good", "great", "really", "very", "some", "more", "now",
}

# ── Simple positive / negative word sets ─────────────────────────────────────

POSITIVE_WORDS = {
    "happy", "great", "love", "awesome", "excellent", "good", "nice", "fantastic",
    "amazing", "wonderful", "brilliant", "excited", "joy", "glad", "thanks",
    "perfect", "cool", "fun", "enjoy", "best",
}

NEGATIVE_WORDS = {
    "sad", "bad", "hate", "terrible", "awful", "horrible", "angry", "upset",
    "annoyed", "frustrated", "broken", "failed", "error", "bug", "crash",
    "problem", "issue", "wrong", "fix", "help", "stuck", "weird", "slow",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_dir(user_id: str) -> str:
    return os.path.join(DATA_DIR, user_id)


def _load_history(user_id: str) -> list:
    path = os.path.join(_user_dir(user_id), "history.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"trend_analyzer: could not load history for {user_id}: {e}")
        return []


def _load_enriched_history(user_id: str) -> list:
    """Try to load enriched history (from memory_engine); fall back to plain history."""
    path = os.path.join(_user_dir(user_id), "history_enriched.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _load_history(user_id)


def _tokenise(text: str) -> list[str]:
    """Lower-case alphabetic tokens, stop-words removed."""
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def _score_emotion(text: str) -> str:
    tokens = set(re.findall(r"[a-z]+", text.lower()))
    pos = len(tokens & POSITIVE_WORDS)
    neg = len(tokens & NEGATIVE_WORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _parse_ts(msg: dict) -> datetime | None:
    """Try to parse a timestamp from an enriched message dict."""
    ts = msg.get("timestamp") or msg.get("ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


# ── Core analysis ─────────────────────────────────────────────────────────────

def get_user_trends(user_id: str) -> dict:
    """
    Analyse the user's conversation history and return a trend dict:
    {
      total_messages, user_messages, sara_messages,
      top_topics: [(word, count), ...],
      mood_counts: {positive, neutral, negative},
      mood_trend: "improving" | "stable" | "declining",
      most_active_hour: int | None,
      avg_message_length: int,
      daily_counts: {date_str: count},
      first_message_date: str | None,
      last_message_date:  str | None,
    }
    """
    history = _load_enriched_history(user_id)

    user_msgs   = [m for m in history if m.get("role") == "user"]
    sara_msgs   = [m for m in history if m.get("role") == "assistant"]

    # ── Topic frequency ───────────────────────────────────────────────────────
    all_tokens: list[str] = []
    for m in user_msgs:
        all_tokens.extend(_tokenise(m.get("content", "")))
    top_topics = Counter(all_tokens).most_common(10)

    # ── Mood counts ───────────────────────────────────────────────────────────
    moods = [_score_emotion(m.get("content", "")) for m in user_msgs]
    mood_counts = Counter(moods)

    # Mood trend: compare first half vs second half
    if len(moods) >= 4:
        mid      = len(moods) // 2
        def _pos_ratio(lst):
            if not lst: return 0
            return lst.count("positive") / len(lst)
        early = _pos_ratio(moods[:mid])
        late  = _pos_ratio(moods[mid:])
        if late - early > 0.1:
            mood_trend = "improving 📈"
        elif early - late > 0.1:
            mood_trend = "declining 📉"
        else:
            mood_trend = "stable ➡️"
    else:
        mood_trend = "not enough data"

    # ── Timestamps ───────────────────────────────────────────────────────────
    hour_counts: Counter = Counter()
    daily_counts: dict[str, int] = defaultdict(int)
    dates_seen: list[datetime] = []

    for m in history:
        dt = _parse_ts(m)
        if dt:
            hour_counts[dt.hour] += 1
            daily_counts[dt.strftime("%Y-%m-%d")] += 1
            dates_seen.append(dt)

    most_active_hour = hour_counts.most_common(1)[0][0] if hour_counts else None
    first_date = min(dates_seen).strftime("%Y-%m-%d") if dates_seen else None
    last_date  = max(dates_seen).strftime("%Y-%m-%d") if dates_seen else None

    # ── Avg message length ────────────────────────────────────────────────────
    lengths  = [len(m.get("content", "")) for m in user_msgs]
    avg_len  = round(sum(lengths) / len(lengths)) if lengths else 0

    return {
        "total_messages":      len(history),
        "user_messages":       len(user_msgs),
        "sara_messages":       len(sara_msgs),
        "top_topics":          top_topics,
        "mood_counts":         dict(mood_counts),
        "mood_trend":          mood_trend,
        "most_active_hour":    most_active_hour,
        "avg_message_length":  avg_len,
        "daily_counts":        dict(daily_counts),
        "first_message_date":  first_date,
        "last_message_date":   last_date,
    }


# ── Formatting ────────────────────────────────────────────────────────────────

def _hour_label(h: int | None) -> str:
    if h is None:
        return "–"
    suffix = "AM" if h < 12 else "PM"
    display = h % 12 or 12
    return f"{display}:00 {suffix}"


def _mini_bar(count: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "░" * width
    filled = round((count / total) * width)
    return "█" * filled + "░" * (width - filled)


def format_trends_for_user(user_id: str) -> str:
    """Return a Telegram-ready, emoji-rich trends summary for the user."""
    t = get_user_trends(user_id)

    if t["total_messages"] == 0:
        return "📊 No conversation data yet — start chatting to build your trends!"

    # Top topics
    topic_lines = ""
    total_tokens = sum(c for _, c in t["top_topics"])
    for word, count in t["top_topics"][:5]:
        bar = _mini_bar(count, total_tokens)
        topic_lines += f"  `{word:<15}` {bar} {count}x\n"

    # Mood breakdown
    mc = t["mood_counts"]
    pos = mc.get("positive", 0)
    neu = mc.get("neutral",  0)
    neg = mc.get("negative", 0)
    total_mood = pos + neu + neg or 1

    mood_block = (
        f"  😊 Positive: {round(pos/total_mood*100)}%\n"
        f"  😐 Neutral:  {round(neu/total_mood*100)}%\n"
        f"  😟 Negative: {round(neg/total_mood*100)}%\n"
        f"  📈 Trend:    {t['mood_trend']}"
    )

    # Active since
    since = f"since {t['first_message_date']}" if t["first_message_date"] else ""

    return (
        f"📊 *Your Sara v2 Trends* {since}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💬 *Conversation Stats*\n"
        f"  Total messages:   *{t['total_messages']}*\n"
        f"  You sent:         {t['user_messages']}\n"
        f"  Sara replied:     {t['sara_messages']}\n"
        f"  Avg msg length:   {t['avg_message_length']} chars\n"
        f"  Most active at:   {_hour_label(t['most_active_hour'])}\n\n"
        f"🔥 *Your Top Topics*\n"
        f"{topic_lines}\n"
        f"😊 *Your Mood Pattern*\n"
        f"{mood_block}\n\n"
        f"_Sara v2 uses these insights to personalise every reply for you._"
    )
