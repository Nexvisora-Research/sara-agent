# Langfuse Observability Plugin

This plugin ships bundled with sara but is **opt-in** — it only loads when
you explicitly enable it.

## Enable

Pick one:

```bash
# Interactive: walks you through credentials + SDK install + enable
sara tools  # → Langfuse Observability

# Manual
pip install langfuse
sara plugins enable observability/langfuse
```

## Required credentials

Set these in `~/.sara/.env` (or via `sara tools`):

```bash
sara_LANGFUSE_PUBLIC_KEY=pk-lf-...
sara_LANGFUSE_SECRET_KEY=sk-lf-...
sara_LANGFUSE_BASE_URL=https://cloud.langfuse.com   # or your self-hosted URL
```

Without the SDK or credentials the hooks no-op silently — the plugin fails
open.

## Verify

```bash
sara plugins list                 # observability/langfuse should show "enabled"
sara chat -q "hello"              # then check Langfuse for a "sara turn" trace
```

## Optional tuning

```bash
sara_LANGFUSE_ENV=production       # environment tag
sara_LANGFUSE_RELEASE=v1.0.0       # release tag
sara_LANGFUSE_SAMPLE_RATE=0.5      # sample 50% of traces
sara_LANGFUSE_MAX_CHARS=12000      # max chars per field (default: 12000)
sara_LANGFUSE_DEBUG=true           # verbose plugin logging
```

## Disable

```bash
sara plugins disable observability/langfuse
```
