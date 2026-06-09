"""
Enterprise Agentic RAG Assistant
Memory Store — creates and manages a separate ChromaDB collection for long-term memories.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag.embeddings import get_embedding_service
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


class MemoryStore:
    """
    Manages a distinct ChromaDB collection for long-term user memories,
    preferences, and conversation summaries.
    """

    def __init__(
        self,
        collection_name: str = "long_term_memories",
        persist_dir: str | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir = Path(persist_dir or settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._embedding_service = get_embedding_service()

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._get_or_create_collection()

        logger.info(
            "MemoryStore initialised",
            extra={
                "collection": self.collection_name,
                "persist_dir": str(self.persist_dir),
                "num_memories": self._collection.count(),
            },
        )

    def _get_or_create_collection(self) -> chromadb.Collection:
        try:
            return self._client.get_collection(name=self.collection_name)
        except Exception:
            return self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    def add_memory(
        self,
        memory_id: str,
        content: str,
        memory_type: str,
        session_id: str,
    ) -> None:
        """
        Embed and add a new memory to the long-term collection.
        """
        embedding = self._embedding_service.embed_query(content)
        metadata = {
            "memory_type": memory_type,
            "session_id": session_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
        
        self._collection.add(
            ids=[memory_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.info(
            f"Stored {memory_type} memory: '{content[:50]}...'",
            extra={"memory_id": memory_id, "session_id": session_id},
        )

    def search_memories(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.45,
    ) -> list[dict[str, Any]]:
        """
        Query relevant long-term memories using query embedding.
        Converts ChromaDB cosine distance to similarity score = 1 - distance.
        """
        if self._collection.count() == 0:
            return []

        query_embedding = self._embedding_service.embed_query(query)
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error(f"Memory search failed: {exc}", exc_info=True)
            return []

        parsed = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        for mid, content, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
            score = max(0.0, 1.0 - float(dist))
            if score >= score_threshold:
                parsed.append({
                    "memory_id": mid,
                    "content": content,
                    "memory_type": meta.get("memory_type"),
                    "session_id": meta.get("session_id"),
                    "timestamp": meta.get("timestamp"),
                    "score": round(score, 4),
                })
        return parsed

    def list_all_memories(self) -> list[dict[str, Any]]:
        """
        List all stored memories in long-term store.
        """
        if self._collection.count() == 0:
            return []

        results = self._collection.get(include=["documents", "metadatas"])
        parsed = []
        ids_list = results.get("ids", [])
        docs_list = results.get("documents", [])
        metas_list = results.get("metadatas", [])

        for mid, content, meta in zip(ids_list, docs_list, metas_list):
            parsed.append({
                "memory_id": mid,
                "content": content,
                "memory_type": meta.get("memory_type", "fact"),
                "session_id": meta.get("session_id", ""),
                "timestamp": meta.get("timestamp", ""),
            })
        return parsed

    def delete_memory(self, memory_id: str) -> None:
        """
        Remove a specific memory by ID.
        """
        self._collection.delete(ids=[memory_id])
        logger.info(f"Deleted memory {memory_id} from long-term memory store.")

    def clear_all(self) -> None:
        """
        Wipe out the entire memory collection.
        """
        if self._collection.count() > 0:
            all_ids = self._collection.get().get("ids", [])
            if all_ids:
                self._collection.delete(ids=all_ids)
        logger.info("Cleared all records from long-term memory store.")


_memory_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    """Return the singleton MemoryStore instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store
