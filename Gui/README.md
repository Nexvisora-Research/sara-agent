# 📱 SaraGUI

**Cross-platform messenger with voice control.**

Connect Telegram, Discord, and more in one beautiful desktop app. Control everything with your voice — send messages, switch chats, search contacts.

## ✨ Features

- 🔌 **Multi-Platform Messaging** — Telegram, Discord in one app (WhatsApp, X coming soon)
- 🎤 **Voice Control** — Send messages, navigate chats, search by voice
- 💬 **Unified Chat View** — All conversations in one place
- 🎨 **Beautiful Dark UI** — Glassmorphism design with smooth animations
- 🖥️ **Cross-Platform** — Windows, Linux, Android
- 🔔 **System Tray** — Minimize to tray, quick voice toggle from tray
- ⚡ **Plugin System** — Extensible architecture for new messaging platforms

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop Shell | Electron |
| UI Framework | React 18 + TypeScript |
| State | Zustand |
| Styling | Tailwind CSS |
| Animations | Framer Motion |
| Telegram API | MTProto (@mtproto/core) |
| Discord API | Discord.js |
| Android | Capacitor |
| Builder | Vite + Electron Builder |

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Development

```bash
# Install dependencies
npm install

# Start dev mode (Electron + Vite HMR)
npm run dev

# Build for production
npm run build
npm run electron:build
```

### Build for Platforms

```bash
# Windows (.exe - NSIS)
npm run build:win

# Linux (.AppImage)
npm run build:linux

# Android (APK via Capacitor)
npm run build:android
```

## 🔐 Configuration

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` | Your Telegram API ID (my.telegram.org) |
| `TELEGRAM_API_HASH` | Your Telegram API Hash |
| `TELEGRAM_PHONE` | Your phone number |
| `DISCORD_TOKEN` | Your Discord user token |
| `VOICE_COMMAND_ENABLED` | Enable/disable voice (true/false) |

## 🎤 Voice Commands

| Command | Action |
|---------|--------|
| "Open [app]" | Switch to Telegram/Discord |
| "Send message to [name]" | Send a message |
| "Search [query]" | Search contacts/channels |
| "Who is online" | Show online contacts |
| "Disconnect" | Disconnect all plugins |
| "Mute" / "Unmute" | Toggle voice input |
| "New message" | Start new conversation |
| "Reply [text]" | Reply to last message |
| "Go to chat [name]" | Navigate to specific chat |

## 📁 Project Structure

```
Gui/
├── src/
│   ├── main/              # Electron main process
│   │   ├── index.ts       # Window creation, IPC
│   │   ├── preload.ts     # Context bridge
│   │   ├── plugin-manager.ts  # Plugin lifecycle
│   │   ├── voice-manager.ts   # Voice recognition
│   │   ├── tray-manager.ts    # System tray
│   │   └── auto-launch.ts     # Startup settings
│   └── renderer/          # React UI
│       ├── components/    # UI components
│       ├── stores/        # Zustand state
│       ├── styles/        # Tailwind CSS
│       └── types/         # TypeScript types
├── plugins/
│   ├── base/              # Plugin interface + base class
│   ├── telegram/          # Telegram plugin (MTProto)
│   └── discord/           # Discord plugin
├── resources/             # Icons, tray assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── electron-builder.json
```

## 🔌 Plugin Development

Create a plugin by extending `BasePlugin`:

```typescript
import { BasePlugin } from '../base/BasePlugin';

class MyPlugin extends BasePlugin {
  manifest = { id: 'my-app', name: 'My App', ... };

  async connect(creds) { /* connect logic */ }
  async getChannels() { /* return channels */ }
  async sendMessage(channelId, content) { /* send */ }
}
```

## 📄 License

MIT
