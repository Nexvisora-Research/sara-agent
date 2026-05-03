# Sara AI Features

Sara AI is a personal assistant that can chat with you through Telegram, Discord, and WhatsApp, remember useful details, use tools, run workflows, and delegate complex work to multiple sub-agents.

## What Sara Can Do

### Chat With You

- Reply to normal conversations.
- Answer quick questions.
- Help explain ideas, code, errors, documents, and plans.
- Use your profile and past context to make replies more personal.

### Work Across Bot Platforms

- Use Sara from Telegram.
- Use Sara from Discord.
- Use Sara from WhatsApp through a webhook provider such as Twilio.
- Keep each platform connected to the same core agent brain.

### Remember Important Information

- Save personal notes.
- Learn profile facts naturally from conversation.
- Keep conversation history per user.
- Store summaries and useful long-term memory.
- Recall relevant context in future chats.

### Use Built-In Tools

Sara can use tools for:

- Current time and date.
- Weather lookup.
- Calculations.
- Notes.
- Reminders.
- File reading and writing.
- Folder creation and file listing.
- Web search.
- YouTube search.
- Website scraping.
- File downloads.
- Browser automation.
- Knowledge-base search.
- News and trending headlines.
- System information.
- CPU, RAM, disk, and process monitoring.
- Screenshots and OCR screen reading.
- Clipboard reading and writing.
- Media play/pause, next, previous, volume, mute, and unmute.

### Control Local System Tasks

Sara can help with local machine actions such as:

- Open apps.
- Open folders.
- Open a terminal.
- Run terminal commands.
- Run Python files.
- Install packages.
- Clone git repositories.
- Create simple projects.
- Shut down or restart the computer.

Risky actions ask for confirmation before running.

### Send Messages

Sara can send outbound messages through supported channels:

- Telegram.
- WhatsApp.
- Discord.
- Email.
- Slack.
- Generic channel routing.

### Manage Routines And Automations

Sara can:

- Save named routines.
- List routines.
- Run saved routines.
- Delete routines.
- Schedule workflows.
- List scheduled workflows.
- Remove scheduled workflows.
- Start the automation scheduler on app startup.

### Use Multi-Agent Mode

Sara can delegate complex tasks to sub-agents:

- `planner`: breaks work into steps.
- `researcher`: gathers facts and constraints.
- `builder`: proposes concrete implementation or action steps.
- `reviewer`: checks risks, gaps, and verification.

You can ask:

```text
agents status
use agents to plan a better memory system
delegate: compare these options and recommend one
multi agents: design, build, and review this feature idea
```

### Use Plugins

Sara can surface plugin tools from the `plugins/` folder.

Examples of plugin areas:

- Google Meet tools.
- Spotify tools.
- Memory provider plugins.
- Dashboard plugins.
- Observability plugins.
- Platform adapter plugins.

If a plugin is declared but its runtime dependencies are missing, Sara still shows the tool and explains why it cannot run yet.

### Use Skills

Sara can inspect skill files from:

- `skills/`
- `optional-skills/`

Useful skill commands:

```text
list_skills
list_skills all
read_skill creative/p5js
read_skill blender-mcp
```

Skills help Sara follow specialized workflows for coding, creative work, research, diagrams, media, productivity, and more.

### Build And Plan Projects

Sara includes a project-building workflow that can:

- Discuss a project idea.
- Ask clarifying questions.
- Turn the idea into a plan.
- Accept changes.
- Track build progress.
- Execute build steps through the agent loop.

### Train Personal Models

Sara includes optional personal training features:

- Collect training examples from conversations.
- Track training data.
- Train a personal model.
- Train a small Sara SLM.
- Show training status.
- Delete trained models.
- Optionally run auto-training checks.

These features may require extra dependencies and more system resources.

## Example Things To Ask Sara

```text
What time is it?
Weather in Mumbai
Save note: call the bank tomorrow
Show my notes
Calculate 2500 / 12
Search YouTube for Python tutorials
Search web for latest AI tools
Read file README.md
List files in plugins
Create folder test-output
Run command python -m unittest test_agent_vnext.py
Open Chrome
Take a screenshot
Read my screen
Set volume to 40
Get CPU usage
Get top processes
Get trending news
Send Telegram message: hello
Schedule a workflow for 9 AM daily news summary
Use agents to review this project structure
List plugins
List skills all
Read skill software-development/test-driven-development
```

## Safety Behavior

Sara treats some tools as safe and others as risky.

Safe actions usually run directly, such as:

- Reading notes.
- Getting time.
- Listing files.
- Searching knowledge.
- Checking system stats.

Risky actions ask for approval first, such as:

- Running terminal commands.
- Installing packages.
- Writing or deleting files.
- Opening apps.
- Sending outbound messages.
- Browser automation.
- Shutdown or restart.

Reply `yes` to continue or `no` to stop.

## Main Use Cases

- Personal assistant.
- Chatbot across Telegram, Discord, and WhatsApp.
- Local productivity assistant.
- Memory-based assistant.
- Developer helper.
- Research assistant.
- Automation assistant.
- Multi-agent planning assistant.
- Plugin and skill-powered AI workspace.
