# Sara Agent Wiki Memory Core

This subsystem implements Sara Agent memory with a strict authority boundary:

`Markdown Wiki = Source of Truth`
`Knowledge Graph = Relationship Layer`
`Vector/Search Index = Accelerator`

Derived SQLite tables, graph exports, and chunk indexes can always be rebuilt from Markdown.

## File Targets

- `memory/wiki_memory.py`: production API and storage engine.
- `${sara_HOME}/memories/wiki/<space>/`: default Obsidian-compatible memory vault. If `sara_HOME` is unset, this is `~/.sara/memories/wiki/<space>/`.
- `${sara_HOME}/memories/wiki/<space>/.memory/index.sqlite3`: derived SQLite index.
- `${sara_HOME}/memories/wiki/<space>/graph/graph.json`: derived graph export.
- `${sara_HOME}/memories/wiki/<space>/graph/schema.md`: graph schema documentation.

## Folder Structure

```text
~/.sara/memories/wiki/
├── personal/
├── sara-agent/
│   ├── episodes/
│   ├── wiki/
│   │   ├── Projects/
│   │   └── Sara-Agent-Identity.md
│   ├── daily/
│   ├── mocs/
│   ├── reflections/
│   ├── graph/
│   │   ├── graph.json
│   │   └── schema.md
│   ├── embeddings/
│   └── .memory/
│       └── index.sqlite3
├── riva/
├── tunify/
├── whisp-agentis/
└── eden-agent/
```

Each project is a separate memory space with its own wiki, graph, reflections, and derived indexes.

## Markdown Templates

Episode pages live in `episodes/YYYY-MM-DD-<id>.md`.

```markdown
---
id: abc123
space: sara-agent
type: episode
title: Episode 2026-06-15
created_at: 2026-06-15T00:00:00+00:00
updated_at: 2026-06-15T00:00:00+00:00
participants: [user, Sara]
tags: [episode, decision]
importance: 0.74
relations:
  - predicate: links_to
    target: Projects/Sara-Agent
source: markdown_wiki
authoritative: true
---

# Episode 2026-06-15

## Summary
The user decided Sara memory must use Markdown as source of truth.

## Observations
- Vector databases are search accelerators only.
```

Semantic pages live in `wiki/`, support `[[Internal Links]]`, and expose relationships in frontmatter plus body links.

Identity memory is initialized at `wiki/Sara-Agent-Identity.md` with mission, values, behavior, capabilities, and limitations.

Reflection pages live in `reflections/` and contain lessons learned, mistakes, patterns, goals, and insights.

## Database Schema

SQLite is derived storage:

- `memories`: canonical index rows pointing back to Markdown path, content, tags, timestamps, importance, and metadata.
- `memory_fts`: FTS5 wiki search over title, content, and tags.
- `graph_nodes`: derived nodes for pages and external linked concepts.
- `graph_edges`: derived edges from frontmatter relations and Obsidian links.
- `vector_chunks`: derived chunk accelerator metadata. This table is not authoritative.

## Knowledge Graph Schema

Node types:

- `identity`
- `episode`
- `semantic`
- `reflection`
- `external`

Edge predicates:

- `links_to`
- `belongs_to`
- `owns`
- `inspired_by`
- `related_to`
- `uses`

Graph data is exported to `graph/graph.json` for NetworkX, Neo4j, ArangoDB, or visualization ingestion.

## Retrieval Pipeline

`search_memory()` combines:

1. Wiki full-text search.
2. Graph relationship lookup.
3. Semantic/search accelerator lookup.
4. Recency score.
5. Importance score.

Every result returns provenance and reasons so Sara can explain why a memory was retrieved.

## Consolidation Pipeline

`consolidate_memory()` performs the sleep cycle:

1. Accept short-term events.
2. Write episodic Markdown.
3. Extract stable facts into semantic Markdown.
4. Rebuild SQLite search.
5. Rebuild graph relationships.
6. Generate a reflection page.

## API

```python
from memory.wiki_memory import WikiMemorySystem

memory = WikiMemorySystem()
memory.create_memory("User prefers concise implementation plans.", tags=["preference"])
memory.search_memory("implementation preferences")
memory.graph_query("Sara Agent")
memory.reflect()
memory.consolidate_memory(short_term_events=[{"summary": "Sara Agent uses Markdown memory."}])
```

Module-level helpers are also available:

- `create_memory()`
- `update_memory()`
- `delete_memory()`
- `search_memory()`
- `graph_query()`
- `wiki_query()`
- `semantic_search()`
- `reflect()`
- `consolidate_memory()`

## Git Integration

Use:

- `commit_memory(message)`
- `memory_diff()`
- `rollback_memory_state(git_ref)`

The intended audit trail is Git history over Markdown files. SQLite, graph exports, and vector chunks are rebuildable.

## Definition Of Done

The subsystem is done when Markdown writes succeed, derived indexes rebuild, graph relationships are inspectable, retrieval returns explainable provenance, reflections are persisted, and tests pass without any vector database being authoritative.
