# Sara AI

Sara AI is a personal assistant runtime that connects chat integrations to a shared agent loop, memory system, tool registry, plugins, and skills. The main process starts one or more bot integrations, each incoming message is handled by `agent/agent_loop.py`, and tools are dispatched through `tools/register_tool.py`.

## Features

- Telegram bot with first-time onboarding, saved user profile, training commands, and normal chat.
- Discord bot that reads channel messages and replies through the shared agent loop.
- WhatsApp webhook server for inbound WhatsApp messages through Twilio or a compatible provider.
- Long-term memory and profile learning in `memory/`.
- Local and cloud LLM fallback through the brain modules.
- Tool execution for time, weather, notes, reminders, files, web search, browser automation, system info, media controls, communication, developer commands, and knowledge search.
- Confirmation policy for risky actions such as terminal commands, app launching, shutdown/restart, browser automation, outbound messages, and file writes.
- Multi-agent delegation with planner, researcher, builder, and reviewer sub-agents for complex work.
- Plugin surface that reads plugin manifests and exposes plugin tools through the main registry.
- Skill surface with `list_skills` and `read_skill` so the agent can inspect installed and optional `SKILL.md` files.
- Optional automation scheduler for reminders and scheduled workflows.

## Project Flow

```text
main.py
  -> integrations/telegram_bot.py
  -> integrations/discord_bot.py
  -> integrations/whatsapp_bot.py
  -> agent/agent_loop.py
  -> agent/planner.py / agent/observer.py
  -> tools/register_tool.py
  -> agent/multi_agent.py
  -> tools/*, plugins/*, skills/*, .agents/*
```

`main.py` chooses which bot integrations to start based on environment variables. All integrations call:

```python
process_turn(user_id, user_message, channel="telegram|discord|whatsapp")
```

The agent loop stores context, updates memory, classifies the request, plans tool use when needed, asks for approval for risky actions, executes tools, and returns an `AgentResponse`.

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
```

On Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create your local environment file.

```bash
cp example.env .env
```

4. Edit `.env` and set at least one bot option:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DISCORD_BOT_TOKEN=your_discord_bot_token
WHATSAPP_WEBHOOK_ENABLED=true
```

Optional model/provider settings:

```env
SARA_ALLOW_CLOUD_FALLBACK=true
GROQ_API_KEY=your_groq_key
ANTHROPIC_API_KEY=your_anthropic_key
```

## Running

Start Sara AI:

```bash
python main.py
```

Startup behavior:

- If `TELEGRAM_BOT_TOKEN` is set, Sara starts the Telegram bot.
- If `DISCORD_BOT_TOKEN` is set, Sara starts the Discord bot.
- If both Telegram and Discord are set, Discord runs in a background thread and Telegram runs in the foreground.
- If `WHATSAPP_WEBHOOK_ENABLED=true`, Sara starts the WhatsApp webhook server. If other bots are also enabled, WhatsApp runs in a background thread.

WhatsApp webhook defaults:

```env
WHATSAPP_WEBHOOK_HOST=0.0.0.0
WHATSAPP_WEBHOOK_PORT=5005
```

Point your Twilio WhatsApp sandbox or WhatsApp provider webhook to:

```text
http://your-host:5005/whatsapp
```

## Using Sara

Send messages through Telegram, Discord, or WhatsApp. Example requests:

```text
hi
what time is it?
weather in Mumbai
save note: renew passport this week
show my notes
calculate 200 * 12 / 4
search youtube for relaxing coding music
list routines
run command echo hello
shutdown pc
```

Risky commands will ask for approval before execution. Reply with `yes` to continue or `no` to stop.

## Tools

Tools are registered in `tools/register_tool.py`. Important public helpers:

- `execute_tool(action, value, user_id="")` dispatches a tool call.
- `get_tools_description()` renders tool descriptions for prompts.
- `get_tool_catalog()` returns structured tool metadata for planning.
- `get_tool_policy(action)` returns whether a tool is safe or requires confirmation.

Useful built-in tool groups:

- Core: time, system info, calculator, weather, jokes, notes.
- System: open apps, terminal, screenshots, clipboard, shutdown/restart.
- Developer: terminal command, Python runner, package install, git clone, project creation.
- Files: read, write, create folder, delete, list, export chat.
- Web: search, YouTube search, open URL, scrape website, download file.
- Browser: open page, screenshot page, fill forms.
- Knowledge: add/search/count knowledge items.
- Communication: Telegram, WhatsApp, Discord, email, Slack, generic channel send.
- Voice: microphone input and audio device listing.
- Monitor: CPU, RAM, disk, processes, system stats.
- News: topic news and trending news.
- Media: play/pause, next/previous, volume, mute/unmute.
- Multi-agent: `delegate_task`, `multi_agent_status`.
- Skills/plugins: `list_skills`, `read_skill`, `list_plugins`.

## Multi-Agent Mode

Sara initializes the multi-agent runtime during `main.py` startup. The runtime uses `.agents/` as its local agent home. If `.agents/sara_agents.json` exists, Sara reads agent definitions from it. If it does not exist, Sara uses built-in defaults:

- `planner`: breaks complex work into clear steps.
- `researcher`: gathers facts, context, and constraints.
- `builder`: proposes implementation or action steps.
- `reviewer`: checks risks, gaps, and verification.

Use it from any bot:

```text
agents status
use agents to plan a better memory system
delegate: compare these options and recommend one
multi agents: design, build, and review this feature idea
```

Tool calls:

```text
multi_agent_status
delegate_task Improve the project README and test plan
```

The runtime is intentionally lightweight. It coordinates sub-agent prompts through Sara's existing `brain/llm_engine.py`, so it works with the same Claude, Groq, and Ollama fallback stack as normal chat.

## Plugins

Plugins live under `plugins/` and usually include a `plugin.yaml` manifest. Some plugins also expose a sara-style `register(ctx)` hook. The tool registry surfaces declared plugin tools so the agent can see them.

Examples:

- `plugins/google_meet/` declares Meet tools such as `meet_join`, `meet_status`, and `meet_transcript`.
- `plugins/spotify/` declares Spotify tools such as `spotify_search`, `spotify_playback`, and `spotify_devices`.
- `plugins/memory/` contains optional memory provider plugins.
- Dashboard plugins include frontend assets and API modules under `dashboard/`.

If a plugin depends on runtime modules that are not installed in this Sara environment, its declared tools still appear, but calling them returns a clear unavailable-runtime message.

## Skills

Skills live in:

- `skills/` for installed skills.
- `optional-skills/` for opt-in skill packs.

Sara exposes skill inspection through tools:

```text
list_skills
list_skills all
read_skill creative/p5js
read_skill blender-mcp
```

Installed skills are considered active library content. Optional skills are discoverable when requested but are not assumed active unless copied, installed, or explicitly loaded.

## Memory

Memory data is stored under `memory/data/<user_id>/`. The agent records conversation history, profile facts, notes, summaries, and training data. Bot integrations use channel-specific user IDs such as:

- Telegram: the Telegram user ID.
- Discord: `discord_<author_id>`.
- WhatsApp: `whatsapp_<phone_number>`.

## Development

Run tests:

```bash
python -m unittest test_agent_vnext.py
```

Compile-check the tool registry:

```bash
python -m py_compile tools/register_tool.py
```

Useful files:

- `main.py`: process entry point and integration startup.
- `agent/agent_loop.py`: shared turn engine.
- `agent/planner.py`: complex task planning and tool inference.
- `agent/observer.py`: result review and confirmation messaging.
- `agent/multi_agent.py`: planner/researcher/builder/reviewer coordinator.
- `tools/register_tool.py`: master tool registry and plugin/skill surface.
- `integrations/`: Telegram, Discord, and WhatsApp adapters.
- `memory/`: user profile, context, memory engine, and automation scheduler.
- `plugins/`: optional plugin integrations.
- `skills/` and `optional-skills/`: skill instructions.

## Notes

- Some tools need OS packages or external apps. For example, OCR and screenshots may need `pytesseract`, desktop permissions, or Playwright browser setup.
- Some integrations require provider-side setup, such as Telegram bot tokens, Discord Message Content Intent, Twilio webhooks, or API keys.
- Keep secrets in `.env`; do not commit real tokens.
