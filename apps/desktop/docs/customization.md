# Customization

## Themes

Sara Desktop has **6 built-in skins**, each with light and dark variants:

| Skin | Vibe |
|------|------|
| **neXvisora** | Default premium dark — red accent, glass UI |
| **Midnight** | Deep blue palette, cool tones |
| **Ember** | Warm orange/crimson glow |
| **Mono** | Grayscale, minimal |
| **Cyberpunk** | Neon purple/cyan |
| **Slate** | Muted blue-gray |

### Switching Themes

**Command palette:** `Ctrl+K` → type "theme" → pick a skin.

**Settings:** `Ctrl+,` → Appearance → Theme.

Themes are **per-profile** — each profile can have its own theme.

### VS Code Theme Import

You can import any VS Code Marketplace theme:

1. Open **Settings → Appearance → Install from VS Code**
2. Paste a Marketplace extension ID (e.g., `dracula-theme.theme-dracula`)
3. Click Install

The theme is converted into a desktop palette and added to your theme list.

## Color Mode

Three modes, toggleable via `Shift+X`:

| Mode | Description |
|------|-------------|
| **Light** | Bright desktop surfaces |
| **Dark** | Low-glare workspace (default) |
| **System** | Follows your OS appearance setting |

The mode applies on top of the selected skin — so "Midnight Light" or "Cyberpunk Dark" are both possible.

## Languages

Sara Desktop supports **8 languages**:

| Language | Code | Native Name |
|----------|------|-------------|
| English | `en` | English |
| Simplified Chinese | `zh` | 简体中文 |
| Traditional Chinese | `zh-hant` | 繁體中文 |
| Japanese | `ja` | 日本語 |
| Korean | `ko` | 한국어 |
| French | `fr` | Français |
| German | `de` | Deutsch |
| Spanish | `es` | Español |

### Switching Language

Go to **Settings → Language** and pick your locale. The UI updates immediately.

New languages can be added by creating a translation file in `src/i18n/`. Missing translations automatically fall back to English.

### Translating

To add a new locale:

1. Create `src/i18n/<code>.ts` using the `defineLocale()` helper (partial overrides, English fallback)
2. Add the locale code to the `Locale` type in `src/i18n/types.ts`
3. Register in `src/i18n/catalog.ts` and `src/i18n/languages.ts`
