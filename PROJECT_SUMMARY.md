# Sara Agent v2.2.0 — Complete Project Summary

> Read this single file to understand the entire codebase. No need to read individual source files.

---

## 1. Overview

**Sara Agent** is a self-improving personal AI assistant with persistent memory, reusable skills, tool use, scheduled automation, multi-agent delegation, and a shared messaging gateway. It runs locally or in managed environments and can be used from the terminal (CLI/TUI), desktop app (Electron), web UI, or connected chat platforms (Telegram, Discord, WhatsApp).

- **Package:** `sara-agent` v2.2.0 (MIT, Nexvisora Research)
- **Python:** >= 3.11
- **Entry:** `sara` (`sara_cli.main:cli_main`) or `python cli.py` / `python run_agent.py`
- **Data dir:** `~/.sara/` (configurable via `SARA_HOME` env var)
- **Config:** `~/.sara/config.yaml` (primary), `cli-config.yaml` (project fallback)

---

## 2. Directory Structure

```
saraAgent/
├── agent/                      # Core turn engine, planner, multi-agent, build workflow
│   ├── agent_loop.py           # Shared turn engine (process_turn / process_command)
│   ├── planner.py              # Planner/worker coordinator (Subtask, ToolCall, ExecutionPlan)
│   ├── multi_agent.py          # Multi-agent coordinator (planner/researcher/builder/reviewer)
│   ├── observer.py             # Reviewer/response composer
│   ├── build_workflow.py       # 5-stage project builder (IDLE→DONE)
│   ├── redact.py               # Secret redaction formatter
│   ├── memory_manager.py       # Streaming context scrubber
│   ├── retry_utils.py          # Jittered backoff helpers
│   ├── error_classifier.py     # API error classification & failover
│   ├── prompt_builder.py       # System prompt construction
│   ├── model_metadata.py       # Model metadata fetching & token estimation
│   ├── context_compressor.py   # Context window compression
│   ├── anthropic_adapter.py    # Anthropic API client builder
│   ├── auxiliary_client.py     # Provider router & client resolution
│   ├── usage_pricing.py        # Token cost estimation
│   ├── display.py              # Spinner, tool preview, emoji helpers
│   ├── tool_guardrails.py      # Tool loop guardrails
│   ├── trajectory.py           # Conversation trajectory saving
│   ├── prompt_caching.py       # Anthropic cache control
│   ├── subdirectory_hints.py   # Subdirectory tracking
│   ├── codex_responses_adapter.py  # OpenAI Responses API adapter
│   └── ...                     # More support files
├── apps/desktop/               # Electron desktop app (glass UI, voice, themes, i18n)
├── backend/computer_use/       # Desktop automation agent
├── brain/                      # Multi-provider AI engine
│   ├── llm_engine.py           # Unified AI caller (Claude→Groq→Ollama fallback)
│   ├── personal_llm.py         # Inference routing (SLM→LoRA→cloud)
│   ├── sara_slm.py             # Custom ~30M param GPT-style transformer (RoPE, RMSNorm, SwiGLU, GQA)
│   ├── persona_model.py        # LoRA fine-tuned TinyLlama (Sara v2)
│   ├── auto_trainer.py         # Cloud auto-training for Sara v2 LoRA
│   ├── slm_auto_trainer.py     # Auto-training for SLM
│   ├── dataset_downloader.py   # Public dataset download (Alpaca, Dolly, OpenOrca, ShareGPT)
│   └── trend_analyzer.py       # Conversation trends & mood analytics
├── core/                       # Phase A: concurrent agent orchestration
│   ├── models.py               # Pydantic models (AgentTask, Event, AgentResult)
│   ├── agents.py               # BaseAgent + specialized (Planner, Research, Coding, etc.)
│   ├── events.py               # In-process async event bus
│   ├── orchestrator.py         # Concurrent agent orchestration (spawn, run_many, cancel)
│   ├── database.py             # SQLite connection management & migrations
│   ├── tasks.py                # Persistent background task engine
│   ├── scheduler.py            # APScheduler adapter
│   ├── watchers.py             # Polling watchers (Folder, Repository, Log)
│   └── notifications.py        # Notification fan-out service
├── cron/                       # Cron/scheduled job system
│   ├── jobs.py                 # Job definitions
│   └── scheduler.py            # Cron scheduler
├── integrations/               # Chat platform connectors
│   ├── telegram_bot.py         # Full Telegram bot with onboarding
│   ├── discord_bot.py          # Discord integration
│   └── whatsapp_bot.py         # WhatsApp integration (Twilio/whatsapp-web.js)
├── maestro/                    # Phase B: advanced orchestration
│   ├── models.py               # Kanban, Workflow, Swarm, Router, Reflection models
│   ├── conductor.py            # Wiring layer (core + maestro)
│   ├── swarm.py                # Agent swarm coordination
│   ├── planner.py              # Multi-agent planner (goal decomposition, task graph)
│   ├── router.py               # Model router (capability-based, cost-aware)
│   ├── kanban.py               # Kanban task board (SQLite-backed)
│   ├── workflow.py             # Workflow engine (sequential/parallel/conditional)
│   ├── reflection.py           # Reflection & self-correction
│   └── monitor.py              # Watch & monitoring system
├── memory/                     # Memory subsystem
│   ├── memory_engine.py        # Layered memory (profile signals, rolling summary, episodic, semantic)
│   ├── wiki_memory.py          # Obsidian-compatible long-term memory (Markdown→SQLite+graph)
│   ├── context_manager.py      # Chat history management (JSON, context windowing)
│   ├── knowledge.py            # Semantic knowledge base (ChromaDB/sentence-transformers)
│   ├── user_profile.py         # User profile CRUD
│   ├── automation_engine.py    # Automation rules engine
│   └── data/                   # Per-user data storage
├── plugins/                    # Plugin examples (disk-cleanup, example-dashboard)
├── sara_cli/                   # CLI application package (installed as `sara`)
│   ├── main.py                 # CLI entry point (argparse, subcommands)
│   ├── commands.py             # Slash commands
│   ├── banner.py               # Welcome banner
│   ├── skin_engine.py          # Theme/skin system
│   ├── config.py               # Configuration loading
│   ├── auth.py                 # Provider auth registry
│   ├── model_normalize.py      # Model name normalization
│   ├── platforms.py            # Platform definitions
│   ├── timeouts.py             # Provider timeout config
│   ├── env_loader.py           # .env file loader
│   ├── runtime_python.py       # Python runtime resolution
│   ├── gateway.py              # Gateway subprocess management
│   ├── kanban_db.py            # Kanban CLI
│   └── ...
├── tools/                      # Tool system (89 files)
│   ├── registry.py             # Central tool registry (ToolRegistry, ToolEntry)
│   ├── register_tool.py        # Master tool registry (TOOLS dict, execute_tool, ToolPolicy)
│   ├── terminal_tool.py        # Terminal execution
│   ├── browser_tool.py         # Browser automation (Playwright)
│   ├── browser_cdp_tool.py     # Chrome DevTools Protocol browser
│   ├── browser_camofox.py      # Alternative browser provider
│   ├── file_operations.py      # File read/write/patch
│   ├── file_tools.py           # File system tools
│   ├── web_tools.py            # Web search/extract
│   ├── ai_tools.py             # AI-powered sub-agent tools
│   ├── memory_tool.py          # Memory store tool
│   ├── skill_manager_tool.py   # Skill management
│   ├── skills_tool.py          # Skill execution
│   ├── skills_hub.py           # Skills hub sync
│   ├── code_execution_tool.py  # Sandboxed code execution
│   ├── vision_tools.py         # Image analysis
│   ├── image_generation_tool.py# Image generation
│   ├── tts_tool.py             # Text-to-speech
│   ├── voice_mode.py           # Voice input mode
│   ├── communication_tools.py  # Send message/broadcast
│   ├── todo_tool.py            # Todo list
│   ├── cronjob_tools.py        # Cron job management
│   ├── delegate_tool.py        # Task delegation
│   ├── kanban_tools.py         # Kanban board integration
│   ├── homeassistant_tool.py   # Home Assistant control
│   ├── discord_tool.py         # Discord fetch/search
│   ├── mcp_tool.py             # MCP server tools
│   ├── mcp_oauth.py            # MCP OAuth handling
│   ├── computer_use_tool.py    # Desktop automation
│   ├── automation_tools.py     # Automation trigger tools
│   ├── routine_tools.py        # Saved routines
│   ├── news_tools.py           # News/RSS fetching
│   ├── media_tools.py          # Media processing
│   ├── session_search_tool.py  # Session search
│   ├── reminder_tools.py       # Reminders
│   ├── system_tools.py         # System info/control
│   ├── dev_tools.py            # Development tools
│   ├── clarify_tool.py         # Clarification questions
│   ├── monitor_tools.py        # Monitor integration
│   ├── approval.py             # Tool approval UI
│   ├── tool_result_storage.py  # Tool result persistence
│   ├── checkpoint_manager.py   # Filesystem checkpoints
│   ├── schema_sanitizer.py     # Tool schema sanitization
│   ├── path_security.py        # Path security validation
│   └── ... (more tool modules)
├── tui_gateway/                # TUI gateway server
├── web/                        # Web UI
├── temporal-engine/            # Temporal workflow engine integration
├── gateway/                    # Gateway platform adapters
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
├── docs/                       # Documentation
├── nix/                        # Nix flake config
├── config/                     # Default config files
├── skills/                     # Optional skills
├── optional-skills/            # Optional skills (package-manager wrappers)
├── .agents/                    # Multi-agent home/config
├── cli.py                      # Legacy CLI (prompt_toolkit TUI, 12K lines)
├── run_agent.py                # AIAgent class (14K lines, main agent loop)
├── model_tools.py              # Tool orchestration layer (sync/async bridge)
├── toolsets.py                 # Compat toolset registry
├── sara_constants.py           # Import-safe shared constants
├── sara_logging.py             # Centralized logging setup
├── sara_state.py               # SQLite session/state store
├── sara_time.py                # Time utilities
├── utils.py                    # Shared utility functions
├── pyproject.toml              # Build config & dependencies
└── README.md                   # Quick start
```

---

## 3. Architecture & Data Flow

### Entry Points

1. **`sara` CLI** → `sara_cli.main:cli_main()` — production CLI with session management, slash commands, subcommands (gateway, setup, cron, doctor, sessions, etc.)
2. **`python cli.py`** — legacy interactive TUI with prompt_toolkit, Rich, spinner, skins/themes
3. **`python run_agent.py`** — direct `AIAgent` class usage for programmatic embedding

### Turn Processing Flow (`agent/agent_loop.py:process_turn`)

```
User Input
    │
    ├─► Add message to history, extract facts, auto-update profile
    ├─► Auto-train checks (if enabled)
    ├─► Check pending confirmations → yes/no handling
    ├─► Check interactive shopping state → browser automation flow
    ├─► Check build workflow → 5-stage project builder
    ├─► Check routine save/delete/list → routine management
    ├─► Check automation triggers
    ├─► Check power actions, run commands, install apps/packages
    │
    ├─► Intent Classification (SIMPLE_TOOL|SMALL_TALK|COMPLEX_TASK|NORMAL_CHAT)
    │
    ├─► SIMPLE_TOOL → regex match → direct tool execution
    ├─► SMALL_TALK → local/personal model
    ├─► COMPLEX_TASK → planner → workers → reviewer pipeline
    └─► NORMAL_CHAT → cloud fallback (Claude→Groq→Ollama)
```

### AI Provider Fallback Chain (`brain/llm_engine.py`)

```
1. Sara SLM (local, ~30M params, from-scratch transformer)
2. Sara v2 LoRA (local, fine-tuned TinyLlama via PEFT)
3. Claude AI (cloud, claude-3.5-sonnet / haiku)
4. Groq Cloud (ultra-fast, llama3-70b / mixtral)
5. Ollama (local fallback, gemma3:1b / phi4-mini / mistral:7b)
```

Each tier has three model variants: **FAST**, **SMART**, **CREATIVE**.

`brain/personal_llm.py` provides confidence-gated routing: SLM → LoRA v2 → cloud, with tool request detection.

### Two-Phase Orchestration Architecture

**Phase A (`core/`):** Concurrent agent orchestration
- **EventBus** (`core/events.py`): In-process async pub/sub with bounded subscriber queues
- **AgentOrchestrator** (`core/orchestrator.py`): Spawns specialized agents concurrently, manages lifecycle, cancellation
- **BaseAgent** hierarchy (`core/agents.py`): PlannerAgent, ResearchAgent, CodingAgent, MemoryAgent, BrowserAgent
- **BackgroundTaskEngine** (`core/tasks.py`): Persistent task runner with SQLite store
- **Watchers** (`core/watchers.py`): FolderWatcher, RepositoryWatcher, LogWatcher

**Phase B (`maestro/`):** Higher-level orchestration
- **Conductor** (`maestro/conductor.py`): Integrated entry point wiring core + maestro
- **AgentSwarm** (`maestro/swarm.py`): Collaborative multi-agent with message bus, consensus, supervisor
- **PlannerAgent** (`maestro/planner.py`): Hierarchical goal decomposition, dependency resolution, task graph
- **ModelRouter** (`maestro/router.py`): Intelligent model selection by capability (code, reasoning, vision)
- **WorkflowEngine** (`maestro/workflow.py`): Sequential/parallel/conditional steps with retry/timeout
- **Kanban** (`maestro/kanban.py`): SQLite-backed project management (6 columns: backlog→archived)
- **ReflectionAgent** (`maestro/reflection.py`): Critique, confidence scoring, improvement loops
- **Monitor** (`maestro/monitor.py`): File/Repo/Log watchers with rule-based alerting

### Tool System Architecture (`tools/registry.py`, `tools/register_tool.py`)

- **Central Registry** (`registry.ToolRegistry`): Singleton holding all tool definitions with schema, handler, metadata
- **ToolEntry**: name, toolset, schema (JSON Schema dict), handler function, check_fn, requires_env, is_async, emoji
- **Tool Registration**: tools self-register via `registry.register()` on import
- **Discovery**: `discover_builtin_tools()` lazily imports all tool modules
- **Dispatch**: `registry.dispatch(name, args)` handles sync/async bridging automatically
- **Lazy Master Registry** (`register_tool.py`): Legacy `TOOLS` dict with `ToolPolicy` (category, requires_confirmation), `execute_tool()`, `get_tools_description()`
- **Tool Policies**: `safe_read` / `safe_write` / `risky` categories with confirmation gates
- **Async bridging** (`model_tools.py`): Persistent per-thread event loops for cached httpx/AsyncOpenAI clients

### Model Provider System (`run_agent.py:AIAgent`)

The `AIAgent` class (14K lines) is the main agent runtime:

- **API modes**: `chat_completions` | `codex_responses` | `anthropic_messages` | `bedrock_converse`
- **Auto-detection**: URL pattern matching for provider (OpenAI, Anthropic, Bedrock, OpenRouter, etc.)
- **Provider routing**: `agent/auxiliary_client.py:resolve_provider_client()` handles credential resolution
- **Fallback chain**: Primary provider → fallback chain (list of {provider, model})
- **IterationBudget**: Thread-safe iteration counter (default 90 for parent, 50 for subagents)
- **Tool execution**: Sequential or parallel (path-scoped concurrency safety)
- **Streaming**: Delta callbacks, tool streaming for Anthropic on OpenRouter
- **Prompt caching**: Anthropic protocol (system_and_3 strategy, configurable TTL: 5m or 1h)
- **Session persistence**: SQLite via `sara_state.py:SessionDB`

---

## 4. Memory Subsystem (`memory/`)

### Three Layers (`memory/memory_engine.py`)

1. **Profile signals**: Topics, mood, goals, habits, preferences (JSON files, auto-extracted from conversation)
   - Topic matching: 12 categories (coding, music, fitness, gaming, food, travel, study, work, finance, ai, family, movies)
   - Mood tracking: Positive/negative word counters, 4-level scale
   - Goal extraction: 7 regex patterns, habit/preference patterns
   - UnderstandingFrame: Forced-choice reasoning validation

2. **Rolling summary**: Compressed conversation log (14 line max, JSON)

3. **Episodic memories**: Stable preferences, goals, corrections, tasks (100 record deduped FIFO, JSON)

### Semantic Knowledge (`memory/knowledge.py`)
- **ChromaDB** + **sentence-transformers** for vector search
- Document add/delete/update, similarity search with filtering

### Wiki Memory (`memory/wiki_memory.py`)
- **Obsidian-compatible** Markdown vault
- **SQLite FTS5** full-text search
- **Graph edges** for backlinks
- **Git-backed** version control
- Auto-summarization of added content

### User Profile (`memory/user_profile.py`)
- Fields: name, language, timezone, interests, preferences (verbosity, detail level)
- Fact extraction from conversation (20+ patterns)
- Full context string for system prompt injection

### Context Manager (`memory/context_manager.py`)
- JSON-persisted chat history per user
- Configurable max messages (default 20)
- Channel-aware storage (cli, telegram, discord, whatsapp)

---

## 5. Brain (AI Models) (`brain/`)

### `llm_engine.py` — Unified AI Caller
- 3-tier model selection: FAST, SMART, CREATIVE
- Provider chain: Claude → Groq → Ollama (automatic fallback)
- `ask_ai_best()`: Auto-routes based on content analysis
- `ask_ai_with_chain()`: LangChain structured call support
- `get_model_status()`: Shows active models/providers

### `sara_slm.py` — Custom Transformer (~30M params)
- **Architecture**: RoPE, RMSNorm, SwiGLU, GQA (Grouped Query Attention), KV-Cache
- **Config**: 8 layers, 8 heads, 512 embed dim, 2048 context
- **3-stage training**: Knowledge → Instruction → Chat
- Conversation-aware dataset (preserves boundaries)

### `personal_llm.py` — Inference Routing
- Confidence-gated: SLM → LoRA v2 → cloud
- Tool request detection wrapper
- Graceful degradation on low confidence

### `persona_model.py` — LoRA Fine-Tuned TinyLlama
- PEFT/LoRA on TinyLlama-1.1B
- Uses transformers, peft, datasets, accelerate

### Auto-Training (`auto_trainer.py`, `slm_auto_trainer.py`)
- Cloud auto-training for Sara v2 LoRA
- SLM auto-training with conversation data
- Configurable via environment variables

---

## 6. Tool System Detail (`tools/`)

### Tool Categories (by toolset)

| Toolset | Tools | Dependencies |
|---------|-------|-------------|
| web | web_search, web_extract | httpx, bs4 |
| browser | navigate, click, type, scroll, screenshot | playwright |
| terminal | terminal, process | subprocess |
| file | read, write, patch, search | - |
| code_execution | execute_code | docker/sandbox |
| vision | vision_analyze | anthropic/openai |
| image_gen | image_generate | - |
| moa | mixture_of_agents | - |
| tts | text_to_speech | - |
| skills | list_skills, read_skill, manage_skills | - |
| todo | todo | - |
| memory | memory_add, memory_search, memory_list, memory_delete | chromadb |
| session_search | search_sessions | - |
| clarify | clarify | - |
| delegation | delegate_task | - |
| cronjob | create_job, list_jobs, update_job, pause_job, resume_job, run_job | - |
| messaging | send_message, broadcast_message | - |
| computer_use | computer_task, computer_observe, computer_action, computer_screenshot, computer_status, computer_workflow | mss, opencv, ewmh |
| homeassistant | homeassistant_control | requests |
| discord | discord_fetch_messages, discord_search_members, discord_create_thread | discord.py |
| kanban | kanban_create, kanban_list, kanban_move, etc. | - |
| mcp | mcp_call_tool, mcp_list_tools, mcp_connect | - |

### Key Tool Implementation Details
- **terminal_tool.py**: Persistent VM environment with approval/sudo password callbacks
- **browser_tool.py**: Playwright-based with CDP fallback, file upload dialog handling
- **browser_cdp_tool.py**: Chrome DevTools Protocol direct browser control
- **browser_camofox.py**: Camofox browser provider (alternative to Playwright)
- **file_operations.py**: Read, write, edit, patch operations with path security validation
- **web_tools.py**: Google search, web page extraction with readability
- **code_execution_tool.py**: Docker-sandboxed code execution
- **mcp_tool.py**: MCP server connection, tool discovery, tool calling with OAuth

---

## 7. CLI System (`sara_cli/`)

### Command Structure (`sara_cli/main.py`)
```
sara                          Interactive chat
sara chat                     Interactive chat  
sara gateway [start|stop|status|install|uninstall]
sara setup                    Interactive setup wizard
sara logout                   Clear stored auth
sara status                   Component status
sara cron [list|status]       Cron management
sara doctor                   Configuration & dependency check
sara model                    Change model/provider
sara sessions browse          Session picker
sara honcho [...]             Honcho AI memory integration
sara acp                      ACP server for editor integration
sara version                  Show version
sara update                   Update to latest
sara uninstall                Uninstall
```

### Slash Commands (`sara_cli/commands.py`)
- `/memory`, `/skill`, `/todo`, `/kanban`, `/sessions`, `/model`, `/usage`, `/status`
- `/voice`, `/tts`, `/image`, `/cron`, `/doctor`, `/feedback`, `/steer`, `/interrupt`
- `/delegate`, `/checkpoint`, `/reset`, `/diff`, `/revert`, `/bug`

### Legacy CLI (`cli.py`)
- prompt_toolkit interactive TUI with fixed input area
- Rich formatting, ASCII art branding, spinner
- Theme/skin system (`skin_engine.py`)
- Session management with history

---

## 8. Gateway System

### Architecture
- **TUI Gateway** (`tui_gateway/server.py`): WebSocket server for TUI clients
- **Gateway platforms** (`gateway/platforms/`): Adapters for CLI, Telegram, Discord, WhatsApp
- **Gateway hooks** (`gateway/builtin_hooks/`): Pre/post-processing hooks
- **Session management**: Platform-agnostic session key, message routing, delivery

### Platform Integrations
- **Telegram** (`integrations/telegram_bot.py`): Full onboarding (name/lang/interests/timezone), build workflow with inline buttons, approval callbacks, all commands
- **Discord** (`integrations/discord_bot.py`): Discord bot with channel-aware dispatch
- **WhatsApp** (`integrations/whatsapp_bot.py`): WhatsApp via Twilio/whatsapp-web.js

---

## 9. Database & State

### `sara_state.py:SessionDB`
- **SQLite with WAL mode**, foreign keys ON
- **Tables**: `sessions` (metadata, billing, token counts), `messages` (role, content, tool_calls, reasoning), `state_meta` (key-value), `schema_version`
- **Session fields**: source, model, system_prompt, parent_session_id, message_count, tool_call_count, token usage, billing info, title
- **Message fields**: role, content, tool_call_id, tool_calls, tool_name, token_count, finish_reason, reasoning, codex fields
- **Features**: session CRUD, message append/replace, search, title management, auto-prune, lineage resolution, ghost session cleanup

### `core/database.py`
- SQLite with WAL mode, schema versioning, dependency injection
- Used by Phase A orchestration

### `maestro/kanban.py`
- SQLite-backed Kanban board (SQLAlchemy)
- 6 columns: backlog, ready, in_progress, review, completed, archived
- Priorities, metrics, CLI management

---

## 10. Key Dependencies (`pyproject.toml`)

### Core Runtime
- python-dotenv, requests, beautifulsoup4, pydantic, httpx, pyyaml
- prompt-toolkit, simple-term-menu
- fastapi, uvicorn (gateway)

### AI Providers
- anthropic, groq, openai
- langchain (core, community, ollama)

### Local Models (optional)
- torch, transformers, peft, datasets, accelerate, bitsandbytes

### Memory
- chromadb, sentence-transformers

### Integrations
- python-telegram-bot, discord.py, twilio

### Desktop Automation
- playwright, mss, opencv-python-headless, ewmh, python-xlib, pynput, pyperclip, pytesseract

### Other
- boto3, psutil, feedparser, pdfplumber, pywhatkit, SpeechRecognition, Pillow, plyer, flask

---

## 11. Key Constants & Configuration (`sara_constants.py`)

- **`get_sara_home()`**: Returns `~/.sara/` (or `SARA_HOME` env override), profile-aware
- **Platform detection**: `is_termux()`, `is_wsl()`, `is_container()` — import-safe
- **Network**: `apply_ipv4_preference()` — monkey-patches socket for broken IPv6
- **Reasoning efforts**: `minimal`, `low`, `medium`, `high`, `xhigh`
- **Well-known paths**: `get_config_path()`, `get_skills_dir()`, `get_env_path()`
- **URL constants**: OPENROUTER_BASE_URL, AI_GATEWAY_BASE_URL

---

## 12. Logging System (`sara_logging.py`)

- **3 log files**: `agent.log` (INFO+, all activity), `errors.log` (WARNING+, quick triage), `gateway.log` (INFO+, gateway-only)
- **Rotating file handlers** with secret redaction (`RedactingFormatter`)
- **Session context**: Thread-local `[session_id]` injected into all log records
- **Component filtering**: gateway-specific records filtered to `gateway.log`
- **Managed mode**: Group-writable perms (0660) for shared log access
- **Noisy logger suppression**: openai, httpx, httpcore, asyncio, etc. at WARNING
- **Config-driven**: `logging.*` settings from `config.yaml`

---

## 13. Build Workflow (`agent/build_workflow.py`)

5-stage state machine for project generation:
```
IDLE → DISCUSSING → PLANNING → AWAITING_APPROVAL → BUILDING → DONE
```

- **Trigger**: "build a website", "create an app", "make a bot", etc.
- **Discussing**: 3 questions (purpose, users, tech preference)
- **Planning**: LLM generates project plan (name, framework, stack, pages, features, build steps)
- **Approval**: User approves or requests changes (re-plan)
- **Building**: Executes scaffold/generate/install/run steps via shell + LLM file generation
- **Output**: `~/sara_projects/<project_name>/`

---

## 14. Multi-Agent System (`agent/multi_agent.py`)

Lightweight coordinator with 4 default agents:
- **planner**: Break complex requests into ordered work
- **researcher**: Gather facts, options, context
- **builder**: Design implementation steps
- **reviewer**: Review outputs for bugs, gaps, risks

Uses `ThreadPoolExecutor` for parallel agent execution, then synthesizes results via LLM.

---

## 15. Phase A (core/) vs Phase B (maestro/)

| Aspect | Phase A (`core/`) | Phase B (`maestro/`) |
|--------|------------------|---------------------|
| Purpose | Concurrent agent orchestration | Higher-level workflow & collaboration |
| Key class | `BaseAgent` hierarchy | `Conductor`, `AgentSwarm`, `WorkflowEngine` |
| Communication | EventBus (async pub/sub) | Swarm message bus + consensus |
| Task model | `AgentTask` (role-based) | `KanbanTask`, `WorkflowStep` |
| Persistence | SQLite via `Database` | SQLite via Kanban |
| Scheduling | `APScheduler` + BackgroundTaskEngine | Workflow engine (sequential/parallel/conditional) |
| Intelligence | Basic agent specialization | Model routing, reflection, self-correction |

---

## 16. Coding Conventions

- **Type annotations**: Full Python 3.11+ type hints (`str | None`, `list[str]`, `dict[str, Any]`)
- **Imports**: stdlib → third-party → local (grouped with blank lines)
- **Logging**: Module-level `logger = logging.getLogger(__name__)`
- **Error handling**: Defensive with specific exception types, `logger.debug()` for expected failures
- **Thread safety**: `threading.Lock` / `threading.RLock` for shared state
- **Config**: `config.yaml` under `~/.sara/` loaded via `sara_cli.config`
- **Secrets**: Environment variables (`.env` in `~/.sara/`), redacted in logs
- **Pydantic**: Used in core/ and maestro/ for model validation
- **Dataclasses**: Used in agent/ and tools/ for lightweight data structures
- **Lazy imports**: Heavy SDKs (openai, torch, etc.) imported lazily to speed startup

---

## 17. Build & Install

```bash
pip install -r requirements.txt
# Or with optional dependencies:
pip install -e ".[all]"     # Full install with torch, transformers, etc.
pip install -e ".[computer-use]"  # Desktop automation deps
pip install -e ".[termux]"       # Termux Android deps

# Run:
sara                    # Production CLI
python cli.py           # Legacy TUI
python run_agent.py     # Programmatic embedding
```

---

## 18. Quick Reference: Key Classes & Functions

| Module | Symbol | Purpose |
|--------|--------|---------|
| `agent/agent_loop.py` | `process_turn()` | Main turn processing entry point |
| `agent/planner.py` | `plan_complex_task()` | LLM-based task planning |
| `agent/planner.py` | `execute_plan()` | Plan execution with dependency resolution |
| `agent/planner.py` | `Subtask`, `ToolCall`, `ExecutionPlan`, `AgentResponse` | Core plan data structures |
| `agent/observer.py` | `review_execution()` | Worker result review & response composition |
| `agent/multi_agent.py` | `MultiAgentRuntime` | Multi-agent coordinator |
| `agent/multi_agent.py` | `delegate_task()` | Task delegation entry point |
| `agent/build_workflow.py` | `start_session()`, `handle_input()`, `execute_next_step()` | 5-stage project builder |
| `brain/llm_engine.py` | `ask_ai()`, `ask_ai_smart()`, `ask_ai_creative()`, `ask_ai_best()` | Unified AI caller |
| `brain/personal_llm.py` | `ask_personal()`, `is_tool_request()` | Local inference routing |
| `brain/sara_slm.py` | `SaraSLM`, `train_slm()` | Custom transformer model |
| `brain/persona_model.py` | `FineTunedModel` | LoRA fine-tuned TinyLlama |
| `core/models.py` | `AgentTask`, `AgentRole`, `EventType` | Phase A data models |
| `core/agents.py` | `BaseAgent`, `PlannerAgent`, `ResearchAgent`, etc. | Phase A agent types |
| `core/events.py` | `EventBus` | Async event bus |
| `core/orchestrator.py` | `AgentOrchestrator` | Concurrent agent lifecycle |
| `core/tasks.py` | `BackgroundTaskEngine` | Persistent background tasks |
| `maestro/models.py` | `KanbanTask`, `WorkflowStep`, `SwarmMessage`, etc. | Phase B data models |
| `maestro/conductor.py` | `Conductor` | Phase A+B wiring |
| `maestro/swarm.py` | `AgentSwarm` | Multi-agent collaboration |
| `maestro/planner.py` | `MaestroPlanner` | Hierarchical goal decomposition |
| `maestro/router.py` | `ModelRouter` | Capability-based model selection |
| `maestro/kanban.py` | `KanbanBoard` | SQLite-backed task board |
| `maestro/workflow.py` | `WorkflowEngine` | Sequential/parallel workflow execution |
| `maestro/reflection.py` | `ReflectionEngine` | Self-correction & critique |
| `maestro/monitor.py` | `Monitor` | File/repo/log watchers |
| `memory/memory_engine.py` | `auto_update_profile()`, `finalize_turn_memory()`, `get_rich_context_string()` | Layered memory |
| `memory/wiki_memory.py` | `WikiMemory` | Obsidian-compatible long-term memory |
| `memory/context_manager.py` | `add_message()`, `get_context()` | Chat history management |
| `memory/knowledge.py` | `KnowledgeBase` | ChromaDB semantic search |
| `memory/user_profile.py` | `add_fact()`, `get_full_context_string()` | User profile management |
| `memory/automation_engine.py` | `AutomationEngine` | Automation rules engine |
| `tools/registry.py` | `ToolRegistry`, `register()`, `dispatch()` | Central tool registry |
| `tools/register_tool.py` | `TOOLS`, `execute_tool()`, `get_tool_policy()` | Master tool registry |
| `model_tools.py` | `get_tool_definitions()`, `handle_function_call()` | Tool orchestration |
| `toolsets.py` | `resolve_toolset()`, `validate_toolset()` | Toolset resolution |
| `run_agent.py` | `AIAgent` | Main agent runtime (14K lines) |
| `run_agent.py` | `IterationBudget` | Thread-safe iteration counter |
| `cli.py` | `main()` | Legacy TUI entry point (12K lines) |
| `sara_cli/main.py` | `cli_main()` | Production CLI entry point |
| `sara_state.py` | `SessionDB` | SQLite session/state store |
| `sara_logging.py` | `setup_logging()`, `set_session_context()` | Logging system |
| `sara_constants.py` | `get_sara_home()`, `is_wsl()`, `is_termux()`, `is_container()` | Constants & platform detection |
| `utils.py` | `atomic_json_write()`, `atomic_yaml_write()`, `safe_json_loads()` | Shared utilities |
