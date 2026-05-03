"""
tools/reminder_tools.py — Real Timed Reminders with Toast Notifications for Sara AI.

Schedules background threads that fire OS notifications after a delay.
Requires: pip install plyer

Input format examples:
  "drink water in 5 minutes"
  "meeting in 30 minutes"
  "call mom in 1 hour"
  "standup in 45 mins"
"""

import re
import threading
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── In-memory reminder store ──────────────────────────────────────────────────
_reminders: list[dict] = []
_lock = threading.Lock()


def _parse_delay_seconds(text: str) -> tuple[int, str]:
    """
    Parse natural language delay from reminder text.
    Returns (delay_in_seconds, task_description).
    Returns (0, text) if no time found.
    """
    text = text.strip()

    # Patterns: "in N minutes/hours/seconds"
    patterns = [
        (r"in\s+(\d+)\s+hours?\b",   3600),
        (r"in\s+(\d+)\s+mins?\b",    60),
        (r"in\s+(\d+)\s+minutes?\b", 60),
        (r"in\s+(\d+)\s+secs?\b",    1),
        (r"in\s+(\d+)\s+seconds?\b", 1),
        (r"after\s+(\d+)\s+hours?\b",   3600),
        (r"after\s+(\d+)\s+mins?\b",    60),
        (r"after\s+(\d+)\s+minutes?\b", 60),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = int(match.group(1))
            delay = amount * multiplier
            # Strip the time phrase from the task description
            task = re.sub(pattern, "", text, flags=re.IGNORECASE)
            task = re.sub(r"\s{2,}", " ", task).strip().strip(",").strip()
            if not task:
                task = "Reminder!"
            return delay, task

    return 0, text


def _fire_notification(title: str, message: str, reminder_id: int) -> None:
    """Background thread: waits, fires toast notification, marks done."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Sara AI",
            timeout=10,
        )
        logger.info(f"Reminder fired: {message!r}")
    except ImportError:
        # Fallback: Windows MessageBox via ctypes
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        except Exception:
            logger.warning(f"Notification fallback also failed for: {message!r}")
    except Exception as e:
        logger.error(f"Notification error: {e}")
    finally:
        # Mark reminder as done
        with _lock:
            for r in _reminders:
                if r["id"] == reminder_id:
                    r["done"] = True
                    break


def set_reminder(text: str) -> str:
    """
    Set a timed reminder with a notification.

    Examples:
      "drink water in 5 minutes"
      "meeting in 30 minutes"
      "call mom in 1 hour"
    """
    if not text.strip():
        return "❓ Please say what to remind you about. E.g. 'drink water in 5 minutes'"

    delay_secs, task = _parse_delay_seconds(text)

    if delay_secs <= 0:
        # No time detected — set a 1-minute default
        delay_secs = 60
        task = text.strip()

    # Store reminder
    with _lock:
        reminder_id = len(_reminders) + 1
        fire_at = datetime.now() + timedelta(seconds=delay_secs)
        _reminders.append({
            "id":      reminder_id,
            "task":    task,
            "fire_at": fire_at,
            "delay":   delay_secs,
            "done":    False,
        })

    # Schedule background thread
    t = threading.Timer(
        delay_secs,
        _fire_notification,
        args=(f"⏰ Sara Reminder #{reminder_id}", task, reminder_id),
    )
    t.daemon = True
    t.start()

    # Build friendly time string
    if delay_secs < 60:
        time_str = f"{delay_secs} second{'s' if delay_secs != 1 else ''}"
    elif delay_secs < 3600:
        mins = delay_secs // 60
        time_str = f"{mins} minute{'s' if mins != 1 else ''}"
    else:
        hrs = delay_secs // 3600
        time_str = f"{hrs} hour{'s' if hrs != 1 else ''}"

    fire_at_str = fire_at.strftime("%I:%M %p")

    return (
        f"⏰ Reminder set! I'll notify you in **{time_str}** (at {fire_at_str}).\n"
        f"📌 Task: \"{task}\""
    )


def list_reminders(unused: str = "") -> str:
    """List all pending and completed reminders."""
    with _lock:
        if not _reminders:
            return "📭 No reminders set yet.\nTry: 'remind me to drink water in 5 minutes'"

        lines = []
        now = datetime.now()
        for r in _reminders:
            status = "✅ Done" if r["done"] else f"⏳ in {max(0, int((r['fire_at'] - now).total_seconds()))}s"
            fire_str = r["fire_at"].strftime("%I:%M %p")
            lines.append(f"  [{r['id']}] {r['task']} — {fire_str} ({status})")

        return "⏰ Reminders:\n" + "\n".join(lines)
