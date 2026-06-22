"""Tests for selecting the gateway's source-tree Python interpreter."""

import tempfile
import unittest
from pathlib import Path

from sara_cli.runtime_python import project_venv_python


class GatewayRuntimePythonTests(unittest.TestCase):
    def test_selects_project_venv_when_current_python_is_external(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.touch()

            selected = project_venv_python(
                root,
                current_prefix=Path("/opt/conda"),
            )

            self.assertEqual(selected, python)

    def test_does_not_reexec_when_already_inside_project_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / ".venv"
            python = venv / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.touch()

            selected = project_venv_python(root, current_prefix=venv)

            self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
