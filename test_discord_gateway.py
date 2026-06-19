"""Regression tests for Discord gateway startup diagnostics."""

import asyncio
import unittest

from gateway.platforms.discord import DiscordAdapter, DiscordConfigurationError, discord


class DiscordGatewayStartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_privileged_intent_failure_is_not_reported_as_timeout(self) -> None:
        adapter = object.__new__(DiscordAdapter)
        adapter._ready_event = asyncio.Event()

        async def rejected_start() -> None:
            raise discord.errors.PrivilegedIntentsRequired(None)

        adapter._bot_task = asyncio.create_task(rejected_start())

        with self.assertRaisesRegex(
            DiscordConfigurationError,
            "enable Message Content Intent",
        ):
            await adapter._wait_for_ready_or_startup_error(timeout=1)

    async def test_timeout_collects_terminal_error_during_client_close(self) -> None:
        adapter = object.__new__(DiscordAdapter)
        adapter._ready_event = asyncio.Event()
        closed = asyncio.Event()

        class FakeClient:
            def is_closed(self) -> bool:
                return False

            async def close(self) -> None:
                closed.set()

        async def rejected_on_close() -> None:
            await closed.wait()
            raise discord.errors.PrivilegedIntentsRequired(None)

        adapter._client = FakeClient()
        adapter._bot_task = asyncio.create_task(rejected_on_close())

        with self.assertRaisesRegex(
            DiscordConfigurationError,
            "enable Message Content Intent",
        ):
            await adapter._wait_for_ready_or_startup_error(timeout=0.01)


if __name__ == "__main__":
    unittest.main()
