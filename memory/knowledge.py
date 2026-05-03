"""
memory/knowledge.py — Vector Knowledge System using ChromaDB + LangChain.

Provides long-term semantic memory for Sara AI.
Documents/facts are embedded and stored locally in memory/data/chroma/.
Similarity search runs fully offline after the first install.

First install:
    pip install chromadb sentence-transformers langchain-community

Tools exposed:
  knowledge_add(text)        — Embed and store a chunk of text
  knowledge_search(query)    — Semantic search, returns top 3 results
"""

import hashlib
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma")
COLLECTION_NAME = "sara_knowledge"

# Lazy globals
_client = None
_collection = None
_embedder = None


def _check_deps():
    """Return error string if deps missing, else None."""
    missing = []
    try:
        import chromadb  # noqa
    except ImportError:
        missing.append("chromadb")
    try:
        from sentence_transformers import SentenceTransformer  # noqa
    except ImportError:
        missing.append("sentence-transformers")
    if missing:
        return (
            f"❌ Missing: {', '.join(missing)}\n"
            f"Run: `pip install {' '.join(missing)}`"
        )
    return None


def _get_collection():
    """Return (and cache) the ChromaDB collection."""
    global _client, _collection
    if _collection is None:
        import chromadb
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _get_embedder():
    """Return (and cache) the SentenceTransformer model."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model (first time may be slow)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks if chunks else [text]


def _build_where(user_id: str = "", memory_type: str = "") -> dict | None:
    where = {}
    if user_id:
        where["user_id"] = user_id
    if memory_type:
        where["memory_type"] = memory_type
    return where or None


def search_knowledge_records(query: str, *, user_id: str = "", memory_type: str = "", limit: int = 3) -> list[dict]:
    """Internal structured semantic search used by layered memory retrieval."""
    query = query.strip()
    if not query:
        return []

    err = _check_deps()
    if err:
        return []

    try:
        collection = _get_collection()
        if collection.count() == 0:
            return []

        embedder = _get_embedder()
        query_embedding = embedder.encode(query).tolist()
        where = _build_where(user_id=user_id, memory_type=memory_type)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(limit, 1), collection.count()),
            where=where,
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        items = []
        for doc, dist, metadata in zip(docs, distances, metadatas):
            items.append(
                {
                    "document": doc,
                    "distance": dist,
                    "relevance": round((1 - dist) * 100),
                    "metadata": metadata or {},
                }
            )
        return items
    except Exception as e:
        logger.error(f"search_knowledge_records error: {e}")
        return []


def knowledge_add(
    text: str,
    user_id: str = "",
    *,
    memory_type: str = "general",
    source: str = "tool",
) -> str:
    """Embed and store text in the knowledge base."""
    text = text.strip()
    if not text:
        return "❓ Please provide text to add to the knowledge base."

    err = _check_deps()
    if err:
        return err

    try:
        collection = _get_collection()
        embedder = _get_embedder()

        chunks = _chunk_text(text)
        ids, embeddings, docs, metadatas = [], [], [], []
        timestamp = datetime.now(timezone.utc).isoformat()

        for chunk in chunks:
            doc_id = hashlib.md5(f"{user_id}|{memory_type}|{chunk}".encode()).hexdigest()
            embedding = embedder.encode(chunk).tolist()
            ids.append(doc_id)
            embeddings.append(embedding)
            docs.append(chunk)
            metadatas.append(
                {
                    "user_id": user_id or "global",
                    "memory_type": memory_type,
                    "source": source,
                    "timestamp": timestamp,
                }
            )

        # Upsert (avoid duplicates)
        collection.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)

        return (
            f"🧠 Added to knowledge base! ({len(chunks)} chunk{'s' if len(chunks) > 1 else ''})\n"
            f"_Preview: \"{text[:100]}{'...' if len(text) > 100 else ''}\"_"
        )
    except Exception as e:
        logger.error(f"knowledge_add error: {e}")
        return f"❌ Failed to store knowledge: {e}"


def knowledge_search(query: str, user_id: str = "", *, memory_type: str = "") -> str:
    """Search the knowledge base semantically and return the top 3 results."""
    query = query.strip()
    if not query:
        return "❓ Please provide a search query."

    items = search_knowledge_records(query, user_id=user_id, memory_type=memory_type, limit=3)
    if not items:
        err = _check_deps()
        if err:
            return err
        return "🔍 No relevant knowledge found for that query."

    lines = []
    for i, item in enumerate(items, 1):
        preview = item["document"][:300] + ("..." if len(item["document"]) > 300 else "")
        meta = item.get("metadata", {})
        scope = []
        if meta.get("memory_type"):
            scope.append(meta["memory_type"])
        if meta.get("source"):
            scope.append(meta["source"])
        scope_text = f" ({', '.join(scope)})" if scope else ""
        lines.append(f"**{i}. [{item['relevance']}% match]**{scope_text}\n{preview}")

    return f"🧠 **Knowledge Search: _{query}_**\n\n" + "\n\n---\n\n".join(lines)


def knowledge_count(unused: str = "") -> str:
    """Return the number of stored knowledge chunks."""
    err = _check_deps()
    if err:
        return err
    try:
        col = _get_collection()
        count = col.count()
        return f"🧠 Knowledge base contains **{count}** chunk{'s' if count != 1 else ''}."
    except Exception as e:
        return f"❌ {e}"
