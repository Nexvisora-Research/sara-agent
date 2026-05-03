import os
import threading

from dotenv import load_dotenv

from integrations.discord_bot import start_discord_bot
from integrations.whatsapp_bot import run_whatsapp_bot_in_thread, start_whatsapp_bot
from integrations.telegram_bot import start_telegram_bot
from agent.multi_agent import initialize_multi_agent_runtime
from memory.automation_engine import start_scheduler


load_dotenv()

def main():
    print("Starting Sara AI...")
    initialize_multi_agent_runtime()
    start_scheduler()
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    discord_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    whatsapp_enabled = os.getenv("WHATSAPP_WEBHOOK_ENABLED", "false").lower() in {"1", "true", "yes", "on"}

    if not telegram_token and not discord_token and not whatsapp_enabled:
        raise ValueError(
            "No bot configured. Set TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, or WHATSAPP_WEBHOOK_ENABLED=true in .env"
        )

    if whatsapp_enabled and not telegram_token and not discord_token:
        start_whatsapp_bot()
        return

    if whatsapp_enabled:
        run_whatsapp_bot_in_thread()

    # If both are configured, run Discord in background and Telegram in foreground.
    if discord_token and telegram_token:
        t = threading.Thread(target=start_discord_bot, daemon=True, name="discord-bot")
        t.start()
        start_telegram_bot()
        return

    if discord_token:
        start_discord_bot()
        return

    start_telegram_bot()

if __name__ == "__main__":
    main()
