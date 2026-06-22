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

---

## 7. `_handle_simple_tool_intent()` may match "smart_open_app" for app install requests that aren't app installs

**File:** `agent/agent_loop.py:300-308`

**Severity:** Low (logic)

**Description:** The `_INSTALL_APP_RE` regex at line 181 matches patterns like `"install app <name>"`. But in `_handle_simple_tool_intent`, the matched group is passed to `smart_open_app` which both opens AND potentially installs apps. There's no validation that the "app" is actually installable or exists. This is a minor UX issue but could produce confusing results.

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

---

## 15. Memory compaction: `memory_engine.py` and `context_manager.py` both define `DATA_DIR` to `memory/data/`

**Files:** `memory/context_manager.py:9`, `memory/memory_engine.py:23`, `memory/user_profile.py:27`

**Severity:** Low (architectural)

**Description:** All three memory modules define `DATA_DIR = os.path.join(os.path.dirname(__file__), "data")` independently, all resolving to `memory/data/`. While this works (each module uses its own subdirectory structure under `data/<user_id>/`), the redundancy makes it easy to accidentally break the convention. A shared constant would be cleaner.

---

## Summary

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 1 | **High** | `build_workflow.py` | 172-178 | `NameError` when `ask_ai_smart()` raises before `raw` is assigned |
| 2 | Medium | `agent_loop.py` | 232-233 | Dead intent classification for "coding time" etc. — no handler |
| 3 | Medium | `agent_loop.py` | 756-763 | SMALL_TALK returns hardcoded string instead of calling local LLM |
| 4 | Low | `agent_loop.py` | 351-352 | Dead code `_build_desktop_routine_plan` |
| 5 | Low | `register_tool.py` | 76-77, 324 | Local `set_reminder` shadowed by import |
| 6 | Medium | `planner.py` | 441-443 | `_split_segments` over-splits on `" and "` |
| 7 | Low | `agent_loop.py` | 300-308 | App install handler lacks validation |
| 8 | Low | `agent_loop.py` | 636-802 | Every path stores user message redundantly |
| 9 | Low | `planner.py` | 119-188 | `execute_plan` has no overall "partial" flag |
| 10 | Low | `agent_loop.py` | 60-69 | Dataclass mutable default (defensive) |
| 11 | Low | `agent_loop.py` | 156-159 | Redundant `^` anchor in `_SMALL_TALK_RE` |
| 12 | Medium | `core/agents.py` | 97-111 | Default agents silently succeed without real logic |
| 13 | Low | `planner.py` | 458-459 | Reuses `text.lower()` instead of cached `lower` |
| 14 | Low | `agent_loop.py` | 491-492 | Redundant local imports of `re` and `os` |
| 15 | Low | `memory/*.py` | multiple | Three independent `DATA_DIR` definitions |
