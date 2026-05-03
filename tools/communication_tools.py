"""
tools/communication_tools.py — Communication Tools for Sara AI.

Supports: Telegram, WhatsApp, Discord, Email, and a plugin registry
so ANY new channel can be added with just 3 lines of code.

Config (add to .env):
  TELEGRAM_BOT_TOKEN   = already set
  TELEGRAM_CHAT_ID     = your personal chat ID (get from @userinfobot)
  DISCORD_WEBHOOK_URL  = Discord channel webhook URL
  EMAIL_SENDER         = your gmail address
  EMAIL_PASSWORD       = Gmail app password (not account password)
  EMAIL_RECEIVER       = default receiver email
  WHATSAPP_PHONE       = phone number with country code e.g. +919876543210
"""

import os
import logging
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv()
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# PLUGIN REGISTRY — Add any new channel here in 3 lines
# ══════════════════════════════════════════════════════════════════════════════

_CHANNELS: dict[str, callable] = {}


def register_channel(name: str):
    """Decorator to register a new communication channel."""
    def decorator(fn):
        _CHANNELS[name.lower()] = fn
        return fn
    return decorator


def list_channels() -> str:
    """List all registered communication channels."""
    if not _CHANNELS:
        return "📭 No communication channels registered."
    names = ", ".join(f"**{n}**" for n in _CHANNELS)
    return f"📡 Available channels: {names}"


def send_via_channel(value: str) -> str:
    """
    Send a message via any registered channel.
    Input format: 'channel_name::message'
    Example: 'discord::Hello from Sara!'
    """
    if "::" not in value:
        return (
            "❓ Format: `channel::message`\n"
            f"Available: {', '.join(_CHANNELS.keys()) or 'none configured'}"
        )
    channel, message = value.split("::", 1)
    channel = channel.strip().lower()
    message = message.strip()
    fn = _CHANNELS.get(channel)
    if not fn:
        return (
            f"❌ Unknown channel: `{channel}`\n"
            f"Available: {', '.join(_CHANNELS.keys()) or 'none'}"
        )
    return fn(message)


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL 1 — Telegram (uses existing bot token, sends to your chat)
# ══════════════════════════════════════════════════════════════════════════════

@register_channel("telegram")
def send_telegram_message(text: str) -> str:
    """
    Send a Telegram message to TELEGRAM_CHAT_ID via the Sara bot.
    Get your chat ID: message @userinfobot on Telegram.
    """
    import requests
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    if not TOKEN:
        return "❌ TELEGRAM_BOT_TOKEN not set in .env"
    if not CHAT_ID:
        return (
            "❌ TELEGRAM_CHAT_ID not set in .env\n"
            "💡 Message @userinfobot on Telegram to get your chat ID, then add:\n"
            "   TELEGRAM_CHAT_ID=123456789"
        )

    text = text.strip()
    if not text:
        return "❓ Please provide a message to send."

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return f"📨 Telegram message sent: \"{text[:60]}{'...' if len(text)>60 else ''}\""
        return f"❌ Telegram error: {data.get('description', 'unknown')}"
    except requests.exceptions.Timeout:
        return "⌛ Telegram request timed out."
    except Exception as e:
        return f"❌ Telegram send error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL 2 — WhatsApp (via pywhatkit — opens WhatsApp Web)
# ══════════════════════════════════════════════════════════════════════════════

@register_channel("whatsapp")
def send_whatsapp_message(text: str) -> str:
    """
    Send a WhatsApp message via WhatsApp Web (pywhatkit).
    Requires: pip install pywhatkit
    Set WHATSAPP_PHONE in .env e.g. +919876543210
    """
    PHONE = os.getenv("WHATSAPP_PHONE", "")
    if not PHONE:
        return (
            "❌ WHATSAPP_PHONE not set in .env\n"
            "💡 Add: WHATSAPP_PHONE=+919876543210 (include country code)"
        )

    text = text.strip()
    if not text:
        return "❓ Please provide a message to send."

    try:
        import pywhatkit
    except ImportError:
        return (
            "❌ pywhatkit not installed.\n"
            "Run: `pip install pywhatkit`\n"
            "Also make sure you are logged in to WhatsApp Web in your browser."
        )

    try:
        import datetime
        now = datetime.datetime.now()
        # Schedule 1 minute from now (pywhatkit requirement)
        send_hour = now.hour
        send_min = now.minute + 1
        if send_min >= 60:
            send_min = 0
            send_hour += 1

        pywhatkit.sendwhatmsg(PHONE, text, send_hour, send_min, wait_time=15, tab_close=True)
        return (
            f"📱 WhatsApp message scheduled for {send_hour:02d}:{send_min:02d}\n"
            f"Message: \"{text[:60]}{'...' if len(text)>60 else ''}\"\n"
            "_(WhatsApp Web will open in your browser)_"
        )
    except Exception as e:
        return f"❌ WhatsApp send error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL 3 — Discord Webhook
# ══════════════════════════════════════════════════════════════════════════════

@register_channel("discord")
def send_discord_message(text: str) -> str:
    """
    Send a message to a Discord channel via webhook.
    Set DISCORD_WEBHOOK_URL in .env.
    Get webhook: Channel Settings → Integrations → Webhooks → New Webhook.
    """
    import requests
    WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not WEBHOOK:
        return (
            "❌ DISCORD_WEBHOOK_URL not set in .env\n"
            "💡 Go to Discord → Channel Settings → Integrations → New Webhook\n"
            "   Then add: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..."
        )

    text = text.strip()
    if not text:
        return "❓ Please provide a message to send."

    try:
        resp = requests.post(
            WEBHOOK,
            json={"content": text, "username": "Sara AI"},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            return f"🎮 Discord message sent: \"{text[:60]}{'...' if len(text)>60 else ''}\""
        return f"❌ Discord error: HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return "⌛ Discord request timed out."
    except Exception as e:
        return f"❌ Discord send error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL 4 — Email (Gmail SMTP)
# ══════════════════════════════════════════════════════════════════════════════

@register_channel("email")
def send_email(value: str) -> str:
    """
    Send an email via Gmail SMTP.
    Input: just the message body (uses EMAIL_RECEIVER from .env),
           or 'to@email.com::subject::body' for full control.

    .env config:
      EMAIL_SENDER   = yourgmail@gmail.com
      EMAIL_PASSWORD = your_app_password  (not account password)
      EMAIL_RECEIVER = default_receiver@gmail.com

    💡 Gmail App Password: myaccount.google.com → Security → App Passwords
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    SENDER   = os.getenv("EMAIL_SENDER", "")
    PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    RECEIVER = os.getenv("EMAIL_RECEIVER", "")

    if not SENDER or not PASSWORD:
        return (
            "❌ Email not configured in .env\n"
            "💡 Add these to .env:\n"
            "   EMAIL_SENDER=yourgmail@gmail.com\n"
            "   EMAIL_PASSWORD=your_app_password\n"
            "   EMAIL_RECEIVER=receiver@gmail.com"
        )

    # Parse input: "to::subject::body" or just "body"
    parts = value.split("::")
    if len(parts) == 3:
        to_addr, subject, body = parts[0].strip(), parts[1].strip(), parts[2].strip()
    elif len(parts) == 2:
        to_addr = RECEIVER or parts[0].strip()
        subject, body = parts[0].strip(), parts[1].strip()
    else:
        to_addr = RECEIVER
        subject = "Message from Sara AI"
        body = value.strip()

    if not to_addr:
        return "❌ No recipient. Set EMAIL_RECEIVER in .env or use format: 'to@email.com::subject::body'"

    try:
        msg = MIMEMultipart()
        msg["From"]    = SENDER
        msg["To"]      = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SENDER, PASSWORD)
            server.send_message(msg)

        return (
            f"📧 Email sent!\n"
            f"  To: {to_addr}\n"
            f"  Subject: {subject}\n"
            f"  Preview: \"{body[:80]}{'...' if len(body)>80 else ''}\""
        )
    except smtplib.SMTPAuthenticationError:
        return (
            "❌ Gmail authentication failed.\n"
            "💡 Make sure you are using an App Password, not your regular password.\n"
            "   Generate at: myaccount.google.com → Security → App Passwords"
        )
    except smtplib.SMTPException as e:
        return f"❌ SMTP error: {e}"
    except Exception as e:
        return f"❌ Email send error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CHANNEL 5 — Slack Webhook
# ══════════════════════════════════════════════════════════════════════════════

@register_channel("slack")
def send_slack_message(text: str) -> str:
    """
    Send a message to a Slack channel via Incoming Webhook.
    Set SLACK_WEBHOOK_URL in .env.
    Get webhook: api.slack.com/apps → Your App → Incoming Webhooks.
    """
    import requests
    WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
    if not WEBHOOK:
        return (
            "❌ SLACK_WEBHOOK_URL not set in .env\n"
            "💡 Go to api.slack.com/apps → Incoming Webhooks → Activate\n"
            "   Then add: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..."
        )

    text = text.strip()
    if not text:
        return "❓ Please provide a message to send."

    try:
        resp = requests.post(WEBHOOK, json={"text": f"🤖 Sara AI: {text}"}, timeout=10)
        if resp.text == "ok":
            return f"💬 Slack message sent: \"{text[:60]}{'...' if len(text)>60 else ''}\""
        return f"❌ Slack error: {resp.text}"
    except Exception as e:
        return f"❌ Slack send error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# EASY PLUGIN — Add ANY new channel in 3 lines (example):
#
# @register_channel("myapp")
# def send_myapp_message(text: str) -> str:
#     # your logic here
#     return "✅ Sent!"
#
# That's it — it's immediately available as a tool.
# ══════════════════════════════════════════════════════════════════════════════
