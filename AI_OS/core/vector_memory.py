"""
Neural network memory for YALI — sentence-transformers + ChromaDB.

Architecture:
  Encoder  → all-MiniLM-L6-v2 (384-dim, CPU, ~80MB, free forever)
  Store    → ChromaDB local (memory/chroma_db/)
  Recall   → cosine similarity search → top-K semantically relevant memories

Replaces keyword-only JSON recall with true semantic understanding:
  "What did we discuss about IT stocks last week?" → finds INFY/TCS conversations
  "Remind me about that prediction" → finds the actual prediction entry
"""

import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("yali")

_CHROMA_DIR = str(Path(__file__).parent.parent / "memory" / "chroma_db")
_COLLECTION  = "yali_memory"
_MODEL_NAME  = "all-MiniLM-L6-v2"   # 384-dim, 80MB, runs on CPU

_client     = None
_collection = None
_encoder    = None


# ── lazy init ─────────────────────────────────────────────────────────────────

def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer model…")
            _encoder = SentenceTransformer(_MODEL_NAME)
            logger.info("Encoder ready.")
        except Exception as e:
            logger.error(f"Encoder load failed: {e}")
    return _encoder


def _get_collection():
    global _client, _collection
    if _collection is None:
        try:
            import chromadb
            os.makedirs(_CHROMA_DIR, exist_ok=True)
            _client = chromadb.PersistentClient(path=_CHROMA_DIR)
            _collection = _client.get_or_create_collection(
                name=_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB ready — {_collection.count()} memories stored.")
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
    return _collection


def is_available() -> bool:
    return _get_encoder() is not None and _get_collection() is not None


# ── core ops ──────────────────────────────────────────────────────────────────

def store(query: str, response: str, agent: str = ""):
    """
    Embed query+response and store in ChromaDB.
    Called on every interaction — runs in background so it doesn't block.
    """
    enc = _get_encoder()
    col = _get_collection()
    if enc is None or col is None:
        return

    try:
        ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
        doc  = f"Q: {query}\nA: {response[:600]}"
        vec  = enc.encode(doc).tolist()
        uid  = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        col.add(
            ids=[uid],
            embeddings=[vec],
            documents=[doc],
            metadatas=[{
                "ts":       ts,
                "agent":    agent,
                "query":    query[:200],
                "response": response[:400],
            }],
        )
    except Exception as e:
        logger.warning(f"vector_memory.store failed: {e}")


def search(query: str, n: int = 5) -> list[dict]:
    """
    Semantic search — returns top-N relevant memories.
    Each result: {query, response, ts, agent, distance}
    """
    enc = _get_encoder()
    col = _get_collection()
    if enc is None or col is None:
        return []

    try:
        vec = enc.encode(query).tolist()
        results = col.query(
            query_embeddings=[vec],
            n_results=min(n, max(col.count(), 1)),
            include=["metadatas", "distances"],
        )
        out = []
        for meta, dist in zip(
            results["metadatas"][0], results["distances"][0]
        ):
            out.append({
                "query":    meta.get("query", ""),
                "response": meta.get("response", ""),
                "ts":       meta.get("ts", ""),
                "agent":    meta.get("agent", ""),
                "distance": round(dist, 4),
            })
        return out
    except Exception as e:
        logger.warning(f"vector_memory.search failed: {e}")
        return []


def build_context(query: str, n: int = 5) -> str:
    """
    Returns a formatted memory context string for LLM injection.
    Combines semantic search results into a readable block.
    """
    hits = search(query, n=n)
    if not hits:
        return ""

    lines = ["Relevant past context (semantic recall):"]
    for h in hits:
        lines.append(
            f"  [{h['ts']}] Raja: {h['query'][:70]} → Yali: {h['response'][:100]}"
        )
    return "\n".join(lines)


def count() -> int:
    col = _get_collection()
    return col.count() if col else 0


def migrate_from_json(json_entries: list):
    """
    One-time migration — import existing mid_term JSON entries into ChromaDB.
    Called once on startup if chroma_db is empty but JSON has data.
    """
    if not json_entries:
        return
    col = _get_collection()
    if col is None or col.count() > 0:
        return   # already migrated or unavailable

    logger.info(f"Migrating {len(json_entries)} JSON memories to ChromaDB…")
    for e in json_entries:
        store(
            query=e.get("query", ""),
            response=e.get("response", ""),
            agent=e.get("agent", ""),
        )
    logger.info("Migration complete.")
