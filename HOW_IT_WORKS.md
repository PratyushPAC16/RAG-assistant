# How TalentMind AI Works: Detailed Technical Architecture & Pipeline Guide

This document provides a comprehensive, component-level breakdown of **TalentMind AI** (also known as Enterprise RAG Assistant). It explains how the multi-agent orchestrator, hybrid retrieval algorithms, document processors, API backend, and the React + Streamlit front-ends work together to deliver a production-ready agentic knowledge assistant.

---

## ── Overview: What is TalentMind AI? ──

**TalentMind AI** is an advanced, production-ready Enterprise Knowledge Intelligence and Career Agent platform. Built using a multi-agent orchestrator, it acts as an intelligent cognitive layer over unstructured company data and candidate resumes. Users can upload various documents (PDFs, Word documents, text files), query them using natural language, and receive grounded answers backed by precise page-level and source citations.

---

## ── Core Features ──

* **🤖 Intelligent Multi-Agent Orchestrator**: Graph-based state machine powered by **LangGraph** to dynamically route user questions to specialized agents (semantic document retrieval, real-time web search, or conversation memory recall).
* **📚 Hybrid Search & Fusion Retrieval**: Merges neural semantic vector search (ChromaDB + Gemini Embeddings) with traditional exact keyword matching (BM25Okapi) using **Reciprocal Rank Fusion (RRF)** to optimize keyword and context accuracy.
* **⚡ Neural Reranking**: Utilizes a cross-attention transformer (`MiniLM-L6`) to rerank document snippets, filtering the top 20 candidate chunks down to the 5 most semantically relevant results before generation.
* **🌐 Grounded Web Search Agent**: Automatically supplements local knowledge with real-time web lookups (via **Tavily Search API**) for questions about current events or missing document contexts.
* **🧠 Long-Term Memory Store**: Dedicated ChromaDB memory collection that extracts facts, preferences, and summaries in a background thread and applies user personalization across query contexts.
* **💼 Talent & Resume Analyzer (ATS)**: Evaluates PDF resumes against Job Descriptions (JDs), computing precise alignment scores, extracting key skill gaps, and generating recommendations.
* **📈 Multi-Provider Benchmarks**: Compares latency, cost, and token counts of Ollama, Groq, and Gemini, assessing answer faithfulness using LLM-graded evaluators.
* **🔌 Provider Control Center**: Live hot-swapping of active model providers (Gemini, Groq, Ollama) and embeddings (Gemini, Local, Ollama) by updating backend state and `.env` on-the-fly.
* **🎨 Glassmorphic Montserrat UI**: Built with a sleek, translucent dark/light glass design system, Montserrat typography, and custom dashboard components.

---

## ── 1. High-Level Architecture Overview ──

TalentMind AI is structured as a decoupled, multi-tier platform built for high-performance retrieval and low-latency interaction:

```
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│     Next.js Frontend (Port 3000)     │     │    Streamlit Frontend (Port 8501)    │
│ - Montserrat & Glassmorphism Styling │     │ - Real-Time Node Playback            │
│ - Visual Flow Workflow DAG Builder   │     │ - Telemetry Analytics Dashboard      │
│ - ATS Resume Upload & Comparison     │     │ - LLM Provider Controller            │
└──────────────────┬───────────────────┘     └──────────────────┬───────────────────┘
                   │                                            │
                   │               HTTP Requests                │
                   └─────────────────────┬──────────────────────┘
                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend (Port 8000)                            │
│ - RESTful Endpoints (/chat, /upload, /analyze-resume, /memories, /benchmark)      │
│ - Pydantic Payload Validation & Structured Request-ID JSON Logging                │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │ Pipeline Execution
┌────────────────────────────────────────▼──────────────────────────────────────────┐
│                            LangGraph Orchestrator                                 │
│ - StateGraph with Typed AgentState context                                        │
│ - Memory Retriever node, Router node, parallel agent branches, Formatter node    │
└───────────────────────────────────────────────────────────────────────────────────┘
```

1. **Next.js Frontend**: The primary, modern Web interface built using React, TailwindCSS, Zustand state stores, and React Flow, hosting the main dashboard, chat interface, visual workflow creator, and resume comparison module.
2. **Streamlit UI Layer**: A companion Python dashboard providing system telemetry charts, live model switching controls, and modular @st.fragment refresh loops.
3. **FastAPI Application Gateway**: The core backend API that hosts document ingestion pipelines, manages the session stores, runs evaluations, and hosts background tasks.
4. **LangGraph Agentic Layer**: The state machine orchestrating incoming queries across a fleet of specialized sub-agents based on semantic routing decisions.

---

## ── 2. The Multi-Agent Orchestrator (LangGraph) ──

The core decision-making brain of the application runs on a **LangGraph StateGraph**. Instead of running a linear chain, the query undergoes graph-based routing where active agent nodes write telemetry, update memories, and fetch contexts dynamically.

### A. Graph Definition & State Flow
The graph context is defined by `AgentState` (located in [`app/models/schemas.py`](file:///Users/pratyush/Desktop/RAG2/app/models/schemas.py)), which holds:
* `query`: The user's input string.
* `session_id`: Unique identifier for the user's session.
* `agent_type`: Determined pathway (`rag`, `web`, `memory`, or `hybrid`).
* `retrieved_chunks`: List of chunks retrieved from semantic and keyword searches.
* `reranked_chunks`: Chunks remaining after running the reranker.
* `web_results`: List of JSON payloads representing external Tavily search hits.
* `context`: Retrieved chunks or web summaries merged together.
* `answer`: Generated final response.
* `sources`: Extracted citation objects containing document names and page numbers.
* `conversation_history`: List of prior conversation messages (turn-level history).
* `error`: Logged exception strings if any node fails.
* `latency_ms`: A dictionary tracking individual node completion times in milliseconds.
* `routing_decision`: The router's JSON classification object.
* `routing_trace`: Visual logging checklist of steps executed.
* `prompt_tokens` / `completion_tokens` / `total_tokens`: Token counts across nodes.
* `cost_usd`: Consolidated cost based on active provider pricing.
* `filter_document_ids`: Optional list of document IDs to restrict RAG searches.
* `retrieved_memories`: Facts or user preferences retrieved from the long-term memory store.

```
                  START ──► [Memory Retriever Node]
                                  │
                            [Router Node]
                                  │
                      Conditional Branch Routing
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        [RAG Node]           [Web Node]         [Memory Node]
        (RAG Agent)         (Web Search)        (Memory Agent)
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                          [Synthesizer Node]
                                  │
                          [Formatter Node] ──► END
```

### B. Node Breakdown
1. **Memory Retriever Node** ([`app/agents/graph.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/graph.py)):
   * Runs as the first node in the graph (START → `memory_retriever_node`).
   * Queries the dedicated ChromaDB `long_term_memories` database for user preferences and historical facts matching the current query.
   * Feeds matching records into `retrieved_memories` inside the graph state.
2. **Router Agent** ([`app/agents/router.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/router.py)):
   * Uses the configured LLM with a structured JSON prompt to classify queries.
   * If the query is related to previous conversation contexts, it routes to `memory`.
   * If it requires real-time facts/current dates, it routes to `web`.
   * If it requests local document analysis and documents are indexed, it routes to `rag`.
   * If it asks for a combination, it routes to `hybrid` (executing both `rag` and `web` in parallel).
   * *Fallback Heuristics*: If the LLM router times out or fails, it falls back to a deterministic keyword-matching heuristic (e.g., checks for words like "latest", "today", "yesterday" for web search routing).
3. **RAG Agent** ([`app/agents/rag_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/rag_agent.py)):
   * Triggered when a query targets local documents.
   * Performs hybrid semantic and keyword searches, runs the retrieved segments through the Cross-Encoder reranker, and constructs a contextual prompt.
4. **Web Search Agent** ([`app/agents/web_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/web_agent.py)):
   * Executes web lookups using the **Tavily Search API**.
   * Merges organic search result descriptions and URLs into the context list to ground answers with active web citations.
5. **Memory Agent** ([`app/agents/memory_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/memory_agent.py)):
   * Extracts historical conversational topics from memory and resolves coreferences (e.g., "what did they say about the second document?" becomes "what did the documents say about Q3 revenue forecasts?").
6. **Response Synthesizer Node** ([`app/agents/synthesizer.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/synthesizer.py)):
   * Aggregates retrieved contexts, active memories, and web results into a grounding prompt, instructing the LLM to generate a factual response with source citations.
7. **Response Formatter Node** ([`app/agents/graph.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/graph.py)):
   * Takes the accumulated context, cleans up whitespace, deduplicates source citations, and computes final pipeline latency metrics before ending.

---

## ── 3. Data Ingestion & The RAG Pipeline ──

The local RAG pipeline is built for high retrieval precision by leveraging **hybrid search** and **reranking**.

```
    [Upload] ──► Text Extraction ──► Chunking ──► Embedding (Gemini) ──► ChromaDB (Vector)
                                  │
                                  └──────────────────────────────────► BM25 Inverted Index
```

### A. Document Processing
* **Extractors** ([`app/rag/document_processor.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/document_processor.py)):
  * **PDF**: Extracted page-by-page using PyPDF/pdfplumber, attaching the page index to each chunk's metadata to support page-level citations.
  * **DOCX**: Extracted paragraph-by-paragraph.
  * **TXT**: Read directly.
* **Chunking**: Uses a recursive text splitter targeting a `CHUNK_SIZE` of 1000 characters and a `CHUNK_OVERLAP` of 200 characters to prevent loss of semantic meaning at boundary divisions.

### B. Semantic Vector Store
* **Embeddings** ([`app/rag/embeddings.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/embeddings.py)): Computes vector representations using the `models/gemini-embedding-001` API, featuring automatic rate-limiting handling and retry buffers.
* **Vector Store** ([`app/rag/vector_store.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/vector_store.py)): Leverages a local **ChromaDB** instance utilizing Cosine Similarity distance.

### C. Keyword Search
* **BM25 Search** ([`app/rag/retriever.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/retriever.py)): Maintains a local **BM25Okapi** index. When a document is processed, its text is tokenized (lowercased, punctuation removed) to create a term frequency matrix. This resolves issues where neural embeddings miss exact keyword queries like serial numbers or product model codes.

### D. Hybrid Retrieval & Reciprocal Rank Fusion (RRF)
To combine semantic and keyword retrieval ranks, the system uses **RRF (Reciprocal Rank Fusion)**:
1. Retrieval is performed on ChromaDB (returning top $K$ items) and BM25 (returning top $K$ items).
2. For each document, its RRF score is computed as:
   $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
   Where $M$ is the set of retrieval systems (Semantic and BM25), $r_m(d)$ is the rank of document $d$ in system $m$, and $k$ is a constant smoothing parameter (default $k=60$).
3. The items are sorted by their RRF score, and the top 20 candidate chunks are passed to the next stage.

### E. Neural Reranking
* **MiniLM Cross-Encoder** ([`app/rag/reranker.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/reranker.py)):
  * The top 20 chunks are evaluated by `cross-encoder/ms-marco-MiniLM-L6-v2`.
  * Unlike embeddings (which evaluate sentences independently), a Cross-Encoder processes the query and the chunk text together, calculating attention weights between query terms and document terms.
  * This narrows down the top 20 candidates into the **Top 5 highest-scoring chunks**, keeping the LLM generation context window clean and free of noise.

---

## ── 4. Long-Term Memory System ──

Long-term memory provides personalized context preservation across distinct chat sessions:

```
  AgentOrchestrator.run() completed
                 │
                 ▼
     Spawns background thread
                 │
                 ▼
       [Memory Extractor LLM] ──► Parses query/answer turn for facts & preferences
                 │
                 ▼
       [MemoryStore collection] ──► Inserts embeddings and metadatas into ChromaDB
```

1. **Asynchronous Extraction**: Once the orchestrator generates a response, it triggers `extract_and_persist_memory` in a daemon background thread ([`app/utils/long_term_memory.py`](file:///Users/pratyush/Desktop/RAG2/app/utils/long_term_memory.py)) to avoid blocking API response latency.
2. **Preference & Fact Parsing**: The background worker invokes the LLM with a strict system prompt to isolate explicit user preferences and important factual statements.
3. **Database Insertion**: Extracted memories are embedded and stored in a separate ChromaDB collection named `long_term_memories` ([`app/rag/memory_store.py`](file:///Users/pratyush/Desktop/RAG2/app/rag/memory_store.py)) along with the session ID, timestamp, and category tags (`fact`, `preference`, or `summary`).
4. **Context Injection**: During subsequent turns, the `memory_retriever_node` query searches this collection using semantic cosine similarity, injecting relevant facts/preferences back into the active agent pipeline.

---

## ── 5. Career Intelligence & Resume Analyzer (ATS) ──

The Career Intelligence module provides automated resume evaluations against job requirements:

1. **PDF Text Extraction**: Receives uploaded PDF documents for both candidate resumes and target Job Descriptions (JDs), extracting raw string content via pdfplumber/PyPDF pipelines ([`app/utils/pdf_extractor.py`](file:///Users/pratyush/Desktop/RAG2/app/utils/pdf_extractor.py)).
2. **ATS Comparison Prompting**: Formulates a detailed evaluation request containing both text bodies and submits it to the LLM ([`app/api/main.py`](file:///Users/pratyush/Desktop/RAG2/app/api/main.py#L385-L427)).
3. **Attribute Extraction**: Isolates key structural metrics:
   - Candidate skills, projects, education history, and experience lists.
   - Job requirements, missing skills, candidate strengths, and action items.
4. **Scoring Engine**: Computes granular indexes:
   - `match_score` (Overall fit).
   - `skill_match_pct` (Technical capability matching).
   - `project_match_pct` (Project relevancy score).
   - `education_match_pct` (Academics criteria verification).
   - `interview_readiness_score` (Seniority alignment index).
5. **Structured JSON Validation**: Enforces strict JSON response outputs, stripping markdown formatting fences, and validating keys against frontend Pydantic models.

---

## ── 6. Concurrent Multi-Provider Benchmarks ──

To facilitate model comparison, the platform supports parallel evaluations across different provider instances:

1. **Asynchronous parallelization**: Leverages Python's `asyncio.gather` and thread pools (`run_in_executor`) to invoke configured provider models (Google Gemini, Groq, local Ollama) concurrently on the same query.
2. **RAG Context Integration**: Optionally retrieves contextual documents from the local ChromaDB index and appends it to the benchmark prompt template to isolate RAG performance.
3. **Metrics Tracking**: Records specific dimensions:
   - Latency (seconds to first token/completion).
   - Token volume (prompt, completion, and total counts).
   - Financial cost (computed using provider-specific pricing databases).
   - Response details (character and word length).
4. **Faithfulness Evaluation**: The active model evaluates the generated answers using an LLM-graded prompt. It scores faithfulness from 0 to 100 based on how well the response is grounded in the retrieved context, returning detailed reasoning.
5. **Composite Scoring**: Calculates a normalized composite score:
   $$\text{Composite Score} = 0.5 \times \text{Faithfulness} + 0.3 \times \text{Speed Score} + 0.2 \times \text{Cost Score}$$
   Where speed and cost scores are normalized against the highest-latency and highest-cost models in the concurrent batch.
6. **Leaderboards**: Persists results to `benchmark_runs.jsonl` to render historical telemetry comparisons in the frontend.

---

## ── 7. Visual Workflow execution ──

Custom agent DAG workflows are visualised on the Next.js React Flow builder and executed by the backend's `workflow_executor.py` ([`app/services/workflow_executor.py`](file:///Users/pratyush/Desktop/RAG2/app/services/workflow_executor.py)):

1. **Topological Ordering**: Uses **Kahn's topological sort algorithm** to evaluate nodes in order of their dependencies, identifying cycle conflicts before executing the workflow.
2. **Context Accumulation**: Maintains a shared `ctx` dictionary containing the original query.
3. **Step Execution**: Maps nodes to registered executors:
   - `router`: Classifies the query (`web`, `memory`, or `rag`).
   - `rag`: Fetches RAG documents using the local BM25/ChromaDB hybrid search.
   - `memory`: Queries long-term memories for personalization.
   - `web_search`: Executes search queries via Tavily client connections.
   - `llm`: Invokes LLM generation, appending retrieved contexts, memory items, or web summaries as context blocks.
   - `evaluator`: Invokes LLM-graded verification checks.
4. **State Propagation**: Step executions save outputs to the shared `ctx` dictionary, making data available to downstream nodes.
5. **Telemetry Trace**: Logs execution times, outputs, and status values (`running`, `done`, `error`) for each node, returning a structured execution report.

---

## ── 8. Configuration Reloading ──

To support provider hot-swapping without server restarts, the backend exposes a `/reload` route:

1. **Cache Clearing**: Clears the LRU cache on Pydantic's `get_settings()` utility, forcing it to read updated values from the `.env` file on disk.
2. **Singleton Resets**: Resets module-level singletons (`_embedding_service`, `_vector_store`, `_retriever`, and agent objects) to `None`.
3. **Eager Re-initialization**: Re-initializes connectors using the new configurations. This ensures API keys and endpoint settings are validated and active immediately.
