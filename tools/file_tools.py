import os
import logging

logger = logging.getLogger(__name__)

MAX_READ_BYTES = 4096  # 4 KB read limit
MAX_LIST_ITEMS = 50

# Paths that are never allowed for write/delete operations
PROTECTED_ROOTS = [
    os.environ.get("WINDIR", "C:\\Windows"),
    os.environ.get("SystemRoot", "C:\\Windows"),
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
]


def _is_protected(path: str) -> bool:
    """Return True if the path is inside a protected system directory."""
    abs_path = os.path.abspath(path)
    return any(abs_path.lower().startswith(p.lower()) for p in PROTECTED_ROOTS if p)


def read_file(file_path: str) -> str:
    """Read and return the contents of a text file (up to 4 KB)."""
    path = file_path.strip().strip('"').strip("'")
    if not os.path.isfile(path):
        return f"❌ File not found: `{path}`"
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_READ_BYTES)
        truncated = size > MAX_READ_BYTES
        note = f"\n\n_(Showing first 4 KB of {size:,} byte file)_" if truncated else ""
        return f"📄 **{os.path.basename(path)}**:\n```\n{content}\n```{note}"
    except PermissionError:
        return f"⛔ Permission denied: `{path}`"
    except Exception as e:
        return f"❌ Could not read file: {e}"


def write_file(value: str) -> str:
    """Create or overwrite a file. Input format: 'path::content'"""
    if "::" not in value:
        return "❓ Format: `write_file path::content`\nExample: `notes.txt::Hello World`"
    path, content = value.split("::", 1)
    path = path.strip().strip('"').strip("'")
    if _is_protected(path):
        return f"⛔ Writing to `{path}` is not allowed (protected system path)."
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ File written: `{path}` ({len(content):,} chars)"
    except PermissionError:
        return f"⛔ Permission denied: `{path}`"
    except Exception as e:
        return f"❌ Could not write file: {e}"


def create_folder(path: str) -> str:
    """Create a directory and all intermediate parents."""
    folder = path.strip().strip('"').strip("'")
    if _is_protected(folder):
        return f"⛔ Creating folders in `{folder}` is not allowed."
    try:
        os.makedirs(folder, exist_ok=True)
        return f"✅ Folder created: `{folder}`"
    except PermissionError:
        return f"⛔ Permission denied: `{folder}`"
    except Exception as e:
        return f"❌ Could not create folder: {e}"


def delete_file(file_path: str) -> str:
    """Delete a file (not directories). Blocked on protected system paths."""
    path = file_path.strip().strip('"').strip("'")
    if _is_protected(path):
        return f"⛔ Deleting `{path}` is not allowed (protected path)."
    if os.path.isdir(path):
        return f"⛔ `{path}` is a directory. Only files can be deleted this way."
    if not os.path.isfile(path):
        return f"❌ File not found: `{path}`"
    try:
        os.remove(path)
        return f"🗑️ Deleted: `{path}`"
    except PermissionError:
        return f"⛔ Permission denied: `{path}`"
    except Exception as e:
        return f"❌ Could not delete file: {e}"


def list_files(directory: str) -> str:
    """List files and folders in a directory (up to 50 items)."""
    folder = directory.strip().strip('"').strip("'") or "."
    if not os.path.isdir(folder):
        return f"❌ Directory not found: `{folder}`"
    try:
        entries = sorted(os.scandir(folder), key=lambda e: (not e.is_dir(), e.name.lower()))
        if not entries:
            return f"📁 `{folder}` is empty."

        lines = []
        for entry in entries[:MAX_LIST_ITEMS]:
            if entry.is_dir():
                lines.append(f"  📁 {entry.name}/")
            else:
                size = entry.stat().st_size
                size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                lines.append(f"  📄 {entry.name}  ({size_str})")

        total = len(list(os.scandir(folder)))
        note = f"\n_(showing {MAX_LIST_ITEMS} of {total})_" if total > MAX_LIST_ITEMS else ""
        return f"📂 `{folder}`:\n" + "\n".join(lines) + note
    except PermissionError:
        return f"⛔ Permission denied: `{folder}`"
    except Exception as e:
        return f"❌ Could not list folder: {e}"


def export_chat(user_id: str = "") -> str:
    """
    Export the full conversation history to a Markdown file.
    Saves to ~/Documents/sara_exports/chat_<timestamp>.md
    Input: user_id (passed automatically by execute_tool via user_id kwarg)
    """
    import datetime
    from memory.context_manager import get_recent_messages, _get_history

    uid = (user_id or "default").strip()

    # Load all messages
    try:
        # Access full history (not just recent)
        from memory.context_manager import _chat_histories, _load_history
        history = _chat_histories.get(uid) or _load_history(uid)
    except Exception:
        history = []

    if not history:
        return "📭 No conversation history to export yet."

    # Build output directory
    export_dir = os.path.join(os.path.expanduser("~"), "Documents", "sara_exports")
    os.makedirs(export_dir, exist_ok=True)

    # Build filename
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_{uid}_{ts}.md"
    filepath = os.path.join(export_dir, filename)

    # Format as Markdown
    lines = [
        f"# Sara AI — Chat Export",
        f"**User:** `{uid}`  ",
        f"**Exported:** {datetime.datetime.now().strftime('%A, %d %B %Y at %I:%M %p')}  ",
        f"**Messages:** {len(history)}",
        "",
        "---",
        "",
    ]

    for i, msg in enumerate(history, 1):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        emoji = "🧑" if role == "user" else "🤖"
        lines.append(f"### {emoji} {role.title()} (msg {i})")
        lines.append(content)
        lines.append("")

    content_str = "\n".join(lines)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content_str)
        return (
            f"💾 Chat exported!\n"
            f"  File: `{filepath}`\n"
            f"  Messages: {len(history)}\n"
            f"  Size: {len(content_str):,} chars"
        )
    except Exception as e:
        return f"❌ Could not export chat: {e}"

