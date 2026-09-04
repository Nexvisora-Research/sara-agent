# Bug Report — saraAgent

## 1. `NameError` in `build_workflow.py` when LLM plan generation raises

**File:** `agent/build_workflow.py:172-178`

**Severity:** High (crash)

**Description:** In `_transition_to_planning()`, the `raw` variable is assigned inside the `try` block at line 172. If `ask_ai_smart(prompt)` itself raises an exception (network error, all providers down, etc.), `raw` is never assigned. The `except` block at line 177-178 then references `raw` in the log message (`f"Raw: {raw!r}"`), causing a cascading `NameError` that prevents the fallback plan from being used.

```python
try:
    raw = ask_ai_smart(prompt).strip()    # <-- might raise
    raw = re.sub(...)
    raw = re.sub(...)
    plan = json.loads(raw)
except (json.JSONDecodeError, Exception) as e:
    logger.error(f"Plan generation failed: {e}\nRaw: {raw!r}")  # <-- NameError if ask_ai_smart raised
```

**Fix:** Assign `raw = ""` before the `try` block, or guard the reference with `getattr`.

**Status: ✅ Fixed** — Initialized `raw = ""` before the `try` block at `build_workflow.py:171`.

---

## 2. Dead-code intent classification in `agent_loop.py`

**File:** `agent/agent_loop.py:232-233`

**Severity:** Medium (logic bug)

**Description:** `_classify_intent()` classifies inputs `"coding time"`, `"free time"`, `"movie time"`, `"study time"`, `"gaming time"`, `"meeting time"`, and `"editing time"` as `Intent.SIMPLE_TOOL`. However, `_handle_simple_tool_intent()` has no matching handler for any of these phrases, so it returns `None`. The response falls through to subsequent intent handlers, which may produce unexpected behavior.

```python
if lower in {"coding time", "free time", "movie time", "study time",
              "gaming time", "meeting time", "editing time"}:
    return Intent.SIMPLE_TOOL
```

**Fix:** Either remove these from the intent classifier or add corresponding handlers.

**Status: ✅ Fixed** — Removed dead intent classification at `agent_loop.py:232-233`.

---

## 3. `SMALL_TALK` intent returns hardcoded string instead of using local LLM

**File:** `agent/agent_loop.py:756-763`

**Severity:** Medium (feature not working as documented)

**Description:** When the intent is classified as `SMALL_TALK`, the handler returns a hardcoded response `"Hey! What can I help you with? 😊"` instead of invoking the personal/local LLM (`ask_personal()`). The architecture document (`MAIN_LOOP_ARCHITECTURE.md`) specifies that small talk should route to `brain/personal_llm.py:ask_personal()` for fast local inference.

```python
if intent is Intent.SMALL_TALK:
    return _respond_and_store(
        user_id, user_input,
        AgentResponse(status="final", final_text="Hey! What can I help you with? 😊"),
        channel=channel,
    )
```

**Fix:** Route to `ask_personal()` instead of returning a hardcoded string.

**Status: ✅ Fixed** — SMALL_TALK now calls `ask_personal()` at `agent_loop.py:757`.

---

## 4. Dead code: `_build_desktop_routine_plan` always returns `None`

**File:** `agent/agent_loop.py:351-352`

**Severity:** Low (dead code)

**Description:** `_build_desktop_routine_plan()` is defined but always returns `None` and is never referenced anywhere in the codebase.

```python
def _build_desktop_routine_plan(user_input: str) -> ExecutionPlan | None:
    return None
```

**Fix:** Remove the stub or implement it.

**Status: ✅ Fixed** — Removed dead `_build_desktop_routine_plan` function at `agent_loop.py:351-352`.

---

## 5. Dead code: local `set_reminder` shadowed by import

**File:** `tools/register_tool.py:76-77, 324`

**Severity:** Low (dead code)

**Description:** A local `set_reminder()` function is defined at line 76 that simply returns a string. At line 324, `set_reminder` is imported from `tools.reminder_tools`, which overwrites the local definition. The local function is never used.

```python
def set_reminder(text: str) -> str:
    return f"⏰ Reminder set: '{text}'"

# ... lines later ...
from tools.reminder_tools import set_reminder, list_reminders  # overwrites local definition
```

**Fix:** Remove the unused local definition.

**Status: ✅ Fixed** — Removed unused local `set_reminder` stub at `register_tool.py:76-77`.

---

## 6. Heuristic planner `_split_segments` over-splits on `" and "`

**File:** `agent/planner.py:441-443`

**Severity:** Medium (incorrect behavior)

**Description:** `_split_segments()` splits user input on `" and "`, `" then "`, and `","`. This incorrectly splits phrases like `"research and development"` or `"design and implement"` into separate segments, even when they describe a single concept. The heuristic planner then creates unnecessary tool calls for fragments.

```python
def _split_segments(text: str) -> list[str]:
    parts = re.split(r"\bthen\b|,| and ", text, flags=re.IGNORECASE)
```

**Fix:** Use a more nuanced split that joins coordinator-connected concepts, or use LLM-based segmentation for the heuristic fallback.

**Status: ✅ Fixed** — Changed `_split_segments` to split on `" then "` and `,` only, not bare `" and "` at `planner.py:441`.

---

## 7. `_handle_simple_tool_intent()` may match "smart_open_app" for app install requests that aren't app installs

**File:** `agent/agent_loop.py:300-308`

**Severity:** Low (logic)

**Description:** The `_INSTALL_APP_RE` regex at line 181 matches patterns like `"install app <name>"`. But in `_handle_simple_tool_intent`, the matched group is passed to `smart_open_app` which both opens AND potentially installs apps. There's no validation that the "app" is actually installable or exists. This is a minor UX issue but could produce confusing results.

**Status: ✅ Fixed** — Added app name validation with regex at `agent_loop.py:304`.

---

## 8. `process_turn` stores response before checking intent handlers, causing duplicate memory storage

**File:** `agent/agent_loop.py:636-802`

**Severity:** Low (redundant writes)

**Description:** `add_message()` is called at line 637 at the very start of `process_turn()` for the user message. Then `_respond_and_store()` at each return point calls both `add_message()` (for assistant) and `finalize_turn_memory()`. There is no early-exit guard — every path through the function stores the user message, even when a state handler processes it immediately. This is by design but means utils like trivial corrections always generate a full memory write cycle.

---

## 9. `execute_plan` allows unfinished plans to silently succeed

**File:** `agent/planner.py:119-188`

**Severity:** Low (logic)

**Description:** In `execute_plan()`, the `while remaining:` loop breaks when `blocked` subtasks exist (line 163) or when `executable` is empty (line 167). However, if not all subtasks were processed (e.g., some were skipped due to dependency failures), the function still returns `results` with status fields but no overall "partial completion" flag. The caller (`_run_structured_plan`) passes these results to `review_execution()` which does detect partial failures, but the planner itself has no concept of incomplete execution.

**Status: ✅ Fixed** — Added `partial_completion` flag returned as 4th tuple element from `execute_plan()` at `planner.py`.

---

## 10. `InteractiveShoppingState` has mutable defaults with no `field(default_factory=...)`

**Files:** `agent/agent_loop.py:60-69`

**Severity:** Low (defensive)

**Description:** `InteractiveShoppingState` is a `@dataclass` with default string values that are safe. However, Python dataclass best practice recommends using `field(default_factory=...)` for mutable types. The current fields are all strings/ints, so this is not a runtime bug, but could become one if mutable fields are added later.

---

## 11. `_SMALL_TALK_RE` matches `"hi"` at word boundaries but `"hi"` matches single letters

**File:** `agent/agent_loop.py:156-159`

**Severity:** Low

**Description:** The regex `r"^(hi+|hey+|hello|howdy|hiya|yo|sup|...)"` uses `^` anchor but `re.match()` already anchors at the start. The `^` is redundant. Not a functional bug, but the pattern `hi+` matches `"h"` followed by one or more `"i"` characters, meaning "hiiii" matches but "h" alone doesn't. This is correct.

**Pattern:**
```python
_SMALL_TALK_RE = re.compile(
    r"^(hi+|hey+|hello|howdy|hiya|yo|sup|what'?s up|how are you"
    r"|good (morning|afternoon|evening|night))[\s!?.]*$",
    re.IGNORECASE,
)
```

Note: `"hiiii"` matches, `"hi"` matches, `"h"` doesn't — correct.

**Status: ✅ Fixed** — Removed redundant `^` anchor at `agent_loop.py:156`.

---

## 12. `core/agents.py:DefaultSpecializedAgent.run` always succeeds without real work

**File:** `core/agents.py:97-111`

**Severity:** Medium (safety net issue)

**Description:** The `_DefaultSpecializedAgent` (base for `PlannerAgent`, `ResearchAgent`, `CodingAgent`, etc.) always returns a success response with a hardcoded message. If a production agent fails to register its handler override, it silently succeeds with fake output instead of raising or reporting an error.

```python
async def run(self, task, context):
    await context.report_progress(10, f"{self.role.value} agent accepted task")
    ...
    return {"title": task.title, "description": task.description, ...}
```

**Fix:** The default `run()` should raise `NotImplementedError` to ensure specialized agents implement real behavior.

**Status: ✅ Fixed** — `_DefaultSpecializedAgent.run()` now raises `NotImplementedError` at `core/agents.py:100`.

---

## 13. `_infer_tool_calls` uses `text` instead of `lower` for some checks

**File:** `agent/planner.py:458-459`

**Severity:** Low (inconsistent)

**Description:** In `_infer_tool_calls()`, `lower = text.lower().strip()` is computed at line 447, but subsequent code at line 459 calls `text.lower()` again instead of reusing `lower`:

```python
if "weather in " in lower:
    city = text.lower().split("weather in ", 1)[1].strip()  # should use `lower`
```

Not a functional bug (same result) but wastes computation and is inconsistent with the rest of the function.

**Status: ✅ Fixed** — Changed to use cached `lower` variable at `planner.py:459`.

---

## 14. `agent_loop.py` imports `re` and `os` inside `_handle_interactive_shopping`

**File:** `agent/agent_loop.py:491-492`

**Severity:** Low (style/performance)

**Description:** `import re` and `import os` are repeated inside the function body even though both modules are already imported at the top of the file. Wasteful on every call.

```python
def _handle_interactive_shopping(...):
    from tools.browser_tools import ...
    import re    # already imported at line 13
    import os    # already imported at line 12
```

**Fix:** Remove the redundant local imports.

**Status: ✅ Fixed** — Removed redundant `import re` and `import os` from function body at `agent_loop.py:492-493`.

---

## 15. Memory compaction: `memory_engine.py` and `context_manager.py` both define `DATA_DIR` to `memory/data/`

**Files:** `memory/context_manager.py:9`, `memory/memory_engine.py:23`, `memory/user_profile.py:27`

**Severity:** Low (architectural)

**Description:** All three memory modules define `DATA_DIR = os.path.join(os.path.dirname(__file__), "data")` independently, all resolving to `memory/data/`. While this works (each module uses its own subdirectory structure under `data/<user_id>/`), the redundancy makes it easy to accidentally break the convention. A shared constant would be cleaner.

**Status: ✅ Fixed** — Created shared `memory/__init__.py` with centralized `DATA_DIR` constant; all three modules now import it.

---

## 16. Command injection via unsanitized f-string in `_open_url_in_browser` on Windows

**File:** `tools/web_tools.py:35-37`

**Severity:** **High** (security)

**Description:** `_open_url_in_browser()` constructs a Windows shell command using an f-string with `shell=True`, but the `url` parameter (originating from LLM-generated tool calls) is never sanitized or shell-quoted. A URL containing `"`, `;`, `|`, `&`, or backticks can break out of the double-quote context and execute arbitrary shell commands.

```python
subprocess.Popen(
    f'start "" "{url}"',       # <-- url unsanitized
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

**Fix:** Pass `url` as a list argument or use `shlex.quote(url)`.

**Status: ✅ Fixed** — Changed to `["start", "", url]` list argument at `web_tools.py:35`.

---

## 17. Command injection via unsanitized f-string in `_open_windows` on Windows

**File:** `tools/system_tools.py:380-386`

**Severity:** **High** (security)

**Description:** `_open_windows()` uses the identical insecure pattern with `executable`. When the app name is not found in `APP_MAP`, the raw user-provided name is passed through via `APP_MAP.get(name, name)`, allowing shell metacharacter injection.

```python
subprocess.Popen(
    f'start "" "{executable}"',
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
```

**Fix:** Use list argument form or `shlex.quote(executable)`.

**Status: ✅ Fixed** — Changed to `["start", "", executable]` list argument at `system_tools.py:381`.

---

## 18. Command injection via unsanitized f-string in `open_youtube_music` on Windows

**File:** `tools/system_tools.py:657-658`

**Severity:** **High** (security)

**Description:** `open_youtube_music()` URL-encodes the search query for HTTP but still embeds it into the same `f'start "" "{url}"'` shell pattern on Windows. A crafted search query can inject shell metacharacters.

**Fix:** Use list argument form or `shlex.quote(url)`.

**Status: ✅ Fixed** — Changed to `["start", "", url]` list argument at `system_tools.py:658`.

---

## 19. Bare `except: pass` swallows `KeyboardInterrupt`/`SystemExit` in `browser_tools.py`

**File:** `tools/browser_tools.py:301, 348`

**Severity:** **High** (process unkillable)

**Description:** Two bare `except:` clauses (not `except Exception:`) catch `KeyboardInterrupt` and `SystemExit`, making the process unkillable via Ctrl+C during Playwright browser automation. `browser.close()` may also never execute.

```python
try: page.wait_for_selector(selector, timeout=5000)
except: pass                           # Line 301 — bare except

# Later:
except:                                # Line 348 — bare except
    continue
```

**Fix:** Replace `except:` with `except Exception:`.

**Status: ✅ Fixed** — Both bare `except:` changed to `except Exception:` at `browser_tools.py:301, 348`.

---

## 20. Silently swallowed callback exceptions in `brain/sara_slm.py` training loops

**Files:** `brain/sara_slm.py:632, 848, 1012`

**Severity:** Medium (debugging impossible)

**Description:** Three identical callback wrapper functions silently swallow ALL exceptions from callback invocations with zero logging. If a callback raises (UI update failure, progress reporter crash), the exception is invisible.

```python
def cb(msg, pct=0):
    if callback:
        try: callback(msg, pct)
        except Exception: pass    # silently dropped
```

**Fix:** Log the exception: `logger.warning("Training callback failed: %s", e, exc_info=True)`.

**Status: ✅ Fixed** — Added logging to all 3 callback wrappers at `brain/sara_slm.py:632, 848, 1012`.

---

## 21. Unsandboxed `eval()` in `maestro/workflow.py` step conditions

**File:** `maestro/workflow.py:192`

**Severity:** Medium (potential code execution)

**Description:** `_is_skipped()` uses `eval(step.condition, {"__builtins__": {}}, context)` to evaluate step conditions. Even with `__builtins__` restricted, Python `eval()` is notoriously hard to sandbox — expressions like `().__class__.__bases__[0].__subclasses__()` can access arbitrary modules.

```python
return not bool(eval(step.condition, {"__builtins__": {}}, context))
```

**Fix:** Replace with a safe expression parser (e.g., `simpleeval` or restricted AST evaluator).

**Status: ✅ Fixed** — Replaced raw `eval()` with AST-validated `_safe_eval()` at `maestro/workflow.py:192`.

---

## 22. Silent `except Exception: pass` hides gateway startup failures

**File:** `gateway/run.py:473-474, 480-481, 487-488`

**Severity:** Medium (misconfiguration invisible)

**Description:** Three consecutive module-level try/except blocks silently swallow ALL exceptions from configuration-import functions (`apply_ipv4_preference`, `print_config_warnings`, `warn_deprecated_cwd_env_vars`). Critical misconfiguration warnings are invisible to operators.

```python
try:
    from sara_constants import apply_ipv4_preference
    ...
except Exception:        # silent
    pass
```

**Fix:** Log a warning: `logger.warning("Startup task failed: %s", e)`.

**Status: ✅ Fixed** — Added logging to all 3 startup try/except blocks at `gateway/run.py:473, 480, 487`.

---

## 23. Silent exception swallowing in `backend/computer_use/vision/llm.py` parser

**File:** `backend/computer_use/vision/llm.py:25-26, 29-30`

**Severity:** Medium (silent downstream failures)

**Description:** `extract_text()` silently swallows all exceptions from two parsing paths and returns an empty string. The caller cannot distinguish between "no content" and "parsing failed."

```python
try:
    return extract_content_or_reasoning(response).strip()
except Exception:
    pass
try:
    return str(response.choices[0].message.content or "").strip()
except Exception:
    return ""
```

**Fix:** Log the exception on the first path before attempting the fallback.

**Status: ✅ Fixed** — Added debug logging to the first parser path at `backend/computer_use/vision/llm.py:25`.

---

## 24. TOCTOU race condition: double `os.scandir()` in `file_tools.py:list_files()`

**File:** `tools/file_tools.py:103, 116`

**Severity:** Medium (inconsistent output)

**Description:** `list_files()` calls `os.scandir(folder)` TWICE — once at line 103 to build the display list, and again at line 116 to count total entries. Between the two calls, files may be added or removed, causing `total` to be inconsistent. Also wasteful.

```python
entries = sorted(os.scandir(folder), ...)    # First scan
# ...
total = len(list(os.scandir(folder)))         # Second scan — redundant + race
```

**Fix:** Use `total = len(entries)` from the already-sorted list.

**Status: ✅ Fixed** — Changed to `total = len(entries)` at `file_tools.py:116`.

---

## 25. `shell=True` with f-string commands in Docker container cleanup

**File:** `tools/environments/docker.py:623-627, 634-637`

**Severity:** Medium (injection surface)

**Description:** Docker cleanup uses `shell=True` with f-string-constructed shell commands containing `self._container_id` and `self._docker_exe`. While internal values, they could be contaminated by a malicious container. The second `except Exception: pass` at line 638 also silently hides cleanup failures.

```python
stop_cmd = (
    f"(timeout 60 {self._docker_exe} stop {self._container_id} || "
    f"{self._docker_exe} rm -f {self._container_id}) >/dev/null 2>&1 &"
)
subprocess.Popen(stop_cmd, shell=True)
```

**Fix:** Use list-based subprocess calls.

**Status: ✅ Fixed** — Replaced `shell=True` f-string with list-based `subprocess.run()` at `docker.py:623-637`.

---

## 26. Symlink TOCTOU: `os.path.abspath` vs `os.path.realpath` in protected path check

**File:** `tools/file_tools.py:24`

**Severity:** Low (defense-in-depth)

**Description:** `_is_protected()` uses `os.path.abspath()` which does not resolve symlinks. An attacker could create a symlink in a writable directory pointing to a protected path (e.g., `/etc/passwd`), bypassing the protection check.

```python
def _is_protected(path: str) -> bool:
    abs_path = os.path.abspath(path)       # does NOT resolve symlinks
```

**Fix:** Use `os.path.realpath()` which follows symlinks.

**Status: ✅ Fixed** — Switched to `os.path.realpath()` at `file_tools.py:24`.

---

## 27. Silent cleanup failures in `system_tools.py` screenshot functions

**File:** `tools/system_tools.py:903, 1002-1005, 1012-1015`

**Severity:** Low (temp file accumulation)

**Description:** Multiple `os.remove()` cleanup calls swallow exceptions silently. While cleanup failures are usually non-fatal, temporary file accumulation can occur with no indication.

```python
finally:
    try:
        os.remove(tmp_path)
    except Exception:   # silent
        pass
```

**Fix:** Log cleanup failures at DEBUG level.

**Status: ✅ Fixed** — Added logging to all 3 cleanup blocks at `system_tools.py:909-912, 1006-1010, 1016-1020`.

---

## 28. Silent resource cleanup failures in `ComputerAgent.shutdown()`

**File:** `backend/computer_use/__init__.py:185-186, 190-191`

**Severity:** Low (dangling resources)

**Description:** `ComputerAgent.shutdown()` silently swallows exceptions from `executor.shutdown()` and `overlay.hide()`. Failed cleanup leaves dangling resources with no indication.

```python
def shutdown(self):
    try:
        if self._executor:
            self._executor.shutdown()
    except Exception:       # silent
        pass
```

**Fix:** Log a warning: `logger.warning("Shutdown step failed: %s", e)`.

**Status: ✅ Fixed** — Added logging to both shutdown blocks at `backend/computer_use/__init__.py:185, 190`.

---

## Summary

| # | Severity | File | Line(s) | Description | Status |
|---|----------|------|---------|-------------|--------|
| 1 | **High** | `build_workflow.py` | 172-178 | `NameError` when `ask_ai_smart()` raises before `raw` is assigned | ✅ Fixed |
| 2 | Medium | `agent_loop.py` | 232-233 | Dead intent classification for "coding time" etc. — no handler | ✅ Fixed |
| 3 | Medium | `agent_loop.py` | 756-763 | SMALL_TALK returns hardcoded string instead of calling local LLM | ✅ Fixed |
| 4 | Low | `agent_loop.py` | 351-352 | Dead code `_build_desktop_routine_plan` | ✅ Fixed |
| 5 | Low | `register_tool.py` | 76-77, 324 | Local `set_reminder` shadowed by import | ✅ Fixed |
| 6 | Medium | `planner.py` | 441-443 | `_split_segments` over-splits on `" and "` | ✅ Fixed |
| 7 | Low | `agent_loop.py` | 300-308 | App install handler lacks validation | ✅ Fixed |
| 8 | Low | `agent_loop.py` | 636-802 | Every path stores user message redundantly | ⏸ Design |
| 9 | Low | `planner.py` | 119-188 | `execute_plan` has no overall "partial" flag | ✅ Fixed |
| 10 | Low | `agent_loop.py` | 60-69 | Dataclass mutable default (defensive) | ⏸ Wontfix |
| 11 | Low | `agent_loop.py` | 156-159 | Redundant `^` anchor in `_SMALL_TALK_RE` | ✅ Fixed |
| 12 | Medium | `core/agents.py` | 97-111 | Default agents silently succeed without real logic | ✅ Fixed |
| 13 | Low | `planner.py` | 458-459 | Reuses `text.lower()` instead of cached `lower` | ✅ Fixed |
| 14 | Low | `agent_loop.py` | 491-492 | Redundant local imports of `re` and `os` | ✅ Fixed |
| 15 | Low | `memory/*.py` | multiple | Three independent `DATA_DIR` definitions | ✅ Fixed |
| 16 | **High** | `tools/web_tools.py` | 35-37 | Command injection via unsanitized f-string on Windows | ✅ Fixed |
| 17 | **High** | `tools/system_tools.py` | 380-386 | Command injection via unsanitized f-string on Windows | ✅ Fixed |
| 18 | **High** | `tools/system_tools.py` | 657-658 | Command injection in `open_youtube_music` on Windows | ✅ Fixed |
| 19 | **High** | `tools/browser_tools.py` | 301, 348 | Bare `except: pass` swallows `KeyboardInterrupt`/`SystemExit` | ✅ Fixed |
| 20 | Medium | `brain/sara_slm.py` | 632, 848, 1012 | Silently swallowed callback exceptions in training | ✅ Fixed |
| 21 | Medium | `maestro/workflow.py` | 192 | Unsandboxed `eval()` in step conditions | ✅ Fixed |
| 22 | Medium | `gateway/run.py` | 473-474, 480-481, 487-488 | Silent `except Exception: pass` hides startup failures | ✅ Fixed |
| 23 | Medium | `backend/computer_use/vision/llm.py` | 25-26, 29-30 | Silent exception swallowing, returns empty string | ✅ Fixed |
| 24 | Medium | `tools/file_tools.py` | 103, 116 | TOCTOU race condition: double `os.scandir()` | ✅ Fixed |
| 25 | Medium | `tools/environments/docker.py` | 623-627, 634-637 | `shell=True` with f-string in Docker cleanup | ✅ Fixed |
| 26 | Low | `tools/file_tools.py` | 24 | `os.path.abspath` vs `os.path.realpath` — symlink bypass | ✅ Fixed |
| 27 | Low | `tools/system_tools.py` | 903, 1002-1005, 1012-1015 | Silent cleanup failures in screenshot functions | ✅ Fixed |
| 28 | Low | `backend/computer_use/__init__.py` | 185-186, 190-191 | Silent resource cleanup failures in `shutdown()` | ✅ Fixed |
