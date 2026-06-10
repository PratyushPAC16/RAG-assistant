# How TalentMind AI Works: Detailed Technical Architecture & Pipeline Guide

This document provides a comprehensive, component-level breakdown of **TalentMind AI** (formerly Enterprise RAG Assistant). It explains how the multi-agent orchestrator, hybrid retrieval algorithms, document processors, API backend, and the telemetry front-end work together to deliver a production-ready agentic knowledge assistant.

---

## ── Overview: What is TalentMind AI? ──

**TalentMind AI** is an advanced, production-ready Enterprise Knowledge Intelligence and Career Agent platform. Built using a multi-agent orchestrator, it acts as an intelligent cognitive layer over unstructured company data and candidate resumes. Users can upload various documents (PDFs, Word documents, text files), query them using natural language, and receive grounded answers backed by precise page-level and source citations.

---

## ── Core Features ──

* **🤖 Intelligent Multi-Agent Orchestrator**: Leverages a graph-based state machine powered by **LangGraph** to dynamically route user questions to specialized agents (semantic document retrieval, real-time web search, or conversation memory recall).
* **📚 Hybrid Search & Fusion Retrieval**: Merges neural semantic vector search (ChromaDB + Gemini Embeddings) with traditional exact keyword matching (BM25Okapi) using **Reciprocal Rank Fusion (RRF)** to optimize keyword and context accuracy.
* **⚡ Neural Reranking**: Utilizes a cross-attention transformer (`MiniLM-L6`) to rerank document snippets, filtering the top 20 candidate chunks down to the 5 most semantically relevant results before generation.
* **🌐 Grounded Web Search Agent**: Automatically supplements local knowledge with real-time web lookups (via **Tavily Search API**) for questions about current events or missing document contexts.
* **🧠 Episodic Conversational Memory**: Tracks topic history and references across multiple turns, enabling natural follow-up questions and coreference resolution.
* **💼 Talent & Resume Analyzer**: Evaluates resumes against Job Descriptions (JDs), computing precise alignment scores, extracting key skill gaps, and generating recommendations.
* **📈 System Telemetry & Live Analytics**: Monitored via a dual-axis dashboard displaying daily volume metrics, LLM latency distributions, and active provider usages.
* **🔌 Provider Control Center**: Supports hot-swapping active model endpoints (Google Gemini, Groq, local Ollama models) with built-in health diagnostics pings.
* **🎨 Glassmorphic Montserrat UI**: Built with a sleek, translucent dark/light glass design system and Montserrat typography.

---

## ── Primary Use Cases & Applications ──

* **🏢 Enterprise Knowledge Management**: Empower teams to instantly search across dense internal manuals, project specifications, and policy handbooks without manual reading.
* **🔍 Talent Acquisition & HR Intelligence**: Automate resume matching, JD evaluations, candidate scoring, and skill gap analyses to streamline recruitment workflows.
* **📰 Real-Time Research & Analysis**: Combine local report indexes with search engine insights to generate grounded comparative reports on market trends.
* **💬 Conversational Data Assistants**: Provide departments (legal, engineering, finance) with self-governing chatbot interfaces that always cite the exact page, score, and source segment.

---

## ── 1. High-Level Architecture Overview ──

TalentMind AI is structured as a decoupled, multi-tier platform built for high-performance retrieval and low-latency interaction:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 Streamlit Front-End                    │
                  │   - Montserrat Typography & Glassmorphism Styling       │
                  │   - Real-Time Node Workflow Playback Visualizer        │
                  │   - Telemetry Analytics Dashboard (Plotly Charts)     │
                  │   - Active LLM Provider Control Center                 │
                  └───────────────────────────┬────────────────────────────┘
                                              │ HTTP Requests
                  ┌───────────────────────────▼────────────────────────────┐
                  │                FastAPI Application Gateway             │
                  │   - RESTful Endpoints (/chat, /upload, /analytics)    │
                  │   - Pydantic Validation & Telemetry Tracking           │
                  └───────────────────────────┬────────────────────────────┘
                                              │ Pipeline Execution
                  ┌───────────────────────────▼────────────────────────────┐
                  │                  LangGraph Orchestrator                │
                  │   - StateGraph with Typed AgentState Context           │
                  │   - Router / RAG / Web / Memory / Formatter Nodes      │
                  └────────────────────────────────────────────────────────┘
```

1. **Streamlit UI Layer**: A modern, glassmorphic client interface serving the landing page portal, agentic chat session, knowledge registry, system settings, and interactive metrics charts.
2. **FastAPI Layer**: An API service layer that validates payloads, manages document indexing background tasks, stores session databases, and serves metrics.
3. **LangGraph Agentic Layer**: A graph-based state machine orchestrating queries across a fleet of specialized sub-agents based on semantic routing decisions.

---

## ── 2. The Multi-Agent Orchestrator (LangGraph) ──

The core decision-making brain of the application runs on a **LangGraph StateGraph**. Instead of running a linear chain, the query undergoes graph-based routing where active agent nodes write telemetry, update memories, and fetch contexts dynamically.

### A. Graph Definition & State Flow
The graph context is defined by `AgentState` (located in [`app/models/schemas.py`](file:///Users/pratyush/Desktop/RAG2/app/models/schemas.py)), which holds:
* `query`: The user's input string.
* `chat_history`: A list of prior conversation turns.
* `session_id`: Unique identifier for the user's session.
* `agent_used`: Determined pathway (`rag`, `web`, `memory`, or `hybrid`).
* `sources`: Extracted citation objects.
* `routing_decision`: The router's JSON classification object.
* `context`: Retrieved chunks or web summaries merged together.
* `answer`: Generated final response.
* `latency_ms`: A dictionary tracking individual node completion times in milliseconds.

```
                  START ──► [Router Node]
                                 │
                     Conditional Branch Routing
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
       [RAG Agent]         [Web Agent]        [Memory Agent]
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                         [Formatter Node] ──► END
```

### B. Node Breakdown
1. **Router Agent** ([`app/agents/router.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/router.py)):
   * Uses the configured LLM with a structured JSON prompt to classify queries.
   * If the query is related to previous conversation contexts, it routes to `memory`.
   * If it requires real-time facts/current dates, it routes to `web`.
   * If it requests local document analysis and documents are indexed, it routes to `rag`.
   * *Fallback Logic*: If the LLM router times out or fails, it falls back to a deterministic keyword-matching heuristic (e.g., checks for words like "latest", "today", "yesterday" for web search routing).
2. **RAG Agent** ([`app/agents/rag_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/rag_agent.py)):
   * Triggered when a query targets local documents.
   * Performs hybrid semantic and keyword searches, runs the retrieved segments through the Cross-Encoder reranker, and constructs a contextual prompt.
3. **Web Search Agent** ([`app/agents/web_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/web_agent.py)):
   * Executes web lookups using the **Tavily Search API**.
   * Merges organic search result descriptions and URLs into the context list to ground answers with active web citations.
4. **Memory Agent** ([`app/agents/memory_agent.py`](file:///Users/pratyush/Desktop/RAG2/app/agents/memory_agent.py)):
   * Extracts historical conversational topics from memory and resolves coreferences (e.g., "what did they say about the second document?" becomes "what did the documents say about Q3 revenue forecasts?").
5. **Response Synthesizer / Formatter Node**:
   * Takes the accumulated context, formats the system guidance, instructs the LLM to generate the final response while adhering strictly to grounding rules, and compiles citation metadata.

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

## ── 4. Telemetry, Analytics, & UI Systems ──

The user interface is built on Streamlit using custom styling and telemetry hooks to ensure high-fidelity interactions:

### A. Advanced Montserrat UI Styling
* **Backdrop Blur & Glassmorphism**: High-blur glass overlays (`backdrop-filter: blur(20px)`) are styled using translucent borders and radial mesh gradients behind elements.
* **Montserrat Font Family**: Injected as the primary stylesheet import at the top of the HTML header to deliver clean geometric typography.
* **Custom Vertical Radio Navigation**: Hidden default circular checkboxes using custom `:has(input[type="radio"]:checked)` CSS rules, transforming them into hover-animated sidebar buttons.

### B. Real-Time Node Playback Visualizer
When a query is submitted, the frontend displays an interactive progress flow:
* Nodes are colored dynamically: `pending` (translucent gray), `active` (pulsating neon-blue glow with spin loaders), or `done` (neon-green border with its specific execution times).
* It reads individual node times directly from the FastAPI response payload (`latency_ms`), representing actual hardware and API transaction metrics.

### C. Live Telemetry Analytics Dashboard
* **Dual-Axis Plotly Charts**: Integrates interactive dual-axis data grids showing Daily Query Volume (bars) and Average Latency (lines).
* **Provider Share & Activity Plots**: Plots LLM provider share distributions (Gemini vs Groq vs Ollama) and hourly query frequency heatmaps.
* **Modular Refresh Fragment Loops**: Uses `@st.fragment` intervals (5s, 15s, 30s) to update metrics and logs in place, bypassing sidebar redraws or page flicker.

### D. Provider Control Center
* **Availability Checks**: Verification routes ping local Ollama endpoints and check environment variables for API keys to mark availability as `Online` or `Offline`.
* **Telemetry and Model Switcher**: Renders select interfaces. Changing the provider dynamically updates the workspace `.env` configuration file and reboots the FastAPI connection pool in real-time.

---

## ── 5. API Gateway & Endpoints ──

The backend exposes a highly structured FastAPI interface (documented via Swagger at `/docs`):

### 📄 POST `/upload`
* **Purpose**: Parse, chunk, embed, and store document segments.
* **Payload**: Form-data file.
* **Response**: Returns document identifier, chunk metrics, and ingestion status.

### 💬 POST `/chat`
* **Purpose**: Execute the LangGraph multi-agent chain.
* **Payload**: `{"query": str, "session_id": str}`
* **Response**: Returns the synthesised answer, source citation metadata, routing decision records, and latency metrics.

### 📊 GET `/analytics/extended`
* **Purpose**: Feeds the Plotly dashboard with query frequencies, latency distributions, and provider shares.
* **Response**: Serialized JSON lists containing structured daily trends, hourly indices, and document capacities.

### 🔌 POST `/provider/switch`
* **Purpose**: Rewrites the `.env` settings parameters and updates active backend schemas.
* **Payload**: `{"provider": str, "model": str}`
* **Response**: Restart state confirmations.
