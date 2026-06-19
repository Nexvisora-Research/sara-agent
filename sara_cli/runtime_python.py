"""Interpreter selection helpers for source-tree CLI entrypoints."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_venv_python(
    project_root: Path,
    *,
    current_prefix: Path | None = None,
) -> Path | None:
    """Return the project venv interpreter when the current Python is outside it."""
    venv_dir = project_root / ".venv"
    prefix = Path(current_prefix or sys.prefix)
    try:
        if prefix.resolve() == venv_dir.resolve():
            return None
    except OSError:
        if prefix == venv_dir:
            return None

    candidates = (
        venv_dir / "Scripts" / "python.exe",
        venv_dir / "bin" / "python",
        venv_dir / "bin" / "python3",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def reexec_gateway_in_project_venv(project_root: Path, script_path: Path) -> None:
    """Re-exec a source gateway command with the repository's virtualenv."""
    python = project_venv_python(project_root)
    if python is None:
        return

    os.environ["VIRTUAL_ENV"] = str(project_root / ".venv")
    os.environ["PATH"] = f"{python.parent}{os.pathsep}{os.environ.get('PATH', '')}"
    os.execv(
        str(python),
        [str(python), str(script_path), *sys.argv[1:]],
    )
