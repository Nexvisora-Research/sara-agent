"""Resolve sara_HOME for standalone skill scripts.

Skill scripts may run outside the sara process (e.g. system Python,
nix env, CI) where ``sara_constants`` is not importable.  This module
provides the same ``get_sara_home()`` and ``display_sara_home()``
contracts as ``sara_constants`` without requiring it on ``sys.path``.

When ``sara_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``sara_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``sara_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from sara_constants import display_sara_home as display_sara_home
    from sara_constants import get_sara_home as get_sara_home
except (ModuleNotFoundError, ImportError):

    def get_sara_home() -> Path:
        """Return the sara home directory (default: ~/.sara).

        Mirrors ``sara_constants.get_sara_home()``."""
        val = os.environ.get("sara_HOME", "").strip()
        return Path(val) if val else Path.home() / ".sara"

    def display_sara_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``sara_constants.display_sara_home()``."""
        home = get_sara_home()
        try:
            return "~/" + str(home.relative_to(Path.home()))
        except ValueError:
            return str(home)
