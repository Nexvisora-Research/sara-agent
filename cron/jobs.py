"""Small JSON-backed cron job store used by the CLI and cron tool."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sara_constants import get_sara_home

_jobs_file_lock = threading.RLock()


def _jobs_path() -> Path:
    path = get_sara_home() / "cron" / "jobs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jobs() -> List[Dict[str, Any]]:
    path = _jobs_path()
    with _jobs_file_lock:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except Exception:
            return []
    if isinstance(payload, dict):
        jobs = payload.get("jobs", [])
    else:
        jobs = payload
    return [job for job in jobs if isinstance(job, dict)]


def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    path = _jobs_path()
    with _jobs_file_lock:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"jobs": jobs}, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def parse_schedule(schedule: str) -> Dict[str, Any]:
    text = str(schedule or "").strip()
    if not text:
        raise ValueError("schedule is required")
    return {"type": "cron", "value": text, "display": text}


def _next_run_at(_schedule: Dict[str, Any]) -> str:
    return _now_iso()


def list_jobs(include_disabled: bool = False) -> List[Dict[str, Any]]:
    jobs = load_jobs()
    if include_disabled:
        return jobs
    return [job for job in jobs if job.get("enabled", True)]


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    target = str(job_id)
    for job in load_jobs():
        if str(job.get("id")) == target:
            return job
    return None


def create_job(
    *,
    prompt: str,
    schedule: str,
    name: Optional[str] = None,
    repeat: Optional[int] = None,
    deliver: Optional[str] = None,
    origin: Optional[Dict[str, str]] = None,
    skills: Optional[List[str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    parsed = parse_schedule(schedule)
    job = {
        "id": f"job_{uuid.uuid4().hex[:12]}",
        "name": name or "Scheduled job",
        "prompt": prompt,
        "schedule": parsed,
        "schedule_display": parsed.get("display", schedule),
        "repeat": {"times": repeat} if repeat else None,
        "deliver": deliver or "local",
        "origin": origin,
        "skills": list(skills or []),
        "skill": (skills or [None])[0],
        "enabled": True,
        "state": "scheduled",
        "created_at": _now_iso(),
        "next_run_at": _next_run_at(parsed),
    }
    for key, value in extra.items():
        if value is not None:
            job[key] = value
    jobs = load_jobs()
    jobs.append(job)
    save_jobs(jobs)
    return job


def update_job(job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    jobs = load_jobs()
    for index, job in enumerate(jobs):
        if str(job.get("id")) == str(job_id):
            updated = dict(job)
            updated.update(updates)
            if "schedule" in updates and "next_run_at" not in updates:
                updated["next_run_at"] = _next_run_at(updated["schedule"])
            jobs[index] = updated
            save_jobs(jobs)
            return updated
    raise KeyError(f"Job not found: {job_id}")


def remove_job(job_id: str) -> bool:
    jobs = load_jobs()
    kept = [job for job in jobs if str(job.get("id")) != str(job_id)]
    if len(kept) == len(jobs):
        return False
    save_jobs(kept)
    return True


def pause_job(job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    return update_job(job_id, {
        "enabled": False,
        "state": "paused",
        "paused_at": _now_iso(),
        "paused_reason": reason,
    })


def resume_job(job_id: str) -> Dict[str, Any]:
    return update_job(job_id, {
        "enabled": True,
        "state": "scheduled",
        "paused_at": None,
        "paused_reason": None,
    })


def trigger_job(job_id: str) -> Dict[str, Any]:
    return update_job(job_id, {"state": "triggered", "next_run_at": _now_iso()})


def rewrite_skill_refs(old_name: str, new_name: str) -> int:
    changed = 0
    jobs = load_jobs()
    for job in jobs:
        skills = list(job.get("skills") or [])
        rewritten = [new_name if skill == old_name else skill for skill in skills]
        if rewritten != skills:
            job["skills"] = rewritten
            job["skill"] = rewritten[0] if rewritten else None
            changed += 1
    if changed:
        save_jobs(jobs)
    return changed
