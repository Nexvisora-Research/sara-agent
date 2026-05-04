"""Compatibility package for `agent.*` modules.

This project keeps many agent modules under the hidden `.agents/` directory.
Expose that directory as part of the `agent` package so imports like
`agent.model_metadata` continue to work.
"""

from __future__ import annotations

import sys
from pathlib import Path


_AGENTS_DIR = Path(__file__).resolve().parent.parent / ".agents"

if _AGENTS_DIR.is_dir():
    _agents_dir_str = str(_AGENTS_DIR)
    if _agents_dir_str not in __path__:
        __path__.append(_agents_dir_str)
    if _agents_dir_str not in sys.path:
        sys.path.insert(0, _agents_dir_str)
