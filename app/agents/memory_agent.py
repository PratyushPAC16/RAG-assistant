"""
Enterprise Agentic RAG Assistant
Memory Agent — maintains conversation history, supports follow-up questions
by injecting prior context, and answers questions grounded in conversation memory.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.schemas import (
    AgentState,
    AgentType,
    ChatMessage,
    ConversationMemory,
    MessageRole,
    SourceCitation,
)
from app.utils.config import get_settings
from app.utils.logger import get_logger, log_latency
from app.utils.llm_factory import get_llm

logger = get_logger(__name__)
settings = get_settings()

_MEMORY_SYSTEM_PROMPT = """You are a context-aware conversation assistant with access to the full conversation history.

Your responsibilities:
1. Answer follow-up questions by leveraging the conversation history.
2. Resolve coreferences (e.g., "it", "that", "the previous answer").
3. Synthesise information from earlier turns to form complete answers.
4. Be aware of what has already been explained and avoid repetition.
5. If the memory context is insufficient, clearly indicate what additional information is needed."""

_MEMORY_PROMPT_TEMPLATE = """FULL CONVERSATION HISTORY:
{history}

CURRENT USER QUESTION:
{query}

Based on the conversation history above, provide a complete and accurate answer.
Reference specific earlier messages when relevant using [Turn N] notation."""


class MemoryAgent:
    """
    Conversation-memory agent that answers queries grounded in session history.

    This agent is invoked when the router determines the query is a follow-up
    or is best answered using conversational context rather than new retrieval.

    The agent maintains a per-session :class:`~app.models.schemas.ConversationMemory`
    registry in memory (a dict keyed by session_id).

    Usage::

        agent = MemoryAgent()
        updated_state = agent.run(state)
        # Separately track history:
        agent.add_to_memory(session_id, role, content)
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationMemory] = {}
        self._llm = get_llm(
            temperature=settings.gemini_temperature,
            max_output_tokens=settings.gemini_max_output_tokens,
        )
        logger.info(
            "MemoryAgent initialised",
            extra={"llm_provider": settings.llm_provider},
        )

    # ── LangGraph node entry-point ─────────────────────────────────────────────

    def run(self, state: AgentState) -> AgentState:
        """
        Answer the query using conversation history.

        Args:
            state: Current :class:`~app.models.schemas.AgentState`.

        Returns:
            Updated state with ``answer``, ``sources`` (empty for memory),
            and ``agent_type`` set to MEMORY.
        """
        query = state.query
        session_id = state.session_id
        logger.info(
            "MemoryAgent.run called",
            extra={"query": query[:80], "session_id": session_id},
        )

        try:
            # ── Get or create memory for this session ──────────────────────────
            memory = self._get_session_memory(session_id)

            # ── Build history from both agent state and session memory ─────────
            all_messages = self._merge_history(state, memory)
            formatted_history = self._format_history(all_messages)

            # ── Generate answer ────────────────────────────────────────────────
            with log_latency(logger, "memory_agent_generation") as llm_ctx:
                answer = self._generate_answer(query, formatted_history)
            state.latency_ms["llm"] = llm_ctx.get("latency_ms", 0.0)

            # ── Update state ───────────────────────────────────────────────────
            state.answer = answer
            state.sources = []  # Memory answers don't have document sources
            state.agent_type = AgentType.MEMORY

        except Exception as exc:
            logger.error(
                "MemoryAgent.run failed",
                extra={"error": str(exc), "query": query[:80]},
                exc_info=True,
            )
            state.error = str(exc)
            state.answer = (
                f"Memory agent encountered an error: {exc}\n"
                "Please try rephrasing your question."
            )

        return state

    # ── Session memory management ─────────────────────────────────────────────

    def get_or_create_session(self, session_id: str) -> ConversationMemory:
        """
        Return the memory for *session_id*, creating a new one if absent.
        """
        return self._get_session_memory(session_id)

    def add_to_memory(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        **kwargs: object,
    ) -> None:
        """
        Append a message to the session's conversation history.

        Args:
            session_id: Session identifier.
            role:       MessageRole (USER or ASSISTANT).
            content:    Message text.
            **kwargs:   Additional ChatMessage fields (agent_type, metadata).
        """
        memory = self._get_session_memory(session_id)
        memory.add_message(role=role, content=content, **kwargs)
        logger.debug(
            "Message added to memory",
            extra={
                "session_id": session_id,
                "role": role.value,
                "total_turns": len(memory.messages),
            },
        )

    def get_session_history(self, session_id: str) -> list[ChatMessage]:
        """Return all messages for a given session."""
        return self._get_session_memory(session_id).messages

    def clear_session(self, session_id: str) -> None:
        """Clear the memory for a given session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Session memory cleared", extra={"session_id": session_id})

    def list_sessions(self) -> list[str]:
        """Return all active session IDs."""
        return list(self._sessions.keys())

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_session_memory(self, session_id: str) -> ConversationMemory:
        """Return or initialise a ConversationMemory for the session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationMemory(
                session_id=session_id,
                max_turns=settings.max_memory_turns,
            )
        return self._sessions[session_id]

    def _merge_history(
        self, state: AgentState, memory: ConversationMemory
    ) -> list[ChatMessage]:
        """
        Merge conversation history from agent state and session memory.
        Deduplicates based on (role, content) to avoid repeated messages.
        """
        seen: set[tuple[str, str]] = set()
        merged: list[ChatMessage] = []
        all_msgs = memory.messages + state.conversation_history
        for msg in all_msgs:
            key = (msg.role.value, msg.content[:100])
            if key not in seen:
                seen.add(key)
                merged.append(msg)
        return merged

    @staticmethod
    def _format_history(messages: list[ChatMessage]) -> str:
        """Format a list of ChatMessages as numbered turns."""
        if not messages:
            return "No conversation history available."
        lines: list[str] = []
        turn = 1
        for msg in messages:
            prefix = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"[Turn {turn}] {prefix}: {msg.content}")
            if msg.role == MessageRole.ASSISTANT:
                turn += 1
        return "\n".join(lines)

    def _generate_answer(self, query: str, formatted_history: str) -> str:
        """Use Gemini to answer the query given the conversation history."""
        prompt = _MEMORY_PROMPT_TEMPLATE.format(
            history=formatted_history, query=query
        )
        messages = [
            SystemMessage(content=_MEMORY_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self._llm.invoke(messages)
        return response.content


# ── Module-level singleton ─────────────────────────────────────────────────────

_memory_agent: MemoryAgent | None = None


def get_memory_agent() -> MemoryAgent:
    """Return the singleton MemoryAgent instance."""
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent
