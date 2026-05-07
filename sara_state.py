"""SQLite session/state store for Sara Agent.

This module intentionally keeps the public surface small and dependency-free:
CLI, gateway, TUI, and session-search all share this database for session
metadata, transcripts, titles, and lightweight state metadata.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Optional

from sara_constants import get_sara_home

DEFAULT_DB_PATH = get_sara_home() / "state.db"


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _json_loads_maybe(value: Any) -> Any:
    if value is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if text[0] not in "[{\"":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _as_epoch(value: Any) -> float:
    if value is None:
        return time.time()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if hasattr(value, "timestamp"):
        try:
            return float(value.timestamp())
        except Exception:
            return time.time()
    return time.time()


class SessionDB:
    """SQLite-backed session metadata and transcript store."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError:
            pass
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL DEFAULT 'cli',
                user_id TEXT,
                model TEXT,
                model_config TEXT,
                system_prompt TEXT,
                parent_session_id TEXT,
                started_at REAL NOT NULL,
                ended_at REAL,
                end_reason TEXT,
                message_count INTEGER DEFAULT 0,
                tool_call_count INTEGER DEFAULT 0,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                reasoning_tokens INTEGER DEFAULT 0,
                billing_provider TEXT,
                billing_base_url TEXT,
                billing_mode TEXT,
                estimated_cost_usd REAL,
                actual_cost_usd REAL,
                cost_status TEXT,
                cost_source TEXT,
                pricing_version TEXT,
                title TEXT,
                api_call_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_call_id TEXT,
                tool_calls TEXT,
                tool_name TEXT,
                timestamp REAL NOT NULL,
                token_count INTEGER,
                finish_reason TEXT,
                reasoning TEXT,
                reasoning_content TEXT,
                reasoning_details TEXT,
                codex_reasoning_items TEXT,
                codex_message_items TEXT
            );

            CREATE TABLE IF NOT EXISTS state_meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_source ON sessions(source);
            CREATE INDEX IF NOT EXISTS idx_sessions_parent ON sessions(parent_session_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp, id);
            CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content);
            """
        )
        self._ensure_columns()
        self._conn.execute("INSERT INTO schema_version(version) SELECT 11 WHERE NOT EXISTS (SELECT 1 FROM schema_version)")
        self._conn.commit()

    def _ensure_columns(self) -> None:
        wanted = {
            "sessions": {
                "api_call_count": "INTEGER DEFAULT 0",
                "title": "TEXT",
                "pricing_version": "TEXT",
                "actual_cost_usd": "REAL",
                "estimated_cost_usd": "REAL",
                "billing_mode": "TEXT",
                "billing_base_url": "TEXT",
                "billing_provider": "TEXT",
                "reasoning_tokens": "INTEGER DEFAULT 0",
                "cache_write_tokens": "INTEGER DEFAULT 0",
                "cache_read_tokens": "INTEGER DEFAULT 0",
            },
            "messages": {
                "finish_reason": "TEXT",
                "reasoning": "TEXT",
                "reasoning_content": "TEXT",
                "reasoning_details": "TEXT",
                "codex_reasoning_items": "TEXT",
                "codex_message_items": "TEXT",
            },
        }
        for table, columns in wanted.items():
            existing = {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}
            for name, decl in columns.items():
                if name not in existing:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    @staticmethod
    def sanitize_title(title: str) -> str:
        cleaned = re.sub(r"\s+", " ", (title or "").strip())
        cleaned = cleaned.strip(" \t\r\n\"'")
        if not cleaned:
            raise ValueError("Title cannot be empty")
        return cleaned[:120]

    def create_session(
        self,
        session_id: str,
        source: str = "cli",
        user_id: str | None = None,
        model: str | None = None,
        model_config: Any = None,
        system_prompt: str | None = None,
        parent_session_id: str | None = None,
        **extra: Any,
    ) -> None:
        now = _as_epoch(extra.get("started_at"))
        self._conn.execute(
            """
            INSERT INTO sessions (
                id, source, user_id, model, model_config, system_prompt,
                parent_session_id, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source=COALESCE(excluded.source, sessions.source),
                user_id=COALESCE(excluded.user_id, sessions.user_id),
                model=COALESCE(excluded.model, sessions.model),
                model_config=COALESCE(excluded.model_config, sessions.model_config),
                system_prompt=COALESCE(excluded.system_prompt, sessions.system_prompt),
                parent_session_id=COALESCE(excluded.parent_session_id, sessions.parent_session_id)
            """,
            (
                session_id,
                str(source or "cli"),
                user_id,
                model,
                _json_dumps(model_config),
                system_prompt,
                parent_session_id,
                now,
            ),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def end_session(self, session_id: str, end_reason: str = "ended") -> None:
        self._conn.execute(
            "UPDATE sessions SET ended_at = ?, end_reason = ? WHERE id = ?",
            (time.time(), end_reason, session_id),
        )
        self._conn.commit()

    def reopen_session(self, session_id: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET ended_at = NULL, end_reason = NULL WHERE id = ?",
            (session_id,),
        )
        self._conn.commit()

    def update_system_prompt(self, session_id: str, system_prompt: str) -> None:
        self._conn.execute("UPDATE sessions SET system_prompt = ? WHERE id = ?", (system_prompt, session_id))
        self._conn.commit()

    def append_message(
        self,
        session_id: str,
        role: str,
        content: Any = None,
        tool_call_id: str | None = None,
        tool_calls: Any = None,
        tool_name: str | None = None,
        timestamp: Any = None,
        token_count: int | None = None,
        finish_reason: str | None = None,
        reasoning: Any = None,
        reasoning_content: Any = None,
        reasoning_details: Any = None,
        codex_reasoning_items: Any = None,
        codex_message_items: Any = None,
        **_: Any,
    ) -> int:
        if not self.get_session(session_id):
            self.create_session(session_id=session_id, source="cli")
        if isinstance(content, (dict, list)):
            stored_content = json.dumps(content, ensure_ascii=False)
        else:
            stored_content = "" if content is None else str(content)
        cur = self._conn.execute(
            """
            INSERT INTO messages (
                session_id, role, content, tool_call_id, tool_calls, tool_name,
                timestamp, token_count, finish_reason, reasoning,
                reasoning_content, reasoning_details, codex_reasoning_items,
                codex_message_items
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                stored_content,
                tool_call_id,
                _json_dumps(tool_calls),
                tool_name,
                _as_epoch(timestamp),
                token_count,
                finish_reason,
                _json_dumps(reasoning),
                _json_dumps(reasoning_content),
                _json_dumps(reasoning_details),
                _json_dumps(codex_reasoning_items),
                _json_dumps(codex_message_items),
            ),
        )
        tool_count = 1 if tool_name else 0
        if isinstance(tool_calls, list):
            tool_count += len(tool_calls)
        self._conn.execute(
            """
            UPDATE sessions
            SET message_count = (SELECT COUNT(*) FROM messages WHERE session_id = ?),
                tool_call_count = COALESCE(tool_call_count, 0) + ?
            WHERE id = ?
            """,
            (session_id, tool_count, session_id),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def replace_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn.commit()
        for msg in messages:
            self.append_message(
                session_id=session_id,
                role=msg.get("role", "unknown"),
                content=msg.get("content"),
                tool_call_id=msg.get("tool_call_id"),
                tool_calls=msg.get("tool_calls"),
                tool_name=msg.get("tool_name") or msg.get("name"),
                finish_reason=msg.get("finish_reason"),
                reasoning=msg.get("reasoning"),
                reasoning_content=msg.get("reasoning_content"),
                reasoning_details=msg.get("reasoning_details"),
                codex_reasoning_items=msg.get("codex_reasoning_items"),
                codex_message_items=msg.get("codex_message_items"),
            )

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp, id",
            (session_id,),
        ).fetchall()
        return [self._message_row_to_dict(row) for row in rows]

    def get_messages_as_conversation(
        self,
        session_id: str,
        include_timestamps: bool = True,
        **_: Any,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for row in self.get_messages(session_id):
            msg: dict[str, Any] = {
                "role": row["role"],
                "content": row.get("content") or "",
            }
            for key in (
                "tool_call_id",
                "tool_calls",
                "tool_name",
                "finish_reason",
                "reasoning",
                "reasoning_content",
                "reasoning_details",
                "codex_reasoning_items",
                "codex_message_items",
            ):
                if row.get(key) not in (None, ""):
                    msg[key] = row[key]
            if include_timestamps and row.get("timestamp") is not None:
                msg["timestamp"] = row["timestamp"]
            messages.append(msg)
        return messages

    def set_session_title(self, session_id: str, title: str) -> bool:
        title = self.sanitize_title(title)
        existing = self.get_session_by_title(title)
        if existing and existing.get("id") != session_id:
            raise ValueError(f"Title already exists: {title}")
        self._conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        self._conn.commit()
        return True

    def get_session_title(self, session_id: str) -> Optional[str]:
        row = self._conn.execute("SELECT title FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row["title"] if row and row["title"] else None

    def get_session_by_title(self, title: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE title = ? ORDER BY started_at DESC LIMIT 1",
            (title,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def resolve_session_by_title(self, name: str) -> Optional[str]:
        found = self.get_session_by_title(name)
        if found:
            return found["id"]
        row = self._conn.execute(
            "SELECT id FROM sessions WHERE id = ? OR title LIKE ? ORDER BY started_at DESC LIMIT 1",
            (name, f"%{name}%"),
        ).fetchone()
        return row["id"] if row else None

    def get_next_title_in_lineage(self, base_title: str) -> str:
        base = self.sanitize_title(re.sub(r"\s+#\d+$", "", base_title or "branch"))
        rows = self._conn.execute(
            "SELECT title FROM sessions WHERE title = ? OR title LIKE ?",
            (base, f"{base} #%"),
        ).fetchall()
        used = {row["title"] for row in rows if row["title"]}
        if base not in used:
            return base
        n = 2
        while f"{base} #{n}" in used:
            n += 1
        return f"{base} #{n}"

    def resolve_resume_session_id(self, session_id: str) -> str:
        current = session_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            count = self._conn.execute(
                "SELECT COUNT(*) AS c FROM messages WHERE session_id = ?",
                (current,),
            ).fetchone()["c"]
            if count:
                return current
            child = self._conn.execute(
                "SELECT id FROM sessions WHERE parent_session_id = ? ORDER BY started_at DESC LIMIT 1",
                (current,),
            ).fetchone()
            if not child:
                return current
            current = child["id"]
        return current or session_id

    def list_sessions_rich(
        self,
        source: str | None = None,
        exclude_sources: Iterable[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        include_children: bool = True,
        order_by_last_active: bool = False,
        **_: Any,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if source:
            where.append("s.source = ?")
            params.append(source)
        if exclude_sources:
            placeholders = ",".join("?" for _ in exclude_sources)
            where.append(f"s.source NOT IN ({placeholders})")
            params.extend(list(exclude_sources))
        if not include_children:
            where.append("s.parent_session_id IS NULL")
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        order_sql = "last_active DESC" if order_by_last_active else "s.started_at DESC"
        rows = self._conn.execute(
            f"""
            SELECT s.*,
                   COALESCE((SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id), s.started_at) AS last_active,
                   COALESCE((SELECT SUBSTR(m.content, 1, 240) FROM messages m
                             WHERE m.session_id = s.id AND m.role = 'user' AND m.content IS NOT NULL
                             ORDER BY m.timestamp, m.id LIMIT 1), '') AS preview
            FROM sessions s
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            (*params, int(limit), int(offset)),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def search_messages(
        self,
        query: str,
        source_filter: Iterable[str] | None = None,
        exclude_sources: Iterable[str] | None = None,
        role_filter: Iterable[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        **_: Any,
    ) -> list[dict[str, Any]]:
        terms = [t for t in re.findall(r"[\w.-]+", query or "") if t.upper() not in {"OR", "AND", "NOT"}]
        where: list[str] = []
        params: list[Any] = []
        for term in terms:
            where.append("(m.content LIKE ? OR m.tool_name LIKE ? OR m.tool_calls LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like, like])
        if source_filter:
            placeholders = ",".join("?" for _ in source_filter)
            where.append(f"s.source IN ({placeholders})")
            params.extend(list(source_filter))
        if exclude_sources:
            placeholders = ",".join("?" for _ in exclude_sources)
            where.append(f"s.source NOT IN ({placeholders})")
            params.extend(list(exclude_sources))
        if role_filter:
            placeholders = ",".join("?" for _ in role_filter)
            where.append(f"m.role IN ({placeholders})")
            params.extend(list(role_filter))
        where_sql = "WHERE " + " AND ".join(where) if where else ""
        rows = self._conn.execute(
            f"""
            SELECT m.*, s.source, s.model, s.started_at AS session_started, s.title
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            {where_sql}
            ORDER BY m.timestamp DESC, m.id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, int(limit), int(offset)),
        ).fetchall()
        results = []
        for row in rows:
            item = self._message_row_to_dict(row)
            content = item.get("content") or ""
            item.update(
                {
                    "source": row["source"],
                    "model": row["model"],
                    "session_started": row["session_started"],
                    "title": row["title"],
                    "snippet": content[:500],
                    "context": [],
                }
            )
            results.append(item)
        return results

    def get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: Any) -> None:
        self._conn.execute(
            """
            INSERT INTO state_meta(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, _json_dumps(value), time.time()),
        )
        self._conn.commit()

    def prune_empty_ghost_sessions(self, sessions_dir: Path | None = None) -> int:
        cur = self._conn.execute(
            """
            DELETE FROM sessions
            WHERE COALESCE(message_count, 0) = 0
              AND id NOT IN (SELECT DISTINCT session_id FROM messages)
              AND ended_at IS NOT NULL
            """
        )
        self._conn.commit()
        return int(cur.rowcount or 0)

    def maybe_auto_prune_and_vacuum(
        self,
        retention_days: int = 90,
        min_interval_hours: int = 24,
        vacuum: bool = True,
        sessions_dir: Path | None = None,
    ) -> int:
        key = "auto_prune_last_run"
        now = time.time()
        last = self.get_meta(key)
        try:
            if last and now - float(last) < min_interval_hours * 3600:
                return 0
        except ValueError:
            pass
        cutoff = now - max(1, int(retention_days)) * 86400
        ids = [
            row["id"]
            for row in self._conn.execute(
                "SELECT id FROM sessions WHERE ended_at IS NOT NULL AND ended_at < ?",
                (cutoff,),
            ).fetchall()
        ]
        for sid in ids:
            self.delete_session(sid)
        self.set_meta(key, str(now))
        if ids and vacuum:
            self._conn.execute("VACUUM")
        return len(ids)

    def delete_session(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()

    def clear_messages(self, session_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn.execute("UPDATE sessions SET message_count = 0, tool_call_count = 0 WHERE id = ?", (session_id,))
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for key in ("model_config",):
            data[key] = _json_loads_maybe(data.get(key))
        return data

    def _message_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for key in (
            "tool_calls",
            "reasoning",
            "reasoning_content",
            "reasoning_details",
            "codex_reasoning_items",
            "codex_message_items",
        ):
            data[key] = _json_loads_maybe(data.get(key))
        return data


def get_messages(session_id: str, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    return SessionDB(db_path=db_path).get_messages(session_id)

