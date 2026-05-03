"""
brain/auto_trainer.py - Sara v2 Auto-Training Scheduler.

Watches the user's conversation growth and automatically triggers
TinyLlama LoRA fine-tuning in a background thread whenever enough
new messages have accumulated since the last training run.

How it works:
  - After every message, check_and_train() is called from agent_loop.
  - If (messages since last training) >= AUTO_TRAIN_THRESHOLD, fire off training.
  - Progress messages are pushed back to the user via Telegram (bot + chat_id).
  - All model weights stay 100% local — you own Sara v2.

Config (env vars or defaults):
  SARA_AUTO_TRAIN_THRESHOLD   int   default 40   messages before auto-retrain
  SARA_AUTO_TRAIN_MIN_SAMPLES int   default 10   min JSONL pairs needed

Public API:
  check_and_train(user_id, bot=None, chat_id=None)  -> None  (async-safe)
  get_auto_train_status(user_id)                    -> str
  set_threshold(n)                                  -> None
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
AUTO_TRAIN_THRESHOLD   = int(os.getenv("SARA_AUTO_TRAIN_THRESHOLD",   "40"))
AUTO_TRAIN_MIN_SAMPLES = int(os.getenv("SARA_AUTO_TRAIN_MIN_SAMPLES", "10"))

DATA_DIR    = os.path.join(os.path.dirname(__file__), "..", "memory", "data")
STATE_FILE  = "auto_train_state.json"

_fire_lock   = threading.Lock()
_firing: set = set()   # user_ids currently auto-training


# ── State helpers ──────────────────────────────────────────────────────────────

def _state_path(user_id: str) -> str:
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, STATE_FILE)


def _load_state(user_id: str) -> dict:
    path = _state_path(user_id)
    if not os.path.exists(path):
        return {"messages_at_last_train": 0, "last_train_ts": None, "total_trains": 0}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"messages_at_last_train": 0, "last_train_ts": None, "total_trains": 0}


def _save_state(user_id: str, state: dict) -> None:
    try:
        with open(_state_path(user_id), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"auto_trainer: save_state error: {e}")


def _count_messages(user_id: str) -> int:
    hist_path = os.path.join(DATA_DIR, user_id, "history.json")
    if not os.path.exists(hist_path):
        return 0
    try:
        with open(hist_path, "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


# ── Telegram notification helper ───────────────────────────────────────────────

async def _send_tg(bot, chat_id: str, text: str) -> None:
    """Send a Telegram message safely."""
    try:
        await bot.send_message(chat_id=int(chat_id), text=text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"auto_trainer: could not send Telegram msg: {e}")


# ── Background training thread ─────────────────────────────────────────────────

def _run_auto_train(user_id: str, bot, chat_id: str, loop) -> None:
    """Runs in a daemon thread. Collects data, trains, notifies via Telegram."""
    try:
        from brain.personal_trainer import collect_training_data
        from brain.persona_model import train_personal_model, is_available

        if not is_available():
            logger.info("auto_trainer: skipping — torch/transformers not installed")
            return

        # Collect data
        n = collect_training_data(user_id)
        if n < AUTO_TRAIN_MIN_SAMPLES:
            logger.info(f"auto_trainer: only {n} samples — skipping (need {AUTO_TRAIN_MIN_SAMPLES})")
            return

        # Notify start
        if bot and chat_id:
            asyncio.run_coroutine_threadsafe(
                _send_tg(bot, chat_id,
                    f"🤖 *Sara v2 Auto-Training Started!*\n\n"
                    f"I collected *{n}* training samples from our conversations.\n"
                    f"Training TinyLlama in the background... I'll let you know when it's done! 🧠"
                ),
                loop,
            )

        # Progress callback → push to Telegram
        def callback(msg: str, pct: int = 0) -> None:
            if bot and chat_id and pct in (0, 25, 50, 75, 100):
                icon = "✅" if pct >= 100 else "🔄"
                bar  = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                text = f"{icon} *Sara v2* `[{bar}]` {pct}%\n_{msg}_"
                asyncio.run_coroutine_threadsafe(_send_tg(bot, chat_id, text), loop)

        # Train
        start_msg = train_personal_model(user_id, callback=callback)
        logger.info(f"auto_trainer: training started for {user_id}: {start_msg}")

        # Update state
        state = _load_state(user_id)
        state["messages_at_last_train"] = _count_messages(user_id)
        state["last_train_ts"]  = datetime.now(timezone.utc).isoformat()
        state["total_trains"]   = state.get("total_trains", 0) + 1
        _save_state(user_id, state)

    except Exception as e:
        logger.error(f"auto_trainer: error for {user_id}: {e}")
        if bot and chat_id:
            try:
                asyncio.run_coroutine_threadsafe(
                    _send_tg(bot, chat_id, f"⚠️ Sara v2 auto-training hit an error: {e}"),
                    loop,
                )
            except Exception:
                pass
    finally:
        with _fire_lock:
            _firing.discard(user_id)


# ── Public API ─────────────────────────────────────────────────────────────────

def check_and_train(user_id: str, bot=None, chat_id: str = "") -> None:
    """
    Call this after every user message.
    Fires auto-training in a background thread when the threshold is reached.
    bot       : telegram.Bot instance (for push notifications)
    chat_id   : str Telegram chat ID
    """
    # Already training — skip
    with _fire_lock:
        if user_id in _firing:
            return

    state      = _load_state(user_id)
    total_msgs = _count_messages(user_id)
    msgs_since = total_msgs - state.get("messages_at_last_train", 0)

    if msgs_since < AUTO_TRAIN_THRESHOLD:
        return   # not enough new messages yet

    logger.info(
        f"auto_trainer: threshold reached for {user_id} "
        f"({msgs_since} new msgs >= {AUTO_TRAIN_THRESHOLD}) — firing training"
    )

    with _fire_lock:
        _firing.add(user_id)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    t = threading.Thread(
        target=_run_auto_train,
        args=(user_id, bot, chat_id, loop),
        daemon=True,
    )
    t.start()


def get_auto_train_status(user_id: str) -> str:
    """Return a Telegram-ready status string."""
    from brain.persona_model import is_available

    if not is_available():
        return (
            "⚙️ *Sara v2 Auto-Training — Disabled*\n\n"
            "Install training deps to enable:\n"
            "`pip install torch transformers peft datasets accelerate`\n\n"
            "Once installed, Sara v2 will train herself automatically every "
            f"*{AUTO_TRAIN_THRESHOLD}* messages!"
        )

    with _fire_lock:
        training_now = user_id in _firing

    if training_now:
        return "🔄 *Sara v2 Auto-Training is running right now!* I'll notify you when done."

    state      = _load_state(user_id)
    total_msgs = _count_messages(user_id)
    msgs_since = total_msgs - state.get("messages_at_last_train", 0)
    remaining  = max(0, AUTO_TRAIN_THRESHOLD - msgs_since)
    last_ts    = (state.get("last_train_ts") or "")[:10] or "Never"
    trains     = state.get("total_trains", 0)

    return (
        f"🤖 *Sara v2 Auto-Training Status*\n\n"
        f"  Messages since last train: *{msgs_since}*\n"
        f"  Threshold:                  {AUTO_TRAIN_THRESHOLD} messages\n"
        f"  Next train in:              ~{remaining} more messages\n"
        f"  Last trained:               {last_ts}\n"
        f"  Total training runs:        {trains}\n\n"
        f"_Sara v2 trains herself automatically as you chat!_ 🧠"
    )


def set_threshold(n: int) -> None:
    """Override the auto-train threshold at runtime."""
    global AUTO_TRAIN_THRESHOLD
    AUTO_TRAIN_THRESHOLD = max(5, int(n))
    logger.info(f"auto_trainer: threshold set to {AUTO_TRAIN_THRESHOLD}")
