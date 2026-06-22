# Troubleshooting

## Boot Issues

### App won't start

Check the boot log:

```bash
# macOS / Linux
cat ~/.sara/logs/desktop.log

# Windows (PowerShell)
Get-Content "$env:LOCALAPPDATA\sara\logs\desktop.log"
```

### Force clean first-launch setup

```bash
# macOS / Linux
rm "$HOME/.sara/sara-agent/.sara-bootstrap-complete"

# Windows (PowerShell)
Remove-Item "$env:LOCALAPPDATA\sara\sara-agent\.sara-bootstrap-complete"
```

### Rebuild broken Python venv

```bash
# macOS / Linux
rm -rf "$HOME/.sara/sara-agent/venv"

# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\sara\sara-agent\venv"
```

## Gateway Issues

### "Gateway not connected"

1. Check **System Panel** from the status bar for gateway status.
2. Try **Restart Gateway** from the status bar menu.
3. Check `desktop.log` for connection errors.
4. If using a remote gateway, verify the URL and credentials in **Settings → Gateway**.

### Gateway crashes on start

- Check the backend logs in `~/.sara/logs/`.
- Ensure Python 3.11+ is installed.
- Try clearing the venv and restarting.

## Voice Issues

| Problem | Solution |
|---------|----------|
| Microphone not working | Check OS mic permissions. On macOS: `tccutil reset Microphone com.nexvisoraresearch.sara` |
| "No microphone found" | Ensure mic is connected and not used by another app |
| Transcription fails | Verify STT provider key in Settings → Voice. Try local (faster-whisper) which needs no key |
| Playback fails | Try Edge TTS provider (free, no key needed) |
| Voice button disabled | Speech-to-text may be disabled in Settings → Voice |

## Theme / Display Issues

### Theme not applying

1. Try switching to a different theme and back.
2. Use `Shift+X` to cycle color modes.
3. If colors look wrong after an update, try restarting the app.

### White flash on startup

This is normal on first launch — the theme system initializes after the Electron shell loads. Persistent flashing may indicate a slow backend.

## Session Issues

### Session won't load

- Check gateway is connected.
- Try the Retry button if it appears.
- If "Session unavailable", the backend may have lost the session state — start a new chat.

### Messages out of order

Sessions use branching for edits and retries. Use **Restore checkpoint** from a message's action menu to rewind to an earlier point.

## Update Issues

### Update check fails

- Check your internet connection.
- If behind a proxy, ensure the gateway can reach the update server.
- Try updating via CLI: `sara update`

### Update stuck

Check `desktop.log` for updater errors. If the app won't launch after an update:

```bash
sara update --force
```

## Getting Help

- Check `~/.sara/logs/desktop.log` for detailed error information.
- Join the [Discord](https://discord.gg/nexvisoraresearch) for community support.
- Open a [GitHub Issue](https://github.com/nexvisoraresearch/sara-agent/issues).
