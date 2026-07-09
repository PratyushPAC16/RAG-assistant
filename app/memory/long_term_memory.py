"""
Enterprise Agentic RAG Assistant
Long-Term Memory Extractor — extracts facts, preferences, and summaries from conversation turns.
"""

from __future__ import annotations

import json
import uuid
from langchain_core.messages import HumanMessage, SystemMessage

from app.memory.memory_store import get_memory_store
from app.utils.llm_factory import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """You are an AI Memory Extractor.
Analyze the conversation turn (User query and Assistant response) and extract:
1. User preferences (e.g. "prefers markdown tables", "focused on hiring trends", "wants short summaries").
2. Important facts (e.g. specific data points, company info, project names, technical specifications).
3. A concise summary of the conversation turn.

Return the results as a JSON list of objects, where each object has:
- "content": the extracted memory text (e.g. "User prefers markdown tables for data presentation")
- "type": "preference" | "fact" | "summary"

Only extract actual facts or preferences explicitly stated. Do not make assumptions. If nothing is worth remembering, return an empty list []."""


def extract_and_persist_memory(session_id: str, query: str, answer: str) -> None:
    """
    Extract facts, preferences, and turn summary from query-answer pair and save to long-term memory.
    Runs inside a background thread to prevent blocking main response generation.
    """
    logger.info(f"Triggering long-term memory extraction background thread for session {session_id}")
    try:
        llm = get_llm(temperature=0.1)
        prompt = f"USER QUERY:\n{query}\n\nASSISTANT ANSWER:\n{answer}"

        messages = [
            SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # Clean code fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        if not content:
            return

        memories = json.loads(content)
        if not isinstance(memories, list):
            logger.warning("LLM memory extractor response is not a JSON list.")
            return

        store = get_memory_store()
        for m in memories:
            m_content = m.get("content")
            m_type = m.get("type")
            if m_content and m_type in ("fact", "preference", "summary"):
                memory_id = f"mem_{uuid.uuid4().hex[:12]}"
                store.add_memory(
                    memory_id=memory_id,
                    content=m_content,
                    memory_type=m_type,
                    session_id=session_id,
                )
        logger.info(f"Completed memory extraction for session {session_id}: stored {len(memories)} entries.")
    except Exception as exc:
        logger.error(f"Failed to extract and persist memory: {exc}", exc_info=True)
