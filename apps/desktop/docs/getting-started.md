# Getting Started

## Install

### Via CLI (recommended)

If you already have the Sara CLI:

```bash
sara desktop
```

This builds and launches the desktop app against your existing install — same config, keys, sessions, and skills.

### Prebuilt Installers

Download from the [Sara Desktop website](https://sara-agent.nexvisoraresearch.com). Available for **macOS, Windows, and Linux**.

## First Run

1. Launch the app. On first boot, Sara installs the Python runtime and backend automatically.
2. The **onboarding wizard** appears — pick a model provider:
   - **nexvisora** — one subscription, 300+ frontier models
   - **OpenRouter** — one key, hundreds of models
   - **OpenAI**, **Gemini**, **xAI**, or a **local/self-hosted** endpoint
3. Sign in or paste an API key. The app picks a default model automatically.
4. You're ready to chat.

## Your First Chat

1. Type a message in the **composer** (the glass input bar at the bottom).
2. Press **Enter** to send. Press **Shift+Enter** for a newline.
3. Sara streams the response with live tool activity in the chat thread.

## Profiles

Profiles are independent Sara environments — separate config, skills, and system prompts.

- Create profiles from **Settings → Profiles** or the command palette.
- Switch via the sidebar or keyboard shortcut.
- Each profile keeps its own model, theme, and memory.

## Updating

The app checks for updates in the background. When one is ready, a notification appears — click to update.

You can also update from the CLI:

```bash
sara update
```
