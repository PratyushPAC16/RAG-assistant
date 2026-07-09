"""
Enterprise Agentic RAG Assistant
Memory Manager — manages local JSON persistence of conversation histories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from app.models.schemas import ChatMessage, ConversationMemory
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MemoryManager:
    """
    Manages persistent local storage for session-based conversation histories.
    Saves and loads sessions to/from the data directory as JSON.
    """

    def __init__(self, conversations_dir: Path | None = None) -> None:
        self.conversations_dir = conversations_dir or (settings.data_path / "conversations")
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MemoryManager initialised at {self.conversations_dir}")

    def save_session(self, session_id: str, memory: ConversationMemory) -> None:
        """Save a session's conversation history to a JSON file."""
        file_path = self._get_session_path(session_id)
        try:
            data = {
                "session_id": memory.session_id,
                "max_turns": memory.max_turns,
                "messages": [msg.model_dump(mode="json") for msg in memory.messages]
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved session {session_id} to disk.")
        except Exception as exc:
            logger.error(f"Failed to save session {session_id} to disk: {exc}", exc_info=True)

    def load_session(self, session_id: str) -> ConversationMemory | None:
        """Load a session's conversation history from disk."""
        file_path = self._get_session_path(session_id)
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            msgs = []
            for m in data.get("messages", []):
                msgs.append(ChatMessage.model_validate(m))
                
            memory = ConversationMemory(
                session_id=data.get("session_id", session_id),
                messages=msgs,
                max_turns=data.get("max_turns", settings.max_memory_turns),
            )
            logger.debug(f"Loaded session {session_id} from disk.")
            return memory
        except Exception as exc:
            logger.error(f"Failed to load session {session_id} from disk: {exc}", exc_info=True)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session's JSON file from disk."""
        file_path = self._get_session_path(session_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted session file {session_id} from disk.")
                return True
            except Exception as exc:
                logger.error(f"Failed to delete session file {session_id}: {exc}", exc_info=True)
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """
        List all saved sessions, including session ID, title, and last modified timestamp.
        Returns sorted list with most recently updated sessions first.
        """
        sessions = []
        for file_path in self.conversations_dir.glob("*.json"):
            session_id = file_path.stem
            try:
                mtime = file_path.stat().st_mtime
                last_updated = datetime.fromtimestamp(mtime)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                messages = data.get("messages", [])
                title = "New Conversation"
                for m in messages:
                    if m.get("role") == "user":
                        content = m.get("content", "")
                        title = (content[:50] + "...") if len(content) > 50 else content
                        break
                        
                sessions.append({
                    "session_id": session_id,
                    "title": title,
                    "last_updated": last_updated.isoformat(),
                    "message_count": len(messages),
                })
            except Exception as exc:
                logger.warning(f"Failed to peek session {session_id}: {exc}")
                
        sessions.sort(key=lambda x: x["last_updated"], reverse=True)
        return sessions

    def _get_session_path(self, session_id: str) -> Path:
        return self.conversations_dir / f"{session_id}.json"


_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
