"""
tools/system_tools.py — System Control Tools for Sara AI.

Features:
    - open_app / open_terminal / close_app / shutdown_pc / restart_pc / open_folder
  - take_screenshot  — Capture desktop to ~/Pictures/sara_screenshots/
  - read_screen      — Screenshot + OCR (pytesseract) to read on-screen text
  - clipboard_read   — Return current clipboard text
  - clipboard_write  — Write text to clipboard
"""

import os
import subprocess
import platform
import logging
import shutil
import time
import webbrowser
import urllib.parse
import re

logger = logging.getLogger(__name__)
OS = platform.system()   # 'Windows', 'Linux', 'Darwin'


# ── App name → executable map ─────────────────────────────────────────────────
APP_MAP = {
    # Browsers
    "chrome":           "chrome",
    "google chrome":    "chrome",
    "firefox":          "firefox",
    "edge":             "msedge",
    "microsoft edge":   "msedge",

    # Dev tools
    "vscode":           "code",
    "vs code":          "code",
    "visual studio code": "code",
    "visual studio":    "devenv",
    "pycharm":          "pycharm64",
    "git bash":         "git-bash",
    "powershell":       "powershell",
    "cmd":              "cmd",
    "terminal":         "wt",

    # Microsoft Office
    "word":             "winword",
    "excel":            "excel",
    "powerpoint":       "powerpnt",
    "outlook":          "outlook",
    "teams":            "teams",
    "onenote":          "onenote",

    # System / Built-in
    "notepad":          "notepad",
    "notepad++":        "notepad++",
    "calculator":       "calc",
    "explorer":         "explorer",
    "task manager":     "taskmgr",
    "control panel":    "control",
    "settings":         "ms-settings:",
    "paint":            "mspaint",
    "snipping tool":    "snippingtool",

    # Media & Entertainment
    "spotify":          "spotify",
    "vlc":              "vlc",
    "windows media":    "wmplayer",

    # Communication
    "discord":          "discord",
    "telegram":         "telegram",
    "whatsapp":         "whatsapp",
    "zoom":             "zoom",
    "skype":            "skype",
    "slack":            "slack",

    # Other popular
    "steam":            "steam",
    "obs":              "obs64",
    "7zip":             "7zfm",
    "winrar":           "winrar",
    "postman":          "postman",
    "capcut":           "capcut",

    # File managers
    "this pc":          "explorer",
    "file explorer":    "explorer",
    "my computer":      "explorer",
}

WEB_APP_MAP = {
    "flipkart":         "https://www.flipkart.com",
    "amazon":           "https://www.amazon.in",
    "amazon india":     "https://www.amazon.in",
    "amazon prime":     "https://www.primevideo.com",
    "chatgpt":          "https://chatgpt.com",
    "github":           "https://github.com",
    "google":           "https://www.google.com",
    "google calendar":  "https://calendar.google.com",
    "calendar":         "https://calendar.google.com",
    "google maps":      "https://www.google.com/maps",
    "maps":             "https://www.google.com/maps",
    "stackoverflow":    "https://stackoverflow.com",
    "stack overflow":   "https://stackoverflow.com",
    "wikipedia":        "https://www.wikipedia.org",
    "youtube":          "https://www.youtube.com",
    "youtube music":    "https://music.youtube.com",
    "gmail":            "https://mail.google.com",
    "instagram":        "https://www.instagram.com",
    "facebook":         "https://www.facebook.com",
    "x":                "https://x.com",
    "twitter":          "https://x.com",
    "linkedin":         "https://www.linkedin.com",
    "reddit":           "https://www.reddit.com",
    "quora":            "https://www.quora.com",
    "medium":           "https://medium.com",
    "netflix":          "https://www.netflix.com",
    "prime video":      "https://www.primevideo.com",
}

APP_INSTALL_HINTS = {
    "chrome": {
        "windows": "Google.Chrome",
        "mac": "google-chrome",
        "linux": "google-chrome-stable",
    },
    "google chrome": {
        "windows": "Google.Chrome",
        "mac": "google-chrome",
        "linux": "google-chrome-stable",
    },
    "firefox": {
        "windows": "Mozilla.Firefox",
        "mac": "firefox",
        "linux": "firefox",
    },
    "edge": {
        "windows": "Microsoft.Edge",
        "mac": "microsoft-edge",
        "linux": "microsoft-edge-stable",
    },
    "vscode": {
        "windows": "Microsoft.VisualStudioCode",
        "mac": "visual-studio-code",
        "linux": "code",
    },
    "vs code": {
        "windows": "Microsoft.VisualStudioCode",
        "mac": "visual-studio-code",
        "linux": "code",
    },
    "visual studio code": {
        "windows": "Microsoft.VisualStudioCode",
        "mac": "visual-studio-code",
        "linux": "code",
    },
    "spotify": {
        "windows": "Spotify.Spotify",
        "mac": "spotify",
        "linux": "spotify",
    },
    "discord": {
        "windows": "Discord.Discord",
        "mac": "discord",
        "linux": "discord",
    },
    "telegram": {
        "windows": "Telegram.TelegramDesktop",
        "mac": "telegram",
        "linux": "telegram-desktop",
    },
    "slack": {
        "windows": "SlackTechnologies.Slack",
        "mac": "slack",
        "linux": "slack",
    },
    "postman": {
        "windows": "Postman.Postman",
        "mac": "postman",
        "linux": "postman",
    },
    "capcut": {
        "windows": "Bytedance.CapCut",
        "mac": "capcut",
        "linux": "capcut",
    },
    "vlc": {
        "windows": "VideoLAN.VLC",
        "mac": "vlc",
        "linux": "vlc",
    },
}


def _os_key() -> str:
    if OS == "Windows":
        return "windows"
    if OS == "Darwin":
        return "mac"
    return "linux"


def _normalize_app_name(app_name: str) -> str:
    name = app_name.strip().strip('"').strip("'").lower()
    name = name.removeprefix("the ")
    # FIX: tightened regex — only strip if the word is alone at the start,
    # followed by a space, to avoid eating "software X" → "X" unexpectedly.
    name = re.sub(r"^(?:app|application|program|software)\s+", "", name)
    return name.strip()


def _normalize_terminal_command(command: str) -> str:
    """
    Strip natural-language prefixes like 'run: ', 'execute command: ', etc.
    FIX: was too greedy — now only strips the prefix phrase, not content after
    a colon that is part of the actual command (e.g. 'python -c: ...' is kept).
    """
    cmd = command.strip()
    # Only strip if the prefix is followed by optional whitespace at the start
    cmd = re.sub(
        r"^(?:run|execute)(?:\s+(?:the\s+)?command)?\s*:\s*",
        "",
        cmd,
        flags=re.IGNORECASE,
    )
    return cmd.strip()


def _linux_app_candidates(app_name: str, executable: str) -> list[str]:
    candidates = [executable]
    if app_name in {"chrome", "google chrome"}:
        candidates = [
            "google-chrome",
            "google-chrome-stable",
            "chrome",
            "chromium",
            "chromium-browser",
            "brave-browser",
        ]
    elif app_name in {"edge", "microsoft edge"}:
        candidates = ["microsoft-edge", "microsoft-edge-stable", "msedge"]
    elif app_name in {"vscode", "vs code", "visual studio code"}:
        candidates = ["code", "codium"]
    elif app_name == "terminal":
        candidates = [
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "mate-terminal",
            "tilix",
            "lxterminal",
            "alacritty",
            "kitty",
            "xterm",
            "x-terminal-emulator",
        ]
    return list(dict.fromkeys(candidates))


def _is_app_installed(app_name: str, executable: str) -> bool:
    if app_name in WEB_APP_MAP:
        return True

    if OS == "Windows":
        candidate = executable.replace('"', "").strip()
        if shutil.which(candidate):
            return True
        candidate_exe = candidate if candidate.lower().endswith(".exe") else candidate + ".exe"
        for base in filter(None, [
            os.getenv("ProgramFiles"),
            os.getenv("ProgramFiles(x86)"),
            os.getenv("LocalAppData"),
        ]):
            if os.path.exists(os.path.join(base, candidate_exe)):
                return True
        start_menu_roots = [
            os.path.join(os.getenv("ProgramData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
            os.path.join(os.getenv("AppData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        ]
        needles = {app_name, candidate.lower().removesuffix(".exe")}
        for root in filter(os.path.isdir, start_menu_roots):
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if not filename.lower().endswith((".lnk", ".url", ".appref-ms")):
                        continue
                    stem = os.path.splitext(filename)[0].lower()
                    if any(needle and needle in stem for needle in needles):
                        return True
        return False

    if OS == "Darwin":
        if shutil.which(executable):
            return True
        app_bundle = executable if executable.endswith(".app") else f"{executable}.app"
        app_dirs = ["/Applications", os.path.expanduser("~/Applications")]
        for app_dir in app_dirs:
            if os.path.exists(os.path.join(app_dir, app_bundle)):
                return True
            if os.path.isdir(app_dir):
                expected = app_bundle.lower()
                if any(entry.lower() == expected for entry in os.listdir(app_dir)):
                    return True
        return False

    for candidate in _linux_app_candidates(app_name, executable):
        if shutil.which(candidate):
            return True

    desktop_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
    ]
    needles = {app_name, executable.lower()}
    for desktop_dir in filter(os.path.isdir, desktop_dirs):
        for filename in os.listdir(desktop_dir):
            stem = os.path.splitext(filename)[0].lower().replace("-", " ")
            if filename.lower().endswith(".desktop") and any(needle and needle in stem for needle in needles):
                return True
    return False


def _find_package_manager() -> tuple[str | None, list[str] | None]:
    if OS == "Windows":
        if shutil.which("winget"):
            return "winget", ["winget", "install", "--id"]
        if shutil.which("choco"):
            return "choco", ["choco", "install", "-y"]
        if shutil.which("scoop"):
            return "scoop", ["scoop", "install"]
        return None, None

    if OS == "Darwin":
        if shutil.which("brew"):
            return "brew", ["brew", "install"]
        return None, None

    linux_candidates = [
        ("apt", ["apt-get", "install", "-y"]),
        ("dnf", ["dnf", "install", "-y"]),
        ("pacman", ["pacman", "-S", "--noconfirm"]),
        ("snap", ["snap", "install"]),
        ("flatpak", ["flatpak", "install", "-y", "flathub"]),
    ]
    for name, cmd in linux_candidates:
        if shutil.which(name):
            return name, cmd
    return None, None


def _install_app(app_name: str, executable: str) -> tuple[bool, str]:
    hint = APP_INSTALL_HINTS.get(app_name, {})
    package_name = hint.get(_os_key()) or executable
    manager_name, base_cmd = _find_package_manager()
    if not manager_name or not base_cmd:
        return False, f"No supported package manager found to install '{app_name}'."

    cmd = list(base_cmd)
    if manager_name == "winget":
        cmd.extend([package_name, "-e", "--accept-package-agreements", "--accept-source-agreements"])
    else:
        cmd.append(package_name)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode == 0:
            return True, output or f"Installed '{app_name}' using {manager_name}."
        if len(output) > 500:
            output = output[-500:]
        return False, output or f"{manager_name} returned exit code {result.returncode}."
    except subprocess.TimeoutExpired:
        return False, f"Install timed out while installing '{app_name}'."
    except Exception as exc:
        return False, str(exc)


def _open_windows(executable: str) -> bool:
    try:
        subprocess.Popen(
            ["start", "", executable],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        pass

    try:
        os.startfile(executable)
        return True
    except Exception:
        pass

    try:
        subprocess.Popen(
            [executable],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        pass

    return False


def _open_linux(app_name: str, executable: str) -> bool:
    """
    Try common Linux launch strategies for apps.
    FIX: removed incorrect fallback that opened a browser tab (about:blank)
    for non-browser apps when the binary wasn't found. That was misleading —
    it returned True (success) even though the requested app never opened.
    """
    for candidate in _linux_app_candidates(app_name, executable):
        resolved = shutil.which(candidate)
        if not resolved:
            continue
        try:
            subprocess.Popen([resolved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue

    # Only fall back to xdg-open for browser-like apps
    if app_name in {"chrome", "google chrome", "firefox", "edge", "microsoft edge"}:
        try:
            webbrowser.open_new_tab("about:blank")
            return True
        except Exception:
            pass
        try:
            subprocess.Popen(["xdg-open", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    return False


def _linux_terminal_candidates(command: str) -> list[list[str]]:
    if command:
        shell_cmd = f"{command}; exec bash"
        return [
            ["gnome-terminal", "--", "bash", "-lc", shell_cmd],
            ["konsole", "-e", "bash", "-lc", shell_cmd],
            ["xfce4-terminal", "-e", "bash", "-lc", shell_cmd],
            ["mate-terminal", "--", "bash", "-lc", shell_cmd],
            ["tilix", "-e", "bash", "-lc", shell_cmd],
            ["lxterminal", "-e", "bash", "-lc", shell_cmd],
            ["alacritty", "-e", "bash", "-lc", shell_cmd],
            ["kitty", "-e", "bash", "-lc", shell_cmd],
            ["xterm", "-e", "bash", "-lc", shell_cmd],
            ["x-terminal-emulator", "-e", "bash", "-lc", shell_cmd],
        ]
    return [
        ["gnome-terminal"],
        ["konsole"],
        ["xfce4-terminal"],
        ["mate-terminal"],
        ["tilix"],
        ["lxterminal"],
        ["alacritty"],
        ["kitty"],
        ["xterm"],
        ["x-terminal-emulator"],
    ]


def open_app(app_name: str) -> str:
    """
    Open an application by name on Windows, macOS, or Linux.
    Supports 50+ common app aliases.
    """
    name = _normalize_app_name(app_name)

    if name in WEB_APP_MAP:
        url = WEB_APP_MAP[name]
        try:
            opened = webbrowser.open_new_tab(url)
            if opened:
                return f"🌐 Opened **{app_name}** in your browser."
        except Exception:
            pass

        if OS == "Linux":
            try:
                subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"🌐 Opened **{app_name}** in your browser."
            except Exception:
                pass

        return f"❌ Could not open '{app_name}' in a browser. Try: {url}"

    executable = APP_MAP.get(name, name)

    logger.info(f"open_app: '{app_name}' → '{executable}' on {OS}")

    try:
        if OS == "Windows":
            ok = _open_windows(executable)
            if ok:
                return f"✅ Opened **{app_name}** successfully."
            return (
                f"❌ Could not open '{app_name}'.\n"
                f"Make sure it's installed. You can also try 'run terminal: start {executable}'"
            )

        elif OS == "Darwin":
            subprocess.Popen(
                ["open", "-a", executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"✅ Opened **{app_name}**."

        else:  # Linux
            ok = _open_linux(name, executable)
            if ok:
                return f"✅ Opened **{app_name}**."
            return (
                f"❌ Could not open '{app_name}'. It may not be installed.\n"
                f"Try: `which {executable}` in a terminal to check."
            )

    except FileNotFoundError:
        if OS == "Windows":
            return (
                f"❌ '{app_name}' not found on PATH.\n"
                f"Try the full path, or use: 'run terminal: start {executable}'"
            )
        return (
            f"❌ '{app_name}' not found on PATH.\n"
            f"Try installing it first."
        )
    except Exception as e:
        return f"❌ Could not open '{app_name}': {e}"


def open_terminal(command: str = "") -> str:
    """
    Open a terminal window, optionally running a command.
    FIX (Linux): replaced unreliable proc.poll() race-condition check with a
    short sleep + explicit returncode check to detect immediately-crashed terminals.
    """
    cmd = _normalize_terminal_command(command)
    try:
        if OS == "Windows":
            if cmd:
                if shutil.which("wt"):
                    subprocess.Popen(["wt", "cmd", "/k", cmd])
                else:
                    subprocess.Popen(["cmd", "/k", cmd])
                return "✅ Opened terminal and ran the command."
            if shutil.which("wt"):
                subprocess.Popen(["wt"])
            else:
                subprocess.Popen(["cmd"])
            return "✅ Opened terminal."

        if OS == "Darwin":
            if cmd:
                escaped = cmd.replace("\\", "\\\\").replace('"', '\\"')
                subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{escaped}"'])
                return "✅ Opened Terminal and ran the command."
            subprocess.Popen(["open", "-a", "Terminal"])
            return "✅ Opened Terminal."

        # ── Linux ────────────────────────────────────────────────────────────
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return "❌ No active Linux GUI session detected to open a terminal."

        candidates = _linux_terminal_candidates(cmd)
        for candidate in candidates:
            exe = candidate[0]
            if not shutil.which(exe):
                continue
            try:
                proc = subprocess.Popen(
                    candidate,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # FIX: give the process a moment to start, then check if it
                # crashed immediately. A healthy terminal stays running (None).
                time.sleep(0.15)
                rc = proc.poll()
                if rc is not None and rc != 0:
                    # Terminal exited immediately with an error — try next one
                    logger.debug(f"open_terminal: {exe} exited with rc={rc}, trying next")
                    continue
                msg = "✅ Opened terminal."
                if cmd:
                    msg = "✅ Opened terminal and ran the command."
                return msg
            except Exception as exc:
                logger.debug(f"open_terminal: {exe} raised {exc}, trying next")
                continue

        return "❌ Could not find a working terminal application. Install gnome-terminal, konsole, or xterm."

    except Exception as e:
        return f"❌ Could not open terminal: {e}"


def smart_open_app(app_name: str) -> str:
    """
    Open an app with OS-aware install fallback.
    FIX: guard against empty executable string after normalization.
    """
    name = _normalize_app_name(app_name)
    if not name:
        return "❓ Please tell me which app to open."

    executable = APP_MAP.get(name, name)

    # FIX: if normalization produced an empty executable, bail early
    if not executable:
        return f"❓ Could not determine the executable for '{app_name}'."

    if name in WEB_APP_MAP:
        return open_app(name)

    if _is_app_installed(name, executable):
        return open_app(name)

    installed, install_msg = _install_app(name, executable)
    if not installed:
        return (
            f"❌ '{app_name}' is not installed and I couldn't auto-install it on {OS}.\n"
            f"Reason: {install_msg}"
        )

    launch_result = open_app(name)
    if launch_result.startswith("✅") or launch_result.startswith("🌐"):
        return f"✅ Installed and opened **{app_name}** on {OS}."
    return (
        f"✅ Installed **{app_name}** on {OS}, but opening it still failed.\n"
        f"{launch_result}"
    )


def open_youtube_music(query: str = "") -> str:
    """Open YouTube Music, optionally with a search query."""
    q = query.strip()
    if q:
        url = "https://music.youtube.com/search?q=" + urllib.parse.quote_plus(q)
    else:
        url = "https://music.youtube.com"
    try:
        if OS == "Linux":
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif OS == "Darwin":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["start", "", url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "🎵 Opened YouTube Music."
    except Exception:
        ok = webbrowser.open_new_tab(url)
        if ok:
            return "🎵 Opened YouTube Music."
        return f"❌ Could not open YouTube Music. Try: {url}"


def close_app(app_name: str) -> str:
    """
    Close a running application by name.
    FIX (Linux): pkill return code is now checked properly.
      rc=0 → processes killed, rc=1 → no matching process found.
    """
    name = app_name.strip().lower()
    PROC_MAP = {
        "chrome":       "chrome.exe",
        "firefox":      "firefox.exe",
        "edge":         "msedge.exe",
        "vscode":       "Code.exe",
        "vs code":      "Code.exe",
        "notepad":      "notepad.exe",
        "spotify":      "Spotify.exe",
        "discord":      "Discord.exe",
        "vlc":          "vlc.exe",
        "paint":        "mspaint.exe",
        "word":         "WINWORD.EXE",
        "excel":        "EXCEL.EXE",
        "powerpoint":   "POWERPNT.EXE",
        "teams":        "Teams.exe",
        "zoom":         "Zoom.exe",
        "steam":        "steam.exe",
        "task manager": "taskmgr.exe",
    }
    proc = PROC_MAP.get(name, name if name.endswith(".exe") else name + ".exe")

    try:
        if OS == "Windows":
            result = subprocess.run(
                ["taskkill", "/IM", proc, "/F"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return f"✅ Closed **{app_name}**."
            result2 = subprocess.run(
                ["taskkill", "/IM", proc.replace(".exe", ""), "/F"],
                capture_output=True, text=True, timeout=10,
            )
            if result2.returncode == 0:
                return f"✅ Closed **{app_name}**."
            return f"⚠️ Could not close '{app_name}': {result.stderr.strip()}"

        else:
            # FIX: strip .exe suffix for Linux/macOS process names, and check
            # pkill return code. rc=1 means no process matched.
            proc_name = name.replace(".exe", "").strip()
            result = subprocess.run(
                ["pkill", "-f", proc_name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return f"✅ Closed **{app_name}**."
            if result.returncode == 1:
                return f"⚠️ No running process found matching '{app_name}'."
            return f"⚠️ Could not close '{app_name}': {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return f"⚠️ Timed out trying to close '{app_name}'."
    except Exception as e:
        return f"❌ Error closing '{app_name}': {e}"


def shutdown_pc(unused: str = "") -> str:
    """
    Shut down the computer.
    FIX (Linux): removed broken `sudo -n` prefix that caused silent failures on
    most desktop systems. `systemctl poweroff` works without sudo for the
    logged-in session user via polkit/logind on modern distros (Ubuntu, Fedora,
    Arch, etc.). Also removed invalid `loginctl poweroff` command.
    Fallback chain: systemctl → shutdown → poweroff binary.
    """
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
            return "🔴 **Shutting down** in 5 seconds...\nRun `shutdown /a` in CMD to cancel."

        # macOS
        if OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to shut down'], check=True)
            return "🔴 **Shutting down** now."

        # Linux — try commands that work for a logged-in desktop user
        # without sudo. systemctl poweroff is handled by logind/polkit on
        # all major modern distros when run from an active session.
        linux_shutdown_cmds = [
            ["systemctl", "poweroff"],
            ["shutdown", "-h", "now"],
            ["poweroff"],
        ]
        last_error: Exception | None = None
        for cmd in linux_shutdown_cmds:
            if not shutil.which(cmd[0]):
                continue
            try:
                subprocess.run(cmd, check=True)
                return "🔴 **Shutting down** now."
            except subprocess.CalledProcessError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

        err_detail = str(last_error) if last_error else "no supported shutdown command found"
        return (
            f"❌ Shutdown failed: {err_detail}\n"
            "If you're not in a graphical session, you may need sudo rights."
        )

    except Exception as e:
        return f"❌ Shutdown failed: {e}"


def restart_pc(unused: str = "") -> str:
    """
    Restart the computer.
    FIX (Linux): same fixes as shutdown_pc — removed `sudo -n` and invalid
    `loginctl reboot`. Fallback chain: systemctl → shutdown -r → reboot binary.
    """
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
            return "🔄 **Restarting** in 5 seconds...\nRun `shutdown /a` in CMD to cancel."

        if OS == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to restart'], check=True)
            return "🔄 **Restarting** now."

        # Linux — same polkit/logind logic as shutdown
        linux_reboot_cmds = [
            ["systemctl", "reboot"],
            ["shutdown", "-r", "now"],
            ["reboot"],
        ]
        last_error: Exception | None = None
        for cmd in linux_reboot_cmds:
            if not shutil.which(cmd[0]):
                continue
            try:
                subprocess.run(cmd, check=True)
                return "🔄 **Restarting** now."
            except subprocess.CalledProcessError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

        err_detail = str(last_error) if last_error else "no supported reboot command found"
        return (
            f"❌ Restart failed: {err_detail}\n"
            "If you're not in a graphical session, you may need sudo rights."
        )

    except Exception as e:
        return f"❌ Restart failed: {e}"


def open_folder(path: str) -> str:
    """Open a folder in the system file explorer."""
    folder = path.strip().strip('"').strip("'")

    aliases = {
        "desktop":   os.path.join(os.path.expanduser("~"), "Desktop"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "pictures":  os.path.join(os.path.expanduser("~"), "Pictures"),
        "music":     os.path.join(os.path.expanduser("~"), "Music"),
        "videos":    os.path.join(os.path.expanduser("~"), "Videos"),
        "home":      os.path.expanduser("~"),
    }
    folder = aliases.get(folder.lower(), folder)

    if not os.path.isdir(folder):
        return f"❌ Folder not found: `{folder}`"

    try:
        if OS == "Windows":
            subprocess.Popen(["explorer", folder])
        elif OS == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
        return f"📂 Opened folder: `{folder}`"
    except Exception as e:
        return f"❌ Could not open folder: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# SCREENSHOT + SCREEN READER
# ══════════════════════════════════════════════════════════════════════════════

def _take_screenshot_linux(save_path: str) -> tuple[bool, str]:
    """
    FIX: PIL.ImageGrab.grab() does not work on Linux without a special Pillow
    build. Use system screenshot tools instead.
    Priority: scrot → gnome-screenshot → import (ImageMagick) → xwd+convert.
    """
    # scrot — lightweight, widely available
    if shutil.which("scrot"):
        try:
            result = subprocess.run(["scrot", save_path], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, save_path
        except Exception:
            pass

    # gnome-screenshot
    if shutil.which("gnome-screenshot"):
        try:
            result = subprocess.run(
                ["gnome-screenshot", "-f", save_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True, save_path
        except Exception:
            pass

    # ImageMagick import
    if shutil.which("import"):
        try:
            result = subprocess.run(
                ["import", "-window", "root", save_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return True, save_path
        except Exception:
            pass

    # xwd + convert (ImageMagick) as last resort
    if shutil.which("xwd") and shutil.which("convert"):
        xwd_path = save_path.replace(".png", ".xwd")
        try:
            r1 = subprocess.run(["xwd", "-root", "-out", xwd_path], capture_output=True, text=True, timeout=10)
            if r1.returncode == 0:
                r2 = subprocess.run(["convert", xwd_path, save_path], capture_output=True, text=True, timeout=10)
                if r2.returncode == 0:
                    return True, save_path
        except Exception:
            pass
        finally:
            if os.path.exists(xwd_path):
                try:
                    os.remove(xwd_path)
                except OSError as e:
                    logger.debug("Failed to clean up temp file %s: %s", xwd_path, e)

    return False, (
        "No screenshot tool found on this Linux system.\n"
        "Install one with: `sudo apt install scrot` or `sudo apt install gnome-screenshot`"
    )


def take_screenshot(filename: str = "") -> str:
    """
    Capture a full screenshot of the desktop.
    Input: optional filename (without extension). Defaults to timestamped name.
    Saves to ~/Pictures/sara_screenshots/.
    Windows/macOS: requires Pillow (`pip install Pillow`).
    Linux: uses scrot / gnome-screenshot / ImageMagick (no Pillow needed).
    """
    import datetime

    save_dir = os.path.join(os.path.expanduser("~"), "Pictures", "sara_screenshots")
    os.makedirs(save_dir, exist_ok=True)

    fn = filename.strip().replace(" ", "_") if filename.strip() else ""
    if not fn:
        fn = datetime.datetime.now().strftime("screenshot_%Y%m%d_%H%M%S")
    if not fn.lower().endswith(".png"):
        fn += ".png"
    save_path = os.path.join(save_dir, fn)

    # ── Linux: use system tools ───────────────────────────────────────────────
    if OS == "Linux":
        ok, detail = _take_screenshot_linux(save_path)
        if ok:
            return f"📸 Screenshot saved!\n  Path: `{save_path}`"
        return f"❌ Screenshot failed: {detail}"

    # ── Windows / macOS: use Pillow ───────────────────────────────────────────
    try:
        from PIL import ImageGrab
    except ImportError:
        return "❌ Pillow not installed.\nRun: `pip install Pillow`"

    try:
        img = ImageGrab.grab()
        img.save(save_path)
        w, h = img.size
        return (
            f"📸 Screenshot saved!\n"
            f"  Path: `{save_path}`\n"
            f"  Size: {w} × {h} px"
        )
    except Exception as e:
        return f"❌ Screenshot failed: {e}"


def read_screen(unused: str = "") -> str:
    """
    Take a screenshot and extract all visible text using OCR (pytesseract).
    FIX (Linux): use system screenshot tools instead of PIL.ImageGrab which
    does not work on Linux. Screenshot is saved to a temp file, then OCR'd.
    Requires: pip install pytesseract
    Also requires Tesseract OCR binary.
    Linux install: sudo apt install tesseract-ocr
    """
    import datetime
    import tempfile

    try:
        import pytesseract
    except ImportError:
        return (
            "❌ pytesseract not installed.\n"
            "Run: `pip install pytesseract`\n"
            "Also install Tesseract: `sudo apt install tesseract-ocr` (Linux) or\n"
            "  https://github.com/UB-Mannheim/tesseract/wiki (Windows)"
        )

    # ── Grab the screenshot ───────────────────────────────────────────────────
    if OS == "Linux":
        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"sara_ocr_{datetime.datetime.now().strftime('%H%M%S%f')}.png",
        )
        ok, detail = _take_screenshot_linux(tmp_path)
        if not ok:
            return f"❌ Could not capture screen: {detail}"
        try:
            from PIL import Image
            img = Image.open(tmp_path)
        except ImportError:
            # pytesseract can also work with a file path directly
            try:
                text = pytesseract.image_to_string(tmp_path).strip()
            except Exception as e:
                return f"❌ OCR error: {e}"
            finally:
                try:
                    os.remove(tmp_path)
                except OSError as e:
                    logger.debug("Failed to clean up temp file %s: %s", tmp_path, e)
            if not text:
                return "👁️ Screen captured but no readable text found."
            if len(text) > 2000:
                text = text[:1970] + "\n... [truncated]"
            return f"👁️ Text on screen:\n```\n{text}\n```"
        finally:
            try:
                os.remove(tmp_path)
            except OSError as e:
                logger.debug("Failed to clean up temp file %s: %s", tmp_path, e)
    else:
        try:
            from PIL import ImageGrab
        except ImportError:
            return "❌ Pillow not installed. Run: `pip install Pillow`"
        try:
            img = ImageGrab.grab()
        except Exception as e:
            return f"❌ Screenshot failed: {e}"

    try:
        text = pytesseract.image_to_string(img).strip()
        if not text:
            return "👁️ Screen captured but no readable text found."
        if len(text) > 2000:
            text = text[:1970] + "\n... [truncated]"
        return f"👁️ Text on screen:\n```\n{text}\n```"
    except pytesseract.TesseractNotFoundError:
        return (
            "❌ Tesseract binary not found.\n"
            "Linux:   sudo apt install tesseract-ocr\n"
            "Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as e:
        return f"❌ Screen reader error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# CLIPBOARD
# ══════════════════════════════════════════════════════════════════════════════

def clipboard_read(unused: str = "") -> str:
    """Read and return the current clipboard text content."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text:
            return "📋 Clipboard is empty."
        preview = text[:500] + ("..." if len(text) > 500 else "")
        return f"📋 Clipboard ({len(text)} chars):\n```\n{preview}\n```"
    except ImportError:
        return "❌ pyperclip not installed. Run: `pip install pyperclip`"
    except Exception as e:
        return f"❌ Clipboard read error: {e}"


def clipboard_write(text: str) -> str:
    """Write text to the system clipboard."""
    text = text.strip()
    if not text:
        return "❓ Please provide text to write to clipboard."
    try:
        import pyperclip
        pyperclip.copy(text)
        preview = text[:80] + ("..." if len(text) > 80 else "")
        return f"📋 Copied to clipboard ({len(text)} chars): \"{preview}\""
    except ImportError:
        return "❌ pyperclip not installed. Run: `pip install pyperclip`"
    except Exception as e:
        return f"❌ Clipboard write error: {e}"