export interface ThemeColors {
  primary: string
  accent: string
  border: string
  text: string
  muted: string
  completionBg: string
  completionCurrentBg: string

  label: string
  ok: string
  error: string
  warn: string

  prompt: string
  sessionLabel: string
  sessionBorder: string

  statusBg: string
  statusFg: string
  statusGood: string
  statusWarn: string
  statusBad: string
  statusCritical: string
  selectionBg: string

  diffAdded: string
  diffRemoved: string
  diffAddedWord: string
  diffRemovedWord: string

  shellDollar: string
}

export interface ThemeBrand {
  name: string
  icon: string
  prompt: string
  welcome: string
  goodbye: string
  tool: string
  helpHeader: string
}

export interface Theme {
  color: ThemeColors
  brand: ThemeBrand
  bannerLogo: string
  bannerHero: string
}

// ── Color math ───────────────────────────────────────────────────────

const HEX_6_RE = /^[0-9a-f]{6}$/
const HEX_3_RE = /^[0-9a-f]{3}$/

function parseHex(h: string): [number, number, number] | null {
  const v = h.replace(/^#/, '').toLowerCase()
  if (HEX_6_RE.test(v)) {
    const n = parseInt(v, 16)
    return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff]
  }
  if (HEX_3_RE.test(v)) {
    return [
      parseInt(v[0]! + v[0]!, 16),
      parseInt(v[1]! + v[1]!, 16),
      parseInt(v[2]! + v[2]!, 16),
    ]
  }
  return null
}

function mix(a: string, b: string, t: number): string {
  const pa = parseHex(a)
  const pb = parseHex(b)
  if (!pa || !pb) return a
  const lerp = (i: 0 | 1 | 2) => Math.round(pa[i] + (pb[i] - pa[i]) * t)
  return '#' + ((1 << 24) | (lerp(0) << 16) | (lerp(1) << 8) | lerp(2)).toString(16).slice(1)
}

function channelLuminance(value: number): number {
  const n = value / 255
  return n <= 0.03928 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4
}

function relativeLuminance(r: number, g: number, b: number): number {
  return 0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b)
}

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  const rn = r / 255, gn = g / 255, bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  const h =
    max === rn ? (gn - bn) / d + (gn < bn ? 6 : 0) :
    max === gn ? (bn - rn) / d + 2 :
                 (rn - gn) / d + 4
  return [h / 6, s, l]
}

function circularDistance(a: number, b: number): number {
  const d = Math.abs(a - b)
  return Math.min(d, 1 - d)
}

// ── ANSI color mapping ───────────────────────────────────────────────

const XTERM_6_LEVELS = [0, 95, 135, 175, 215, 255] as const

const ANSI_LIGHT_MAX_LUMINANCE = 0.72
const ANSI_LIGHT_TARGET_LUMINANCE = 0.34
const ANSI_LIGHT_MIN_SATURATION = 0.22
const ANSI_MUTED_BUCKET = 245

const ANSI_NORMALIZED_FOREGROUNDS: readonly (keyof ThemeColors)[] = [
  'text', 'label', 'ok', 'error', 'warn', 'prompt',
  'statusFg', 'statusGood', 'statusWarn', 'statusBad', 'statusCritical', 'shellDollar',
]

const ANSI_MUTED_FOREGROUNDS: readonly (keyof ThemeColors)[] = [
  'muted', 'sessionLabel', 'sessionBorder',
]

function xtermEightBitRgb(n: number): [number, number, number] {
  if (n >= 232) {
    const v = 8 + (n - 232) * 10
    return [v, v, v]
  }
  if (n >= 16) {
    const offset = n - 16
    return [
      XTERM_6_LEVELS[Math.floor(offset / 36) % 6]!,
      XTERM_6_LEVELS[Math.floor(offset / 6) % 6]!,
      XTERM_6_LEVELS[offset % 6]!,
    ]
  }
  return [0, 0, 0]
}

// Mirrors @sara/ink's colorize.ts. Keep local: app code compiles from
// ui-tui/src, while @sara/ink is bundled separately from packages/.
function richEightBitColorNumber(r: number, g: number, b: number): number {
  const [, s, l] = rgbToHsl(r, g, b)
  if (s < 0.15) {
    const gray = Math.round(l * 25)
    return gray === 0 ? 16 : gray === 25 ? 231 : 231 + gray
  }
  const sr = r < 95 ? r / 95 : 1 + (r - 95) / 40
  const sg = g < 95 ? g / 95 : 1 + (g - 95) / 40
  const sb = b < 95 ? b / 95 : 1 + (b - 95) / 40
  return 16 + 36 * Math.round(sr) + 6 * Math.round(sg) + Math.round(sb)
}

function bestReadableAnsiColor(r: number, g: number, b: number): number {
  const [hue, sat, light] = rgbToHsl(r, g, b)
  let best = richEightBitColorNumber(r, g, b)
  let bestScore = Number.POSITIVE_INFINITY

  for (let n = 16; n <= 255; n++) {
    const [cr, cg, cb] = xtermEightBitRgb(n)
    if (relativeLuminance(cr, cg, cb) > ANSI_LIGHT_MAX_LUMINANCE) continue

    const [ch, cs, cl] = rgbToHsl(cr, cg, cb)
    const satFloorPenalty = cs < ANSI_LIGHT_MIN_SATURATION
      ? (ANSI_LIGHT_MIN_SATURATION - cs) * 3
      : 0
    const score =
      circularDistance(ch, hue) * 4 +
      Math.abs(cs - Math.max(ANSI_LIGHT_MIN_SATURATION, sat)) * 0.8 +
      Math.abs(cl - Math.min(light, ANSI_LIGHT_TARGET_LUMINANCE)) * 2 +
      satFloorPenalty

    if (score < bestScore) {
      best = n
      bestScore = score
    }
  }
  return best
}

function normalizeAnsiForeground(color: string): string {
  const rgb = parseHex(color)
  if (!rgb) return color
  const richAnsi = richEightBitColorNumber(rgb[0], rgb[1], rgb[2])
  const richRgb = xtermEightBitRgb(richAnsi)
  const ansi = relativeLuminance(richRgb[0], richRgb[1], richRgb[2]) > ANSI_LIGHT_MAX_LUMINANCE
    ? bestReadableAnsiColor(rgb[0], rgb[1], rgb[2])
    : richAnsi
  return `ansi256(${ansi})`
}

// ── Brand defaults ───────────────────────────────────────────────────

const BRAND: ThemeBrand = {
  name: 'sara Agent',
  icon: '⚕',
  prompt: '❯',
  welcome: 'Type your message or /help for commands.',
  goodbye: 'Goodbye! ⚕',
  tool: '┊',
  helpHeader: '(^_^)? Commands',
}

function cleanPromptSymbol(s: string | undefined, fallback: string): string {
  return String(s ?? '').replace(/\s+/g, ' ').trim() || fallback
}

// ── Palettes ─────────────────────────────────────────────────────────

export const DARK_THEME: Theme = {
  color: {
    primary: '#FFD700',
    accent: '#FFBF00',
    border: '#CD7F32',
    text: '#FFF8DC',
    // Bumped from the old `#B8860B` darkgoldenrod (~53% luminance) — the
    // new value sits ~60% luminance, readable without losing secondary semantics.
    muted: '#CC9B1F',
    completionBg: '#FFFFFF',
    completionCurrentBg: mix('#FFFFFF', '#FFBF00', 0.25),

    label: '#DAA520',
    ok: '#4caf50',
    error: '#ef5350',
    warn: '#ffa726',

    prompt: '#FFF8DC',
    // sessionLabel/sessionBorder intentionally track `muted` — same role,
    // same colour. fromSkin's banner_dim fallback relies on this pairing.
    sessionLabel: '#CC9B1F',
    sessionBorder: '#CC9B1F',

    statusBg: '#1a1a2e',
    statusFg: '#C0C0C0',
    statusGood: '#8FBC8F',
    statusWarn: '#FFD700',
    statusBad: '#FF8C00',
    statusCritical: '#FF6B6B',
    selectionBg: '#3a3a55',

    diffAdded: 'rgb(220,255,220)',
    diffRemoved: 'rgb(255,220,220)',
    diffAddedWord: 'rgb(36,138,61)',
    diffRemovedWord: 'rgb(207,34,46)',
    shellDollar: '#4dabf7',
  },
  brand: BRAND,
  bannerLogo: '',
  bannerHero: '',
}

// Light-terminal palette: darker golds/ambers that stay legible on white
// backgrounds. Same shape as DARK_THEME so `fromSkin` still layers cleanly.
export const LIGHT_THEME: Theme = {
  color: {
    primary: '#8B6914',
    accent: '#A0651C',
    border: '#7A4F1F',
    text: '#3D2F13',
    muted: '#7A5A0F',
    completionBg: '#F5F5F5',
    completionCurrentBg: mix('#F5F5F5', '#A0651C', 0.25),

    label: '#7A5A0F',
    ok: '#2E7D32',
    error: '#C62828',
    warn: '#E65100',

    prompt: '#2B2014',
    sessionLabel: '#7A5A0F',
    sessionBorder: '#7A5A0F',

    statusBg: '#F5F5F5',
    statusFg: '#333333',
    statusGood: '#2E7D32',
    statusWarn: '#8B6914',
    statusBad: '#D84315',
    statusCritical: '#B71C1C',
    selectionBg: '#D4E4F7',

    diffAdded: 'rgb(200,240,200)',
    diffRemoved: 'rgb(240,200,200)',
    diffAddedWord: 'rgb(27,94,32)',
    diffRemovedWord: 'rgb(183,28,28)',
    shellDollar: '#1565C0',
  },
  brand: BRAND,
  bannerLogo: '',
  bannerHero: '',
}

// ── Light-mode detection ─────────────────────────────────────────────

const TRUE_RE = /^(?:1|true|yes|on)$/
const FALSE_RE = /^(?:0|false|no|off)$/

// TERM_PROGRAM allow-list for terminals whose default profile is light and
// which may not expose COLORFGBG. Apple Terminal is the canonical case.
// Explicit sara_TUI_THEME / COLORFGBG signals always take priority.
const LIGHT_DEFAULT_TERM_PROGRAMS = new Set<string>(['Apple_Terminal'])

const LUMA_LIGHT_THRESHOLD = 0.6

function backgroundLuminance(raw: string): number | null {
  const hex = raw.trim().toLowerCase().replace(/^#/, '')
  if (!hex) return null

  const rgb = HEX_6_RE.test(hex)
    ? [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)]
    : HEX_3_RE.test(hex)
      ? [parseInt(hex[0]! + hex[0]!, 16), parseInt(hex[1]! + hex[1]!, 16), parseInt(hex[2]! + hex[2]!, 16)]
      : null

  if (!rgb) return null
  // Rec. 709 luma — sufficient for bright/dark background classification.
  return (0.2126 * rgb[0]! + 0.7152 * rgb[1]! + 0.0722 * rgb[2]!) / 255
}

// Pick light vs dark with ordered, explainable signals:
//
//  1. sara_TUI_LIGHT boolean    — 1/true/yes/on → light; 0/false/no/off → dark.
//  2. sara_TUI_THEME named      — "light" / "dark".
//  3. sara_TUI_BACKGROUND hex   — luminance ≥ LUMA_LIGHT_THRESHOLD → light.
//  4. COLORFGBG last field      — slot 7 or 15 → light; 0–15 range → authoritative dark.
//  5. TERM_PROGRAM allow-list   — e.g. Apple_Terminal.
//
// Unresolved defaults to dark (the base sara palette).
export function detectLightMode(
  env: NodeJS.ProcessEnv = process.env,
  lightDefaultTermPrograms: ReadonlySet<string> = LIGHT_DEFAULT_TERM_PROGRAMS,
): boolean {
  const lightFlag = env.sara_TUI_LIGHT?.trim().toLowerCase() ?? ''
  if (TRUE_RE.test(lightFlag)) return true
  if (FALSE_RE.test(lightFlag)) return false

  const themeFlag = env.sara_TUI_THEME?.trim().toLowerCase() ?? ''
  if (themeFlag === 'light') return true
  if (themeFlag === 'dark') return false

  const bgLuma = backgroundLuminance(env.sara_TUI_BACKGROUND ?? '')
  if (bgLuma !== null) return bgLuma >= LUMA_LIGHT_THRESHOLD

  const colorfgbg = env.COLORFGBG?.trim() ?? ''
  if (colorfgbg) {
    const lastField = colorfgbg.split(';').at(-1) ?? ''
    if (/^\d+$/.test(lastField)) {
      const bg = Number(lastField)
      if (bg === 7 || bg === 15) return true
      // Slots 0–6 and 8–14 are authoritative dark — block TERM_PROGRAM override.
      if (bg >= 0 && bg < 16) return false
    }
  }

  return lightDefaultTermPrograms.has(env.TERM_PROGRAM?.trim() ?? '')
}

// ── ANSI normalization ───────────────────────────────────────────────

function shouldNormalizeAnsiLightTheme(
  env: NodeJS.ProcessEnv = process.env,
  isLight = detectLightMode(env),
): boolean {
  const colorTerm = env.COLORTERM?.trim().toLowerCase() ?? ''
  return (
    env.TERM_PROGRAM?.trim() === 'Apple_Terminal' &&
    colorTerm !== 'truecolor' &&
    colorTerm !== '24bit' &&
    isLight
  )
}

export function normalizeThemeForAnsiLightTerminal(
  theme: Theme,
  env: NodeJS.ProcessEnv = process.env,
  isLight = detectLightMode(env),
): Theme {
  if (!shouldNormalizeAnsiLightTheme(env, isLight)) return theme

  const color = { ...theme.color }
  for (const key of ANSI_NORMALIZED_FOREGROUNDS) color[key] = normalizeAnsiForeground(color[key])
  for (const key of ANSI_MUTED_FOREGROUNDS) color[key] = `ansi256(${ANSI_MUTED_BUCKET})`
  return { ...theme, color }
}

// ── Default theme ────────────────────────────────────────────────────

const DEFAULT_LIGHT_MODE = detectLightMode()

export const DEFAULT_THEME: Theme = normalizeThemeForAnsiLightTerminal(
  DEFAULT_LIGHT_MODE ? LIGHT_THEME : DARK_THEME,
  process.env,
  DEFAULT_LIGHT_MODE,
)

// ── Skin → Theme ─────────────────────────────────────────────────────

export function fromSkin(
  colors: Record<string, string>,
  branding: Record<string, string>,
  bannerLogo = '',
  bannerHero = '',
  toolPrefix = '',
  helpHeader = '',
): Theme {
  const d = DEFAULT_THEME
  const c = (k: string) => colors[k]

  const accent = c('ui_accent') ?? c('banner_accent') ?? d.color.accent
  const bannerAccent = c('banner_accent') ?? c('banner_title') ?? d.color.accent
  const muted = c('banner_dim') ?? d.color.muted
  const completionBg = c('completion_menu_bg') ?? d.color.completionBg

  return normalizeThemeForAnsiLightTerminal({
    color: {
      primary: c('ui_primary') ?? c('banner_title') ?? d.color.primary,
      accent,
      border: c('ui_border') ?? c('banner_border') ?? d.color.border,
      text: c('ui_text') ?? c('banner_text') ?? d.color.text,
      muted,
      completionBg,
      completionCurrentBg: c('completion_menu_current_bg') ?? mix(completionBg, bannerAccent, 0.25),

      label: c('ui_label') ?? d.color.label,
      ok: c('ui_ok') ?? d.color.ok,
      error: c('ui_error') ?? d.color.error,
      warn: c('ui_warn') ?? d.color.warn,

      prompt: c('prompt') ?? c('banner_text') ?? d.color.prompt,
      sessionLabel: c('session_label') ?? muted,
      sessionBorder: c('session_border') ?? muted,

      statusBg: d.color.statusBg,
      statusFg: d.color.statusFg,
      statusGood: c('ui_ok') ?? d.color.statusGood,
      statusWarn: c('ui_warn') ?? d.color.statusWarn,
      statusBad: d.color.statusBad,
      statusCritical: d.color.statusCritical,
      selectionBg: c('selection_bg') ?? d.color.selectionBg,

      diffAdded: d.color.diffAdded,
      diffRemoved: d.color.diffRemoved,
      diffAddedWord: d.color.diffAddedWord,
      diffRemovedWord: d.color.diffRemovedWord,
      shellDollar: c('shell_dollar') ?? d.color.shellDollar,
    },

    brand: {
      name: branding.agent_name ?? d.brand.name,
      icon: d.brand.icon,
      prompt: cleanPromptSymbol(branding.prompt_symbol, d.brand.prompt),
      welcome: branding.welcome ?? d.brand.welcome,
      goodbye: branding.goodbye ?? d.brand.goodbye,
      tool: toolPrefix || d.brand.tool,
      helpHeader: branding.help_header ?? (helpHeader || d.brand.helpHeader),
    },

    bannerLogo,
    bannerHero,
  }, process.env, DEFAULT_LIGHT_MODE)
}