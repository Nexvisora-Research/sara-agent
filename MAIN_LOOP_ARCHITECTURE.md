# Sara AI Main Loop Architecture

## Entry Points

### 1. **main.py** (Application Entry Point)
```
main.py
├── initialize_multi_agent_runtime()  [agent/multi_agent.py]
├── start_scheduler()                 [memory/automation_engine.py]
└── Start Bot(s):
    ├── start_discord_bot()           [integrations/discord_bot.py]
    ├── start_telegram_bot()          [integrations/telegram_bot.py]
    └── start_whatsapp_bot()          [integrations/whatsapp_bot.py]
```

### 2. **cli.py** (Interactive CLI Interface)
```
cli.py
├── process_command()  [inner method]
└── Routes to process_turn() [agent/agent_loop.py]
```

---

## Core Main Loop

### **agent/agent_loop.py** - The Central Hub

#### Main Entry Point: `process_turn(user_id, user_input, channel="chat")`

```
process_turn()
├── Message Storage
│   └── add_message() [memory/context_manager.py]
│
├── Profile Learning
│   ├── _extract_and_learn_facts()
│   ├── auto_update_profile() [memory/memory_engine.py]
│   └── add_fact() [memory/user_profile.py]
│
├── Auto-Training (if enabled)
│   ├── check_and_train() [brain/auto_trainer.py]
│   └── check_and_train_slm() [brain/slm_auto_trainer.py]
│
├── State Handlers (Checked in sequence)
│   ├── _handle_pending_confirmation()
│   ├── _handle_interactive_shopping()
│   └── build_workflow handlers [agent/build_workflow.py]
│       ├── is_build_intent()
│       ├── get_session()
│       ├── handle_input()
│       └── start_session()
│
├── Routine Handlers
│   ├── save_routine_from_text() [tools/routine_tools.py]
│   ├── delete_routine_from_text()
│   ├── list_routines_text()
│   └── _build_named_routine_plan()
│
├── Automation & Power Actions
│   ├── try_handle_automation_request() [tools/automation_tools.py]
│   ├── _power_action_from_text()
│   ├── _RUN_COMMAND_RE handler
│   ├── _INSTALL_APP_RE handler
│   └── _INSTALL_PACKAGE_RE handler
│
├── Intent Classification
│   └── _classify_intent(user_input) → Intent Enum
│       ├── SIMPLE_TOOL
│       ├── SMALL_TALK
│       ├── COMPLEX_TASK
│       └── NORMAL_CHAT
│
└── Intent-Specific Handlers
    ├── SIMPLE_TOOL: _handle_simple_tool_intent()
    │   ├── Multi-agent: execute_tool("delegate_task")
    │   ├── Plugins: execute_tool("list_plugins")
    │   ├── Skills: execute_tool("list_skills")
    │   ├── Features: execute_tool("read_sara_features")
    │   ├── YouTube Music: execute_tool("open_youtube_music")
    │   ├── Power Actions: _run_structured_plan()
    │   ├── Terminal: execute_tool("open_terminal")
    │   ├── App Install: execute_tool("smart_open_app")
    │   ├── Package Install: execute_tool("install_package")
    │   ├── Calculations: execute_tool("calculate")
    │   ├── Weather: execute_tool("get_weather")
    │   ├── YouTube Search: execute_tool("youtube_search")
    │   ├── Time: execute_tool("get_time")
    │   ├── Notes: execute_tool("note_save")
    │   └── Jokes: execute_tool("tell_joke")
    │
    ├── SMALL_TALK: _handle_small_talk()
    │   └── ask_personal() [brain/personal_llm.py]
    │
    ├── COMPLEX_TASK: _run_complex_flow()
    │   ├── plan_complex_task() [agent/planner.py]
    │   ├── execute_plan() [agent/planner.py]
    │   ├── review_execution() [agent/observer.py]
    │   └── to_agent_response() [agent/observer.py]
    │
    └── NORMAL_CHAT: _handle_normal_chat()
        ├── ask_ai_best() [brain/llm_engine.py]
        ├── ask_ai_smart() [brain/llm_engine.py]
        └── is_tool_request() [brain/personal_llm.py]

└── Response Storage & Finalization
    └── _respond_and_store()
        ├── add_message() [memory/context_manager.py]
        └── finalize_turn_memory() [memory/memory_engine.py]
```

---

## Connected Components

### **agent/** - Agent Orchestration
- **agent_loop.py**: Main turn processor (core hub)
- **planner.py**: Complex task planning & execution
  - `plan_complex_task()` - Creates structured execution plans
  - `execute_plan()` - Runs subtasks with worker coordination
  - Data structures: `ExecutionPlan`, `Subtask`, `ToolCall`, `WorkerResult`
- **observer.py**: Result review & response composition
  - `review_execution()` - Analyzes worker results
  - `to_agent_response()` - Converts reviews to API response
- **build_workflow.py**: Project builder state machine
  - BuildState: IDLE → DISCUSSING → PLANNING → AWAITING_APPROVAL → BUILDING → DONE
  - Session management for complex projects
- **multi_agent.py**: Multi-agent coordinator
  - `delegate_task()` - Routes work to specialized agents
  - Agent registry from `.agents/sara_agents.json`

### **memory/** - Context & Profile Management
- **context_manager.py**: Conversation context
  - `add_message()` - Stores user/assistant messages
  - `get_context()` - Retrieves conversation history
- **memory_engine.py**: Dynamic memory updates
  - `auto_update_profile()` - Learns from conversations
  - `finalize_turn_memory()` - Stores turn outcomes
  - `get_rich_context_string()` - Enriches prompts
- **user_profile.py**: User facts & metadata
  - `add_fact()` - Records user information
  - `get_full_context_string()` - User profile context
  - `get_telegram_info()` - Channel-specific data
- **automation_engine.py**: Scheduled tasks
  - `start_scheduler()` - Background automation runner

### **brain/** - Intelligence & Model Selection
- **llm_engine.py**: Language model routing
  - `ask_ai_best()` - Highest quality responses
  - `ask_ai_smart()` - Balanced cost/quality
  - `ask_ai_creative()` - Creative tasks
- **personal_llm.py**: Local SLM (Small Language Model)
  - `ask_personal()` - Fast local inference
  - `is_tool_request()` - Detects tool invocations
- **auto_trainer.py**: Continuous model improvement
  - `check_and_train()` - Auto-trains on user interactions
- **slm_auto_trainer.py**: Local model fine-tuning
  - `check_and_train_slm()` - Trains small language models
- **sara_slm.py**: Local model wrapper
- **persona_model.py**: User personality modeling
- **trend_analyzer.py**: Conversation trend analysis

### **tools/** - Action Execution
- **register_tool.py**: Tool registry & execution
  - `execute_tool(action, input, user_id)` - Universal tool invoker
  - `TOOL_REGISTRY` - All available tools
  - `get_tools_description()` - LLM-friendly tool docs
  - `get_tool_policy()` - Risk levels (safe_read, risky, dangerous)
- **routine_tools.py**: Saved workflow management
  - `save_routine_from_text()` - Creates saved routines
  - `delete_routine_from_text()` - Removes routines
  - `list_routines_text()` - Displays saved routines
  - `get_routine_steps()` - Retrieves routine steps
- **automation_tools.py**: Automated triggers
  - `try_handle_automation_request()` - Processes automation commands

### **integrations/** - Chat Channels
- **discord_bot.py**: Discord integration
- **telegram_bot.py**: Telegram bot handler
- **whatsapp_bot.py**: WhatsApp integration

### **gateway/** - Multi-platform Abstraction
- Platform-agnostic message delivery
- Session context management
- Channel routing

---

## Data Flow Diagram

```
User Input (Discord/Telegram/WhatsApp/CLI)
    ↓
[integrations/*_bot.py]
    ↓
process_turn(user_id, user_input, channel)
    ↓
┌─────────────────────────────────────────────────────────┐
│ Memory Context                                          │
│  ├─ add_message()                                       │
│  ├─ auto_update_profile()                               │
│  └─ get_context() / get_full_context_string()          │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ State Checks (in sequence)                             │
│  ├─ Pending confirmation?                               │
│  ├─ Shopping state?                                     │
│  ├─ Build workflow?                                     │
│  ├─ Routine request?                                    │
│  └─ Automation request?                                 │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Intent Classification                                   │
│  ├─ Simple Tool → Direct tool execution                │
│  ├─ Small Talk → Local LLM (fast)                       │
│  ├─ Complex Task → Planner → Workers → Reviewer         │
│  └─ Normal Chat → LLM selection                         │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Tool Execution (if needed)                              │
│  └─ execute_tool() → Tool policy check → Run            │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Brain Selection (for AI responses)                      │
│  ├─ ask_personal() → Fast local inference               │
│  ├─ ask_ai_smart() → Balanced LLM                       │
│  └─ ask_ai_best() → Best quality LLM                    │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ Response Finalization                                   │
│  ├─ finalize_turn_memory()                              │
│  ├─ add_message() [response]                            │
│  └─ Return AgentResponse                                │
└─────────────────────────────────────────────────────────┘
    ↓
Return to integration layer → Send to user
```

---

## Key Configuration

### Environment Flags
```python
SARA_ALLOW_CLOUD_FALLBACK = "true"          # Enable LLM fallback
SARA_ENABLE_AUTO_TRAIN = "false"            # Auto-train on interactions
SARA_ENABLE_SLM_AUTO_TRAIN = "false"        # Fine-tune local models
```

### Bot Configuration (main.py)
```python
TELEGRAM_BOT_TOKEN                          # Enable Telegram
DISCORD_BOT_TOKEN                           # Enable Discord
WHATSAPP_WEBHOOK_ENABLED = "true|false"     # Enable WhatsApp
```

---

## Tool Execution Pipeline

```
_handle_simple_tool_intent() or execute_tool()
    ↓
get_tool_policy(action_name)  [Risk assessment]
    ├─ Category: safe_read | risky | dangerous
    └─ Risky tools → Confirmation queue
    ↓
execute_tool(action, input, user_id)  [tools/register_tool.py]
    ├─ Lookup in TOOL_REGISTRY
    ├─ Validate input
    ├─ Execute in appropriate runtime
    └─ Return result
```

---

## Planning & Execution (Complex Tasks)

```
_run_complex_flow()
    ├─ plan_complex_task()  [LLM generates execution plan]
    │   └─ Returns: ExecutionPlan
    │       ├─ user_goal
    │       ├─ subtasks[]
    │       │   ├─ id, goal
    │       │   ├─ depends_on[] (dependencies)
    │       │   ├─ tool_calls[] (actions)
    │       │   ├─ risk_level
    │       │   └─ parallelizable
    │       └─ planner_notes
    │
    ├─ execute_plan()  [Runs subtasks as workers]
    │   ├─ Check risks → Ask user if needed
    │   ├─ Execute in parallel (up to MAX_PARALLEL_WORKERS=2)
    │   ├─ Handle failures gracefully
    │   └─ Returns: (completed_results[], pending_subtasks[], progress[])
    │
    └─ review_execution()  [Compose response]
        ├─ review_execution() [agent/observer.py]
        ├─ Analyze success/failure/risk
        ├─ to_agent_response()
        └─ Return AgentResponse with status + text
```

---

## State Machines

### Build Workflow State Machine
```
        ┌─→ DISCUSSING ──→ PLANNING ──→ AWAITING_APPROVAL ──→ BUILDING ──→ DONE
IDLE ──┤
        └─→ (or reset to IDLE)
```

### Confirmation States
```
_pending_confirmations[user_id]
    ├─ user_input (original request)
    ├─ completed_results[] (safe operations done)
    └─ pending_subtasks[] (risky operations waiting)
    
When user says "yes" → Execute pending → Finalize
When user says "no"  → Abort pending
```

### Shopping State Machine
```
_pending_shopping_states[user_id]
    ├─ user_id, user_input
    ├─ step (interactive flow state)
    ├─ current_url, screenshot_path
    ├─ selected_item_index
    ├─ shopping_site, product_query
```

---

## Code Entry Points Summary

| File | Function | Purpose |
|------|----------|---------|
| `main.py` | `main()` | App startup |
| `cli.py` | `process_command()` | CLI entry |
| `agent_loop.py` | `process_turn()` | **Core main loop** |
| `agent_loop.py` | `process_command()` | Compatibility wrapper |
| `planner.py` | `plan_complex_task()` | Task decomposition |
| `planner.py` | `execute_plan()` | Worker execution |
| `observer.py` | `review_execution()` | Result synthesis |
| `memory_engine.py` | `auto_update_profile()` | Memory updates |
| `context_manager.py` | `add_message()` | Conversation logging |
| `tools/register_tool.py` | `execute_tool()` | Action execution |

---

## Critical Path for User Request

1. **Input arrives** → Integration channel (Telegram/Discord/CLI)
2. **Route to main loop** → `process_turn(user_id, user_input)`
3. **Add to context** → `add_message()` stores in memory
4. **Learn facts** → Extract and store user info
5. **Check states** → Pending confirmations, shopping, build workflow
6. **Classify intent** → SIMPLE_TOOL | SMALL_TALK | COMPLEX_TASK | NORMAL_CHAT
7. **Route handler** → Intent-specific path
8. **Execute** → Tool execution / LLM inference / Plan → Workers → Review
9. **Store response** → `finalize_turn_memory()`
10. **Return to user** → Send through integration channel

