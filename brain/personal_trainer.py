"""
brain/personal_trainer.py — Sara v2 Data Pipeline (v2).

Improvements over v1:
  • Multi-turn conversation chains (up to 3 turns of context per sample)
  • Quality scoring: length, diversity, coherence heuristics
  • Deduplication based on instruction fingerprint
  • User context baked into every system prompt

Public API:
  collect_training_data(user_id)        -> int
  format_stats_for_user(user_id)        -> str
  export_jsonl_path(user_id)            -> str
  get_training_stats(user_id)           -> dict
  clear_training_data(user_id)          -> None
  mark_trained(user_id)                 -> None
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "memory", "data")
MODEL_NAME      = "Sara v2"
JSONL_FILENAME  = "training_data.jsonl"
META_FILENAME   = "training_meta.json"

MIN_INSTRUCTION_LEN  = 8    # chars — skip trivial one-liners
MIN_RESPONSE_LEN     = 20   # chars — skip very short responses
MAX_INSTRUCTION_LEN  = 1500
MAX_RESPONSE_LEN     = 2000

# System prompt template for training samples
SARA_V2_SYSTEM = (
    "You are Sara v2, a warm, witty, and deeply personal AI assistant. "
    "You know this user well — their interests, habits, and communication style. "
    "Always reply naturally, concisely, and like a trusted friend."
)


# ── Paths ──────────────────────────────────────────────────────────────────────

def _user_dir(user_id: str) -> str:
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def export_jsonl_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), JSONL_FILENAME)


def _meta_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), META_FILENAME)


def _history_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), "history.json")


def _profile_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), "profile.json")


# ── Loaders ────────────────────────────────────────────────────────────────────

def _load_history(user_id: str) -> list:
    path = _history_path(user_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _load_profile(user_id: str) -> dict:
    path = _profile_path(user_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ── System prompt builder ──────────────────────────────────────────────────────

def _build_system_prompt(profile: dict) -> str:
    """Build a rich system prompt using the user's saved profile."""
    parts = [SARA_V2_SYSTEM]
    extras = []

    name = profile.get("name")
    if name:
        extras.append(f"The user's name is {name}.")

    interests = profile.get("interests", [])
    if interests:
        extras.append(f"Their interests include: {', '.join(interests[:4])}.")

    facts = profile.get("facts", [])[-3:]
    if facts:
        extras.append("Facts: " + "; ".join(facts) + ".")

    goals = profile.get("goals", [])[-2:]
    if goals:
        extras.append("Goals: " + "; ".join(goals) + ".")

    freq = profile.get("topic_frequency", {})
    if freq:
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
        extras.append("Favourite topics: " + ", ".join(t for t, _ in top) + ".")

    if extras:
        parts.append("\n\nAbout the user: " + " ".join(extras))
    return "".join(parts)


# ── Quality scoring ────────────────────────────────────────────────────────────

def _quality_score(instruction: str, response: str) -> float:
    """
    Return a float 0.0-1.0 for (instruction, response) quality.
    Higher = better training sample.
    """
    score = 1.0

    # Penalise very short responses
    if len(response) < 40:
        score *= 0.5
    elif len(response) < 80:
        score *= 0.8

    # Penalise very long responses (unlikely to be natural chat)
    if len(response) > 1200:
        score *= 0.7

    # Penalise tool-call JSON in response
    stripped = response.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        score *= 0.1

    # Penalise heavy repetition in response
    words = response.lower().split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            score *= 0.5

    # Penalise single-word or emoji-only instructions
    if len(instruction.split()) < 3:
        score *= 0.6

    # Reward multi-sentence responses  
    sentences = re.split(r"[.!?]+", response)
    good_sentences = [s for s in sentences if len(s.strip()) > 10]
    if len(good_sentences) >= 2:
        score *= 1.1  # slight boost

    return min(1.0, score)


QUALITY_THRESHOLD = 0.35   # samples below this are discarded


# ── Deduplication ──────────────────────────────────────────────────────────────

def _fingerprint(text: str) -> str:
    """Normalise and hash text for deduplication."""
    normalised = re.sub(r"\s+", " ", text.lower().strip())[:200]
    return hashlib.md5(normalised.encode()).hexdigest()


# ── Multi-turn chain extractor ─────────────────────────────────────────────────

def _build_samples(history: list, profile: dict) -> list:
    """
    Extract training samples from conversation history using two strategies:

    1. SINGLE-TURN: plain user→assistant pairs (fast, covers all turns)
    2. MULTI-TURN: user→assistant→user→assistant chains (richer context)

    Both are deduplicated and quality-filtered before returning.
    """
    system_text = _build_system_prompt(profile)
    samples     = []
    seen_hashes = set()

    def _add(instruction: str, response: str, ctx_prefix: str = "") -> None:
        instr = (ctx_prefix + instruction).strip() if ctx_prefix else instruction.strip()
        resp  = response.strip()

        # Length guards
        if len(instr) < MIN_INSTRUCTION_LEN or len(instr) > MAX_INSTRUCTION_LEN:
            return
        if len(resp) < MIN_RESPONSE_LEN or len(resp) > MAX_RESPONSE_LEN:
            return

        # Deduplication
        fp = _fingerprint(instr)
        if fp in seen_hashes:
            return
        seen_hashes.add(fp)

        # Quality filter
        if _quality_score(instr, resp) < QUALITY_THRESHOLD:
            return

        samples.append({
            "system":      system_text,
            "instruction": instr,
            "response":    resp,
        })

    # Scan history for adjacent user/assistant pairs
    msgs = history
    for i in range(len(msgs) - 1):
        cur  = msgs[i]
        nxt  = msgs[i + 1]

        if cur.get("role") != "user" or nxt.get("role") != "assistant":
            continue

        u1 = cur.get("content", "").strip()
        a1 = nxt.get("content", "").strip()

        # Strategy 1: plain pair
        _add(u1, a1)

        # Strategy 2: multi-turn — include previous turn as context prefix
        if i >= 2:
            prev_user = msgs[i - 2]
            prev_asst = msgs[i - 1]
            if (prev_user.get("role") == "user"
                    and prev_asst.get("role") == "assistant"):
                pu = prev_user.get("content", "").strip()
                pa = prev_asst.get("content", "").strip()
                if pu and pa:
                    ctx = f"[Earlier] User: {pu}\nSara: {pa}\n\n[Now] "
                    _add(u1, a1, ctx_prefix=ctx)

    return samples


# ── Metadata ───────────────────────────────────────────────────────────────────

def _load_meta(user_id: str) -> dict:
    path = _meta_path(user_id)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_meta(user_id: str, sample_count: int, history_len: int) -> None:
    meta = {
        "model_name":       MODEL_NAME,
        "user_id":          user_id,
        "sample_count":     sample_count,
        "history_length":   history_len,
        "collected_at":     datetime.now(timezone.utc).isoformat(),
        "last_trained":     _load_meta(user_id).get("last_trained"),
        "lora_trained":     _load_meta(user_id).get("lora_trained", False),
        "quality_filtered": True,
        "multi_turn":       True,
    }
    try:
        with open(_meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"personal_trainer: save_meta error: {e}")


# ── Public API ─────────────────────────────────────────────────────────────────

def collect_training_data(user_id: str) -> int:
    history = _load_history(user_id)
    profile = _load_profile(user_id)
    samples = _build_samples(history, profile)

    if not samples:
        logger.info(f"personal_trainer: no samples for {user_id}")
        _save_meta(user_id, 0, len(history))
        return 0

    out_path = export_jsonl_path(user_id)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        logger.info(f"personal_trainer: wrote {len(samples)} samples → {out_path}")
    except OSError as e:
        logger.error(f"personal_trainer: JSONL write error: {e}")
        return 0

    _save_meta(user_id, len(samples), len(history))
    return len(samples)


def get_training_stats(user_id: str) -> dict:
    meta  = _load_meta(user_id)
    jsonl = export_jsonl_path(user_id)
    size_kb = round(os.path.getsize(jsonl) / 1024, 1) if os.path.exists(jsonl) else 0
    return {
        "model_name":     meta.get("model_name", MODEL_NAME),
        "sample_count":   meta.get("sample_count", 0),
        "history_length": meta.get("history_length", 0),
        "collected_at":   meta.get("collected_at", "never"),
        "last_trained":   meta.get("last_trained", "never"),
        "lora_trained":   meta.get("lora_trained", False),
        "quality_filtered": meta.get("quality_filtered", False),
        "multi_turn":     meta.get("multi_turn", False),
        "jsonl_path":     jsonl,
        "jsonl_size_kb":  size_kb,
    }


def mark_trained(user_id: str) -> None:
    meta = _load_meta(user_id)
    meta["last_trained"] = datetime.now(timezone.utc).isoformat()
    meta["lora_trained"] = True
    try:
        with open(_meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"personal_trainer mark_trained error: {e}")


def clear_training_data(user_id: str) -> None:
    for path in [export_jsonl_path(user_id), _meta_path(user_id)]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def format_stats_for_user(user_id: str) -> str:
    s = get_training_stats(user_id)
    _lt = s["last_trained"]
    _ca = s["collected_at"]
    trained_icon = "✅" if s["lora_trained"] else "⏳"
    trained_str  = (_lt[:10] if _lt and _lt != "never" else "Not yet")
    collected    = (_ca[:10] if _ca and _ca != "never" else "never")
    qf = "✅" if s.get("quality_filtered") else "❌"
    mt = "✅" if s.get("multi_turn") else "❌"

    return (
        f"🤖 *{s['model_name']} — Training Data*\n\n"
        f"  📝 Training samples:   *{s['sample_count']}*\n"
        f"  💬 Conversations seen:  {s['history_length']}\n"
        f"  📁 Dataset size:        {s['jsonl_size_kb']} KB\n"
        f"  🗓️ Last collected:      {collected}\n\n"
        f"  {qf} Quality filtered\n"
        f"  {mt} Multi-turn context\n\n"
        f"  {trained_icon} Model trained:   *{trained_str}*\n\n"
        f"_Use /train to start training Sara v2!_"
    )
