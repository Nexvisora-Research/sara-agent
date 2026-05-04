---
sidebar_position: 7
---

# Profile Commands Reference

This page covers all commands related to [sara profiles](../user-guide/profiles.md). For general CLI commands, see [CLI Commands Reference](./cli-commands.md).

## `sara profile`

```bash
sara profile <subcommand>
```

Top-level command for managing profiles. Running `sara profile` without a subcommand shows help.

| Subcommand | Description |
|------------|-------------|
| `list` | List all profiles. |
| `use` | Set the active (default) profile. |
| `create` | Create a new profile. |
| `delete` | Delete a profile. |
| `show` | Show details about a profile. |
| `alias` | Regenerate the shell alias for a profile. |
| `rename` | Rename a profile. |
| `export` | Export a profile to a tar.gz archive. |
| `import` | Import a profile from a tar.gz archive. |

## `sara profile list`

```bash
sara profile list
```

Lists all profiles. The currently active profile is marked with `*`.

**Example:**

```bash
$ sara profile list
  default
* work
  dev
  personal
```

No options.

## `sara profile use`

```bash
sara profile use <name>
```

Sets `<name>` as the active profile. All subsequent `sara` commands (without `-p`) will use this profile.

| Argument | Description |
|----------|-------------|
| `<name>` | Profile name to activate. Use `default` to return to the base profile. |

**Example:**

```bash
sara profile use work
sara profile use default
```

## `sara profile create`

```bash
sara profile create <name> [options]
```

Creates a new profile.

| Argument / Option | Description |
|-------------------|-------------|
| `<name>` | Name for the new profile. Must be a valid directory name (alphanumeric, hyphens, underscores). |
| `--clone` | Copy `config.yaml`, `.env`, and `SOUL.md` from the current profile. |
| `--clone-all` | Copy everything (config, memories, skills, sessions, state) from the current profile. |
| `--clone-from <profile>` | Clone from a specific profile instead of the current one. Used with `--clone` or `--clone-all`. |
| `--no-alias` | Skip wrapper script creation. |

Creating a profile does **not** make that profile directory the default project/workspace directory for terminal commands. If you want a profile to start in a specific project, set `terminal.cwd` in that profile's `config.yaml`.

**Examples:**

```bash
# Blank profile — needs full setup
sara profile create mybot

# Clone config only from current profile
sara profile create work --clone

# Clone everything from current profile
sara profile create backup --clone-all

# Clone config from a specific profile
sara profile create work2 --clone --clone-from work
```

## `sara profile delete`

```bash
sara profile delete <name> [options]
```

Deletes a profile and removes its shell alias.

| Argument / Option | Description |
|-------------------|-------------|
| `<name>` | Profile to delete. |
| `--yes`, `-y` | Skip confirmation prompt. |

**Example:**

```bash
sara profile delete mybot
sara profile delete mybot --yes
```

:::warning
This permanently deletes the profile's entire directory including all config, memories, sessions, and skills. Cannot delete the currently active profile.
:::

## `sara profile show`

```bash
sara profile show <name>
```

Displays details about a profile including its home directory, configured model, gateway status, skills count, and configuration file status.

This shows the profile's sara home directory, not the terminal working directory. Terminal commands start from `terminal.cwd` (or the launch directory on the local backend when `cwd: "."`).

| Argument | Description |
|----------|-------------|
| `<name>` | Profile to inspect. |

**Example:**

```bash
$ sara profile show work
Profile: work
Path:    ~/.sara/profiles/work
Model:   anthropic/claude-sonnet-4 (anthropic)
Gateway: stopped
Skills:  12
.env:    exists
SOUL.md: exists
Alias:   ~/.local/bin/work
```

## `sara profile alias`

```bash
sara profile alias <name> [options]
```

Regenerates the shell alias script at `~/.local/bin/<name>`. Useful if the alias was accidentally deleted or if you need to update it after moving your sara installation.

| Argument / Option | Description |
|-------------------|-------------|
| `<name>` | Profile to create/update the alias for. |
| `--remove` | Remove the wrapper script instead of creating it. |
| `--name <alias>` | Custom alias name (default: profile name). |

**Example:**

```bash
sara profile alias work
# Creates/updates ~/.local/bin/work

sara profile alias work --name mywork
# Creates ~/.local/bin/mywork

sara profile alias work --remove
# Removes the wrapper script
```

## `sara profile rename`

```bash
sara profile rename <old-name> <new-name>
```

Renames a profile. Updates the directory and shell alias.

| Argument | Description |
|----------|-------------|
| `<old-name>` | Current profile name. |
| `<new-name>` | New profile name. |

**Example:**

```bash
sara profile rename mybot assistant
# ~/.sara/profiles/mybot → ~/.sara/profiles/assistant
# ~/.local/bin/mybot → ~/.local/bin/assistant
```

## `sara profile export`

```bash
sara profile export <name> [options]
```

Exports a profile as a compressed tar.gz archive.

| Argument / Option | Description |
|-------------------|-------------|
| `<name>` | Profile to export. |
| `-o`, `--output <path>` | Output file path (default: `<name>.tar.gz`). |

**Example:**

```bash
sara profile export work
# Creates work.tar.gz in the current directory

sara profile export work -o ./work-2026-03-29.tar.gz
```

## `sara profile import`

```bash
sara profile import <archive> [options]
```

Imports a profile from a tar.gz archive.

| Argument / Option | Description |
|-------------------|-------------|
| `<archive>` | Path to the tar.gz archive to import. |
| `--name <name>` | Name for the imported profile (default: inferred from archive). |

**Example:**

```bash
sara profile import ./work-2026-03-29.tar.gz
# Infers profile name from the archive

sara profile import ./work-2026-03-29.tar.gz --name work-restored
```

## `sara -p` / `sara --profile`

```bash
sara -p <name> <command> [options]
sara --profile <name> <command> [options]
```

Global flag to run any sara command under a specific profile without changing the sticky default. This overrides the active profile for the duration of the command.

| Option | Description |
|--------|-------------|
| `-p <name>`, `--profile <name>` | Profile to use for this command. |

**Examples:**

```bash
sara -p work chat -q "Check the server status"
sara --profile dev gateway start
sara -p personal skills list
sara -p work config edit
```

## `sara completion`

```bash
sara completion <shell>
```

Generates shell completion scripts. Includes completions for profile names and profile subcommands.

| Argument | Description |
|----------|-------------|
| `<shell>` | Shell to generate completions for: `bash` or `zsh`. |

**Examples:**

```bash
# Install completions
sara completion bash >> ~/.bashrc
sara completion zsh >> ~/.zshrc

# Reload shell
source ~/.bashrc
```

After installation, tab completion works for:
- `sara profile <TAB>` — subcommands (list, use, create, etc.)
- `sara profile use <TAB>` — profile names
- `sara -p <TAB>` — profile names

## See also

- [Profiles User Guide](../user-guide/profiles.md)
- [CLI Commands Reference](./cli-commands.md)
- [FAQ — Profiles section](./faq.md#profiles)
