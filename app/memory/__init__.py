"""
app.memory
~~~~~~~~~~
Consolidated memory layer for the Enterprise Agentic RAG Assistant.

Modules:
  memory_store     — ChromaDB-backed long-term memory store (facts, preferences, summaries)
  memory_manager   — JSON-based session conversation persistence
  long_term_memory — LLM-driven memory extraction from conversation turns
"""
