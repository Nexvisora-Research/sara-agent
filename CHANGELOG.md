# Changelog

All notable changes to Sara Agent are documented here.

## 2.2.0 - 2026-05-27

### Added

- Added **Temporal Intelligence Engine** (`temporal-engine/`) — a TypeScript-based system for understanding deadlines, learning routines, predicting optimal execution windows, and detecting schedule conflicts.
  - **Temporal Memory Graph**: JSON-persisted directed graph with auto-save, BFS pathfinding, timeline/overdue queries, and snapshot export/import.
  - **Habit Learner**: Discovers recurring patterns from repeated events using time-of-day and day-of-week distribution analysis with confidence scoring.
  - **Predictive Scheduler**: Estimates completion times from historical durations, predicts optimal scheduling windows from habit patterns, and generates 30-day workload forecasts.
  - **Conflict Detector**: Detects overlaps (severity-rated), deadline risks (work-to-time ratio analysis), dependency breaches, and computes future impact scores with ripple-effect propagation.
  - **Background Worker**: Cron-parsing engine (5-field) with timer-based job scheduling, pause/resume lifecycle, and event bus.
  - **JSON-RPC Bridge**: 30+ methods over stdin/stdout for Python backend integration.
  - **React Dashboard**: Full `TemporalPage` with tabs for Timeline, Conflicts, Habits, Forecast, and Impact scoring, plus `useTemporalEngine` hook with WebSocket + HTTP fallback.

## 2.1.0 - 2026-05-27

### Added

- Added a pipe-friendly one-line installer for Linux, macOS, WSL, and Termux.
- Added root-level `install.sh` and `scripts/install.sh` entrypoints so hosted URLs like `https://your-domain/install.sh` and raw GitHub script URLs both work.
- Added configurable installer environment variables:
  - `SARA_REPO_URL` to install from a custom repository.
  - `SARA_BRANCH` to install a specific branch.
  - `SARA_INSTALL_DIR` to choose the install location.
  - `SARA_COMMAND_NAME` to create a custom global command, such as `eden`.
  - `SARA_RUN_SETUP=0` to skip the setup wizard during automated installs.

### Changed

- Updated `setup-sara.sh` to reuse an existing virtual environment when possible.
- Updated `setup-sara.sh` to support `.venv` by default while preserving compatibility with existing `venv` installs.
- Updated global command setup so custom command aliases point at the installed Sara CLI.
- Updated installation docs with the custom command example:
  `curl -fsSL https://your-domain/install.sh | SARA_COMMAND_NAME=eden bash`

### Fixed

- Made setup prompts safer for `curl | bash` and other non-interactive install flows.
- Prevented setup prompts from accidentally consuming piped installer input.
- Kept CLI-reported version metadata in sync with package metadata.
