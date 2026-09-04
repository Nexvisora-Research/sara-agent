"""
agent/agent_loop.py — Sara AI shared turn engine.

This keeps the old `process_command()` compatibility wrapper while routing
complex work through the new planner -> workers -> reviewer flow.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto

from agent import build_workflow
from agent.observer import review_execution, to_agent_response
from agent.planner import (
    AgentResponse,
    ExecutionPlan,
    Subtask,
    ToolCall,
    WorkerResult,
    execute_plan,
    plan_complex_task,
)
from brain.auto_trainer import check_and_train
from brain.llm_engine import ask_ai_best, ask_ai_smart
from brain.personal_llm import ask_personal, is_tool_request
from brain.slm_auto_trainer import check_and_train_slm
from memory.context_manager import add_message, get_context
from memory.memory_engine import auto_update_profile, finalize_turn_memory, get_rich_context_string
from memory.user_profile import add_fact, get_full_context_string, get_telegram_info
from tools.register_tool import (
    TOOLS as TOOL_REGISTRY,
    execute_tool,
    get_tool_policy,
    get_tools_description,
)
from tools.automation_tools import try_handle_automation_request
from tools.routine_tools import (
    delete_routine_from_text,
    get_routine_steps,
    list_routines_text,
    routine_name_from_text,
    save_routine_from_text,
)

logger = logging.getLogger(__name__)


@dataclass
class PendingConfirmationState:
    user_input: str
    completed_results: list[WorkerResult]
    pending_subtasks: list[Subtask]
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return current - self.created_at > _PENDING_CONFIRMATION_TTL_SECONDS


@dataclass
class InteractiveShoppingState:
    user_id: str
    user_input: str
    step: str
    current_url: str = ""
    screenshot_path: str = ""
    selected_item_index: int = 0
    shopping_site: str = ""
    product_query: str = ""

_pending_confirmations: dict[str, PendingConfirmationState] = {}
_pending_shopping_states: dict[str, InteractiveShoppingState] = {}
_PENDING_CONFIRMATION_TTL_SECONDS = 10 * 60


def _allow_cloud_fallback() -> bool:
    return os.getenv("SARA_ALLOW_CLOUD_FALLBACK", "true").lower() not in {"0", "false", "no", "off"}


def _allow_auto_train() -> bool:
    return os.getenv("SARA_ENABLE_AUTO_TRAIN", "false").lower() in {"1", "true", "yes", "on"}


def _allow_slm_auto_train() -> bool:
    return os.getenv("SARA_ENABLE_SLM_AUTO_TRAIN", "false").lower() in {"1", "true", "yes", "on"}


SYSTEM_PROMPT = """You are Sara AI, a warm and capable personal assistant.
You know the user's profile and relevant long-term memories.

{user_context}

When tools are necessary, output JSON only.
1. Normal conversation -> plain text only.
2. One tool -> {{"action": "tool_name", "input": "value"}}
3. Multiple tools -> JSON array of tool calls only.
4. Never invent tool results.
5. Keep responses concise and easy to understand.

Available tools:
{tools}
"""


def _extract_and_learn_facts(user_id: str, user_input: str) -> None:
    fact_hooks = [
        ("i work at ", "Works at "),
        ("i work as ", "Works as "),
        ("i am a ", "Is a "),
        ("i'm a ", "Is a "),
        ("i love ", "Loves "),
        ("i hate ", "Hates "),
        ("i live in ", "Lives in "),
        ("i'm from ", "Lives in "),
        ("i am from ", "Lives in "),
        ("my name is ", "Prefers to be called "),
        ("i have a ", "Has a "),
        ("i study ", "Studies "),
        ("i work in ", "Works in "),
        ("i own ", "Owns "),
        ("i use ", "Uses "),
    ]
    lower = user_input.lower()
    learned = 0
    for hook, prefix in fact_hooks:
        if hook in lower:
            idx = lower.index(hook)
            tail = user_input[idx + len(hook):].split(".")[0].strip()
            if 2 < len(tail) < 80:
                add_fact(user_id, f"{prefix}{tail}")
                learned += 1
                if learned >= 3:
                    break


def build_prompt(user_id: str, context: str, user_input: str = "") -> str:
    user_context = get_full_context_string(user_id)
    rich_context = get_rich_context_string(user_id, user_input)
    combined = (user_context + ("\n" + rich_context if rich_context else "")).strip()
    if not combined:
        combined = "_(No profile yet — learn about the user naturally through conversation)_"
    return (
        SYSTEM_PROMPT.format(tools=get_tools_description(), user_context=combined)
        + "\nConversation:\n"
        + context
        + "\nassistant:"
    )


class Intent(Enum):
    SIMPLE_TOOL = auto()
    SMALL_TALK = auto()
    COMPLEX_TASK = auto()
    NORMAL_CHAT = auto()


_SMALL_TALK_RE = re.compile(
    r"(hi+|hey+|hello|howdy|hiya|yo|sup|what'?s up|how are you|good (morning|afternoon|evening|night))[\s!?.]*$",
    re.IGNORECASE,
)
_MATH_EXPR_RE = re.compile(r"^[\d\s+\-*/().]+$")
_YOUTUBE_SEARCH_RE = re.compile(
    r"(?:search(?:\s+(?:in|on))?\s+youtube(?:\s+for)?|youtube\s+search|find\s+on\s+youtube|open\s+youtube(?:\s+and)?(?:\s+search)?|play\s+on\s+youtube|play\s+youtube)\s+(.+)$",
    re.IGNORECASE,
)
_OPEN_APP_RE = re.compile(r"^(?:open|launch|start)\s+(.+)$", re.IGNORECASE)
_YT_MUSIC_RE = re.compile(
    r"^(?:play|open)\s+(.+?)\s+(?:in|on)\s+(?:yt music|youtube music)$|^(?:play|open)\s+(?:yt music|youtube music)(?:\s+for)?\s*(.*)$",
    re.IGNORECASE,
)
_YES_RE = re.compile(r"^(yes|y|okay|ok|go ahead|continue|do it|approve|sure)\b", re.IGNORECASE)
_NO_RE = re.compile(r"^(no|n|stop|cancel|don't|do not)\b", re.IGNORECASE)
_POWER_ACTION_RE = re.compile(
    r"^(?:please\s+)?(?P<action>shutdown|shut\s*down|power\s*off|restart|reboot)(?:\s+(?:pc|computer|system|laptop|machine))?(?:\s+please)?[\s!.]*$",
    re.IGNORECASE,
)
_RUN_COMMAND_RE = re.compile(
    r"^(?:run|execute)(?:\s+(?:terminal|shell|cmd))?(?:\s+command)?\s*[:\-]?\s+(.+)$",
    re.IGNORECASE,
)
_INSTALL_APP_RE = re.compile(
    r"^(?:install|setup|set\s+up)(?:\s+(?:the|an|a))?\s+(?:app|application|program|software)\s+(.+)$",
    re.IGNORECASE,
)
_INSTALL_PACKAGE_RE = re.compile(
    r"^(?:install|pip\s+install|npm\s+install)(?:\s+(?:package|module|library))?\s+(.+)$",
    re.IGNORECASE,
)
_MULTI_AGENT_RE = re.compile(
    r"^(?:use\s+)?(?:multi[-\s]?agents?|agents?|delegate)(?:\s+(?:to|for|on))?\s*[:\-]?\s*(.+)$",
    re.IGNORECASE,
)
_FEATURE_GUIDE_RE = re.compile(
    r"(what can you do|features?|capabilities|plugins?|skills?|daily life|how (?:can|should) i use sara|what should i add|add (?:new|next)|new integration)",
    re.IGNORECASE,
)


def _power_action_from_text(text: str) -> str | None:
    match = _POWER_ACTION_RE.match(text.strip())
    if not match:
        return None
    action = match.group("action").replace(" ", "").lower()
    if action in {"shutdown", "poweroff"}:
        return "shutdown_pc"
    return "restart_pc"


def _single_tool_plan(user_input: str, action: str, value: str = "") -> ExecutionPlan:
    return ExecutionPlan(
        user_goal=user_input,
        subtasks=[
            Subtask(
                id="task_1",
                goal=f"Run {action.replace('_', ' ')}",
                depends_on=[],
                tool_calls=[ToolCall(action, value)],
                risk_level=get_tool_policy(action).category,
                expected_output=f"Result from {action}",
                parallelizable=False,
            )
        ],
        planner_notes="direct deterministic tool route",
    )


def _classify_intent(user_input: str) -> Intent:
    text = user_input.strip()
    lower = text.lower()

    if _SMALL_TALK_RE.match(text):
        return Intent.SMALL_TALK
    if _power_action_from_text(text):
        return Intent.SIMPLE_TOOL
    if _RUN_COMMAND_RE.match(text) or _INSTALL_APP_RE.match(text) or _INSTALL_PACKAGE_RE.match(text):
        return Intent.SIMPLE_TOOL
    if _MULTI_AGENT_RE.match(text):
        return Intent.SIMPLE_TOOL
    if _FEATURE_GUIDE_RE.search(text):
        return Intent.SIMPLE_TOOL
    if lower.startswith("calculate ") or _MATH_EXPR_RE.match(lower):
        return Intent.SIMPLE_TOOL
    if _OPEN_APP_RE.match(text) or _YT_MUSIC_RE.match(text):
        return Intent.SIMPLE_TOOL
    if "weather in " in lower or lower.startswith("weather "):
        return Intent.SIMPLE_TOOL
    if "youtube" in lower and (
        "search" in lower or lower.startswith("find on youtube") or lower.startswith("open youtube") or lower.startswith("play youtube")
    ):
        return Intent.SIMPLE_TOOL
    if lower.startswith("save note") or lower.startswith("note:") or lower.startswith("remember:"):
        return Intent.SIMPLE_TOOL
    if (" and " in lower or " then " in lower or "," in lower) and len(lower.split()) >= 6:
        return Intent.COMPLEX_TASK
    return Intent.NORMAL_CHAT


def _handle_simple_tool_intent(user_id: str, user_input: str) -> str | None:
    text = user_input.strip()
    lower = text.lower()

    multi_agent_match = _MULTI_AGENT_RE.match(text)
    if multi_agent_match:
        goal = multi_agent_match.group(1).strip()
        if goal.lower() in {"status", "list", "show", "info"}:
            return execute_tool("multi_agent_status", "", user_id=user_id)
        return execute_tool("delegate_task", goal, user_id=user_id)

    if lower in {"list plugins", "plugins", "show plugins"}:
        return execute_tool("list_plugins", "", user_id=user_id)
    if lower in {"capabilities", "capability status", "show capabilities", "integration status"}:
        return execute_tool("capabilities_status", "", user_id=user_id)
    if lower in {"list skills", "skills", "show skills"}:
        return execute_tool("list_skills", "", user_id=user_id)
    if lower in {"list skills all", "all skills", "show all skills"}:
        return execute_tool("list_skills", "all", user_id=user_id)
    if _FEATURE_GUIDE_RE.search(text):
        return execute_tool("read_sara_features", "", user_id=user_id)

    yt_music_match = _YT_MUSIC_RE.match(text)
    if yt_music_match:
        query = (yt_music_match.group(1) or yt_music_match.group(2) or "").strip()
        if not query or query.lower() in {"music", "song", "songs"}:
            query = "lofi coding music"
        return execute_tool("open_youtube_music", query, user_id=user_id)

    power_action = _power_action_from_text(text)
    if power_action:
        return _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, power_action)).final_text

    if lower.startswith("open terminal"):
        remainder = text[len("open terminal"):].strip()
        remainder = re.sub(r"^(?:and\s+)?(?:run|execute)(?:\s+command)?\s*[:\-]?\s+", "", remainder, flags=re.IGNORECASE).strip()
        return execute_tool("open_terminal", remainder, user_id=user_id)

    run_match = _RUN_COMMAND_RE.match(text)
    if run_match:
        command = run_match.group(1).strip()
        return _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "run_terminal", command)).final_text

    install_app_match = _INSTALL_APP_RE.match(text)
    if install_app_match:
        app_name = install_app_match.group(1).strip()
        if not re.fullmatch(r"[a-zA-Z0-9_ .\-+]+", app_name):
            return f"❌ Invalid app name: '{app_name}'. Please use a simple app name."
        return _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "smart_open_app", app_name)).final_text

    install_package_match = _INSTALL_PACKAGE_RE.match(text)
    if install_package_match and lower.startswith(("pip install", "npm install", "install package", "install module", "install library")):
        package_name = install_package_match.group(1).strip()
        return _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "install_package", package_name)).final_text

    app_match = _OPEN_APP_RE.match(text)
    if app_match:
        target = re.sub(r"^(?:the\s+)?(?:app|application|program|software)\s+", "", app_match.group(1).strip(), flags=re.IGNORECASE)
        if target and not target.lower().startswith(("youtube ", "google ", "url ", "terminal")):
            return execute_tool("smart_open_app", target, user_id=user_id)

    if lower.startswith("calculate "):
        expr = text[len("calculate "):].strip()
        return execute_tool("calculate", expr, user_id=user_id)
    if _MATH_EXPR_RE.match(lower):
        return execute_tool("calculate", text, user_id=user_id)

    if "weather in " in lower:
        city = text.lower().split("weather in ", 1)[1].strip()
        return execute_tool("get_weather", city, user_id=user_id)
    if lower.startswith("weather "):
        return execute_tool("get_weather", text[len("weather "):].strip(), user_id=user_id)

    yt_match = _YOUTUBE_SEARCH_RE.search(text)
    if yt_match:
        query = yt_match.group(1).strip()
        if query:
            return execute_tool("youtube_search", query, user_id=user_id)
    if lower.startswith("youtube ") or lower.startswith("open youtube ") or lower.startswith("play youtube "):
        query = re.sub(r"^(open\s+youtube|play\s+youtube|youtube)\s+", "", text, flags=re.IGNORECASE).strip()
        if query:
            return execute_tool("youtube_search", query, user_id=user_id)

    if lower in {"time", "what's the time", "what is the time"}:
        return execute_tool("get_time", "", user_id=user_id)

    if lower.startswith("save note:"):
        return execute_tool("note_save", text.split(":", 1)[1].strip(), user_id=user_id)
    if lower.startswith("remember:"):
        return execute_tool("note_save", text.split(":", 1)[1].strip(), user_id=user_id)

    if "joke" in lower and len(lower.split()) <= 8:
        return execute_tool("tell_joke", "", user_id=user_id)
    return None


def _build_named_routine_plan(user_id: str, routine_name: str) -> ExecutionPlan | None:
    steps = get_routine_steps(user_id, routine_name)
    if not steps:
        return None

    subtasks = []
    for index, step in enumerate(steps, start=1):
        action = step.get("action", "").strip().lower()
        value = step.get("input", "")
        goal = step.get("goal", f"Routine step {index}")
        if not action or action not in TOOL_REGISTRY:
            continue
        tool_calls = [ToolCall(action, value)]
        subtasks.append(
            Subtask(
                id=f"routine_{index}",
                goal=goal,
                depends_on=[],
                tool_calls=tool_calls,
                risk_level=get_tool_policy(action).category,
                expected_output=f"Completed: {goal}",
                parallelizable=True,
            )
        )
    if not subtasks:
        return None
    return ExecutionPlan(user_goal=routine_name, subtasks=subtasks)


def _extract_tool_calls(text: str) -> list[dict]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict) and item.get("action")]
        if isinstance(parsed, dict) and parsed.get("action"):
            return [parsed]
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*([\[\{].*?[\]\}])\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict) and item.get("action")]
            if isinstance(parsed, dict) and parsed.get("action"):
                return [parsed]
        except json.JSONDecodeError:
            pass

    calls = []
    for match in re.finditer(r'\{[^{}]*"action"[^{}]*\}', text, re.DOTALL):
        try:
            parsed = json.loads(match.group())
            if parsed.get("action"):
                calls.append(parsed)
        except json.JSONDecodeError:
            continue
    return calls


def _strip_json_from_text(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*[\[\{].*?[\]\}]\s*```", "", text, flags=re.DOTALL)
    text = re.sub(r'\[[^\[\]]*"action"[^\[\]]*\]', "", text, flags=re.DOTALL)
    text = re.sub(r'\{[^{}]*"action"[^{}]*\}', "", text, flags=re.DOTALL)
    return text.strip()


def _direct_text_response(text: str) -> AgentResponse:
    return AgentResponse(status="final", final_text=text)


def _offline_small_talk_response(user_input: str) -> str:
    """Provide basic conversation without requiring an LLM provider."""
    normalized = user_input.strip().lower()
    if normalized in {"hi", "hii", "hiii", "hello", "hey", "hiya", "howdy"}:
        return "Hi! I'm Sara. How can I help? 😊"
    if "how are you" in normalized:
        return "I'm ready to help. What would you like to do? 😊"
    if "good morning" in normalized:
        return "Good morning! What should we work on today? ☀️"
    if "good evening" in normalized or "good night" in normalized:
        return "Good evening! How can I help? 🌙"
    return "I'm here and ready to help. What would you like to do? 😊"


def _respond_and_store(user_id: str, user_input: str, response: AgentResponse, *, channel: str) -> AgentResponse:
    add_message(user_id, "assistant", response.final_text, channel=channel)
    finalize_turn_memory(user_id, user_input, response.final_text, action_summaries=response.action_summaries)
    return response


def _handle_pending_confirmation(user_id: str, user_input: str) -> AgentResponse:
    pending = _pending_confirmations.get(user_id)
    if not pending:
        return _direct_text_response("")

    if pending.is_expired():
        _pending_confirmations.pop(user_id, None)
        return _direct_text_response(
            "⏱️ That approval expired for safety. Please send the original request again."
        )

    if _YES_RE.match(user_input):
        _pending_confirmations.pop(user_id, None)
        approval_plan = ExecutionPlan(user_goal=pending.user_input, subtasks=pending.pending_subtasks)
        new_results, new_pending, progress, partial = execute_plan(user_id, approval_plan, allow_risky=True)
        all_results = pending.completed_results + new_results
        review = review_execution(
            user_input=pending.user_input,
            plan=approval_plan,
            worker_results=all_results,
            pending_confirmation=new_pending,
        )
        response = to_agent_response(review)
        response.progress_updates.extend(progress)
        if response.requires_confirmation:
            completed = [result for result in all_results if result.success]
            _pending_confirmations[user_id] = PendingConfirmationState(
                user_input=pending.user_input,
                completed_results=completed,
                pending_subtasks=new_pending,
            )
        return response

    if _NO_RE.match(user_input):
        _pending_confirmations.pop(user_id, None)
        if pending.completed_results:
            completed = "\n".join(f"- {result.goal}" for result in pending.completed_results[:4])
            return AgentResponse(
                status="partial",
                final_text="Stopped before risky actions.\n\nSafe work already completed:\n" + completed,
            )
        return AgentResponse(status="final", final_text="Okay, I stopped before running the risky actions.")

    return AgentResponse(
        status="confirmation",
        final_text="I still need a clear `yes` or `no` for the pending risky actions.",
        confirmation={"pending": True},
    )


def _save_shopping_workflow(user_id: str, data: dict):
    from memory.memory_engine import _load_episodic_memories, _save_episodic_memories, MemoryRecord, _now_iso
    recs = _load_episodic_memories(user_id)
    recs.append(MemoryRecord(
        memory_type="shopping_workflow",
        content=f"Successfully shopped on {data.get('site', 'unknown')}",
        source="system",
        timestamp=_now_iso(),
        metadata=data
    ))
    _save_episodic_memories(user_id, recs)

def _handle_interactive_shopping(user_id: str, user_input: str, context: str, channel: str) -> AgentResponse | None:
    from tools.browser_tools import browser_screenshot, browser_click_nth_item, browser_add_to_cart, _build_search_url

    # Check if resuming
    if user_id in _pending_shopping_states:
        state = _pending_shopping_states[user_id]
        
        if state.step == "waiting_for_search_query":
            state.product_query = user_input
            search_url = _build_search_url(state.shopping_site, user_input)
            if not search_url:
                search_url = f"https://{state.shopping_site}/search?q={user_input}"
            
            state.current_url = search_url
            state.step = "waiting_for_item_choice"
            
            result = browser_screenshot(f"{search_url}::")
            return AgentResponse(
                status="interactive_shopping",
                final_text=f"🛒 Here are the results for '{user_input}'.\n\nWhich one do you like? Sir, you can reply like 'the first one' or '2'.\n\n{result}"
            )
            
        if state.step == "waiting_for_item_choice":
            match = re.search(r"(\d+)(?:st|nd|rd|th)?|first|second|third", user_input.lower())
            if match:
                if match.group(0) in ["first", "second", "third"]:
                    item_idx = {"first": 1, "second": 2, "third": 3}[match.group(0)]
                else:
                    item_idx = int(match.group(1))
                
                click_result = browser_click_nth_item(state.current_url, item_idx)
                
                if "❌" in click_result:
                    return AgentResponse(status="final", final_text=click_result)

                # Extract the actual product url from the text returned by browser_click_nth_item
                parts = click_result.split("📎 ")
                if len(parts) > 1:
                    product_url = parts[1].strip()
                    cart_result = browser_add_to_cart(product_url)
                else:
                    cart_result = browser_add_to_cart(state.current_url)

                _save_shopping_workflow(user_id, {
                    "site": state.shopping_site,
                    "product": state.product_query,
                    "item_selected": item_idx,
                    "success": True
                })
                
                del _pending_shopping_states[user_id]
                return AgentResponse(
                    status="final",
                    final_text=f"✅ {click_result}\n{cart_result}\n💳 Sir, I carted it. Please check your phone to pay!",
                    action_summaries=["browser_click_nth_item", "browser_add_to_cart"]
                )
            else:
                if any(word in user_input.lower() for word in ["no", "none", "not like", "more"]):
                    state.step = "waiting_for_search_query"
                    return AgentResponse(status="interactive_shopping", final_text="Okay, what else would you like to search for?")
                return AgentResponse(status="interactive_shopping", final_text="I didn't catch which item you wanted. Please specify '1st', '2nd', etc.")
    
    else:
        # Start new shopping flow
        sites = {"flipkart": "flipkart.com", "amazon": "amazon.in"}
        shopping_site = "flipkart.com"
        for site_key, site_domain in sites.items():
            if site_key in user_input.lower():
                shopping_site = site_domain
                break

        _pending_shopping_states[user_id] = InteractiveShoppingState(
            user_id=user_id,
            user_input=user_input,
            step="waiting_for_search_query",
            shopping_site=shopping_site
        )
        return AgentResponse(
            status="interactive_shopping",
            final_text=f"🛍️ You want to shop on {shopping_site}. What are you looking for?"
        )

    return None

def _run_structured_plan(user_id: str, user_input: str, plan: ExecutionPlan) -> AgentResponse:
    worker_results, pending_confirmation, progress, partial = execute_plan(user_id, plan, allow_risky=False)
    review = review_execution(
        user_input=user_input,
        plan=plan,
        worker_results=worker_results,
        pending_confirmation=pending_confirmation,
    )
    response = to_agent_response(review)
    response.progress_updates.extend(progress)
    if response.requires_confirmation:
        completed = [result for result in worker_results if result.success]
        _pending_confirmations[user_id] = PendingConfirmationState(
            user_input=user_input,
            completed_results=completed,
            pending_subtasks=pending_confirmation,
        )
    return response


def _handle_model_tool_calls(user_id: str, user_input: str, ai_response: str, tool_calls: list[dict]) -> AgentResponse:
    tool_calls = tool_calls[:4]
    clean_prefix = _strip_json_from_text(ai_response)

    if len(tool_calls) == 1:
        action = str(tool_calls[0].get("action", "")).strip().lower()
        value = str(tool_calls[0].get("input", ""))
        if action and action in TOOL_REGISTRY and not get_tool_policy(action).requires_confirmation:
            result = execute_tool(action, value, user_id=user_id)
            final_text = f"{clean_prefix}\n\n{result}".strip() if clean_prefix else result
            return AgentResponse(status="final", final_text=final_text, action_summaries=[f"{action}({value})"])

    subtasks = []
    for index, call in enumerate(tool_calls, start=1):
        action = str(call.get("action", "")).strip().lower()
        if not action or action not in TOOL_REGISTRY:
            continue
        value = str(call.get("input", ""))
        subtasks.append(
            Subtask(
                id=f"task_{index}",
                goal=f"Run {action.replace('_', ' ')}",
                depends_on=[],
                tool_calls=[ToolCall(action, value)],
                risk_level=get_tool_policy(action).category,
                expected_output=f"Result from {action}",
                parallelizable=True,
            )
        )

    if not subtasks:
        clean = clean_prefix or "I'm here! How can I help?"
        return AgentResponse(status="final", final_text=clean)

    response = _run_structured_plan(user_id, user_input, ExecutionPlan(user_goal=user_input, subtasks=subtasks))
    if clean_prefix and response.status == "final":
        response.final_text = f"{clean_prefix}\n\n{response.final_text}".strip()
    return response


def process_turn(user_id: str, user_input: str, *, channel: str = "chat") -> AgentResponse:
    add_message(user_id, "user", user_input, channel=channel)
    _extract_and_learn_facts(user_id, user_input)

    try:
        auto_update_profile(user_id, user_input)
    except Exception as exc:
        logger.debug("memory auto_update skipped: %s", exc)

    if _allow_auto_train():
        try:
            tg_bot, tg_chat = get_telegram_info(user_id)
            check_and_train(user_id, bot=tg_bot, chat_id=tg_chat)
        except Exception as exc:
            logger.debug("auto_trainer check skipped: %s", exc)

    if _allow_slm_auto_train():
        try:
            tg_bot, tg_chat = get_telegram_info(user_id)
            check_and_train_slm(user_id, bot=tg_bot, chat_id=tg_chat)
        except Exception as exc:
            logger.debug("slm_auto_trainer check skipped: %s", exc)

    if user_id in _pending_confirmations:
        response = _handle_pending_confirmation(user_id, user_input)
        return _respond_and_store(user_id, user_input, response, channel=channel)

    if user_id in _pending_shopping_states or any(word in user_input.lower() for word in ["shopping", "buy", "shop", "flipkart", "amazon"]):
        response = _handle_interactive_shopping(user_id, user_input, get_context(user_id, max_messages=3), channel=channel)
        if response:
            return _respond_and_store(user_id, user_input, response, channel=channel)

    if build_workflow.is_awaiting_change(user_id):
        response = _direct_text_response(build_workflow.consume_change_input(user_id, user_input))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    if build_workflow.get_session(user_id):
        response = _direct_text_response(build_workflow.handle_input(user_id, user_input))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    if build_workflow.is_build_intent(user_input):
        response = _direct_text_response(build_workflow.start_session(user_id, user_input))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    save_routine_reply = save_routine_from_text(user_id, user_input)
    if save_routine_reply:
        return _respond_and_store(
            user_id,
            user_input,
            AgentResponse(status="final", final_text=save_routine_reply),
            channel=channel,
        )

    delete_routine_reply = delete_routine_from_text(user_id, user_input)
    if delete_routine_reply:
        return _respond_and_store(
            user_id,
            user_input,
            AgentResponse(status="final", final_text=delete_routine_reply),
            channel=channel,
        )

    if user_input.strip().lower() in {"list routines", "show routines", "my routines"}:
        return _respond_and_store(
            user_id,
            user_input,
            AgentResponse(status="final", final_text=list_routines_text(user_id)),
            channel=channel,
        )

    routine_name = routine_name_from_text(user_id, user_input)
    routine_plan = _build_named_routine_plan(user_id, routine_name) if routine_name else None
    if routine_plan:
        response = _run_structured_plan(user_id, user_input, routine_plan)
        return _respond_and_store(user_id, user_input, response, channel=channel)

    automation_reply = try_handle_automation_request(user_id, user_input)
    if automation_reply:
        return _respond_and_store(
            user_id,
            user_input,
            AgentResponse(status="final", final_text=automation_reply),
            channel=channel,
        )

    power_action = _power_action_from_text(user_input)
    if power_action:
        response = _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, power_action))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    run_match = _RUN_COMMAND_RE.match(user_input.strip())
    if run_match:
        command = run_match.group(1).strip()
        response = _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "run_terminal", command))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    install_app_match = _INSTALL_APP_RE.match(user_input.strip())
    if install_app_match:
        app_name = install_app_match.group(1).strip()
        response = _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "smart_open_app", app_name))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    install_package_match = _INSTALL_PACKAGE_RE.match(user_input.strip())
    if install_package_match and user_input.strip().lower().startswith(("pip install", "npm install", "install package", "install module", "install library")):
        package_name = install_package_match.group(1).strip()
        response = _run_structured_plan(user_id, user_input, _single_tool_plan(user_input, "install_package", package_name))
        return _respond_and_store(user_id, user_input, response, channel=channel)

    intent = _classify_intent(user_input)

    if intent is Intent.SIMPLE_TOOL:
        fast_reply = _handle_simple_tool_intent(user_id, user_input)
        if fast_reply:
            return _respond_and_store(
                user_id,
                user_input,
                AgentResponse(status="final", final_text=fast_reply),
                channel=channel,
            )

    if intent is Intent.SMALL_TALK:
        personal_reply = ask_personal(user_id, user_input)
        if personal_reply:
            return _respond_and_store(
                user_id,
                user_input,
                AgentResponse(status="final", final_text=personal_reply),
                channel=channel,
            )
        return _respond_and_store(
            user_id,
            user_input,
            _direct_text_response(_offline_small_talk_response(user_input)),
            channel=channel,
        )

    if intent is Intent.COMPLEX_TASK:
        plan = plan_complex_task(user_id, user_input, get_context(user_id))
        response = _run_structured_plan(user_id, user_input, plan)
        return _respond_and_store(user_id, user_input, response, channel=channel)

    if not is_tool_request(user_input):
        personal_reply = ask_personal(user_id, user_input)
        if personal_reply:
            return _respond_and_store(
                user_id,
                user_input,
                AgentResponse(status="final", final_text=personal_reply),
                channel=channel,
            )

    if not _allow_cloud_fallback():
        msg = (
            "I'm still learning using Sara's local brain and could not confidently answer this "
            "without external cloud models. Cloud fallback is disabled."
        )
        return _respond_and_store(user_id, user_input, AgentResponse(status="final", final_text=msg), channel=channel)

    prompt = build_prompt(user_id, get_context(user_id), user_input)
    ai_response = ask_ai_best(prompt).strip()
    if ai_response.startswith("⚠️"):
        return _respond_and_store(
            user_id,
            user_input,
            AgentResponse(status="error", final_text=ai_response),
            channel=channel,
        )

    tool_calls = _extract_tool_calls(ai_response)
    if tool_calls:
        response = _handle_model_tool_calls(user_id, user_input, ai_response, tool_calls)
        return _respond_and_store(user_id, user_input, response, channel=channel)

    clean = _strip_json_from_text(ai_response) or "I'm here! How can I help? 😊"
    return _respond_and_store(user_id, user_input, AgentResponse(status="final", final_text=clean), channel=channel)


def process_command(user_id: str, user_input: str) -> str:
    """Compatibility wrapper for existing integrations."""
    return process_turn(user_id, user_input).render_text()
