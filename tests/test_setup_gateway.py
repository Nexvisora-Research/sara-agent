"""Regression tests for the section-specific gateway setup wizard."""

import unittest
from unittest.mock import patch

from sara_cli.setup import setup_gateway


class SetupGatewayTests(unittest.TestCase):
    def test_enter_selects_the_highlighted_platform_for_configuration(self) -> None:
        """The gateway menu configures the selected row before choosing Done."""
        platforms = [
            {"key": "telegram", "emoji": "📱", "label": "Telegram"},
            {"key": "discord", "emoji": "💬", "label": "Discord"},
        ]

        with (
            patch("sara_cli.gateway._all_platforms", return_value=platforms),
            patch("sara_cli.gateway._platform_status", return_value="not configured"),
            patch("sara_cli.gateway._configure_platform") as configure_platform,
            patch(
                "sara_cli.curses_ui.curses_radiolist",
                side_effect=[0, len(platforms)],
            ) as choice,
        ):
            setup_gateway({})

        configure_platform.assert_called_once_with(platforms[0])
        self.assertEqual(choice.call_count, 2)
        self.assertEqual(
            choice.call_args_list[0].args,
            (
                "Select a platform to configure:",
                [
                    "📱 Telegram  (not configured)",
                    "💬 Discord  (not configured)",
                    "Done configuring platforms",
                ],
            ),
        )
        self.assertEqual(
            choice.call_args_list[0].kwargs,
            {"selected": 0, "cancel_returns": len(platforms)},
        )


if __name__ == "__main__":
    unittest.main()
