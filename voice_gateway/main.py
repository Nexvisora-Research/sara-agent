"""Voice Gateway entry point.

Starts the FastAPI server that bridges Flutter voice assistant to Sara Agent.

Usage:
    python -m voice_gateway.main
    # or
    python voice_gateway/main.py
"""

import sys
from pathlib import Path
from importlib.util import find_spec

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _missing_required_packages() -> list[str]:
    """Return required packages that are not importable in this interpreter."""
    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "httpx": "httpx",
        "pydantic": "pydantic",
        "python-multipart": "multipart",
    }
    return [
        package
        for package, module in required.items()
        if find_spec(module) is None
    ]


def _print_dependency_help(missing: list[str]) -> None:
    req_file = _project_root / "voice_gateway" / "requirements.txt"
    print(
        "Sara Voice Gateway cannot start because required packages are missing.",
        file=sys.stderr,
    )
    print(f"Missing: {', '.join(missing)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Install them in a project virtual environment, then run again:", file=sys.stderr)
    print("  python -m venv .venv", file=sys.stderr)
    print("  . .venv/bin/activate", file=sys.stderr)
    print(f"  pip install -r {req_file}", file=sys.stderr)
    print("  python -m voice_gateway.main", file=sys.stderr)


def main():
    """Start the Voice Gateway server."""
    missing = _missing_required_packages()
    if missing:
        _print_dependency_help(missing)
        sys.exit(2)

    from voice_gateway.server import start
    start()


if __name__ == "__main__":
    main()
