"""
integrations/telegram_bot.py — Sara AI Telegram Bot with full onboarding flow.

First-time users go through a ConversationHandler:
  STATE 0 (ASK_NAME)       → ask for name
  STATE 1 (ASK_LANGUAGE)   → ask preferred language
  STATE 2 (ASK_INTERESTS)  → ask 3 things they love
  STATE 3 (ASK_TIMEZONE)   → optional timezone, or skip
  → DONE → save profile, start chatting

Returning users are greeted by name and skip onboarding.
"""

import os
import logging
from dotenv import load_dotenv

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import BadRequest

from agent.agent_loop import process_turn
from agent import build_workflow
from memory.context_manager import clear_history, get_recent_messages
from memory.memory_engine import get_memory_summary
from memory.user_profile import (
    is_onboarded,
    mark_onboarded,
    touch_last_seen,
    get_name,
    set_name,
    set_language,
    set_timezone,
    set_interests,
    get_notes,
    get_profile_summary,
    set_preference,
    set_telegram_info,
)
from brain.personal_trainer import collect_training_data, format_stats_for_user
from brain.trend_analyzer import format_trends_for_user
from brain.persona_model import (
    train_personal_model,
    format_model_status,
    is_training,
    delete_model,
)
from brain.auto_trainer import get_auto_train_status
from brain.dataset_downloader import (
    download_datasets,
    get_download_status,
    clear_public_data,
    list_available,
)
from brain.sara_slm import (
    train_from_scratch as slm_train,
    format_slm_status,
    is_training        as slm_is_training,
    delete_slm,
)
from brain.slm_auto_trainer import get_slm_auto_train_status

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_TEXT_LIMIT = 4096
TELEGRAM_SAFE_TEXT_LIMIT = 3900


def _split_telegram_text(text: str, limit: int = TELEGRAM_SAFE_TEXT_LIMIT) -> list[str]:
    """Split text into Telegram-safe chunks, preferring paragraph and line breaks."""
    text = text or ""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks or [""]


async def _reply_text_safely(message, text: str, *, parse_mode=None, reply_markup=None) -> None:
    """Reply without exceeding Telegram's text limit; attach markup to the last chunk."""
    chunks = _split_telegram_text(text)
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        try:
            await message.reply_text(
                chunk,
                parse_mode=parse_mode,
                reply_markup=reply_markup if is_last else None,
            )
        except BadRequest as exc:
            if parse_mode is None:
                raise
            logger.warning("Telegram rejected formatted message, retrying as plain text: %s", exc)
            await message.reply_text(chunk, reply_markup=reply_markup if is_last else None)

# ── Onboarding states ─────────────────────────────────────────────────────────
ASK_NAME, ASK_LANGUAGE, ASK_INTERESTS, ASK_TIMEZONE = range(4)

LANGUAGE_KEYBOARD = [
    ["English 🇬🇧", "Hindi 🇮🇳"],
    ["Spanish 🇪🇸", "French 🇫🇷"],
    ["German 🇩🇪", "Arabic 🇸🇦"],
    ["Other (I'll type it)"],
]

LANG_MAP = {
    "English 🇬🇧": "en",
    "Hindi 🇮🇳":   "hi",
    "Spanish 🇪🇸":  "es",
    "French 🇫🇷":   "fr",
    "German 🇩🇪":   "de",
    "Arabic 🇸🇦":   "ar",
}

TIMEZONE_KEYBOARD = [
    ["Asia/Kolkata 🇮🇳",    "Asia/Dubai 🇦🇪"],
    ["Europe/London 🇬🇧",   "Europe/Paris 🇫🇷"],
    ["America/New_York 🇺🇸", "America/Los_Angeles 🇺🇸"],
    ["Skip ⏭️"],
]


# ══════════════════════════════════════════════════════════════════════════════
# ONBOARDING CONVERSATION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: /start — check if user needs onboarding."""
    user_id = str(update.effective_user.id)
    tg_name = update.effective_user.first_name or "there"

    touch_last_seen(user_id)

    if is_onboarded(user_id):
        name = get_name(user_id) or tg_name
        await update.message.reply_text(
            f"👋 Welcome back, *{name}*! Great to see you again.\n\n"
            "What can I help you with today? 🚀\n"
            "_(Type /help to see all commands)_",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    # New user → begin onboarding
    await update.message.reply_text(
        f"👋 Hey {tg_name}! I'm *Sara AI* — your personal AI assistant, created by Ritik.\n\n"
        "Before we start, let me get to know you a little — it only takes 30 seconds! 😊\n\n"
        "✏️ *What's your name?* (or what should I call you?)",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State 0 — Save name, ask language."""
    user_id = str(update.effective_user.id)
    name = update.message.text.strip()

    if not name or len(name) > 50:
        await update.message.reply_text("Please enter a valid name (up to 50 characters).")
        return ASK_NAME

    set_name(user_id, name)

    await update.message.reply_text(
        f"Nice to meet you, *{name}*! 🙌\n\n"
        "🌍 *What language do you prefer?*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            LANGUAGE_KEYBOARD, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return ASK_LANGUAGE


async def received_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State 1 — Save language, ask interests."""
    user_id = str(update.effective_user.id)
    raw = update.message.text.strip()
    lang = LANG_MAP.get(raw, raw[:5].lower() if raw != "Other (I'll type it)" else "en")
    set_language(user_id, lang)

    await update.message.reply_text(
        "🎯 *What are you interested in?*\n\n"
        "Tell me 2-3 things you love — separated by commas.\n"
        "_Example: coding, music, fitness_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_INTERESTS


async def received_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State 2 — Save interests, ask timezone."""
    user_id = str(update.effective_user.id)
    raw = update.message.text.strip()
    interests = [i.strip() for i in raw.replace("،", ",").split(",") if i.strip()]

    if not interests:
        await update.message.reply_text("Please list at least one interest, separated by commas.")
        return ASK_INTERESTS

    set_interests(user_id, interests[:10])  # cap at 10

    await update.message.reply_text(
        "⏰ *What's your timezone?*\n_(So I can give you accurate time info)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            TIMEZONE_KEYBOARD, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return ASK_TIMEZONE


async def received_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """State 3 — Save timezone, complete onboarding."""
    user_id = str(update.effective_user.id)
    raw = update.message.text.strip()

    if raw and raw != "Skip ⏭️":
        tz = raw.split(" ")[0]  # strip flag emoji
        set_timezone(user_id, tz)

    mark_onboarded(user_id)
    name = get_name(user_id) or "friend"

    await update.message.reply_text(
        f"🎉 *All set, {name}!* Your profile is saved.\n\n"
        "Here's what Sara can do for you:\n"
        "🌤️ Weather · 📝 Notes · 🧮 Maths · 😄 Jokes\n"
        "💻 Terminal · 📁 Files · 🌐 Web scraping\n"
        "✍️ AI writing · 📧 Email · 🎮 Discord\n"
        "🤖 Browser · 🧠 Knowledge base\n\n"
        "Just chat naturally! Type /help anytime. 🚀",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Let user skip onboarding."""
    user_id = str(update.effective_user.id)
    mark_onboarded(user_id)  # mark done so they aren't asked again
    await update.message.reply_text(
        "No problem! You can always set your profile later with /profile.\n"
        "Type /help to see everything Sara can do! 😊",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def handle_build_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current build progress."""
    user_id = str(update.effective_user.id)
    await update.message.reply_text(build_workflow.get_build_status(user_id), parse_mode="Markdown")


async def handle_cancel_build(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel and reset the current build session."""
    user_id = str(update.effective_user.id)
    build_workflow.reset_session(user_id)
    await update.message.reply_text("❌ Build session cancelled. Say 'build me something' to start a new project!")


async def handle_build_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute or advance to the next build step — called as /next_step."""
    user_id = str(update.effective_user.id)
    session = build_workflow.get_session(user_id)
    if not session or session.get("state") != build_workflow.BuildState.BUILDING:
        await update.message.reply_text("⚠️ No active build in progress.")
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    result = build_workflow.execute_next_step(user_id)
    # Re-attach next step button if still building
    new_session = build_workflow.get_session(user_id)
    if new_session and new_session.get("state") == build_workflow.BuildState.BUILDING:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("▶️ Run next step", callback_data="build_next_step"),
            InlineKeyboardButton("❌ Cancel build",  callback_data="build_cancel"),
        ]])
        await update.message.reply_text(result, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(result, parse_mode="Markdown")


async def handle_build_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses for the build workflow."""
    query   = update.callback_query
    user_id = str(query.from_user.id)
    data    = query.data

    await query.answer()  # dismiss the loading spinner on the button

    if data == "build_approve":
        msg = build_workflow.start_building(user_id)
        # First build step button
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("▶️ Run next step", callback_data="build_next_step"),
            InlineKeyboardButton("❌ Cancel build",  callback_data="build_cancel"),
        ]])
        await query.edit_message_reply_markup(reply_markup=None)   # remove approval buttons
        await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "build_next_step":
        await query.message.chat.send_action(ChatAction.TYPING)
        result = build_workflow.execute_next_step(user_id)
        new_session = build_workflow.get_session(user_id)
        if new_session and new_session.get("state") == build_workflow.BuildState.BUILDING:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("▶️ Run next step", callback_data="build_next_step"),
                InlineKeyboardButton("❌ Cancel build",  callback_data="build_cancel"),
            ]])
            await query.message.reply_text(result, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await query.message.reply_text(result, parse_mode="Markdown")

    elif data == "build_changes":
        build_workflow.mark_awaiting_change(user_id)
        await query.edit_message_reply_markup(reply_markup=None)   # remove old buttons
        await query.message.reply_text(
            "✏️ What would you like to change?\n"
            "_(e.g. 'use Vue instead of React' or 'add a login page')_",
            parse_mode="Markdown",
        )

    elif data == "build_cancel":
        build_workflow.reset_session(user_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ Build session cancelled. Say 'build me something' to start fresh!")


async def handle_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle approval buttons for risky multi-agent actions."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data

    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.chat.send_action(ChatAction.TYPING)

    decision = "yes" if data == "agent_confirm_yes" else "no"
    response = process_turn(user_id, decision, channel="telegram")
    await query.message.reply_text(response.render_text())


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Sara AI — Commands*\n\n"
        "*Profile:*\n"
        "  /start — Welcome / re-run onboarding\n"
        "  /profile — View your saved profile\n"
        "  /myname `NAME` — Change your name\n"
        "  /setlang `en|hi|es|fr` — Change language\n\n"
        "*Memory & Intelligence:*\n"
        "  /memory — Everything Sara remembers about you\n"
        "  /brain — Sara v2 personal AI status\n"
        "  /my\\_trends — Your conversation trends and mood\n"
        "  /train — Train Sara v2 on your data (LoRA)\n"
        "  /auto_train_status — Auto-training status for Sara v2\n"
        "  /train_slm — Train Sara SLM (from-scratch local brain)\n"
        "  /slm_status — Sara SLM model info\n"
        "  /slm_auto_status — Sara SLM auto-training status\n"
        "  /history — Last 6 messages\n"
        "  /notes — Your saved notes\n"
        "  /clear — Clear conversation\n\n"
        "*Try saying:*\n"
        "  • \"weather in Delhi\"\n"
        "  • \"tell me a joke\"\n"
        "  • \"calculate 250 x 4\"\n"
        "  • \"save note: buy milk\"\n"
        "  • \"run dir\"\n"
        "  • \"write email about Python\"\n"
        "  • \"screenshot github.com\"\n"
        "  • \"remember: I drink coffee every morning\"\n"
        "  • \"send telegram: hello!\"\n\n"
        "💡 Just chat naturally — I understand you!",
        parse_mode="Markdown",
    )


async def handle_memory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show everything Sara remembers about the user."""
    user_id = str(update.effective_user.id)
    touch_last_seen(user_id)
    summary = get_memory_summary(user_id)
    await update.message.reply_text(summary, parse_mode="Markdown")


async def handle_brain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Sara v2 personal model status."""
    user_id = str(update.effective_user.id)
    status  = format_model_status(user_id)
    # Also show training data stats
    data_stats = format_stats_for_user(user_id)
    await update.message.reply_text(
        status + "\n\n" + data_stats,
        parse_mode="Markdown",
    )


async def handle_my_trends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user's conversation trends and mood analytics."""
    user_id = str(update.effective_user.id)
    trends  = format_trends_for_user(user_id)
    await update.message.reply_text(trends, parse_mode="Markdown")


async def handle_train(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Collect training data then trigger Sara v2 LoRA fine-tuning."""
    user_id = str(update.effective_user.id)

    if is_training(user_id):
        await update.message.reply_text(
            "🔄 Sara v2 is already training! Please wait for it to finish."
        )
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    # Step 1 — collect data
    await update.message.reply_text(
        "📦 *Step 1/3:* Collecting your conversation data...",
        parse_mode="Markdown",
    )
    n = collect_training_data(user_id)

    if n == 0:
        await update.message.reply_text(
            "📭 Not enough conversation data yet!\n\n"
            "Chat with Sara more, then try /train again.\n"
            "_(Need at least a few back-and-forth messages)_",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"✅ *Step 2/3:* Collected *{n}* training samples from your conversations!",
        parse_mode="Markdown",
    )

    # Step 3 — train (background thread with progress callback)
    sent_msg = await update.message.reply_text(
        "🧠 *Step 3/3:* Starting Sara v2 training...\n"
        "_(This runs in background — you'll get updates here)_",
        parse_mode="Markdown",
    )

    async def send_progress(msg: str, pct: int = 0) -> None:
        try:
            icon = "✅" if pct >= 100 else "🔄"
            bar_filled = round(pct / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            text = f"{icon} *Sara v2 Training* [{bar}] {pct}%\n\n_{msg}_"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception:
            pass

    # Use asyncio-safe callback wrapper
    import asyncio
    loop = asyncio.get_event_loop()

    def sync_callback(msg: str, pct: int = 0) -> None:
        asyncio.run_coroutine_threadsafe(send_progress(msg, pct), loop)

    start_msg = train_personal_model(user_id, callback=sync_callback)
    await update.message.reply_text(start_msg, parse_mode="Markdown")


async def handle_delete_sara_v2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete the Sara v2 personal model for this user."""
    user_id = str(update.effective_user.id)
    delete_model(user_id)
    await update.message.reply_text(
        "🗑️ Sara v2 personal model deleted.\n"
        "Use /train to start fresh!"
    )


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's full saved profile."""
    user_id = str(update.effective_user.id)
    touch_last_seen(user_id)
    summary = get_profile_summary(user_id)
    await update.message.reply_text(summary, parse_mode="Markdown")


async def handle_myname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if not context.args:
        name = get_name(user_id)
        msg = f"👤 Your current name: *{name}*" if name else "👤 No name set. Use /myname YourName"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    name = " ".join(context.args).strip()
    set_name(user_id, name)
    await update.message.reply_text(f"✅ Got it! I'll call you *{name}* 😊", parse_mode="Markdown")


async def handle_setlang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Usage: /setlang en  (or hi, es, fr, de, ar...)")
        return
    lang = context.args[0].strip().lower()
    set_language(user_id, lang)
    await update.message.reply_text(f"🌍 Language set to `{lang}`", parse_mode="Markdown")


async def handle_setpref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a preference: /setpref tone formal"""
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setpref <key> <value>\nExample: /setpref tone formal")
        return
    key, value = context.args[0], " ".join(context.args[1:])
    set_preference(user_id, key, value)
    await update.message.reply_text(f"✅ Set `{key}` = `{value}`", parse_mode="Markdown")


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    messages = get_recent_messages(user_id, n=6)
    if not messages:
        await update.message.reply_text("📭 No history yet. Start chatting!")
        return
    lines = []
    for msg in messages:
        icon = "🧑" if msg["role"] == "user" else "🤖"
        content = msg["content"][:120] + ("..." if len(msg["content"]) > 120 else "")
        lines.append(f"{icon} *{msg['role'].capitalize()}:* {content}")
    await update.message.reply_text(
        "🗂️ *Recent Conversation:*\n\n" + "\n\n".join(lines),
        parse_mode="Markdown",
    )


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    notes = get_notes(user_id)
    if not notes:
        await update.message.reply_text("📭 No notes yet.\n\nTry: \"save note: pick up milk\"")
        return
    lines = "\n".join(f"  {i+1}. {n}" for i, n in enumerate(notes))
    await update.message.reply_text(f"📋 *Your Notes:*\n\n{lines}", parse_mode="Markdown")


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    clear_history(user_id)
    await update.message.reply_text("🧹 Conversation cleared! Fresh start. 😊")


async def handle_auto_train_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Sara v2 auto-training status and next-train countdown."""
    user_id = str(update.effective_user.id)
    status = get_auto_train_status(user_id)
    await update.message.reply_text(status, parse_mode="Markdown")


# ── Sara SLM (from-scratch model) commands ────────────────────────────────────

async def handle_train_slm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/train_slm — build Sara's own brain from scratch (no LLaMA/Mistral)."""
    user_id = str(update.effective_user.id)
    if slm_is_training(user_id):
        await update.message.reply_text("🔄 Sara SLM is already training! I'll notify you when done.")
        return

    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()

    async def send_progress(msg: str, pct: int = 0) -> None:
        try:
            icon = "✅" if pct >= 100 else "🧠"
            bar  = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
            text = f"{icon} *Sara SLM* `[{bar}]` {pct}%\n_{msg}_"
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
            )
        except Exception:
            pass

    def sync_cb(msg: str, pct: int = 0) -> None:
        _asyncio.run_coroutine_threadsafe(send_progress(msg, pct), loop)

    import threading
    t = threading.Thread(
        target=slm_train,
        kwargs={"user_id": user_id, "callback": sync_cb},
        daemon=True,
    )
    t.start()

    await update.message.reply_text(
        "🧠 *Sara SLM training started!*\n\n"
        "Building a 25M parameter model _from scratch_ --\n"
        "no LLaMA, no Mistral, no borrowed weights.\n\n"
        "I'll send progress updates as Sara learns.",
        parse_mode="Markdown",
    )


async def handle_slm_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/slm_status — show Sara SLM model info."""
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_slm_status(user_id), parse_mode="Markdown")


async def handle_delete_slm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/delete_slm — remove Sara SLM weights to free disk space."""
    user_id = str(update.effective_user.id)
    delete_slm(user_id)
    await update.message.reply_text(r"🗑️ Sara SLM weights deleted. Run /train\_slm to retrain.", parse_mode="Markdown")


async def handle_slm_auto_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/slm_auto_status — show Sara SLM auto-training info."""
    user_id = str(update.effective_user.id)
    status = get_slm_auto_train_status(user_id)
    await update.message.reply_text(status, parse_mode="Markdown")


async def handle_dataset_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show which public datasets have been downloaded."""
    user_id = str(update.effective_user.id)
    await update.message.reply_text(get_download_status(user_id), parse_mode="Markdown")


async def handle_download_datasets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /download_datasets [alpaca|dolly|openorca|sharegpt] [max_per]
    Default: all 4 datasets, 500 samples each.
    """
    user_id = str(update.effective_user.id)
    args    = context.args or []

    # Parse optional args: dataset name(s) and max_per
    available_names = [d["name"] for d in list_available()]
    str_args = [str(a) for a in args]
    chosen_list = [a.lower() for a in str_args if a.lower() in available_names]
    chosen: "list[str] | None" = chosen_list if chosen_list else None
    max_per = 500
    for a in str_args:
        if a.isdigit():
            max_per = max(50, min(2000, int(a)))
            break

    label = ", ".join(chosen_list) if chosen_list else "all 4 datasets"
    await update.message.reply_text(
        f"📦 *Starting download: {label}*\n"
        f"Max {max_per} samples per dataset.\n"
        "_I'll send progress updates..._",
        parse_mode="Markdown",
    )

    import asyncio
    loop = asyncio.get_event_loop()

    async def send_progress(msg: str, pct: int = 0) -> None:
        try:
            icon = "✅" if pct >= 100 else "📥"
            bar  = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
            text = f"{icon} *Dataset Download* `[{bar}]` {pct}%\n_{msg}_"
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception:
            pass

    def sync_callback(msg: str, pct: int = 0) -> None:
        asyncio.run_coroutine_threadsafe(send_progress(msg, pct), loop)

    import threading
    t = threading.Thread(
        target=_run_download,
        args=(user_id, chosen, max_per, sync_callback, context.bot, update.effective_chat.id, loop),
        daemon=True,
    )
    t.start()


def _run_download(user_id, chosen, max_per, callback, bot, chat_id, loop) -> None:
    """Background thread: download datasets and notify on completion."""
    import asyncio
    n = download_datasets(user_id, names=chosen, max_per_dataset=max_per, callback=callback)
    if n > 0:
        msg = (
            f"🎉 *Download complete!* Got *{n}* public training samples.\n\n"
            "These will be merged with your personal conversations the next time Sara v2 trains.\n"
            "Run /train to start training now!"
        )
    else:
        msg = "⚠️ Download failed or returned 0 samples. Check your internet connection."
    asyncio.run_coroutine_threadsafe(
        bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown"),
        loop,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER — auto-triggers lite onboarding for first-time users
# ══════════════════════════════════════════════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_message = update.message.text
    tg_name = update.effective_user.first_name or ""

    touch_last_seen(user_id)

    # If not onboarded AND it's their first message → nudge them gently
    if not is_onboarded(user_id):
        mark_onboarded(user_id)  # mark so we don't keep asking
        if tg_name:
            set_name(user_id, tg_name)  # use Telegram display name as default
        await update.message.reply_text(
            f"👋 Hi {tg_name or 'there'}! I saved your basic profile.\n"
            "Use /start to complete a quick setup, or just keep chatting!\n"
        )

    logger.info(f"[{user_id}] {user_message}")
    # Register bot + chat_id so auto-trainer can send Telegram notifications
    set_telegram_info(user_id, context.bot, str(update.effective_chat.id))
    await update.message.chat.send_action(ChatAction.TYPING)
    response = process_turn(user_id, user_message, channel="telegram")
    rendered = response.render_text()

    def _extract_screenshot_paths(text: str) -> list[str]:
        import re
        paths: list[str] = []
        for match in re.finditer(r"^\s*📁\s*Path:\s*`([^`]+)`\s*$", text or "", re.MULTILINE):
            paths.append(match.group(1).strip())
        return paths

    def _strip_screenshot_lines(text: str) -> str:
        import re
        return re.sub(r"^\s*📁\s*Path:\s*`[^`]+`\s*$\n?", "", text or "", flags=re.MULTILINE).strip()

    screenshot_paths = _extract_screenshot_paths(rendered)
    if screenshot_paths:
        import os
        for path in screenshot_paths[:3]:
            try:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        await update.message.reply_photo(photo=f)
            except Exception as exc:
                logger.warning("Could not send screenshot %s: %s", path, exc)
        rendered = _strip_screenshot_lines(rendered)

    # ── If response contains the plan card, attach inline buttons ────────────
    session = build_workflow.get_session(user_id)
    if (
        session
        and session.get("state") == build_workflow.BuildState.AWAITING_APPROVAL
    ):
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Looks great! Build it", callback_data="build_approve"),
            ],
            [
                InlineKeyboardButton("✏️ Change something",     callback_data="build_changes"),
                InlineKeyboardButton("❌ Cancel",                callback_data="build_cancel"),
            ],
        ])
        await _reply_text_safely(update.message, rendered, parse_mode="Markdown", reply_markup=keyboard)
    elif response.requires_confirmation:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Continue", callback_data="agent_confirm_yes"),
                InlineKeyboardButton("❌ Stop", callback_data="agent_confirm_no"),
            ]
        ])
        await _reply_text_safely(update.message, rendered, reply_markup=keyboard)
    else:
        await _reply_text_safely(update.message, rendered)


# ══════════════════════════════════════════════════════════════════════════════
# BOT STARTUP
# ══════════════════════════════════════════════════════════════════════════════

def start_telegram_bot() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # ── Onboarding ConversationHandler ────────────────────────────────────────
    onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", start_onboarding)],
        states={
            ASK_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            ASK_LANGUAGE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_language)],
            ASK_INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_interests)],
            ASK_TIMEZONE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, received_timezone)],
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)],
        allow_reentry=True,
    )

    app.add_handler(onboarding)
    app.add_handler(CommandHandler("help",           handle_help))
    app.add_handler(CommandHandler("profile",        handle_profile))
    app.add_handler(CommandHandler("myname",         handle_myname))
    app.add_handler(CommandHandler("setlang",        handle_setlang))
    app.add_handler(CommandHandler("setpref",        handle_setpref))
    app.add_handler(CommandHandler("history",        handle_history))
    app.add_handler(CommandHandler("notes",          handle_notes))
    app.add_handler(CommandHandler("clear",          handle_clear))
    # Sara v2 (LoRA) commands
    app.add_handler(CommandHandler("memory",              handle_memory))
    app.add_handler(CommandHandler("brain",               handle_brain))
    app.add_handler(CommandHandler("my_trends",           handle_my_trends))
    app.add_handler(CommandHandler("train",               handle_train))
    app.add_handler(CommandHandler("auto_train_status",   handle_auto_train_status))
    app.add_handler(CommandHandler("download_datasets",   handle_download_datasets))
    app.add_handler(CommandHandler("dataset_status",      handle_dataset_status))
    app.add_handler(CommandHandler("delete_sara_v2",      handle_delete_sara_v2))
    # Sara SLM (from-scratch model) commands
    app.add_handler(CommandHandler("train_slm",           handle_train_slm))
    app.add_handler(CommandHandler("slm_status",          handle_slm_status))
    app.add_handler(CommandHandler("delete_slm",          handle_delete_slm))
    app.add_handler(CommandHandler("slm_auto_status",     handle_slm_auto_status))
    # Build workflow commands
    app.add_handler(CommandHandler("build_status",   handle_build_status))
    app.add_handler(CommandHandler("cancel_build",   handle_cancel_build))
    app.add_handler(CommandHandler("next_step",      handle_build_step))
    app.add_handler(CallbackQueryHandler(handle_build_callback, pattern=r"^build_"))
    app.add_handler(CallbackQueryHandler(handle_agent_callback, pattern=r"^agent_confirm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Sara AI bot running...")
    app.run_polling()
