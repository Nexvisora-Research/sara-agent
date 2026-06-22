# Interface

## Layout

The app uses a three-panel layout:

```
┌─────────────┬──────────────────────┬─────────────┐
│ Left        │ Center               │ Right       │
│ Sidebar     │                      │ Sidebar     │
│             │                      │             │
│ Sessions    │ Chat Thread          │ File        │
│ Brand       │  or                  │ Browser     │
│ Header      │ Hero Dashboard       │ Terminal    │
│             │                      │             │
│             │ Composer (glass)     │             │
└─────────────┴──────────────────────┴─────────────┘
```

### Left Sidebar

- **Brand header** — Sara logo, wordmark, and online status indicator.
- **Sessions list** — recent chats, pinned sessions, and search.
- **Navigation** — Skills & Tools, Messaging, Artifacts, Memory.

### Center — Chat Area

When no session is active, the **hero dashboard** is shown with:
- Floating animated particles
- Typewriter "SARA AI OS · READY" heading
- Quick-action glass cards
- The composer at the bottom

When a session is active, the **chat thread** appears with:
- Streaming assistant responses
- Live tool call status
- Approval prompts and clarify questions
- Scroll-to-bottom button

### Right Sidebar

- **File browser** — browse and preview the working directory.
- **Terminal** — embedded terminal session.

## Composer

The floating glass chat input at the bottom of the center panel:

- **Text input** — type your message. Supports Markdown and file references (`@file:path`).
- **Attach** — files, folders, images, URLs, or clipboard images.
- **Model picker** — switch models mid-conversation.
- **Voice** — dictation or full-duplex voice conversation.
- **Send/Stop** — send message or stop the current turn. When busy, shows a stop button; when queued, shows queue controls.

### Slash Commands

Type `/` in the composer to see available commands:

| Command | Description |
|---------|-------------|
| `/help` | Full list of commands and hotkeys |
| `/clear` | Start a new session |
| `/resume` | Resume a prior session |
| `/details` | Control transcript detail level |
| `/copy` | Copy selection or last assistant message |
| `/quit` | Exit Sara |

### At-References

Type `@` to reference files, folders, URLs, or search results inline.

## Sessions

- **New session** — `Ctrl+N` or click the + button in the sidebar.
- **Pin/Unpin** — Shift+click a session to pin it. Pinned sessions stay at the top.
- **Archive** — remove from sidebar without deleting. Access archived chats from **Settings → Archived Chats**.
- **Branch** — create a new chat from any message via the message actions menu.
- **Export** — download session as JSON.

## Command Palette

Press `Ctrl+K` (or `Cmd+K` on macOS) to open the command palette. Search and run any action:
- Switch sessions, themes, or profiles
- Open settings, skills, or messaging
- Run system actions (restart gateway, check updates)
