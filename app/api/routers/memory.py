from __future__ import annotations

import logging
from fastapi import APIRouter, Depends

from app.memory.memory_store import get_memory_store
from app.api.dependencies import _require_api_key

router = APIRouter(tags=["Long-Term Memory"])
logger = logging.getLogger(__name__)


@router.get(
    "/memories",
    summary="List all long-term memories",
)
async def list_all_memories() -> list[dict]:
    """
    Retrieve all stored facts, preferences, and summaries from the ChromaDB long-term memory store.
    """
    return get_memory_store().list_all_memories()


@router.get(
    "/memories/search",
    summary="Search matching memories",
)
async def search_memories(query: str, top_k: int = 5) -> list[dict]:
    """
    Query memories matching the user query with similarity scores.
    """
    return get_memory_store().search_memories(query, top_k=top_k, score_threshold=0.45)


@router.delete(
    "/memories/{memory_id}",
    summary="Delete a specific long-term memory",
    dependencies=[Depends(_require_api_key)],
)
async def delete_memory(memory_id: str) -> dict:
    """
    Delete a specific fact/preference/summary from ChromaDB.
    """
    get_memory_store().delete_memory(memory_id)
    return {"status": "success", "message": f"Memory {memory_id} deleted."}


@router.delete(
    "/memories",
    summary="Clear all long-term memories",
    dependencies=[Depends(_require_api_key)],
)
async def clear_all_memories() -> dict:
    """
    Wipe out the entire long-term memories database.
    """
    get_memory_store().clear_all()
    return {"status": "success", "message": "All long-term memories cleared."}
