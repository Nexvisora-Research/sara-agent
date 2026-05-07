/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/renderer/**/*.{html,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#6366f1", light: "#818cf8", dark: "#4f46e5" },
        secondary: { DEFAULT: "#8b5cf6", light: "#a78bfa", dark: "#7c3aed" },
        accent: { DEFAULT: "#06b6d4", light: "#22d3ee", dark: "#0891b2" },
        bg: { dark: "#0f0f23", card: "#1a1a3e", hover: "#252552", surface: "#14142f" },
        text: { primary: "#e2e8f0", secondary: "#94a3b8", muted: "#64748b" },
        success: "#10b981", warning: "#f59e0b", error: "#ef4444", info: "#3b82f6",
      },
      fontFamily: { sans: ["Inter","system-ui","sans-serif"], mono: ["JetBrains Mono","Fira Code","monospace"] },
      animation: { "pulse-slow": "pulse 3s cubic-bezier(.4,0,.6,1) infinite", "slide-in": "slideIn .3s ease-out", "fade-in": "fadeIn .2s ease-out" },
      keyframes: { slideIn: { "0%":{transform:"translateX(-20px)",opacity:"0"}, "100%":{transform:"translateX(0)",opacity:"1"} }, fadeIn: { "0%":{opacity:"0"}, "100%":{opacity:"1"} } },
    },
  },
  plugins: [],
};