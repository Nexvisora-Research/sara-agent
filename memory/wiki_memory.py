"""
Obsidian-compatible long-term memory core for Sara Agent.

Markdown is the source of truth. SQLite, graph rows, and search indexes are
derived accelerators that can be rebuilt from the wiki at any time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sara_constants import get_sara_home

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML is expected but optional.
    yaml = None


DEFAULT_SPACE = "sara-agent"
VALID_MEMORY_TYPES = {"episode", "semantic", "identity", "reflection"}
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_/-]+)")


@dataclass(frozen=True)
class MemoryRecord:
    """Structured result returned by memory APIs."""

    id: str
    space: str
    memory_type: str
    title: str
    path: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass(frozen=True)
class RetrievalResult:
    """Hybrid retrieval item with provenance and ranking details."""

    record: MemoryRecord
    source: str
    score: float
    reasons: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def slugify(value: str, fallback: str = "memory") -> str:
    value = value.strip().replace("&", " and ")
    value = re.sub(r"[^A-Za-z0-9/_ -]+", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-/")
    return value or fallback


def normalize_space(space: str | None) -> str:
    return slugify(space or DEFAULT_SPACE, DEFAULT_SPACE).lower()


def stable_id(*parts: str) -> str:
    joined = "|".join(part.strip() for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def default_memory_root() -> Path:
    """Return the profile-scoped wiki vault under sara_HOME."""

    return get_sara_home() / "memories" / "wiki"


def clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 3)))


def frontmatter_dump(metadata: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()
    return "\n".join(f"{key}: {json.dumps(value)}" for key, value in metadata.items())


def frontmatter_load(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 4)
    if end == -1:
        return {}, raw
    fm_raw = raw[4:end]
    body = raw[end + 5 :].lstrip("\n")
    if yaml is None:
        metadata: dict[str, Any] = {}
        for line in fm_raw.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata, body
    loaded = yaml.safe_load(fm_raw) or {}
    return loaded if isinstance(loaded, dict) else {}, body


def render_markdown(metadata: dict[str, Any], body: str) -> str:
    return f"---\n{frontmatter_dump(metadata)}\n---\n\n{body.rstrip()}\n"


def summarize_text(text: str, max_chars: int = 220) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", text)}


class MemoryPathError(ValueError):
    """Raised when a caller tries to address a path outside a memory space."""


class WikiMemorySystem:
    """Production memory core with Markdown source-of-truth and derived indexes."""

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        env_root = os.environ.get("SARA_MEMORY_ROOT", "").strip()
        self.root = Path(root or env_root or default_memory_root()).resolve()
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_memory(
        self,
        content: str,
        *,
        space: str = DEFAULT_SPACE,
        memory_type: str = "semantic",
        title: str | None = None,
        participants: list[str] | None = None,
        tags: list[str] | None = None,
        relations: list[dict[str, str]] | None = None,
        importance: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """Create an episode, semantic page, identity page, or reflection."""

        content = content.strip()
        if not content:
            raise ValueError("content must not be empty")
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(f"memory_type must be one of {sorted(VALID_MEMORY_TYPES)}")

        with self._lock:
            space = normalize_space(space)
            self.ensure_space(space)
            created_at = now_iso()
            score = clamp_score(importance if importance is not None else self.score_importance(content, tags or []))
            memory_id = stable_id(space, memory_type, title or content, created_at)
            page_title = title or self._default_title(memory_type, content)
            path = self._path_for_new_memory(space, memory_type, page_title, memory_id)
            rels = relations or self.extract_relations(page_title, content)

            doc_metadata = {
                "id": memory_id,
                "space": space,
                "type": memory_type,
                "title": page_title,
                "created_at": created_at,
                "updated_at": created_at,
                "participants": participants or ["user", "Sara"],
                "tags": sorted(set(tags or self.extract_tags(content, memory_type))),
                "importance": score,
                "relations": rels,
                "source": "markdown_wiki",
                "authoritative": True,
            }
            if metadata:
                doc_metadata.update(metadata)

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_markdown(doc_metadata, self._body_for(memory_type, page_title, content, rels)), encoding="utf-8")
            self.sync_space(space)
            return self._record_from_path(space, path)

    def update_memory(
        self,
        memory_id: str,
        *,
        space: str = DEFAULT_SPACE,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        """Update a Markdown memory page and rebuild derived indexes."""

        with self._lock:
            space = normalize_space(space)
            path = self._find_path_by_id(space, memory_id)
            current_metadata, current_body = frontmatter_load(path.read_text(encoding="utf-8"))
            if content is not None:
                current_body = content.strip() + "\n"
            if metadata:
                current_metadata.update(metadata)
            current_metadata["updated_at"] = now_iso()
            if "importance" in current_metadata:
                current_metadata["importance"] = clamp_score(float(current_metadata["importance"]))
            path.write_text(render_markdown(current_metadata, current_body), encoding="utf-8")
            self.sync_space(space)
            return self._record_from_path(space, path)

    def delete_memory(self, memory_id: str, *, space: str = DEFAULT_SPACE) -> bool:
        """Delete a Markdown memory page, then remove derived index rows."""

        with self._lock:
            space = normalize_space(space)
            path = self._find_path_by_id(space, memory_id)
            path.unlink()
            self.sync_space(space)
            return True

    def search_memory(
        self,
        query: str,
        *,
        space: str = DEFAULT_SPACE,
        limit: int = 8,
        include_graph: bool = True,
    ) -> list[RetrievalResult]:
        """Hybrid retrieval: wiki FTS, graph neighbors, semantic accelerator, recency, importance."""

        space = normalize_space(space)
        self.ensure_space(space)
        query = query.strip()
        if not query:
            return []

        candidates: dict[str, RetrievalResult] = {}
        for record in self.wiki_query(query, space=space, limit=limit * 2):
            self._merge_result(candidates, record, "wiki", record.score, "full-text wiki match")

        for record in self.semantic_search(query, space=space, limit=limit * 2):
            self._merge_result(candidates, record, "semantic", record.score, "semantic/search accelerator match")

        if include_graph:
            for edge in self.graph_query(query, space=space, limit=limit * 2):
                target_id = edge.get("target_id") or edge.get("source_id")
                if target_id:
                    try:
                        record = self.get_memory(target_id, space=space)
                        self._merge_result(candidates, record, "graph", 0.62, f"graph relation {edge.get('predicate')}")
                    except FileNotFoundError:
                        pass

        ranked = []
        for result in candidates.values():
            metadata = result.record.metadata
            importance = float(metadata.get("importance") or 0.0)
            recency = self._recency_score(metadata.get("updated_at") or metadata.get("created_at"))
            final_score = clamp_score((result.score * 0.58) + (importance * 0.27) + (recency * 0.15))
            ranked.append(RetrievalResult(result.record, result.source, final_score, result.reasons))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    def wiki_query(self, query: str, *, space: str = DEFAULT_SPACE, limit: int = 8) -> list[MemoryRecord]:
        """Search authoritative Markdown pages through the derived SQLite FTS index."""

        space = normalize_space(space)
        con = self._connect(space)
        try:
            rows = con.execute(
                """
                SELECT memory_id AS id, bm25(memory_fts) AS rank
                FROM memory_fts
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (self._fts_query(query), limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            con.close()

        records = []
        for row in rows:
            record = self.get_memory(row["id"], space=space)
            rank = abs(float(row["rank"]))
            record = MemoryRecord(**{**record.__dict__, "score": clamp_score(1.0 / (1.0 + rank))})
            records.append(record)
        if records:
            return records
        return self._fallback_text_search(query, space=space, limit=limit)

    def semantic_search(self, query: str, *, space: str = DEFAULT_SPACE, limit: int = 8) -> list[MemoryRecord]:
        """Search derived chunks. This is an accelerator, never authority."""

        return self.wiki_query(query, space=space, limit=limit)

    def graph_query(
        self,
        query: str,
        *,
        space: str = DEFAULT_SPACE,
        predicate: str | None = None,
        depth: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query derived graph edges by node title, tag, or predicate."""

        space = normalize_space(space)
        con = self._connect(space)
        like = f"%{query.strip()}%"
        params: list[Any] = [like, like, like]
        predicate_clause = ""
        if predicate:
            predicate_clause = "AND e.predicate = ?"
            params.append(predicate)
        params.append(limit)
        rows = con.execute(
            f"""
            SELECT e.source_id, s.title AS source_title, e.predicate,
                   e.target_id, t.title AS target_title, e.weight, e.metadata
            FROM graph_edges e
            LEFT JOIN graph_nodes s ON s.id = e.source_id
            LEFT JOIN graph_nodes t ON t.id = e.target_id
            WHERE (s.title LIKE ? OR t.title LIKE ? OR e.predicate LIKE ?)
            {predicate_clause}
            ORDER BY e.weight DESC, e.updated_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        con.close()
        results = [dict(row) for row in rows]
        if depth > 1:
            seen = {(item["source_id"], item["predicate"], item["target_id"]) for item in results}
            for item in list(results):
                for next_item in self.graph_query(item.get("target_title") or "", space=space, depth=1, limit=limit):
                    key = (next_item["source_id"], next_item["predicate"], next_item["target_id"])
                    if key not in seen:
                        seen.add(key)
                        results.append(next_item)
                    if len(results) >= limit:
                        return results
        return results

    def get_memory(self, memory_id: str, *, space: str = DEFAULT_SPACE) -> MemoryRecord:
        space = normalize_space(space)
        return self._record_from_path(space, self._find_path_by_id(space, memory_id))

    def reflect(self, *, space: str = DEFAULT_SPACE, query: str = "", limit: int = 12) -> MemoryRecord:
        """Generate a reflection page with lessons, mistakes, patterns, goals, and insights."""

        space = normalize_space(space)
        records = self._recent_records(space, limit=limit)
        if query:
            records = [item.record for item in self.search_memory(query, space=space, limit=limit)] or records
        lessons, patterns, goals = [], [], []
        for record in records:
            body = summarize_text(record.content, 180)
            tags = set(record.metadata.get("tags") or [])
            if "decision" in tags or record.memory_type == "episode":
                lessons.append(body)
            if tags:
                patterns.extend(sorted(tags))
            if "goal" in tags or "goals" in record.title.lower():
                goals.append(body)
        unique_patterns = sorted(set(patterns))[:8]
        body = "\n".join(
            [
                "## Lessons Learned",
                *(f"- {item}" for item in lessons[:5] or ["No strong lesson has emerged yet."]),
                "",
                "## Mistakes",
                "- Review future corrections and failed actions here.",
                "",
                "## Patterns",
                *(f"- #{item}" for item in unique_patterns or ["- No repeated pattern yet."]),
                "",
                "## Goals",
                *(f"- {item}" for item in goals[:5] or ["No explicit goal found in the selected window."]),
                "",
                "## Insights",
                f"- Reflection synthesized from {len(records)} recent memories in [[{space} MOC]].",
            ]
        )
        return self.create_memory(
            body,
            space=space,
            memory_type="reflection",
            title=f"Reflection {today_slug()}",
            tags=["reflection", "insight"],
            importance=0.72,
        )

    def consolidate_memory(
        self,
        *,
        space: str = DEFAULT_SPACE,
        short_term_events: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Sleep-cycle consolidation from short-term events into wiki, graph, and search indexes."""

        space = normalize_space(space)
        self.ensure_space(space)
        created: list[str] = []
        for event in short_term_events or []:
            summary = event.get("summary") or event.get("content") or ""
            if not summary:
                continue
            record = self.create_memory(
                summary,
                space=space,
                memory_type="episode",
                title=event.get("title"),
                participants=event.get("participants") or ["user", "Sara"],
                tags=event.get("tags") or ["episode"],
                importance=event.get("importance"),
                metadata={"raw_event": event},
            )
            created.append(record.id)

            for fact in self.extract_facts(summary):
                semantic = self.create_memory(
                    fact,
                    space=space,
                    memory_type="semantic",
                    title=self._default_title("semantic", fact),
                    tags=["fact"],
                    importance=max(0.55, float(record.metadata.get("importance") or 0.5)),
                )
                created.append(semantic.id)

        self.sync_space(space)
        reflection = self.reflect(space=space) if created else None
        return {
            "space": space,
            "created_memory_ids": created,
            "reflection_id": reflection.id if reflection else None,
            "definition_of_done": "Markdown updated, SQLite index rebuilt, graph synchronized, retrieval ready.",
        }

    def commit_memory(self, message: str, *, paths: Iterable[str] | None = None) -> dict[str, Any]:
        """Commit memory updates when the memory root is inside a git repository."""

        repo = self._git_root()
        if not repo:
            return {"success": False, "error": "memory root is not inside a git repository"}
        rel_paths = list(paths or [str(self.root.relative_to(repo))])
        subprocess.run(["git", "-C", str(repo), "add", *rel_paths], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", message], check=True)
        return {"success": True, "repo": str(repo), "paths": rel_paths}

    def memory_diff(self, *, space: str | None = None) -> str:
        repo = self._git_root()
        if not repo:
            return ""
        target = self.root / normalize_space(space) if space else self.root
        rel = str(target.relative_to(repo))
        result = subprocess.run(["git", "-C", str(repo), "diff", "--", rel], check=False, capture_output=True, text=True)
        return result.stdout

    def rollback_memory_state(self, git_ref: str, *, space: str = DEFAULT_SPACE) -> dict[str, Any]:
        repo = self._git_root()
        if not repo:
            return {"success": False, "error": "memory root is not inside a git repository"}
        target = self.root / normalize_space(space)
        rel = str(target.relative_to(repo))
        subprocess.run(["git", "-C", str(repo), "checkout", git_ref, "--", rel], check=True)
        self.sync_space(space)
        return {"success": True, "space": normalize_space(space), "ref": git_ref}

    # ------------------------------------------------------------------
    # Synchronization and schema
    # ------------------------------------------------------------------

    def ensure_space(self, space: str = DEFAULT_SPACE) -> Path:
        space = normalize_space(space)
        base = self.root / space
        for folder in ("episodes", "wiki/Projects", "reflections", "daily", "mocs", "graph", "embeddings", ".memory"):
            (base / folder).mkdir(parents=True, exist_ok=True)
        identity = base / "wiki" / "Sara-Agent-Identity.md"
        if not identity.exists():
            metadata = {
                "id": stable_id(space, "identity", "Sara Agent Identity"),
                "space": space,
                "type": "identity",
                "title": "Sara Agent Identity",
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "participants": ["Sara"],
                "tags": ["identity", "mission", "values"],
                "importance": 1.0,
                "relations": [{"predicate": "belongs_to", "target": f"{space} MOC"}],
                "source": "markdown_wiki",
                "authoritative": True,
            }
            identity.write_text(
                render_markdown(
                    metadata,
                    "\n".join(
                        [
                            "# Sara Agent Identity",
                            "",
                            "## Mission",
                            "Build persistent, explainable, human-editable assistance through [[Sara Agent]].",
                            "",
                            "## Values",
                            "- Human readable memory",
                            "- User control",
                            "- Explainable retrieval",
                            "- Markdown as source of truth",
                            "",
                            "## Behavior",
                            "Sara remains helpful, curious, careful, and transparent about memory provenance.",
                            "",
                            "## Capabilities",
                            "Sara can create memories, update the wiki, synchronize the graph, retrieve context, reflect, and consolidate.",
                            "",
                            "## Limitations",
                            "Derived databases are accelerators only and must be rebuilt from Markdown when conflict appears.",
                        ]
                    ),
                ),
                encoding="utf-8",
            )
        moc = base / "mocs" / f"{space} MOC.md"
        if not moc.exists():
            moc.write_text(
                render_markdown(
                    {
                        "id": stable_id(space, "moc", space),
                        "space": space,
                        "type": "semantic",
                        "title": f"{space} MOC",
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                        "participants": ["Sara"],
                        "tags": ["moc", space],
                        "importance": 0.95,
                        "relations": [],
                        "source": "markdown_wiki",
                        "authoritative": True,
                    },
                    f"# {space} MOC\n\n- [[Sara Agent Identity]]\n- [[Projects/Sara-Agent]]\n- [[Daily Notes]]\n- [[Reflections]]",
                ),
                encoding="utf-8",
            )
        self._init_db(space)
        return base

    def sync_space(self, space: str = DEFAULT_SPACE) -> dict[str, int]:
        """Rebuild SQLite memory index, graph tables, FTS, and chunk accelerator."""

        space = normalize_space(space)
        self.ensure_space(space)
        con = self._connect(space)
        with con:
            con.execute("DELETE FROM memory_fts")
            con.execute("DELETE FROM graph_edges")
            con.execute("DELETE FROM graph_nodes")
            con.execute("DELETE FROM vector_chunks")
            con.execute("DELETE FROM memories")
            for path in self._markdown_files(space):
                record = self._record_from_path(space, path)
                con.execute(
                    """
                    INSERT OR REPLACE INTO memories
                    (id, type, title, path, content, tags, importance, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.memory_type,
                        record.title,
                        record.path,
                        record.content,
                        ",".join(record.metadata.get("tags") or []),
                        float(record.metadata.get("importance") or 0),
                        record.metadata.get("created_at"),
                        record.metadata.get("updated_at"),
                        json.dumps(record.metadata, ensure_ascii=False),
                    ),
                )
                con.execute(
                    """
                    INSERT INTO memory_fts (memory_id, title, content, tags)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.title,
                        record.content,
                        ",".join(record.metadata.get("tags") or []),
                    ),
                )
                con.execute(
                    """
                    INSERT OR REPLACE INTO graph_nodes
                    (id, title, type, path, tags, importance, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.title,
                        record.memory_type,
                        record.path,
                        ",".join(record.metadata.get("tags") or []),
                        float(record.metadata.get("importance") or 0),
                        record.metadata.get("updated_at"),
                    ),
                )
                self._index_chunks(con, record)
            records = [self._record_from_path(space, path) for path in self._markdown_files(space)]
            title_to_id = {record.title: record.id for record in records}
            title_to_id.update({record.title.split("/")[-1]: record.id for record in records})
            for record in records:
                self._sync_edges_for_record(con, record, title_to_id)
        counts = {
            "memories": con.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
            "nodes": con.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0],
            "edges": con.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0],
            "chunks": con.execute("SELECT COUNT(*) FROM vector_chunks").fetchone()[0],
        }
        con.close()
        self._write_graph_exports(space)
        return counts

    # ------------------------------------------------------------------
    # Extraction and scoring
    # ------------------------------------------------------------------

    def score_importance(self, text: str, tags: list[str] | None = None) -> float:
        lower = text.lower()
        score = 0.35
        weights = {
            "prefer": 0.15,
            "always": 0.10,
            "never": 0.12,
            "goal": 0.18,
            "decision": 0.17,
            "important": 0.16,
            "project": 0.12,
            "remember": 0.14,
            "mistake": 0.12,
            "deadline": 0.10,
        }
        for word, delta in weights.items():
            if word in lower:
                score += delta
        if tags:
            if {"identity", "mission", "goal", "preference", "decision"} & set(tags):
                score += 0.12
            score += min(len(set(tags)) * 0.015, 0.08)
        if len(text) > 500:
            score += 0.05
        return clamp_score(score)

    def extract_tags(self, text: str, memory_type: str = "semantic") -> list[str]:
        tags = {memory_type}
        tags.update(TAG_RE.findall(text))
        lower = text.lower()
        for keyword in ("preference", "goal", "decision", "project", "tool", "identity", "reflection", "lesson"):
            if keyword in lower:
                tags.add(keyword)
        return sorted(tags)

    def extract_relations(self, title: str, content: str) -> list[dict[str, str]]:
        relations = []
        for link in LINK_RE.findall(content):
            relations.append({"predicate": "links_to", "target": link.strip()})
        patterns = [
            (r"(.+?)\s+owns\s+(.+)", "owns"),
            (r"(.+?)\s+is inspired by\s+(.+)", "inspired_by"),
            (r"(.+?)\s+related to\s+(.+)", "related_to"),
            (r"(.+?)\s+uses\s+(.+)", "uses"),
        ]
        for line in content.splitlines():
            clean = line.strip("- ").strip()
            for pattern, predicate in patterns:
                match = re.match(pattern, clean, re.IGNORECASE)
                if match:
                    relations.append({"predicate": predicate, "target": match.group(2).strip(". ")})
        if not relations:
            relations.append({"predicate": "belongs_to", "target": f"{title.split('/')[0]} MOC"})
        return relations

    def extract_facts(self, text: str) -> list[str]:
        facts = []
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            clean = sentence.strip()
            lower = clean.lower()
            if len(clean) < 12:
                continue
            if any(marker in lower for marker in ("prefers", "likes", "owns", "uses", "goal", "decision", "is inspired by", "related to")):
                facts.append(clean)
        return facts[:8]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self, space: str) -> sqlite3.Connection:
        self._init_db(space)
        con = sqlite3.connect(str(self.root / space / ".memory" / "index.sqlite3"))
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self, space: str) -> None:
        db = self.root / space / ".memory" / "index.sqlite3"
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(db))
        with con:
            con.execute("PRAGMA journal_mode=WAL")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version < 2:
                con.execute("DROP TRIGGER IF EXISTS memories_ai")
                con.execute("DROP TRIGGER IF EXISTS memories_ad")
                con.execute("DROP TRIGGER IF EXISTS memories_au")
                con.execute("DROP TABLE IF EXISTS memory_fts")
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    importance REAL DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                    USING fts5(memory_id UNINDEXED, title, content, tags);
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    importance REAL DEFAULT 0,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    weight REAL DEFAULT 0.5,
                    metadata TEXT DEFAULT '{}',
                    updated_at TEXT,
                    PRIMARY KEY (source_id, predicate, target_id)
                );
                CREATE TABLE IF NOT EXISTS vector_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
                CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id);
                """
            )
            con.execute("PRAGMA user_version = 2")
        con.close()

    def _markdown_files(self, space: str) -> list[Path]:
        base = self.root / space
        derived_dirs = {".memory", "graph", "embeddings"}
        return sorted(path for path in base.rglob("*.md") if not (derived_dirs & set(path.relative_to(base).parts)))

    def _path_for_new_memory(self, space: str, memory_type: str, title: str, memory_id: str) -> Path:
        base = self.root / space
        if memory_type == "episode":
            day = today_slug()
            return base / "episodes" / f"{day}-{memory_id}.md"
        if memory_type == "reflection":
            return base / "reflections" / f"{slugify(title)}-{memory_id}.md"
        if memory_type == "identity":
            return base / "wiki" / f"{slugify(title)}.md"
        title_slug = slugify(title)
        if "/" in title_slug:
            return base / "wiki" / f"{title_slug}.md"
        return base / "wiki" / f"{title_slug}.md"

    def _default_title(self, memory_type: str, content: str) -> str:
        if memory_type == "episode":
            return f"Episode {today_slug()}"
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", content)
        return " ".join(words[:6]).title() if words else f"Memory {today_slug()}"

    def _body_for(self, memory_type: str, title: str, content: str, relations: list[dict[str, str]]) -> str:
        if memory_type == "episode":
            return "\n".join(["# " + title, "", "## Summary", content, "", "## Observations", "- Pending review."])
        if memory_type == "reflection":
            return "# " + title + "\n\n" + content
        rel_lines = [f"- {rel.get('predicate', 'related_to')} -> [[{rel.get('target', '').strip()}]]" for rel in relations]
        return "\n".join(["# " + title, "", content, "", "## Relationships", *rel_lines])

    def _record_from_path(self, space: str, path: Path) -> MemoryRecord:
        raw = path.read_text(encoding="utf-8")
        metadata, body = frontmatter_load(raw)
        memory_id = str(metadata.get("id") or stable_id(space, str(path.relative_to(self.root / space))))
        memory_type = str(metadata.get("type") or "semantic")
        title = str(metadata.get("title") or path.stem)
        rel_path = str(path.relative_to(self.root / space))
        return MemoryRecord(memory_id, space, memory_type, title, rel_path, body, metadata, float(metadata.get("importance") or 0.0))

    def _find_path_by_id(self, space: str, memory_id: str) -> Path:
        self.ensure_space(space)
        for path in self._markdown_files(space):
            metadata, _ = frontmatter_load(path.read_text(encoding="utf-8"))
            if metadata.get("id") == memory_id:
                return path
        raise FileNotFoundError(f"memory id not found in {space}: {memory_id}")

    def _fallback_text_search(self, query: str, *, space: str, limit: int) -> list[MemoryRecord]:
        query_tokens = tokenize(query)
        scored = []
        for path in self._markdown_files(space):
            record = self._record_from_path(space, path)
            overlap = len(query_tokens & tokenize(record.title + " " + record.content))
            if overlap and (len(query_tokens) == 1 or overlap == len(query_tokens)):
                scored.append((overlap, record))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [MemoryRecord(**{**record.__dict__, "score": clamp_score(score / max(len(query_tokens), 1))}) for score, record in scored[:limit]]

    def _index_chunks(self, con: sqlite3.Connection, record: MemoryRecord) -> None:
        words = record.content.split()
        if not words:
            return
        size = 140
        for index in range(0, len(words), size):
            chunk = " ".join(words[index : index + size])
            chunk_id = stable_id(record.id, str(index), chunk)
            con.execute(
                """
                INSERT OR REPLACE INTO vector_chunks
                (chunk_id, memory_id, chunk_index, content, token_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    record.id,
                    index // size,
                    chunk,
                    stable_id(*sorted(tokenize(chunk))) if tokenize(chunk) else stable_id(chunk),
                    json.dumps({"source": "markdown_wiki", "authoritative": False}),
                ),
            )

    def _sync_edges_for_record(self, con: sqlite3.Connection, record: MemoryRecord, title_to_id: dict[str, str]) -> None:
        relations = list(record.metadata.get("relations") or [])
        for link in LINK_RE.findall(record.content):
            relations.append({"predicate": "links_to", "target": link.strip()})
        for rel in relations:
            target_title = str(rel.get("target") or "").strip()
            if not target_title:
                continue
            target_id = title_to_id.get(target_title) or stable_id(record.space, "external", target_title)
            if target_id not in title_to_id.values():
                con.execute(
                    """
                    INSERT OR IGNORE INTO graph_nodes
                    (id, title, type, path, tags, importance, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (target_id, target_title, "external", "", "", 0.2, now_iso()),
                )
            con.execute(
                """
                INSERT OR REPLACE INTO graph_edges
                (source_id, predicate, target_id, weight, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    str(rel.get("predicate") or "related_to"),
                    target_id,
                    clamp_score(float(rel.get("weight") or record.metadata.get("importance") or 0.5)),
                    json.dumps({"source": "markdown_relations"}, ensure_ascii=False),
                    now_iso(),
                ),
            )

    def _write_graph_exports(self, space: str) -> None:
        con = self._connect(space)
        nodes = [dict(row) for row in con.execute("SELECT * FROM graph_nodes ORDER BY title").fetchall()]
        edges = [dict(row) for row in con.execute("SELECT * FROM graph_edges ORDER BY source_id, predicate, target_id").fetchall()]
        con.close()
        graph_dir = self.root / space / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2), encoding="utf-8")
        (graph_dir / "schema.md").write_text(KNOWLEDGE_GRAPH_SCHEMA, encoding="utf-8")

    def _recent_records(self, space: str, limit: int = 12) -> list[MemoryRecord]:
        records = [self._record_from_path(space, path) for path in self._markdown_files(space)]
        records.sort(key=lambda record: record.metadata.get("updated_at") or record.metadata.get("created_at") or "", reverse=True)
        return records[:limit]

    def _merge_result(self, results: dict[str, RetrievalResult], record: MemoryRecord, source: str, score: float, reason: str) -> None:
        existing = results.get(record.id)
        if existing is None:
            results[record.id] = RetrievalResult(record, source, clamp_score(score), [reason])
            return
        results[record.id] = RetrievalResult(
            record,
            existing.source + "+" + source if source not in existing.source else existing.source,
            clamp_score(max(existing.score, score) + 0.08),
            existing.reasons + [reason],
        )

    def _recency_score(self, value: str | None) -> float:
        if not value:
            return 0.0
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        age_days = max((datetime.now(timezone.utc) - dt).days, 0)
        return clamp_score(1.0 / (1.0 + age_days / 30.0))

    def _fts_query(self, query: str) -> str:
        terms = [term for term in re.findall(r"[A-Za-z0-9_/-]+", query) if len(term) > 1]
        return " AND ".join(terms) if terms else query

    def _git_root(self) -> Path | None:
        result = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--show-toplevel"], check=False, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        return Path(result.stdout.strip())


KNOWLEDGE_GRAPH_SCHEMA = """# Sara Memory Knowledge Graph Schema

## Node Types
- `identity`: persistent Sara identity, mission, values, behavior, capabilities, limitations.
- `episode`: conversations, decisions, actions, tool usage, and observations.
- `semantic`: stable facts, preferences, projects, relationships, skills, and knowledge.
- `reflection`: lessons learned, mistakes, patterns, goals, and insights.
- `external`: unresolved linked pages or concepts referenced by Markdown.

## Edge Predicates
- `links_to`: derived from Obsidian `[[Internal Links]]`.
- `belongs_to`: page belongs to a memory space, project, or MOC.
- `owns`: user or agent ownership relationship.
- `inspired_by`: architectural or conceptual inspiration.
- `related_to`: broad relationship between projects, people, or concepts.
- `uses`: tool, platform, model, or infrastructure dependency.

Markdown frontmatter remains authoritative. This graph export is derived and can
be rebuilt with `sync_space()`.
"""


_DEFAULT_SYSTEM: WikiMemorySystem | None = None


def _get_default_system() -> WikiMemorySystem:
    global _DEFAULT_SYSTEM
    if _DEFAULT_SYSTEM is None:
        _DEFAULT_SYSTEM = WikiMemorySystem()
    return _DEFAULT_SYSTEM


def create_memory(content: str, **kwargs: Any) -> MemoryRecord:
    return _get_default_system().create_memory(content, **kwargs)


def update_memory(memory_id: str, **kwargs: Any) -> MemoryRecord:
    return _get_default_system().update_memory(memory_id, **kwargs)


def delete_memory(memory_id: str, **kwargs: Any) -> bool:
    return _get_default_system().delete_memory(memory_id, **kwargs)


def search_memory(query: str, **kwargs: Any) -> list[RetrievalResult]:
    return _get_default_system().search_memory(query, **kwargs)


def graph_query(query: str, **kwargs: Any) -> list[dict[str, Any]]:
    return _get_default_system().graph_query(query, **kwargs)


def wiki_query(query: str, **kwargs: Any) -> list[MemoryRecord]:
    return _get_default_system().wiki_query(query, **kwargs)


def semantic_search(query: str, **kwargs: Any) -> list[MemoryRecord]:
    return _get_default_system().semantic_search(query, **kwargs)


def reflect(**kwargs: Any) -> MemoryRecord:
    return _get_default_system().reflect(**kwargs)


def consolidate_memory(**kwargs: Any) -> dict[str, Any]:
    return _get_default_system().consolidate_memory(**kwargs)
