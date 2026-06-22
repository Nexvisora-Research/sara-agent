"use strict"

const fs = require("fs")
const path = require("path")

const root = path.resolve(__dirname, "..")

try {
  fs.accessSync(path.join(root, "node_modules", "vite", "package.json"))
} catch {
  const repoRoot = path.resolve(__dirname, "..", "..", "..")
  console.error(`Run from repo root: cd ${repoRoot} && npm ci`)
  process.exit(1)
}
