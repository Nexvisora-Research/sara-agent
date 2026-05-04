import os
import threading

from dotenv import load_dotenv

from agent.multi_agent import initialize_multi_agent_runtime
from memory.automation_engine import start_scheduler


load_dotenv()


def _read_env_text(name: str) -> str:
    value = (os.getenv(name, "") or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def _read_env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    print("Starting Sara AI...")

    initialize_multi_agent_runtime()
    start_scheduler()

    telegram_token = _read_env_text("TELEGRAM_BOT_TOKEN")
    discord_token = _read_env_text("DISCORD_BOT_TOKEN")
    whatsapp_enabled = _read_env_flag("WHATSAPP_WEBHOOK_ENABLED", default=False)

    if not telegram_token and not discord_token and not whatsapp_enabled:
        raise ValueError(
            "No bot configured. Set TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, or "
            "WHATSAPP_WEBHOOK_ENABLED=true in .env"
        )

    # Lazy imports prevent optional dependency crashes for disabled channels.
    if whatsapp_enabled and not telegram_token and not discord_token:
        from integrations.whatsapp_bot import start_whatsapp_bot

        start_whatsapp_bot()
        return

    if whatsapp_enabled:
        from integrations.whatsapp_bot import run_whatsapp_bot_in_thread

        run_whatsapp_bot_in_thread()

    # If both are configured, run Discord in background and Telegram in foreground.
    if discord_token and telegram_token:
        from integrations.discord_bot import start_discord_bot
        from integrations.telegram_bot import start_telegram_bot

        thread = threading.Thread(target=start_discord_bot, daemon=True, name="discord-bot")
        thread.start()
        start_telegram_bot()
        return

    if discord_token:
        from integrations.discord_bot import start_discord_bot

        start_discord_bot()
        return

    from integrations.telegram_bot import start_telegram_bot

    start_telegram_bot()


if __name__ == "__main__":
    main()
