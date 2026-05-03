"""
integrations/discord_bot.py — Discord bot integration for Sara AI.

This is separate from Discord webhooks:
- Webhook (tools/communication_tools.py) can only SEND messages.
- Bot token (this file) enables Sara to READ and REPLY to channel messages.
"""

import asyncio
import logging
import os
import re

import discord
from dotenv import load_dotenv

from agent.agent_loop import process_turn


logger = logging.getLogger(__name__)
load_dotenv()


def _safe_int(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _split_message(text: str, limit: int = 1900) -> list[str]:
    """Split long replies so they fit Discord's 2000-char limit."""
    text = text or ""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


class SaraDiscordClient(discord.Client):
    def __init__(self, *, allowed_channel_id: int | None, **kwargs):
        super().__init__(**kwargs)
        self.allowed_channel_id = allowed_channel_id

    async def on_ready(self) -> None:
        logger.info("Discord bot logged in as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.allowed_channel_id and message.channel.id != self.allowed_channel_id:
            return

        user_text = (message.content or "").strip()
        if not user_text:
            return

        user_id = f"discord_{message.author.id}"

        try:
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: process_turn(user_id, user_text, channel="discord"),
                )
                reply = response.render_text()

            paths = [m.group(1).strip() for m in re.finditer(r"^\s*📁\s*Path:\s*`([^`]+)`\s*$", reply or "", re.MULTILINE)]
            cleaned = re.sub(r"^\s*📁\s*Path:\s*`[^`]+`\s*$\n?", "", reply or "", flags=re.MULTILINE).strip()

            # Attach screenshots first (best-effort)
            for path in paths[:3]:
                try:
                    if os.path.exists(path):
                        await message.reply(file=discord.File(path), mention_author=False)
                except Exception as exc:
                    logger.warning("Could not attach screenshot %s: %s", path, exc)

            reply = cleaned or reply

            for chunk in _split_message(reply):
                await message.reply(chunk, mention_author=False)
        except Exception as exc:
            logger.exception("Discord message handling failed: %s", exc)
            await message.reply("⚠️ Sorry, I hit an error while processing that.", mention_author=False)


def start_discord_bot() -> None:
    """Start Discord bot polling loop using DISCORD_BOT_TOKEN."""
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not set in .env")

    allowed_channel_id = _safe_int(os.getenv("DISCORD_CHANNEL_ID", ""))

    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True
    intents.message_content = True

    client = SaraDiscordClient(intents=intents, allowed_channel_id=allowed_channel_id)
    try:
        client.run(token, log_handler=None)
    except discord.errors.PrivilegedIntentsRequired as exc:
        raise RuntimeError(
            "Discord rejected the bot because Message Content Intent is not enabled. "
            "Open the Discord Developer Portal, select your application, go to Bot, and enable "
            "Message Content Intent. Then restart Sara."
        ) from exc
