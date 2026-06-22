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

The web application provides graphical access to:

- Chat and session history.
- Models and provider configuration.
- Profiles, skills, plugins, cron jobs, logs, and analytics.
- Environment settings, OAuth providers, platform connections, and tool calls.
- Themes and localization.

### Terminal UI

The terminal UI offers a richer full-screen experience with streaming output, tool-call rendering, slash commands, and keyboard interaction.

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

Plugin integrations are available for external or experimental memory systems, including Honcho, Mem0, Hindsight, Supermemory, OpenViking, Retaindb, ByteRover, and other provider-specific backends. Their availability depends on installation and configuration.

## Skills And Learning

Sara uses skills as portable procedural knowledge. Skills can be bundled with the repository, installed as optional packs, or created and refined from experience.

Skill features include:

- Discovering and reading skills from `skills/` and `optional-skills/`.
- Loading specialized instructions only when relevant.
- Reusing scripts, templates, references, and assets packaged with a skill.
- Skills for software development, research, productivity, media, creative work, MLOps, security testing, and agent workflows.
- A Skills Hub workflow for discovery and management.
- Agent-curated learning and skill improvement across sessions.

## Tools And Extensibility

Sara can combine built-in tools, plugins, MCP servers, browser automation, and managed execution environments.

Major tool areas include:

- Files, folders, terminal commands, Python, and package management.
- Web search, page extraction, downloads, and browser automation.
- Screenshots, OCR, computer vision, and GUI-agent actions.
- Image generation, transcription, text-to-speech, and audio controls.
- Notes, reminders, time, weather, calculations, news, and knowledge search.
- System information, processes, CPU, memory, and disk monitoring.
- Clipboard, notifications, and desktop application controls.
- Email, documents, cloud storage, and platform-specific integrations.
- MCP servers with configurable tool filtering and authentication.

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
- Cron-based schedules.
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
```

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
