# Sara Agent — Bug & Error Report

> Generated: 2026-05-28 | Project: Sara Agent v2.1.0

---

## Status Overview

| Category | Count |
|----------|-------|
| 🔴 CRITICAL (runtime crash) | 2 |
| 🟠 MAJOR (incorrect behavior) | 3 |
| 🟡 MINOR (code quality / tech debt) | 6 |
| ✅ Previously reported — now fixed | 5 |
| ✅ Syntax errors | 0 |

---

## 🔴 CRITICAL — Will crash at runtime

### 1. Naming mismatch: `nexvisora_rate_guard` vs `nous_rate_guard`

- **File on disk**: `.agents/nous_rate_guard.py`
- **Imports reference `agent.nexvisora_rate_guard`** (wrong name):
  - `run_agent.py:11075` — `from agent.nexvisora_rate_guard import ...`
  - `run_agent.py:11769` — `from agent.nexvisora_rate_guard import clear_nexvisora_rate_limit`
  - `run_agent.py:12335` — `from agent.nexvisora_rate_guard import ...`
  - `.agents/auxiliary_client.py:1191` — `from agent.nexvisora_rate_guard import nexvisora_rate_limit_remaining`
- **Impact**: `ModuleNotFoundError: No module named 'agent.nexvisora_rate_guard'` on any Nexvisora provider rate limiting code path.
- **Fix**: Rename file to `nexvisora_rate_guard.py` OR update all 4 imports to `nous_rate_guard`.

### 2. Module-level import in `tools/register_tool.py:297`

```python
from memory.knowledge import knowledge_add, knowledge_search, knowledge_count
```

- **Problem**: This is a **module-level import** (not lazy), so importing `register_tool.py` forces an immediate import of `memory/knowledge.py`, which depends on `chromadb` and `sentence-transformers`. If those aren't installed, **every tool registration crashes**.
- **Impact**: `ModuleNotFoundError` on startup if ChromaDB deps are missing; slows down all imports even when knowledge features aren't used.
- **Fix**: Move import inside the functions that use these symbols (lazy import).

---

## 🟠 MAJOR — Will cause incorrect behavior

### 3. `requirements.txt` missing 5 dependencies from `pyproject.toml`

These packages are declared in `pyproject.toml` under `[project] dependencies` but **missing from `requirements.txt`**:

| Dependency | Usage |
|---|---|
| `httpx` | HTTP client for various tools |
| `fastapi` | Web server / API gateway |
| `uvicorn` | ASGI server for FastAPI |
| `pyyaml` | YAML config parsing |
| `simple-term-menu` | Terminal UI menus |

- **Impact**: `pip install -r requirements.txt` installs an incomplete set of dependencies. Users get `ModuleNotFoundError` on first use of web/API features.
- **Fix**: Add these 5 packages to `requirements.txt`.

### 4. Dead code path — `acp_adapter` import in `sara_cli/main.py:10054`

```python
try:
    from acp_adapter.entry import main as acp_main
    ...
except ImportError:
    print("ACP dependencies not installed.")
```

- **Problem**: `acp_adapter/` directory does **not exist** in the repository. The `sara acp` subcommand is permanently dead code.
- **Documentation references** (all stale): `website/docs/reference/cli-commands.md`, `website/docs/developer-guide/acp-internals.md`, `website/docs/developer-guide/architecture.md`, `website/docs/user-guide/features/acp.md`, `IMPORT_FIXES_STATUS.md`, `LAUNCH_READINESS.md`
- **Fix**: Either create the `acp_adapter/` package or remove all dead code and doc references.

### 5. Stale `IMPORT_FIXES_STATUS.md` — refers to already-resolved issues

- **Claims** 15 remaining `agent.*` import issues in `sara_cli/main.py`, `sara_cli/model_switch.py`, `.agents/model_metadata.py`
- **Reality**: The `agent/__init__.py` compatibility layer (lines 14-21) adds `.agents/` to `__path__`, so `from agent.xxx import yyy` resolves correctly. These are **not actual bugs**.
- **Also lists** `acp_adapter.entry` as a missing module — it never existed.
- **Impact**: Misleads developers into thinking there are unresolved import crashes.
- **Fix**: Update or remove the file.

---

## 🟡 MINOR — Code quality / tech debt

### 6. Unused dependencies in `requirements.txt`

These packages are listed but **never imported** anywhere in the codebase:
- `pyaudio`
- `pycaw`
- `comtypes`

- **Impact**: Unnecessary install footprint (~15MB+).
- **Fix**: Remove unused entries or add the features that need them.

### 7. Empty `__init__.py` files — no public API exports

| File | Contents |
|---|---|
| `brain/__init__.py` | Empty (0 bytes) |
| `memory/__init__.py` | Empty (0 bytes) |
| `integrations/__init__.py` | Empty (0 bytes) |
| `skills/__init__.py` | Empty (0 bytes) |

- **Impact**: These make directories proper Python packages but don't expose convenience imports.
- **Fix**: Add `__all__` and re-exports for a clean public API.

### 8. Empty root `package-lock.json`

- **File**: `package-lock.json` — contains `{"packages": {}}` with no dependencies
- **Impact**: Any Node.js workflow referencing `Gui/dist/src/main/index.js` will fail.
- **Fix**: Either populate properly or remove.

### 9. Voice gateway requirements commented out

- **File**: `voice_gateway/requirements.txt` — STT (`whisper`), TTS (`edge-tts`), and wake word (`pvporcupine`) deps are commented out
- **Impact**: Voice features silently fail with `ModuleNotFoundError` on first use.
- **Fix**: Uncomment and document as optional extras.

### 10. TODO/FIXME/HACK markers in ~31 files

Unresolved markers across tools, gateway, sara_cli, plugins, and root files. See `git grep -n "TODO\|FIXME\|HACK"` for full list.

- **Impact**: Indicates incomplete feature work and missing error handling.
- **Fix**: Audit each marker and resolve or remove.

### 11. Stale documentation files

- `LAUNCH_READINESS.md` — Outdated status checklist, repeats info from IMPORT_FIXES_STATUS.md
- `website/docs/developer-guide/acp-internals.md` — Documents non-existent `acp_adapter/` package
- `website/docs/user-guide/features/acp.md` — References `python -m acp_adapter` which doesn't exist
- **Fix**: Update or remove stale docs.

---

## ✅ Previously reported — now fixed

These items from the original bug report are **resolved**:

| Bug | Status |
|---|---|
| `memory/__init__.py` missing | ✅ Now exists |
| `brain/__init__.py` missing | ✅ Now exists |
| `integrations/__init__.py` missing | ✅ Now exists |
| `skills/__init__.py` missing | ✅ Now exists |
| Missing deps (`aiohttp`, `numpy`, `websockets`) | ✅ All 3 in `requirements.txt` and `pyproject.toml` |
| `display_config.py:182-184` — bare `is True`/`is False` | ✅ Fixed — now uses `isinstance(value, str)` guards |
| `tools/browser_tools.py:302` — bare `except:` | ✅ Changed to `except Exception:` |

---

## ✅ Clean — No issues found

- **Syntax errors**: Zero — all `.py` files pass `py_compile`
- **Circular imports**: Zero — all modules import cleanly
- **Mutable default args**: Zero — no `def f(x=[])` or `def f(x={})`
- **`== None` anti-pattern**: Zero — all use proper `is None`

---

## Recommended Fix Order

1. 🔴 **Rename** `.agents/nous_rate_guard.py` → `.agents/nexvisora_rate_guard.py` OR update 4 import sites
2. 🔴 **Lazy-import** `memory.knowledge` in `tools/register_tool.py:297`
3. 🟠 **Add** `httpx`, `fastapi`, `uvicorn`, `pyyaml`, `simple-term-menu` to `requirements.txt`
4. 🟠 **Remove/implement** dead `acp_adapter` code path
5. 🟠 **Update/remove** stale `IMPORT_FIXES_STATUS.md`
6. 🟡 **Remove** unused `pyaudio`, `pycaw`, `comtypes` from `requirements.txt`
7. 🟡 **Clean up** stale documentation files
8. 🟡 **Audit** TODO/FIXME/HACK markers
