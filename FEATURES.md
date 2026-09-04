# Sara Agent Features

Sara Agent is a self-improving personal AI agent with persistent memory, reusable skills, tool use, scheduled automation, multi-agent delegation, and a shared messaging gateway. It can run locally or in managed environments and can be used from the terminal, web UI, desktop app, or connected chat platforms.

## User Interfaces

### Command-Line Interface

The `sara` command provides the primary interactive agent experience, including:

- Streaming conversations and tool calls.
- One-shot prompts and interactive sessions.
- Model and provider selection.
- Profiles, goals, sessions, logs, and status commands.
- Setup, diagnostics, backup, completion, and uninstall workflows.
- Gateway, webhook, voice, browser, cron, plugin, skill, and MCP configuration.

### Web Interface

The web application (`web/`) provides graphical access to:

- Chat and session history.
- Models and provider configuration.
- Profiles, skills, plugins, cron jobs, logs, and analytics.
- Environment settings, OAuth providers, platform connections, and tool calls.
- Themes and localization.

Built with React, TypeScript, and Vite.

### Terminal UI

The terminal UI (`tui_gateway/` + `ui-tui/`) offers a richer full-screen experience with:

- Python backend (`tui_gateway/`) handling websocket transport, event publishing, slash commands, and server.
- TypeScript/React frontend (`ui-tui/`) with Ink-based rendering, streaming output, tool-call rendering, and keyboard interaction.
- Slash commands, event-driven architecture, and theming support.
- Packages for shared utilities and type definitions.

### Desktop App

`apps/desktop/` is a premium Electron, React, and TypeScript desktop app with:

- A unified chat view with a hero dashboard and floating glass composer.
- Full-duplex voice conversation (STT + TTS with multiple providers).
- A theme system with 6 built-in skins, VS Code theme import, and light/dark/system mode.
- Internationalization with 8 languages (English, Chinese, Traditional Chinese, Japanese, Korean, French, German, Spanish).
- Custom ant-inspired geometric SVG logo and premium dark UI with glassmorphism panels.
- Messaging-platform plugins, system-tray, auto-launch, and settings dialogs.

Desktop platform support depends on each plugin's credentials and runtime dependencies.

## Messaging Gateway

One gateway connects the agent runtime to multiple communication platforms while preserving platform-aware sessions, delivery, pairing, and channel identity.

Gateway adapters are included for:

- Telegram and Discord.
- Slack, WhatsApp, Signal, Matrix, and Mattermost.
- Email, SMS, generic webhooks, and an API server.
- DingTalk, Feishu, WeCom, and Weixin.
- BlueBubbles and Home Assistant.
- Yuanbao and additional platform-specific integrations.

Platform plugins also available for: Microsoft Teams, ntfy push notifications, SimpleX Chat, Google Chat, Raft workspaces, Photon Spectrum (iMessage), IRC, and QQ Bot.

The gateway also supports scheduled delivery, runtime status, restart handling, channel lookup, session context, media-aware delivery, and platform-specific hooks. An adapter being present does not remove the need for its external service, credentials, or optional dependencies.

## Models And Providers

Sara is not tied to one model vendor. The runtime supports multiple model families and OpenAI-compatible endpoints, with configuration for provider credentials, model selection, fallback behavior, and credential pools.

Provider capabilities include:

- OpenAI-compatible APIs.
- Anthropic, Groq, Amazon Bedrock, and OpenRouter-style services.
- Local models through Ollama and compatible runtimes.
- Provider and model switching from the CLI or web UI.
- Fallback providers, rate-limit tracking, and credential rotation.
- Context compression and prompt caching where supported.
- Optional personal model training workflows.

### Model Provider Plugins

29 model provider plugins are available in `plugins/model-providers/`:

| Provider | Type | Notes |
|----------|------|-------|
| Anthropic (Claude) | API | Custom x-api-key auth |
| OpenAI Codex | Responses API | OAuth external auth |
| Google Gemini | API + OAuth | AI Studio + Cloud Code |
| DeepSeek | API | Thinking-mode handling |
| OpenRouter | Aggregator | Reasoning config |
| HuggingFace Inference | API | Fallback models |
| AWS Bedrock | API | Custom profile |
| Custom / Ollama | Local | OpenAI-compatible |
| xAI Grok | Responses API | - |
| NovitaAI | API | Fallback models |
| NVIDIA NIM | API | - |
| GitHub Copilot | API | Editor headers |
| Alibaba DashScope | API | International |
| Alibaba Coding Plan | API | Dedicated tier |
| Arcee AI | API | - |
| Microsoft Foundry | API | OpenAI-compatible |
| Copilot ACP | Subprocess | External ACP |
| GMI Cloud | API | Custom headers |
| Kilo Code | API | - |
| Moonshot Kimi | API | Global + China |
| MiniMax M-series | API | Global + China + OAuth |
| Nexvisora Research | API | Product tags |
| Ollama Cloud | API | - |
| OpenCode Zen/Go | API | Per-model routing |
| Qwen Portal | OAuth | Message normalization |
| StepFun Step Plan | API | - |
| Xiaomi MiMo | API | Health check disabled |
| Z.AI / GLM | API | Fallback models |

Exact model availability is determined by configured credentials, provider access, installed dependencies, and current service availability.

## Persistent Memory

Sara can retain useful context across sessions, including profile facts, conversation summaries, project knowledge, decisions, and reflections.

### Markdown-First Wiki Memory

The wiki memory subsystem uses a strict authority model:

```text
Markdown Wiki = source of truth
Knowledge Graph = relationship layer
Search/Vector Index = rebuildable accelerator
```

It provides:

- Separate memory spaces for different projects or identities.
- Obsidian-compatible Markdown pages and internal links.
- Episodic, semantic, identity, daily, map-of-content, and reflection pages.
- FTS5 search through a derived SQLite index.
- A derived knowledge graph with inspectable nodes and edges.
- Retrieval ranked by text relevance, relationships, recency, and importance.
- Provenance and retrieval reasons with each result.
- Consolidation of short-term events into durable memories and reflections.
- Git diff, commit, and rollback helpers for the authoritative Markdown vault.

Derived indexes can be rebuilt without replacing Markdown as the source of truth.

### Optional Memory Providers

Plugin integrations are available for external or experimental memory systems:

| Provider | Description | Dependencies |
|----------|-------------|-------------|
| Honcho | AI-native cross-session user modeling, dialectic Q&A, peer cards | `honcho-ai` |
| Mem0 | Server-side LLM fact extraction, semantic search, reranking | `mem0ai` |
| Hindsight | Knowledge graph, entity resolution, multi-strategy retrieval | `hindsight-client` |
| Supermemory | Semantic long-term memory, profile recall | `supermemory` |
| OpenViking | Context database by ByteDance, filesystem hierarchy | httpx |
| RetainDB | Cloud memory API, hybrid search (Vector + BM25) | `requests` |
| ByteRover | Persistent knowledge tree via `brv` CLI | `brv` CLI |
| Holographic | Local SQLite fact store, FTS5, trust scoring, HRR retrieval | None (built-in) |

Their availability depends on installation and configuration.

## Skills And Learning

Sara uses skills as portable procedural knowledge. Skills can be bundled with the repository, installed as optional packs, or created and refined from experience.

### Built-in Skills

Skills are organized by category in `skills/`:

| Category | Skills |
|----------|--------|
| **Software Development** | Plan, subagent-driven dev, TDD, writing plans, systematic debugging, Python debugpy, code review, skill authoring, spike/experiments, Node.js inspect debugger, TUI debugging |
| **GitHub** | Code review, PR workflow, issues, repo management, codebase inspection, auth setup |
| **Creative** | Claude design, p5.js sketches, HTML mockups, architecture diagrams, songwriting/AI music, ASCII art |
| **Data Science** | Jupyter live kernel (hamelnb) |
| **Note-Taking** | Obsidian vault read/search/create |
| **Apple/macOS** | iMessage, Apple Notes, Apple Reminders, FindMy |
| **Media** | YouTube transcripts/summaries |
| **Gaming** | Pokemon emulator, Minecraft modpack server |
| **MLOps** | Unsloth, Axolotl, TRL fine-tuning, lm-eval-harness, Weights & Biases |
| **Diagramming** | Flowcharts, Excalidraw |
| **Dogfood** | Exploratory QA, bug finding |
| **inference.sh** | 150+ AI apps (image gen, video, LLMs, 3D, audio) |

Skill features include:

- Discovering and reading skills from `skills/` and `optional-skills/`.
- Loading specialized instructions only when relevant.
- Reusing scripts, templates, references, and assets packaged with a skill.
- A Skills Hub workflow for discovery and management.
- Agent-curated learning and skill improvement across sessions.

### Optional Skills

Additional skills in `optional-skills/` are not activated by default:

| Category | Skills |
|----------|--------|
| **Autonomous AI Agents** | Blackbox AI, Honcho AI CLI integrations |
| **Blockchain** | Base, Solana |
| **Communication** | 1-3-1 Rule framework |
| **Creative** | Meme generation, Blender MCP, concept diagrams |
| **Dogfood** | Adversarial UX testing |
| **Email** | AgentMail integration |
| **MCP** | FastMCP scaffolding, MCPorter |
| **Migration** | OpenClaw to Hermes migration |
| **MLOps** | HuggingFace Accelerate, LLaVA vision, TorchTitan training |
| **Productivity** | Canvas LMS, Here/Now location, Memento flashcards, Shopify, SiYuan notes, telephony |
| **Research** | Bioinformatics, drug discovery, DuckDuckGo search, GitNexus explorer, parallel CLI, QMarkdown, Scrapling |
| **Security** | 1Password, OSINT forensics, Sherlock username search |
| **Web Development** | Page Agent web development |

## Tools And Extensibility

Sara can combine built-in tools, plugins, MCP servers, browser automation, and managed execution environments.

### Tool Categories

There are 70+ tool modules in `tools/`:

| Category | Tools |
|----------|-------|
| **Web & Browser** | `web_search`, `web_extract`, `browser_navigate`, `browser_click`, `browser_type`, `browser_scroll`, `browser_screenshot`, CDP passthrough, dialog handler, Camofox anti-detection browser, URL safety, website policy |
| **Files & Terminal** | `read`, `write`, `patch`, `search`, `terminal` (local/Docker/SSH/Modal), file state coordination, fuzzy match, binary extensions, credential files, path security |
| **Vision & Media** | `vision_analyze`, `screenshot`, OCR, computer vision, image generation, transcription (STT), text-to-speech (TTS), audio controls, media keys |
| **Code & AI** | `code_execute` (PTC), `ai_generate`, `mixture_of_agents`, RL training tool, patch parser |
| **Memory & Knowledge** | `memory_add`, `memory_search`, `memory_list`, `memory_delete`, `session_search`, `news`, `knowledge_search` |
| **Task Management** | `todo`, `kanban`, `reminder` (toast notifications), `clarify` (interactive Q&A) |
| **Delegation & Skills** | `delegate_task`, `list_skills`, `read_skill`, `manage_skills`, skill manager, skills guard, skill usage tracker |
| **System & Monitor** | `system_info`, `open_app`, `shutdown`, `process`, `cpu`, `ram`, `disk`, clipboard, notifications, debug helpers |
| **Communication** | Telegram, Discord, WhatsApp, Email, plugin registry, send message |
| **Automation** | Cron job management, routine management, kanban workflows |
| **MCP** | MCP client (Model Context Protocol), MCP OAuth 2.1, OAuth manager |
| **Computer Use** | `computer_task`, `computer_observe`, `computer_action`, `computer_screenshot`, `computer_status`, `computer_workflow` |
| **Platform Specific** | Feishu Drive, Feishu Doc, Yuanbao, Home Assistant, Discord |
| **Approval & Safety** | `approval` (dangerous command detection), `slash_confirm`, Tirith security scanner, skills guard |

Plugin manifests and MCP connections expose capabilities; individual tools may still require credentials, a running service, system packages, or user approval.

## Vision And Browser Workflows

The vision pipeline can prepare images for models, inspect screenshots, route vision requests, and support GUI-oriented agent workflows. Browser tooling can search, extract, navigate, and interact with pages through supported local or remote browser providers.

These workflows can be combined for tasks such as:

- Reading and reasoning about screenshots.
- Extracting text with OCR.
- Inspecting application state.
- Navigating websites and completing multi-step browser tasks.
- Using visual context during desktop-agent operations.

## Automation

Sara supports both scheduled and reusable automation:

- Named routines and workflows.
- Cron-based schedules (`cron/scheduler.py`, `cron/jobs.py`).
- Delivery of scheduled results to connected platforms.
- Startup and background gateway services.
- Hooks for lifecycle and platform events.
- Saved goals and structured project workflows.

## Delegation And Multi-Agent Work

Complex tasks can be split into isolated workstreams and delegated to sub-agents. Delegated work can cover planning, research, implementation, and review, then return results to the coordinating agent.

The agent runtime supports:

- Parallel sub-agent work where appropriate.
- Scoped context and task instructions.
- Tool use inside delegated work.
- Result synthesis by the parent agent.
- Programmatic multi-step tool execution.

### Core Agent Framework (Phase A)

The `core/` package provides a structured multi-agent orchestration system:

- **AgentOrchestrator** - Concurrent execution of specialized agents with event-driven coordination.
- **Specialized Agents** - Pre-defined agent types for different roles (research, code, review, etc.).
- **Event Bus** - Pub/sub event system for inter-agent communication.
- **Task System** - Typed tasks with status tracking, progress reporting, and cancellation.
- **Watchers** - Background monitors for file changes, system events, and notifications.
- **Scheduler** - APScheduler adapter for recurring task creation.
- **Database** - SQLite-backed persistence for agent state and results.

### Maestro Multi-Agent Orchestration (Phase B)

The `maestro/` package provides advanced orchestration capabilities:

- **Swarm** - Dynamic agent swarm coordination with task distribution and result aggregation.
- **Kanban** - Visual workflow management with columns, cards, and state transitions.
- **Workflow** - Structured multi-step workflow definitions and execution.
- **Planner** - Decomposition of complex goals into actionable subtasks.
- **Router** - Intelligent task routing to the most capable sub-agent.
- **Reflection** - Post-execution analysis and improvement suggestions.
- **Conductor** - Central coordinator managing the full orchestration lifecycle.
- **Monitor** - Real-time progress tracking and alerting across agents.

## Brain & Personal AI

Sara includes a self-contained personal AI subsystem (`brain/`) for on-device learning, fine-tuning, and inference:

### Small Language Model (SLM)

- **sara_slm.py** - Custom 30M-parameter transformer trained from scratch on conversation data.
- **slm_auto_trainer.py** - Automated training pipeline with checkpointing and evaluation.
- **Confidence gating** - SLM responses are only used when confidence exceeds a configurable threshold.

### Personal LLM Fine-Tuning

- **personal_llm.py** - TinyLlama fine-tuning pipeline using PEFT/LoRA.
- **personal_trainer.py** - Orchestrates data preparation, training, and model export.
- **auto_trainer.py** - Automatic scheduling of training runs based on new conversation data.
- **dataset_downloader.py** - Downloads and prepares training datasets from various sources.

### LLM Engine & Analysis

- **llm_engine.py** - Unified inference interface supporting multiple backends (Claude, Groq, Ollama, local).
- **persona_model.py** - User persona modeling for personalized responses.
- **trend_analyzer.py** - Analyzes conversation trends to identify topics, sentiment, and patterns.

## Execution Environments

Terminal work can run through supported local or managed backends, including:

- Local execution.
- Docker and SSH environments.
- Daytona, Modal, and Singularity integrations.

Backend availability depends on installed software, service credentials, and host configuration.

## Safety And Approvals

Sara distinguishes read-only or low-risk actions from actions that can change the machine or communicate externally.

Actions that may require approval include:

- Running commands or installing packages.
- Creating, changing, or deleting files.
- Controlling applications or the operating system.
- Sending messages or invoking external services.
- Browser and GUI automation.
- Shutdown, restart, and other disruptive operations.

The approval layer, tool gateway, authorization rules, and execution-environment boundaries work together to limit unintended actions.

## Computer Use

Sara can directly control the desktop through vision, accessibility, and action execution — a complete Linux desktop agent capability built on top of the existing Sara architecture.

### Live Desktop Vision

- **Real-time screen capture** — 1–5 FPS screen streaming via `mss` with base64 encoding for vision AI.
- **Multi-monitor support** — Enumerate and capture all connected monitors independently.
- **Active window tracking** — EWMH/X11-based window listing and active-window detection (falls back to `xdotool`/`wmctrl`).
- **UI element detection** — Priority chain: AT-SPI → OCR (Tesseract) → Vision AI, producing structured JSON with element types, text, bounds, and confidence scores.
- **Element coordinate mapping** — Every detected element includes its on-screen bounding box for precise mouse targeting.

### Accessibility Layer

Before OCR or vision AI, Sara accesses the native Linux accessibility tree:

- **AT-SPI2 support** (`python3-pyatspi`) — Full application, window, and widget tree access on Linux desktops.
- **Native UI tree** — Flattened or hierarchical tree representation of all accessible UI elements.
- **Button, menu, and input detection** — Role-based classification from the accessibility tree (push button, text entry, combo box, menu, tab, dialog, etc.).
- **Graceful fallback** — When AT-SPI is unavailable, detection falls through to OCR → Vision AI.

### Computer Action Engine

The `ComputerAgent` (`backend/computer_use/`) provides a complete desktop action system:

| Action | Description |
|---------|-------------|
| `move_mouse` | Move pointer to absolute coordinates |
| `click` | Click at position (left/right/middle, single/double) |
| `double_click` | Double-click at position |
| `drag` | Click-drag from start to end coordinates |
| `scroll` | Scroll vertically or horizontally |
| `type_text` | Type text at current focus |
| `press_key` | Press a single key (Enter, Tab, Escape, etc.) |
| `hotkey` | Press a key combination (Ctrl+C, Alt+Tab, etc.) |

Every action returns structured results including before/after state and screenshots.

### Task Execution Loop

Sara follows a rigorous Observe→Analyze→Plan→Execute→Verify→Repeat cycle for desktop tasks:

1. **Observe** — Capture screenshot, window info, UI tree, and detected elements.
2. **Analyze** — LLM-based screen understanding: what's on screen, what needs to happen.
3. **Plan** — Decompose task into a sequence of desktop actions with coordinates.
4. **Execute** — Run each action through the `ActionEngine` with before/after state capture.
5. **Verify** — Compare before/after screenshots, check element presence, use vision AI for task completion.
6. **Repeat** — If incomplete, loop with updated observation.

### Screen Understanding

Structured JSON output for detected UI elements:

```json
{"type": "button", "text": "Save", "bounds": {"x": 100, "y": 200, "width": 80, "height": 30}, "confidence": 0.95, "source": "atspi"}
```

Detectable types: `button`, `input`, `menu`, `tab`, `dialog`, `notification`, `link`, `checkbox`, `dropdown`, `window`, `label`.

### Sara Overlay

Optional always-on-top desktop assistant overlay (`backend/computer_use/overlay/`):

- **Premium Red + Black theme** — `#0a0a0a` background with `#ff1744` accent.
- **Status display** — Current task, action, permission requests, agent thoughts, and action history.
- **Permission buttons** — Approve/Deny buttons for Smart Mode action requests.
- **tkinter-based** — Works on any Linux desktop with Python's built-in tkinter.
- **Configurable opacity** — Default 92% opacity with always-on-top behavior.

### Voice Driven Computer Use

Voice commands route through Sara's existing STT pipeline to control the desktop:

- **Wake word** — "Hey Sara" or "Sara" triggers command listening.
- **Commands**: "open VS Code", "search YouTube for AI news", "create React project", "click", "type", "scroll", "screenshot", "close app", "status".
- **App launcher** — Opens applications via the existing `system_tools.open_app()`.
- **Web search** — Opens browser searches for YouTube, Google, GitHub, Amazon.
- **TTS feedback** — Spoken confirmation of each action via `tts_tool`.

### Memory For UI Actions

Persistent memory (`backend/computer_use/memory/`) for:

- **App layouts** — Remember window positions and element locations per application.
- **Frequent actions** — Track which buttons/locations are clicked most often.
- **Saved workflows** — Name and reuse multi-step action sequences.
- **Action history** — Full log of performed actions with timestamps and success status.

### Permission Levels

Three modes control what the Computer Agent can do:

| Mode | Behavior |
|------|----------|
| **Safe** | Read-only observation only. No mouse, keyboard, or system actions. |
| **Smart** | (Default) Actions proceed but risky operations prompt for approval via the overlay or callback system. |
| **Autonomous** | Full control without prompts. **Disabled by default** — must be explicitly enabled via `enable_autonomous()`. |

The permission system integrates with Sara's existing approval framework (`tools/approval.py`).

### Tool Integration

Six tools registered in the `computer_use` toolset:

| Tool | Description |
|------|-------------|
| `computer_task` | Execute a full desktop automation task with the observe-plan-execute-verify loop |
| `computer_observe` | Observe current desktop state (window, elements, accessibility tree) |
| `computer_action` | Execute a single desktop action (click, type, move, etc.) |
| `computer_screenshot` | Capture a desktop screenshot (base64 or file) |
| `computer_status` | Check Computer Use subsystem availability |
| `computer_workflow` | Manage saved desktop automation workflows |

Availability depends on: `pynput` (mouse/keyboard control), `mss` (fast screen capture), and optional `python3-pyatspi` (accessibility tree).

### Implementation

- `backend/computer_use/` — Core Computer Use package with sub-modules for vision, accessibility, executor, planner, verifier, memory, and overlay.
- `tools/computer_use_tool.py` — Agent tools registered in the `computer_use` toolset.
- `backend/computer_use/config.py` — Configuration via env vars or dict.
- `backend/computer_use/permissions.py` — Safe, Smart, and Autonomous permission levels.
- `backend/computer_use/voice_driven.py` — Wake-word-triggered voice command handler.

## Desktop App

### Premium UI

The desktop app (`apps/desktop/`) features a redesigned premium interface inspired by Linear, Raycast, and Arc Browser:

- **Dark-first aesthetic** — `#050505` base with `#ff2d55` red accent, glassmorphism panels (`backdrop-filter: blur(24px)`), and a custom ant-inspired geometric SVG logo.
- **Spatial layout** — Three-panel layout: glass sidebar (brand header + sessions), center (hero dashboard with floating composer + chat thread), right sidebar (activity/system).
- **Floating composer** — 24px rounded glass chat input with voice, attachment, and command controls.
- **Typography** — Space Grotesk for headings, Inter for UI, JetBrains Mono for code.

### Theme System

- **6 built-in skins** — neXvisora, midnight, ember, mono, cyberpunk, and slate — each with light and dark variants.
- **Color mode** — Light, Dark, and System (follows OS appearance) toggle via `Shift+X`.
- **CSS cascade** — All UI colors derive from `--theme-*` seed variables via `color-mix()` at runtime, so `applyTheme()` propagates skin changes instantly across every surface.
- **VS Code theme import** — Paste a Marketplace extension ID to convert its color theme into a desktop palette.
- **Per-profile themes** — Each profile keeps its own theme and mode.

### Voice Conversation

Full-duplex voice conversation with Voice Activity Detection (VAD):

- **Dictation mode** — Record → transcribe → insert text into composer.
- **Conversation mode** — Listen → transcribe → submit → speak response → loop.
- **STT providers** — local (faster-whisper), Groq, OpenAI, Mistral, xAI, ElevenLabs.
- **TTS providers** — edge-tts, OpenAI, ElevenLabs, xAI, Minimax, Mistral, Gemini, neural TTS.
- **Backend API** — `POST /api/audio/transcribe` and `POST /api/audio/speak` with 120s timeout.

### Internationalization

- **8 supported locales** — English, Simplified Chinese, Traditional Chinese, Japanese, Korean, French, German, Spanish.
- **Partial translation support** — Missing keys automatically fall back to English via `defineLocale()`.
- **Locale aliases** — Browser/OS locale codes normalized to canonical locale IDs.

### Backend API Compatibility

The Electron desktop app communicates with the backend via REST endpoints proxied through the main process:

- Session archiving, messaging platform management, provider validation, toolset management, and cron job runs are all implemented.
- Voice STT/TTS endpoints with configurable provider routing.
- Authentication token normalization and backend readiness signaling.

## Plugin Ecosystem

Sara has a three-part plugin system: platform adapters, memory providers, and model providers.

### Platform Plugins

Available in `plugins/platforms/`:

| Plugin | Description | Requirements |
|--------|-------------|-------------|
| Teams | Microsoft Teams gateway | Azure app registration |
| ntfy | Push notifications | ntfy topic |
| SimpleX | Decentralized chat | SimpleX daemon |
| Home Assistant | Smart home | HA token |
| Google Chat | Google Workspace | GCP project |
| Discord | Discord bot | Bot token (7119 line adapter) |
| Raft | Workspace integration | Raft profile |
| Photon | iMessage via Photon | Photon credentials |
| Mattermost | Team chat | Mattermost server |
| IRC | Internet Relay Chat | IRC server (zero deps) |
| QQ Bot | QQ platform | QQ credentials |

### Memory Plugins

8 memory backends available as plugins in `plugins/memory/` (detailed in the Persistent Memory section above).

### Model Provider Plugins

29 model provider plugins in `plugins/model-providers/` (detailed in the Models and Providers section above).

## Nix/NixOS Support

The `nix/` directory provides Nix expressions for building and deploying Sara:

- `sara-agent.nix` — Main package definition for the Sara agent.
- `web.nix` — Web UI package for Nix.
- `tui.nix` — TUI package for Nix.
- `python.nix` — Python environment with all dependencies.
- `nixosModules.nix` — NixOS module for system-level integration.
- `devShell.nix` — Development shell with all tooling.
- `packages.nix` — Package registry and build targets.
- `overlays.nix` — Nixpkgs overlays for custom dependencies.
- `lib.nix` — Utility functions for build configurations.
- `configMergeScript.nix` — Configuration merging for deployment.
- `checks.nix` — CI checks and validation expressions.

## CLI Commands

The `sara_cli/` package provides 60+ commands:

| Command | Description |
|---------|-------------|
| `sara` | Main interactive session |
| `sara oneshot` | Single-prompt execution |
| `sara session` | Session management |
| `sara model` | Model/switch selection |
| `sara provider` | Provider configuration |
| `sara profile` | Profile management |
| `sara goal` | Goal management |
| `sara setup` | Initial setup wizard |
| `sara doctor` | Diagnostics |
| `sara backup` | Backup agent data |
| `sara completion` | Shell completion |
| `sara uninstall` | Remove agent |
| `sara gateway` | Gateway management |
| `sara webhook` | Webhook configuration |
| `sara voice` | Voice settings |
| `sara browser` | Browser connection |
| `sara cron` | Cron job management |
| `sara plugin` | Plugin management |
| `sara skill` | Skill management |
| `sara mcp` | MCP configuration |
| `sara platform` | Platform management |
| `sara status` | Agent status |
| `sara logs` | Log viewing |
| `sara config` | Configuration editing |
| `sara tools` | Tool configuration |
| `sara auth` | Authentication setup |
| `sara pairing` | Device pairing |
| `sara debug` | Debug session |
| `sara dump` | State dump |
| `sara hooks` | Hook management |
| `sara kanban` | Kanban board CLI |
| `sara memory` | Memory management |
| `sara skills-hub` | Skills Hub launcher |
| `sara curator` | Curator workflow |
| `sara envy` | Environment management |

## Developer Scripts & Tooling

The `scripts/` directory provides:

- `install.sh` / `install.ps1` / `install.cmd` — Cross-platform installers
- `setup_open_webui.sh` — Open WebUI integration setup
- `run_tests.sh` / `run_tests_parallel.py` — Test execution
- `analyze_livetest.py` — Live test analysis
- `benchmark_browser_eval.py` — Browser benchmark evaluation
- `build_model_catalog.py` — Model catalog builder
- `build_skills_index.py` — Skills index builder
- `release.py` — Release workflow automation
- `lint_diff.py` — Lint checking on diffs
- `keystroke_diagnostic.py` — Keyboard input diagnostics
- `sample_and_compress.py` — Data sampling and compression
- `contributor_audit.py` — Contributor analysis
- `profile-tui.py` — TUI profiling

## Website Documentation

The `website/` directory contains a Docusaurus-based documentation site with:

- Product documentation and setup guides.
- Integration and architecture documentation.
- Reference documentation for subsystems.

## Example Requests

```text
Summarize this repository and identify the riskiest subsystem.
Remember that Markdown is the source of truth for this project.
Search my project memory for previous deployment decisions.
Use agents to research, implement, and review this feature.
Schedule a daily summary and send it to Telegram.
Read this screenshot and explain the error.
Open the browser and collect the relevant documentation.
List available skills and load the one for test-driven development.
Connect an MCP server and show only its read-only tools.
Check gateway status and diagnose the Discord connection.
Fine-tune a model on my conversation history.
Deploy a multi-agent swarm to analyze this codebase.
```

## Feature File Targets

- `FEATURES.md`: user-facing feature overview and capability boundaries.
- `README.md`: project overview and quick start.
- `website/docs/`: detailed product, setup, integration, and architecture documentation.
- `memory/README.md`: wiki memory design, schema, API, and completion criteria.
- `apps/desktop/README.md`: desktop app setup and development.
- `gateway/platforms/ADDING_A_PLATFORM.md`: messaging adapter development.
- `pyproject.toml`: package metadata, core dependencies, and optional dependency groups.

## Definition Of Done

This feature overview is current when:

- Every major implemented subsystem has a concise user-facing description.
- Optional, credential-backed, and dependency-backed capabilities are identified as such.
- Claims match repository code or subsystem documentation.
- File targets point readers to the authoritative implementation details.
- The document does not present a plugin manifest or adapter alone as a fully configured integration.
- Markdown formatting is valid.
