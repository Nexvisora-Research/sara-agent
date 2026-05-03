import subprocess
import os
import platform
import logging
import sys
import re

logger = logging.getLogger(__name__)
OS = platform.system()

PROJECTS_DIR = os.path.join(os.path.expanduser("~"), "sara_projects")


def run_terminal(command: str) -> str:
    """Run any shell command and return its output (stdout + stderr, up to 2000 chars)."""
    command = command.strip()
    command = re.sub(r"^(?:run|execute)(?:\s+(?:terminal|shell|cmd))?(?:\s+command)?\s*[:\-]?\s+", "", command, flags=re.IGNORECASE)
    command = re.sub(r"^command\s*[:\-]?\s+", "", command, flags=re.IGNORECASE).strip()
    if not command:
        return "❓ Please provide a command to run."
    # Safety: block obviously destructive commands
    BLOCKED = ["rm -rf /", "del /f /s /q c:\\", "format c:", "mkfs"]
    if any(b in command.lower() for b in BLOCKED):
        return "⛔ That command is blocked for safety reasons."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            output = "(no output)"
        if len(output) > 2000:
            output = output[:1970] + "\n... [truncated]"
        status = "✅" if result.returncode == 0 else "⚠️"
        return f"{status} `{command}`\n\n```\n{output}\n```"
    except subprocess.TimeoutExpired:
        return f"⌛ Command timed out after 30s: `{command}`"
    except Exception as e:
        return f"❌ Error running command: {e}"


def run_python(file_name: str) -> str:
    """Run a Python script and return its output."""
    path = file_name.strip().strip('"').strip("'")
    if not path.endswith(".py"):
        path += ".py"
    if not os.path.isfile(path):
        return f"❌ File not found: `{path}`"
    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip() or "(no output)"
        if len(output) > 2000:
            output = output[:1970] + "\n... [truncated]"
        status = "✅" if result.returncode == 0 else "⚠️"
        return f"{status} Ran `{path}`\n\n```\n{output}\n```"
    except subprocess.TimeoutExpired:
        return f"⌛ Script timed out after 30s."
    except Exception as e:
        return f"❌ Error running script: {e}"


def install_package(package_name: str) -> str:
    """Install a package using pip (Python) or npm (Node.js), auto-detected by name."""
    pkg = package_name.strip()
    pkg = re.sub(r"^(?:package|module|library)\s+", "", pkg, flags=re.IGNORECASE).strip()
    if not pkg:
        return "❓ Please specify a package name."

    # Determine manager: npm packages contain @, or user prefixes "npm:"
    if pkg.startswith("npm:"):
        manager = "npm"
        pkg = pkg[4:].strip()
    else:
        manager = "pip"

    try:
        if manager == "pip":
            cmd = [sys.executable, "-m", "pip", "install", pkg]
        else:
            cmd = ["npm", "install", "-g", pkg]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = (result.stdout + result.stderr).strip()
        if len(output) > 1500:
            output = output[-1500:]  # show tail (most relevant)
        status = "✅" if result.returncode == 0 else "❌"
        return f"{status} `{manager} install {pkg}`\n\n```\n{output}\n```"
    except subprocess.TimeoutExpired:
        return "⌛ Package install timed out (120s)."
    except FileNotFoundError:
        return f"❌ `{manager}` not found on PATH."
    except Exception as e:
        return f"❌ Install error: {e}"


def git_clone(repo_url: str) -> str:
    """Clone a GitHub (or any git) repository into ~/sara_projects/."""
    url = repo_url.strip()
    if not url:
        return "❓ Please provide a Git repo URL."
    if not url.startswith(("http://", "https://", "git@")):
        return "❌ Invalid URL. Use https://github.com/... format."

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    dest = os.path.join(PROJECTS_DIR, repo_name)

    if os.path.isdir(dest):
        return f"⚠️ Already cloned at `{dest}`."

    try:
        result = subprocess.run(
            ["git", "clone", url, dest],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return f"✅ Cloned `{repo_name}` → `{dest}`"
        return f"❌ Git clone failed:\n```\n{result.stderr.strip()}\n```"
    except subprocess.TimeoutExpired:
        return "⌛ Git clone timed out (120s)."
    except FileNotFoundError:
        return "❌ `git` not found on PATH. Please install Git."
    except Exception as e:
        return f"❌ Clone error: {e}"


def create_project(project_name: str) -> str:
    """Scaffold a new project directory with src/, README.md, and main.py."""
    name = project_name.strip().replace(" ", "_")
    if not name:
        return "❓ Please provide a project name."

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    base = os.path.join(PROJECTS_DIR, name)

    if os.path.exists(base):
        return f"⚠️ Project `{name}` already exists at `{base}`."

    try:
        # Create folder structure
        os.makedirs(os.path.join(base, "src"), exist_ok=True)

        # README.md
        with open(os.path.join(base, "README.md"), "w") as f:
            f.write(f"# {name}\n\nCreated by Sara AI.\n")

        # main.py
        with open(os.path.join(base, "main.py"), "w") as f:
            f.write(f'# {name} — Entry point\n\ndef main():\n    print("Hello from {name}!")\n\nif __name__ == "__main__":\n    main()\n')

        # requirements.txt
        with open(os.path.join(base, "requirements.txt"), "w") as f:
            f.write("# Add your dependencies here\n")

        # .gitignore
        with open(os.path.join(base, ".gitignore"), "w") as f:
            f.write("__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\n")

        return (
            f"✅ Project `{name}` created at `{base}`\n\n"
            f"📁 Structure:\n"
            f"  {name}/\n"
            f"  ├── src/\n"
            f"  ├── main.py\n"
            f"  ├── requirements.txt\n"
            f"  ├── README.md\n"
            f"  └── .gitignore"
        )
    except Exception as e:
        return f"❌ Could not create project: {e}"
