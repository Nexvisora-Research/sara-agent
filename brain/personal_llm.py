"""
brain/personal_llm.py — Sara AI Inference Routing Layer.

Priority chain (first confident non-None wins):
  1. Sara SLM  — fully custom model, trained from scratch (sara_slm.py)
  2. Sara v2   — LoRA fine-tuned TinyLlama (persona_model.py)
  3. Cloud LLMs — Groq / Ollama (handled by caller)

Confidence gate:
  Both local models go through _is_confident() before being returned.
  If the output looks blank, repetitive, incoherent, or too short it is
  treated as "no answer" so the caller falls through to the cloud.

Public API:
  ask_personal(user_id, prompt)           -> str | None
  get_personal_model_status(user_id)      -> str
  is_tool_request(user_input)             -> bool
"""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that indicate the message is a tool/command request that should
# ALWAYS route to the cloud (tools can't be called from local model output)
_TOOL_KEYWORDS = re.compile(
    r"\b(open|play|search|weather|time|reminder|alarm|note|run|install|"
    r"shutdown|restart|volume|screenshot|calendar|email|map|news|clip)\b",
    re.IGNORECASE,
)


def is_tool_request(user_input: str) -> bool:
    """Return True if the question likely needs a system tool, not chat."""
    return bool(_TOOL_KEYWORDS.search(user_input))


def _is_confident(text: str, *, min_len: int = 15) -> bool:
    """
    Basic quality gate — returns False (discard) if the response is:
      • Too short  (< 15 chars)
      • Mostly punctuation / spaces
      • Highly repetitive (word repetition ratio > 50%)
      • Starts with special tokens that leaked through
      • Contains only question marks / acknowledgements
    """
    if not text or len(text.strip()) < min_len:
        return False

    t = text.strip()

    # Reject leaked tokeniser special tokens
    bad_starts = ("<|", "</", "[INST]", "<<SYS>>", "<s>", "[/INST]")
    if any(t.startswith(b) for b in bad_starts):
        return False

    # Reject pure punctuation or whitespace
    if not re.search(r"[a-zA-Z]", t):
        return False

    # Reject trivialised "I don't know / I'm not sure" answers
    # (but keep nuanced uncertain answers that have real content)
    trivial = re.compile(
        r"^(I don.?t know[.!]?|I.?m not sure[.!]?|I cannot|I can.?t help|"
        r"No answer|Sorry\.?|N/A)$",
        re.IGNORECASE,
    )
    if trivial.match(t):
        return False

    # Repetition check: if >60% of words are repeated the model is looping
    words = t.lower().split()
    if len(words) > 4:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.40:
            return False

    return True


def ask_personal(user_id: str, user_input: str) -> "str | None":
    """
    Try Sara's own trained models before any cloud API.

    Returns:
      str   — a confident answer from Sara's own brain
      None  — caller should fall through to cloud/tools
    """
    # Tool requests should always go to cloud (tools need JSON routing)
    if is_tool_request(user_input):
        logger.debug(f"[{user_id}] Tool-request detected — skipping local models")
        return None

    # ── Priority 1: Sara SLM (fully from-scratch model) ─────────────────────
    try:
        from brain.sara_slm import (
            generate as slm_generate,
            is_trained as slm_ready,
            is_training as slm_busy,
        )
        if slm_ready(user_id) and not slm_busy(user_id):
            raw = slm_generate(user_id, user_input)
            # Allow slightly shorter answers from SLM while still gating quality
            if raw and _is_confident(raw, min_len=10):
                result = raw.strip()
                logger.info(
                    f"[{user_id}] Sara SLM answered ({len(result)} chars) ✅"
                )
                return result
            else:
                logger.debug(
                    f"[{user_id}] Sara SLM output rejected by confidence gate"
                )
    except Exception as e:
        logger.debug(f"personal_llm SLM path error: {e}")

    # ── Priority 2: Sara v2 LoRA (TinyLlama fine-tuned) ─────────────────────
    try:
        from brain.persona_model import inference, is_available, is_training
        if is_available() and not is_training(user_id):
            raw = inference(user_id, user_input)
            if raw and _is_confident(raw):
                result = raw.strip()
                logger.info(
                    f"[{user_id}] Sara v2 LoRA answered ({len(result)} chars) ✅"
                )
                return result
            else:
                logger.debug(
                    f"[{user_id}] Sara v2 LoRA output rejected by confidence gate"
                )
    except Exception as e:
        logger.debug(f"personal_llm LoRA path error: {e}")

    # Neither local model could confidently answer → fall through to cloud
    return None


def get_personal_model_status(user_id: str) -> str:
    """Return a Telegram-ready string showing all Sara model statuses."""
    lines = ["🤖 *Sara AI — Local Model Status*\n"]

    # Sara SLM status
    try:
        from brain.sara_slm import format_slm_status
        lines.append("*Sara SLM (from-scratch model):*")
        lines.append(format_slm_status(user_id))
    except Exception:
        lines.append("Sara SLM: unavailable (`pip install torch transformers`)")

    lines.append("")

    # Sara v2 LoRA status
    try:
        from brain.persona_model import format_model_status
        lines.append("*Sara v2 (LoRA fine-tuned):*")
        lines.append(format_model_status(user_id))
    except Exception:
        lines.append("Sara v2 LoRA: unavailable")

    lines.append(
        "\n_Sara uses her own brain first. "
        "Cloud AI (Groq) is only used as a fallback._"
    )
    return "\n".join(lines)
