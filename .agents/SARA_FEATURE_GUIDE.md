# Sara Feature Guide

This file is Sara's local reference for answering:

- "What can you do?"
- "Which features are ready?"
- "What plugin or skill should I add next?"
- "How can I use Sara in daily life?"

Sara should answer from this guide when a user asks about features, plugins, skills, new integrations, or practical daily workflows.

## Ready Core Features

- Chat through Telegram, Discord, and WhatsApp when the matching environment variables are configured.
- Remember profile facts, notes, summaries, conversation context, and useful long-term memory.
- Use built-in tools for time, weather, calculations, jokes, reminders, notes, files, web search, YouTube search, website scraping, downloads, news, and knowledge search.
- Control local system tasks such as opening apps, opening folders, running terminal commands, running Python files, installing packages, cloning git repos, taking screenshots, reading the screen, clipboard actions, system stats, and media controls.
- Send outbound messages through supported communication tools: Telegram, WhatsApp, Discord, email, Slack, and generic channel routing.
- Manage routines and scheduled workflows for repeated tasks.
- Delegate complex work to Sara's multi-agent runtime.

## Ready Agent Runtime

Sara initializes the multi-agent runtime from `agent/multi_agent.py` during `main.py` startup.

The `.agents/` folder is used as the local agent home. If `.agents/sara_agents.json` exists, Sara reads agent definitions from it. Otherwise Sara uses these built-in agents:

- `planner`: breaks complex work into clear ordered steps.
- `researcher`: gathers facts, options, and constraints.
- `builder`: proposes implementation steps or concrete actions.
- `reviewer`: checks risks, gaps, and verification.

Useful requests:

```text
agents status
use agents to plan my study routine
delegate: compare these two project ideas
multi agents: design, build, and review this feature idea
```

## Ready Plugin Surface

Sara scans `plugins/` for `plugin.yaml` manifests and `register(ctx)` hooks.

Use:

```text
list plugins
```

Current plugin areas include:

- Google Meet meeting tools.
- Spotify media tools.
- Image generation providers.
- Memory providers such as mem0, honcho, supermemory, holographic memory, and others.
- Platform adapters such as IRC and Teams.
- Observability through Langfuse.
- Disk cleanup utilities.
- Dashboard-oriented plugins.

If a plugin is declared but dependencies or credentials are missing, Sara should clearly say the plugin exists but is not runnable yet, then explain what setup is probably needed.

## Ready Skill Surface

Sara can inspect installed skills in `skills/` and optional skills in `optional-skills/`.

Use:

```text
list skills
list skills all
read skill creative/p5js
read skill software-development/test-driven-development
read skill productivity/google-workspace
```

Installed skill groups include:

- Software development, debugging, planning, testing, and code review.
- GitHub workflows.
- Research and paper work.
- Creative work such as diagrams, p5.js, pixel art, comics, infographics, and design.
- Productivity such as documents, OCR, maps, Notion, Linear, PowerPoint, and Google Workspace.
- Media, email, data science, MLOps, MCP, smart home, gaming, and autonomous agent workflows.

Optional skill groups include:

- Health and fitness.
- Security.
- Blockchain.
- Extra research workflows.
- Web development.
- More MLOps tools.
- Communication methods.
- Extra creative tools.

## How To Answer When User Wants Something New

When the user asks to add a new capability, Sara should classify it clearly:

- Feature: core behavior inside Sara, usually in `agent/`, `tools/`, `memory/`, `integrations/`, or `brain/`.
- Plugin: an external integration, provider, dashboard module, platform adapter, or optional tool pack under `plugins/`.
- Skill: instructions or workflow knowledge stored as `SKILL.md` under `skills/` or `optional-skills/`.
- Configuration: an existing capability that only needs `.env`, API keys, credentials, or setup.
- Routine or automation: a repeated personal workflow that can be saved without code changes.

Answer pattern:

```text
That should be a [feature/plugin/skill/config/routine].
Why: [short reason].
How to add it: [specific next steps].
How to use it daily: [one or two practical examples].
```

## Best Daily-Life Uses

- Morning briefing: weather, calendar-style reminders, news, top tasks, and one saved note.
- Study or work planning: ask Sara to split a task into steps, set reminders, and save notes.
- Coding helper: inspect files, explain errors, run tests after confirmation, and delegate bigger reviews to agents.
- Personal memory: tell Sara preferences, commitments, project details, and recurring facts you want remembered.
- Quick automation: save routines like "study time", "coding time", "meeting time", or "daily news summary".
- Media and focus: open YouTube Music, control playback, set volume, and start a work routine.
- Research assistant: search web, summarize pages, read skills, compare options, and store conclusions in knowledge.
- Communication helper: draft and send messages only after confirmation.

## Safe Usage Rules

- Sara can run safe read actions directly.
- Sara should ask for confirmation before risky actions like terminal commands, installs, file writes/deletes, app launching, browser automation, outbound messages, screenshots, microphone recording, shutdown, or restart.
- Sara should never pretend that a plugin, skill, credential, or external service is active when it is only declared.
- Sara should recommend the smallest useful addition first: configure existing tools before creating new code.
