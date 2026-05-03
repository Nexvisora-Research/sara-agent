"""
tools/monitor_tools.py — System Monitor Tools for Sara AI.

Provides real-time CPU, RAM, disk, and process info via psutil.
Requires: pip install psutil
"""

import logging
import platform

logger = logging.getLogger(__name__)
OS = platform.system()


def _require_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        return None


def get_cpu_usage(unused: str = "") -> str:
    """Get current CPU usage percentage (overall and per-core)."""
    psutil = _require_psutil()
    if not psutil:
        return "❌ psutil not installed. Run: `pip install psutil`"

    try:
        overall = psutil.cpu_percent(interval=1)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        freq = psutil.cpu_freq()
        core_lines = "  ".join(f"Core{i}: {p:.0f}%" for i, p in enumerate(per_core))

        freq_str = ""
        if freq:
            freq_str = f"\n  Frequency : {freq.current:.0f} MHz (max {freq.max:.0f} MHz)"

        return (
            f"🖥️ CPU Usage:\n"
            f"  Overall   : **{overall:.1f}%**\n"
            f"  Cores     : {core_lines}"
            f"{freq_str}\n"
            f"  Logical   : {psutil.cpu_count(logical=True)} cores"
        )
    except Exception as e:
        return f"❌ CPU monitor error: {e}"


def get_ram_usage(unused: str = "") -> str:
    """Get current RAM (memory) usage statistics."""
    psutil = _require_psutil()
    if not psutil:
        return "❌ psutil not installed. Run: `pip install psutil`"

    try:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        def fmt(b):
            gb = b / (1024 ** 3)
            return f"{gb:.2f} GB"

        bar_used = int(vm.percent / 5)  # out of 20 blocks
        bar = "█" * bar_used + "░" * (20 - bar_used)

        return (
            f"🧠 RAM Usage:\n"
            f"  [{bar}] {vm.percent:.1f}%\n"
            f"  Used  : {fmt(vm.used)} / {fmt(vm.total)}\n"
            f"  Free  : {fmt(vm.available)}\n"
            f"  Swap  : {fmt(swap.used)} / {fmt(swap.total)} ({swap.percent:.1f}% used)"
        )
    except Exception as e:
        return f"❌ RAM monitor error: {e}"


def get_disk_usage(path: str = "") -> str:
    """
    Get disk usage for a drive/path.
    Input: path (e.g. 'C:\\' or '/' or 'D:'). Defaults to system root.
    """
    psutil = _require_psutil()
    if not psutil:
        return "❌ psutil not installed. Run: `pip install psutil`"

    import os
    disk_path = path.strip() or ("C:\\" if OS == "Windows" else "/")

    try:
        usage = psutil.disk_usage(disk_path)

        def fmt(b):
            gb = b / (1024 ** 3)
            return f"{gb:.1f} GB"

        bar_used = int(usage.percent / 5)
        bar = "█" * bar_used + "░" * (20 - bar_used)

        # Also list all partitions briefly
        partitions = psutil.disk_partitions(all=False)
        part_lines = []
        for p in partitions[:6]:  # limit to 6
            try:
                u = psutil.disk_usage(p.mountpoint)
                part_lines.append(f"  {p.device:<10} {fmt(u.used):>8} / {fmt(u.total):<10} ({u.percent:.0f}%)")
            except PermissionError:
                continue

        parts_str = ("\nAll drives:\n" + "\n".join(part_lines)) if part_lines else ""

        return (
            f"💾 Disk: `{disk_path}`\n"
            f"  [{bar}] {usage.percent:.1f}%\n"
            f"  Used  : {fmt(usage.used)}\n"
            f"  Free  : {fmt(usage.free)}\n"
            f"  Total : {fmt(usage.total)}"
            f"{parts_str}"
        )
    except FileNotFoundError:
        return f"❌ Path not found: `{disk_path}`"
    except Exception as e:
        return f"❌ Disk monitor error: {e}"


def get_top_processes(n: str = "5") -> str:
    """
    List top N processes sorted by CPU usage.
    Input: number of processes (default 5).
    """
    psutil = _require_psutil()
    if not psutil:
        return "❌ psutil not installed. Run: `pip install psutil`"

    try:
        count = max(1, min(int(str(n).strip() or "5"), 20))
    except ValueError:
        count = 5

    try:
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # First pass to wake cpu_percent (it returns 0 on first call)
        import time
        time.sleep(0.5)
        procs = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        top = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:count]

        lines = [f"{'PID':<8} {'CPU%':>6} {'MEM%':>6}  Process"]
        lines.append("─" * 40)
        for p in top:
            name = (p.get("name") or "?")[:22]
            cpu = p.get("cpu_percent") or 0
            mem = p.get("memory_percent") or 0
            lines.append(f"{p['pid']:<8} {cpu:>5.1f}% {mem:>5.1f}%  {name}")

        return f"📊 Top {count} Processes (by CPU):\n```\n" + "\n".join(lines) + "\n```"
    except Exception as e:
        return f"❌ Process list error: {e}"


def get_system_stats(unused: str = "") -> str:
    """Quick combined system dashboard: CPU + RAM + Disk at a glance."""
    psutil = _require_psutil()
    if not psutil:
        return "❌ psutil not installed. Run: `pip install psutil`"

    try:
        import time

        # CPU — brief interval
        cpu = psutil.cpu_percent(interval=1)
        vm  = psutil.virtual_memory()
        disk_path = "C:\\" if OS == "Windows" else "/"
        try:
            disk = psutil.disk_usage(disk_path)
            disk_pct = disk.percent
            disk_free_gb = disk.free / (1024**3)
        except Exception:
            disk_pct = 0
            disk_free_gb = 0

        # Uptime
        boot = psutil.boot_time()
        uptime_secs = time.time() - boot
        uptime_h = int(uptime_secs // 3600)
        uptime_m = int((uptime_secs % 3600) // 60)

        # Emoji bars (10-block)
        def bar10(pct):
            filled = int(pct / 10)
            return "█" * filled + "░" * (10 - filled)

        return (
            f"📊 **System Dashboard**\n"
            f"  🖥️ CPU   [{bar10(cpu)}] {cpu:.1f}%\n"
            f"  🧠 RAM   [{bar10(vm.percent)}] {vm.percent:.1f}%  "
            f"({vm.used/1024**3:.1f}/{vm.total/1024**3:.1f} GB)\n"
            f"  💾 Disk  [{bar10(disk_pct)}] {disk_pct:.1f}%  "
            f"({disk_free_gb:.1f} GB free)\n"
            f"  ⏱️ Uptime: {uptime_h}h {uptime_m}m\n"
            f"  🔢 Processes: {len(psutil.pids())}"
        )
    except Exception as e:
        return f"❌ System stats error: {e}"
