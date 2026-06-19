"""Regression tests for gateway systemd service generation."""

import unittest

from sara_cli.gateway import _gateway_systemd_exec_start


class GatewaySystemdUnitTests(unittest.TestCase):
    def test_exec_start_quotes_project_paths_containing_spaces(self) -> None:
        command = _gateway_systemd_exec_start(
            "/home/user/Desktop/Red Code/saraAgent/.venv/bin/python"
        )

        self.assertEqual(
            command,
            '"/home/user/Desktop/Red Code/saraAgent/.venv/bin/python" '
            '"-m" "sara_cli.main" "gateway" "run" "--replace"',
        )

    def test_exec_start_preserves_profile_argument_boundaries(self) -> None:
        command = _gateway_systemd_exec_start(
            "/opt/sara/bin/python",
            "--profile coder",
        )

        self.assertEqual(
            command,
            '"/opt/sara/bin/python" "-m" "sara_cli.main" '
            '"--profile" "coder" "gateway" "run" "--replace"',
        )


if __name__ == "__main__":
    unittest.main()
