"""
Enterprise Agentic RAG Assistant
ChromaDB vector store — create, add, delete, and search document chunks.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document

from app.models.schemas import ChunkMetadata, RetrievedChunk
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency

logger = get_logger(__name__)
settings = get_settings()


class VectorStore:
    """
    Manages ChromaDB collections for semantic document search.

    Each instance wraps a single ChromaDB collection identified by
    ``collection_name``.  Documents are stored with their embeddings and
    full :class:`~app.models.schemas.ChunkMetadata` serialised as JSON in
    ChromaDB's metadata dict.

    Usage::

        store = VectorStore()
        store.add_documents(docs, metas)
        results = store.search("What is the revenue forecast?", top_k=20)
    """

    def __init__(
        self,
        collection_name: str | None = None,
        persist_dir: str | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_dir = Path(persist_dir or settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self._embedding_service = embedding_service or get_embedding_service()

        # Initialise persistent ChromaDB client
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._collection = self._get_or_create_collection()

        logger.info(
            "VectorStore initialised",
            extra={
                "collection": self.collection_name,
                "persist_dir": str(self.persist_dir),
                "num_documents": self._collection.count(),
            },
        )

    # ── Collection management ─────────────────────────────────────────────────

    def _get_or_create_collection(self) -> chromadb.Collection:
        """Return existing collection or create a new one."""
        try:
            return self._client.get_collection(name=self.collection_name)
        except Exception:
            return self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    # ChromaDB hard limit on items per batch call
    _CHROMA_MAX_BATCH = 5000

    # ── Write operations ──────────────────────────────────────────────────────

    def add_documents(
        self,
        documents: list[Document],
        chunk_metas: list[ChunkMetadata],
    ) -> list[str]:
        """
        Embed and add document chunks to the collection.

        Large documents (e.g. 2000-page PDFs) can produce tens of thousands of
        chunks. ChromaDB enforces a hard maximum batch size (~5461 items), so
        this method splits the work into batches of at most ``_CHROMA_MAX_BATCH``
        items and inserts them sequentially.

        Args:
            documents:   LangChain Document objects (page_content + metadata).
            chunk_metas: Corresponding ChunkMetadata objects.

        Returns:
            List of ChromaDB IDs for the inserted documents.

        Raises:
            ValueError: If ``documents`` and ``chunk_metas`` lengths differ.
        """
        if len(documents) != len(chunk_metas):
            raise ValueError(
                f"documents ({len(documents)}) and chunk_metas ({len(chunk_metas)}) "
                "must have the same length."
            )
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        ids = [meta.chunk_id for meta in chunk_metas]

        # Serialise metadata dicts — ChromaDB only supports str/int/float/bool values
        serialised_metas = [
            self._serialise_metadata(meta.model_dump()) for meta in chunk_metas
        ]

        with log_latency(
            logger,
            "vector_store_add",
            num_documents=len(documents),
            collection=self.collection_name,
        ):
            embeddings = self._embedding_service.embed_documents(texts)

            # Insert in batches to stay within ChromaDB's hard per-call limit
            total = len(ids)
            batch_size = self._CHROMA_MAX_BATCH
            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                logger.debug(
                    "Inserting ChromaDB batch",
                    extra={"batch": f"{start}–{end}", "total": total},
                )
                try:
                    self._collection.add(
                        ids=ids[start:end],
                        documents=texts[start:end],
                        embeddings=embeddings[start:end],
                        metadatas=serialised_metas[start:end],
                    )
                except Exception as exc:
                    if "dimension" in str(exc).lower() or "dimensionality" in str(exc).lower():
                        logger.error(
                            "ChromaDB dimension mismatch! This usually happens when you switch embedding providers (e.g. from Gemini to Local or Ollama) without resetting the database. Please delete the directory 'chroma_db/' in your workspace to reset the database.",
                            extra={"error": str(exc)}
                        )
                        raise ValueError(
                            "Embedding dimension mismatch with the existing ChromaDB collection. "
                            "Please delete the 'chroma_db/' directory in your workspace to reset the database."
                        ) from exc
                    raise

        logger.info(
            "Documents added to vector store",
            extra={
                "num_added": len(documents),
                "collection": self.collection_name,
            },
        )
        return ids

    def delete_by_document_id(self, document_id: str) -> int:
        """
        Remove all chunks belonging to a given document.

        Args:
            document_id: The UUID of the parent document.

        Returns:
            Number of chunks deleted.
        """
        # Query existing IDs for this document
        results = self._collection.get(
            where={"document_id": document_id},
            include=["documents"],
        )
        ids_to_delete: list[str] = results.get("ids", [])
        if ids_to_delete:
            self._collection.delete(ids=ids_to_delete)
            logger.info(
                "Chunks deleted from vector store",
                extra={"document_id": document_id, "chunks_deleted": len(ids_to_delete)},
            )
        return len(ids_to_delete)

    # ── Read / Search operations ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filter_document_id: str | None = None,
        filter_document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """
        Perform semantic (cosine) search against the collection.

        Args:
            query:              The search query string.
            top_k:              Number of results to return (default from settings).
            filter_document_id: If provided, restrict search to a single document.
            filter_document_ids: If provided, restrict search to a set of documents.

        Returns:
            List of :class:`~app.models.schemas.RetrievedChunk` objects sorted by
            descending similarity score.
        """
        k = top_k or settings.retrieval_top_k

        where: dict[str, Any] | None = None
        doc_ids = []
        if filter_document_id:
            doc_ids.append(filter_document_id)
        if filter_document_ids:
            doc_ids.extend(filter_document_ids)

        if doc_ids:
            doc_ids = list(dict.fromkeys(doc_ids))
            if len(doc_ids) == 1:
                where = {"document_id": doc_ids[0]}
            else:
                where = {"document_id": {"$in": doc_ids}}

        with log_latency(logger, "vector_store_search", query_length=len(query), top_k=k):
            query_embedding = self._embedding_service.embed_query(query)
            try:
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(k, self._collection.count() or 1),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as exc:
                if "dimension" in str(exc).lower() or "dimensionality" in str(exc).lower():
                    logger.error(
                        "ChromaDB dimension mismatch! This usually happens when you switch embedding providers (e.g. from Gemini to Local or Ollama) without resetting the database. Please delete the directory 'chroma_db/' in your workspace to reset the database.",
                        extra={"error": str(exc)}
                    )
                    raise ValueError(
                        "Embedding dimension mismatch with the existing ChromaDB collection. "
                        "Please delete the 'chroma_db/' directory in your workspace to reset the database."
                    ) from exc
                raise

        return self._parse_results(results)

    def get_all_documents_metadata(self) -> list[dict[str, Any]]:
        """
        Return metadata for every chunk in the collection.
        Useful for building the document registry on startup.
        """
        result = self._collection.get(include=["metadatas"])
        return result.get("metadatas", []) or []

    def count(self) -> int:
        """Return total number of chunks stored in the collection."""
        return self._collection.count()

    def collection_exists(self) -> bool:
        """Return True if the collection has at least one chunk."""
        return self._collection.count() > 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _serialise_metadata(meta: dict[str, Any]) -> dict[str, Any]:
        """
        Convert a metadata dict to ChromaDB-compatible format.
        ChromaDB only accepts str, int, float, and bool values; everything else
        is JSON-encoded as a string.
        """
        cleaned: dict[str, Any] = {}
        for key, value in meta.items():
            if isinstance(value, (str, int, float, bool)) and value is not None:
                cleaned[key] = value
            elif value is None:
                cleaned[key] = ""  # ChromaDB does not allow None
            else:
                cleaned[key] = json.dumps(value)
        return cleaned

    @staticmethod
    def _parse_results(raw: dict[str, Any]) -> list[RetrievedChunk]:
        """
        Convert raw ChromaDB query results into :class:`RetrievedChunk` objects.
        ChromaDB returns distances (lower = more similar); we convert to scores
        (higher = more similar) using ``score = 1 - distance``.
        """
        chunks: list[RetrievedChunk] = []

        ids_list = raw.get("ids", [[]])[0]
        docs_list = raw.get("documents", [[]])[0]
        metas_list = raw.get("metadatas", [[]])[0]
        dists_list = raw.get("distances", [[]])[0]

        for chunk_id, content, meta, distance in zip(
            ids_list, docs_list, metas_list, dists_list
        ):
            # Reconstruct ChunkMetadata — handle JSON-encoded fields
            page_val = meta.get("page")
            try:
                page_num = int(page_val) if page_val and str(page_val).isdigit() else None
            except (ValueError, TypeError):
                page_num = None

            chunk_meta = ChunkMetadata(
                source=meta.get("source", "unknown"),
                document_name=meta.get("document_name") or meta.get("source") or "unknown",
                page=page_num,
                file_type=meta.get("file_type") or "",
                chunk_id=chunk_id,
                document_id=meta.get("document_id", ""),
                total_chunks=meta.get("total_chunks"),
            )

            semantic_score = max(0.0, 1.0 - float(distance))
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    content=content,
                    metadata=chunk_meta,
                    semantic_score=round(semantic_score, 4),
                )
            )

        return chunks


# ── Module-level singleton ─────────────────────────────────────────────────────

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Return the singleton :class:`VectorStore` instance.
    Thread-safe as long as FastAPI runs in a single-process mode.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
