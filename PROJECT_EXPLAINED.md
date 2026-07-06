# 🧠 TalentMind AI — Project Explained (From Scratch)

> **Who is this for?**  
> This document assumes you know *nothing* about RAG, LangChain, LangGraph, or AI backends. Every concept is explained from first principles, with analogies, before the code is shown.

---

## 📚 Table of Contents

1. [What Problem Does This Project Solve?](#1-what-problem-does-this-project-solve)
2. [What Is RAG? (The Core Idea)](#2-what-is-rag-the-core-idea)
3. [How an AI "Reads" a Document (Embeddings)](#3-how-an-ai-reads-a-document-embeddings)
4. [What Is a Vector Database?](#4-what-is-a-vector-database)
5. [Big Picture Architecture](#5-big-picture-architecture)
6. [The Backend (FastAPI + Python)](#6-the-backend-fastapi--python)
7. [The Agent System (LangGraph)](#7-the-agent-system-langgraph)
8. [The 5 Agents — What Each One Does](#8-the-5-agents--what-each-one-does)
9. [The Retrieval Pipeline — How the AI Finds Answers](#9-the-retrieval-pipeline--how-the-ai-finds-answers)
10. [Long-Term Memory — How the AI Remembers You](#10-long-term-memory--how-the-ai-remembers-you)
11. [The Frontend (Next.js)](#11-the-frontend-nextjs)
12. [Key Features Explained](#12-key-features-explained)
13. [Technologies Used and Why](#13-technologies-used-and-why)
14. [Complete File Map](#14-complete-file-map)
15. [How a Single Chat Message Flows Through the System](#15-how-a-single-chat-message-flows-through-the-system)

---

## 1. What Problem Does This Project Solve?

Imagine you have a giant pile of company documents — PDFs of reports, DOCX files of policies, text files of notes. You want to ask questions like:

> *"What was our Q3 revenue?"*  
> *"What does our hiring policy say about remote work?"*

A regular LLM (like ChatGPT) can't answer these — it was trained on the internet, not on **your private documents**.

This project solves that by building a **personal AI assistant** that:
- Reads and stores your documents in a smart database
- Answers questions using **only your documents** (with exact page citations)
- Also searches the internet when needed
- Remembers previous conversations
- Can even analyze your resume vs a job description

---

## 2. What Is RAG? (The Core Idea)

**RAG = Retrieval-Augmented Generation**

Break that phrase apart:
- **Retrieval** → Find the most relevant pieces of text from your documents
- **Augmented** → Enhance the AI's knowledge with that text
- **Generation** → Use the AI to generate a natural-language answer

### A Simple Analogy

Imagine you're an open-book exam student. The "exam question" is the user's question. The "book" is your uploaded documents. RAG is the process of:
1. Quickly scanning the book for the most relevant paragraphs
2. Reading only those paragraphs
3. Writing your answer based on them

Without RAG, the AI is doing a **closed-book exam** — guessing from memory. With RAG, it's an **open-book exam** — reading the right passages to answer accurately.

### The RAG Flow (Simplified)

```
User types a question
        ↓
Find top matching paragraphs from documents
        ↓
Give those paragraphs to the AI as context
        ↓
AI writes a grounded, cited answer
```

---

## 3. How an AI "Reads" a Document (Embeddings)

Before the AI can search documents, it needs to understand them. Here's how that works.

### What Is an Embedding?

An **embedding** is a list of numbers (a "vector") that represents the *meaning* of a piece of text.

For example:
- "The dog ran fast" → `[0.12, -0.34, 0.89, ...]` (1000+ numbers)
- "The puppy sprinted quickly" → `[0.11, -0.32, 0.88, ...]` (very similar numbers!)

Similar meanings → similar numbers. Different meanings → very different numbers.

This is powerful because you can now **compare** texts mathematically. If two texts have similar numbers, they probably mean similar things.

### In This Project

When you upload a document, the system:
1. Splits it into small chunks (~500 characters each)
2. Runs each chunk through **Google Gemini's embedding model** to convert it to numbers
3. Stores those numbers in **ChromaDB** (the vector database)

When you ask a question, it:
1. Converts your question to numbers (same embedding model)
2. Finds the stored chunks whose numbers are closest to your question's numbers
3. Returns those chunks as the "most relevant" passages

This is called **semantic search** — searching by *meaning*, not just by keywords.

---

## 4. What Is a Vector Database?

A **vector database** stores those number-lists (vectors) and lets you search them efficiently.

Think of it like a regular database, but instead of searching by exact text match (`WHERE name = "John"`), you search by mathematical similarity ("Find me the 10 vectors closest to this query vector").


### ChromaDB

This project uses **ChromaDB** — a lightweight, local vector database that:
- Stores document chunks + their embeddings
- Runs entirely on your machine (no cloud needed)
- Persists data to disk (in the `chroma_db/` folder) so data survives server restarts
- Supports filtering by document ID, so you can search within specific documents

In this project there are actually **two separate ChromaDB collections**:
1. `rag_documents` — stores all your uploaded document chunks
2. `long_term_memories` — stores facts the AI has learned about you across conversations

---

## 5. Big Picture Architecture

Here's the full system, explained layer by layer:

```
┌────────────────────────────────────────────────────────┐
│              USER'S BROWSER                            │
│  Next.js Frontend (Port 3000)                         │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │  Chat UI │ Documents│Benchmarks│ Resume Analyzer  │ │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
└───────────────────────────┬────────────────────────────┘
                            │  HTTP API Calls
                            ▼
┌────────────────────────────────────────────────────────┐
│              PYTHON BACKEND (Port 8000)                │
│  FastAPI — Handles all API requests                    │
│                                                        │
│  Routes: /chat, /upload, /documents, /benchmark, etc. │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│           LANGGRAPH ORCHESTRATOR                       │
│                                                        │
│   START → [Memory Retriever] → [Router Agent]          │
│                                    │                   │
│              ┌─────────────────────┼──────────────┐   │
│              ▼                     ▼              ▼    │
│         [RAG Agent]          [Web Agent]   [Memory]   │
│              │                     │              │    │
│              └─────────────────────┼──────────────┘   │
│                                    ▼                   │
│                          [Synthesizer Agent]           │
│                                    ▼                   │
│                          [Formatter Agent] → END       │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌────────────┴──────────────┐
               ▼                           ▼
      ┌─────────────────┐       ┌─────────────────────┐
      │    ChromaDB      │       │   ChromaDB           │
      │  (Documents)     │       │  (Long-Term Memories)│
      └─────────────────┘       └─────────────────────┘
```

**In plain English:**
1. You type a message in the browser
2. The frontend sends it to the FastAPI backend
3. The backend passes it to the LangGraph Orchestrator
4. The orchestrator decides: "Is this about uploaded docs? Web? Previous conversation?"
5. The right agents run, find relevant info, and generate an answer
6. The answer (with citations) goes back to your browser

---

## 6. The Backend (FastAPI + Python)

**File:** [`app/api/main.py`](app/api/main.py)

**FastAPI** is a Python web framework. Think of it as the "receptionist" of the system — it receives all incoming requests, validates them, and sends them to the right place.

### Key API Endpoints

| Endpoint | What It Does |
|---|---|
| `POST /chat` | Send a question, get an AI answer with citations |
| `POST /upload` | Upload a PDF, DOCX, or TXT document |
| `GET /documents` | List all uploaded documents |
| `DELETE /documents/{id}` | Delete a specific document |
| `POST /analyze-resume` | Compare a resume PDF vs a job description PDF |
| `POST /benchmark` | Test all LLM providers side-by-side |
| `POST /reload` | Hot-reload environment variables without restarting |
| `GET /memories` | See the AI's long-term memories about you |
| `GET /analytics` | Usage statistics and latency metrics |
| `POST /workflows` | Save/load custom AI pipeline configurations |

### Example: What Happens When You Upload a Document

```
You upload "report.pdf"
        ↓
FastAPI receives the file, saves it temporarily
        ↓
DocumentProcessor reads the PDF, splits it into ~500 char chunks
        ↓
EmbeddingService converts each chunk to a vector (list of numbers)
        ↓
ChromaDB stores: chunk text + vector + metadata (page number, filename, etc.)
        ↓
BM25 index is rebuilt to include the new chunks
        ↓
API returns: { "document_id": "abc123", "num_chunks": 47, ... }
```

---

## 7. The Agent System (LangGraph)

**File:** [`app/agents/graph.py`](app/agents/graph.py)

### What Is LangGraph?

**LangGraph** is a library for building AI workflows as a **graph** — a series of connected steps where each step is a "node" and arrows between nodes define the flow.

Think of it like a **flowchart** where each box is an AI agent doing a specific job, and the arrows say "after this step, go there."

### What Is an Agent?

An **agent** is a piece of code that:
1. Receives some information (the "state")
2. Does something with it (calls an AI, searches a database, etc.)
3. Returns updated information

### The Graph Topology

```
START
  │
  ▼
[Memory Retriever] — "Do I already know anything relevant about this user?"
  │
  ▼
[Router Agent] — "What kind of question is this?"
  │
  ├── "About documents" ──────► [RAG Agent]
  ├── "About current events" ──► [Web Agent]
  ├── "About our conversation" ► [Memory Agent]
  └── "Both docs + web" ──────► [RAG Agent] + [Web Agent] (parallel!)
              │                        │              │
              └────────────────────────┴──────────────┘
                                       │
                                       ▼
                            [Synthesizer Agent] — "Write the final answer"
                                       │
                                       ▼
                            [Formatter Agent] — "Clean up and add metadata"
                                       │
                                       ▼
                                      END
```

### What Is "State"?

The **state** is a shared bag of information that all nodes read from and write to. It contains things like:
- `query` — the user's question
- `retrieved_chunks` — document passages found by RAG
- `web_results` — results from the internet
- `answer` — the final generated answer
- `sources` — list of citations
- `routing_trace` — a step-by-step log of what happened (visible in the UI)

Each node receives the current state, does its work, and returns only the fields it changed.

---

## 8. The 5 Agents — What Each One Does

### 🗺️ Router Agent
**File:** [`app/agents/router.py`](app/agents/router.py)

The "traffic cop." It reads the user's question and decides which agent to send it to.

**How it works:**
1. Counts how many documents are in the knowledge base
2. Checks if there's a conversation history
3. Sends a prompt to Gemini (the AI): *"Given this query and context, route to: rag / web / memory / hybrid"*
4. Gemini returns JSON like: `{"agent": "rag", "reasoning": "User referenced 'the document'", "confidence": 0.95}`
5. If the AI fails, it falls back to keyword-based rules

**Routing Rules (simplified):**
- Keywords like "document", "report", "file" → `rag`
- Keywords like "latest", "news", "today" → `web`
- Keywords like "you said", "earlier", "before" → `memory`
- Both doc + web keywords → `hybrid` (runs both simultaneously!)
- No documents uploaded at all → `web`

---

### 📚 RAG Agent
**File:** [`app/agents/rag_agent.py`](app/agents/rag_agent.py)

Searches your uploaded documents and retrieves the most relevant chunks.

Uses the full **Hybrid Retrieval Pipeline** (see Section 9 for details).

---

### 🌐 Web Search Agent
**File:** [`app/agents/web_agent.py`](app/agents/web_agent.py)

Searches the internet using **Tavily** — a search API designed for AI applications.

**How it works:**
1. Calls `tavily.search(query, max_results=8, search_depth="advanced")`
2. Gets back 8 web pages with title, URL, and content snippets
3. Stores these `web_results` in the state
4. The Synthesizer will cite them with `[Source: https://...]`

---

### 🧠 Memory Agent
**File:** [`app/agents/memory_agent.py`](app/agents/memory_agent.py)

Handles **short-term session memory** — the conversation history within a single chat session.

When you say "explain that more" or "what did you say about X?", this agent retrieves the last 6 messages from the current session and includes them as context.

---

### ✨ Synthesizer Agent (Response Generator)
**File:** [`app/agents/synthesizer.py`](app/agents/synthesizer.py)

The "writer." It takes all the gathered context (document chunks + web results + memories) and asks the AI to write the final answer.

It sends a carefully crafted prompt to Gemini that includes:
- The user's question
- All retrieved document chunks (labeled with source + page)
- All web search results (labeled with URL)
- The recent conversation history

**Citation rules enforced in the prompt:**
- Document info → `[Source: filename.pdf, Page 3]`
- Web info → `[Source: https://example.com]`
- Previous conversation → `[Turn 2]`

The synthesizer also **parses** the AI's answer to extract those citations and build a structured `sources` list.

---

## 9. The Retrieval Pipeline — How the AI Finds Answers

**File:** [`app/rag/retriever.py`](app/rag/retriever.py)

This is the heart of the RAG system. It uses **3 stages** to find the best chunks:

### Stage 1: Semantic Search (ChromaDB)

Converts your query to a vector and finds the 30 most similar document chunks by **cosine similarity**.

✅ Great at: Finding conceptually similar text even if different words are used.  
❌ Bad at: Exact keyword matching ("find all mentions of 'EBITDA'").

### Stage 2: BM25 Keyword Search

**BM25** (Best Match 25) is a classic information retrieval algorithm. It scores documents based on:
- How often the query terms appear in the document
- How rare those terms are across all documents

✅ Great at: Exact keyword matches, abbreviations, proper nouns.  
❌ Bad at: Synonyms, paraphrasing ("automobile" vs "car").

### Stage 3: Reciprocal Rank Fusion (RRF)

**RRF** merges the two ranked lists into one. It doesn't care about the raw scores — only the *ranks*.

For each chunk, it calculates:
```
rrf_score = (semantic_weight / (60 + semantic_rank)) + (bm25_weight / (60 + bm25_rank))
```

A chunk ranked #1 by semantic AND #1 by BM25 gets a very high combined score. A chunk only found by one method gets a lower score.

This **hybrid approach** is much better than either search alone.

### Stage 4: Cross-Encoder Reranking

**File:** [`app/rag/reranker.py`](app/rag/reranker.py)

After RRF produces the top 30 chunks, a **cross-encoder** model scores them.

**What's the difference between embeddings and a cross-encoder?**

- **Embedding (bi-encoder):** Converts query and document *separately* to vectors, then compares. Fast, but less accurate.
- **Cross-encoder:** Reads the query and document *together* as one input. Much more accurate, but slower (can't pre-compute).

The model used is `cross-encoder/ms-marco-MiniLM-L6-v2` (from HuggingFace) — small enough to run on CPU, accurate enough for production.

**Result:** Top 30 chunks → reranked → top 5 best chunks → sent to the AI for synthesis.

### Full Pipeline Summary

```
Your question
    │
    ├──► ChromaDB Semantic Search → top 30 chunks
    │
    ├──► BM25 Keyword Search → top 30 chunks
    │
    ▼
Reciprocal Rank Fusion (merge lists) → best 30 chunks
    │
    ▼
Cross-Encoder Reranker → best 5 chunks
    │
    ▼
Synthesizer AI (Gemini) → final answer with citations
```

---

## 10. Long-Term Memory — How the AI Remembers You

**Files:** [`app/rag/memory_store.py`](app/rag/memory_store.py), [`app/utils/long_term_memory.py`](app/utils/long_term_memory.py)

The system has **two types of memory**:

### Short-Term (Session Memory)
- Stored in RAM
- Only lasts during a chat session
- Contains the conversation turn-by-turn
- Used by the Memory Agent for follow-up questions

### Long-Term (Persistent Memory)
- Stored in ChromaDB (`long_term_memories` collection)
- Survives server restarts
- Contains **extracted facts** about the user

**How it works:**
After every AI response, a **background thread** runs (without slowing down your response) that:
1. Asks Gemini: *"What facts, preferences, or important info can you extract from this conversation?"*
2. Gets back structured memories like: `{"type": "preference", "content": "User prefers concise answers"}`
3. Embeds those memories and stores them in ChromaDB

**On the next conversation**, the Memory Retriever node (first node in the graph) automatically searches long-term memories for anything relevant to your new question and includes it as context.

---

## 11. The Frontend (Next.js)

**Folder:** [`frontend/src/`](frontend/src/)

The frontend is built with **Next.js** (React framework) and **TypeScript**. It has multiple pages:

### Pages

| Page | Path | What It Does |
|---|---|---|
| **Home / Dashboard** | `/` | Overview of system stats, recent activity |
| **Chat** | `/chat` | The main chat interface with the AI |
| **Documents** | `/documents` | Upload/manage your document knowledge base |
| **Benchmarks** | `/benchmarks` | Compare Gemini vs Groq vs Ollama side-by-side |
| **Resume Analyzer** | `/resume` | Upload resume + job description, get ATS score |
| **Workflow Builder** | `/workflow` | Visual DAG builder for custom AI pipelines |
| **Analytics** | `/analytics` | Usage stats, latency graphs |
| **Settings** | `/settings` | Control LLM provider, API keys |

### State Management
**Folder:** [`frontend/src/store/`](frontend/src/store/)

Uses **Zustand** — a lightweight React state manager — to keep track of:
- Settings (which LLM provider is active)
- Workflow configurations

### API Communication
**File:** [`frontend/src/services/api.ts`](frontend/src/services/api.ts)

All API calls to the backend go through this file. It uses `fetch` to communicate with `http://localhost:8000`.

---

## 12. Key Features Explained

### 🎯 Resume ATS Analyzer

You upload two PDFs:
1. Your resume
2. A job description

The AI:
1. Extracts text from both
2. Compares skills, experience, keywords
3. Returns a **match score** (0-100%)
4. Lists missing skills
5. Suggests interview prep talking points

### ⚡ Multi-Provider Benchmarks

You can compare three AI providers on the same prompt:
- **Gemini** (Google) — `gemini-2.0-flash`
- **Groq** (free API) — `llama-3.1-8b-instant`
- **Ollama** (local) — runs on your own machine

The benchmark shows:
- Response time (ms)
- Tokens used
- Cost in USD
- LLM-graded faithfulness score (did it actually answer the question correctly?)

### 🔀 Hybrid Search Mode

When the Router detects a query that needs both document knowledge AND web knowledge, it runs the RAG Agent and Web Agent **in parallel** (simultaneously), then combines their results in the Synthesizer.

### 🏗️ Visual Workflow Builder

A drag-and-drop interface (using **React Flow**) where you can build custom AI pipelines:
- Add nodes: `router`, `rag`, `web_search`, `memory`, `llm`, `evaluator`
- Connect them with arrows
- Save the pipeline configuration
- Run it on demand

### 🔥 Hot-Swappable Providers

You can change the LLM provider (Gemini → Groq → Ollama) from the Settings UI without restarting the server. The `/reload` endpoint reloads environment variables and resets the connection pool.

---

## 13. Technologies Used and Why

| Technology | Role | Why It Was Chosen |
|---|---|---|
| **Python 3.12** | Backend language | Best ecosystem for AI/ML libraries |
| **FastAPI** | Web framework | Async, fast, auto-generates Swagger docs |
| **LangChain** | AI toolkit | Simplifies connecting LLMs, embeddings, and retrievers |
| **LangGraph** | Agent orchestration | Lets you build complex multi-step AI workflows as graphs |
| **ChromaDB** | Vector database | Local, free, persistent, easy to use |
| **Google Gemini** | Main LLM + Embeddings | High quality, cost-effective Flash model |
| **Groq** | Alternative LLM | Free API, very fast inference |
| **Ollama** | Local LLM | Fully offline, no API costs |
| **Tavily** | Web search API | Built specifically for AI agents, structured results |
| **BM25 (rank-bm25)** | Keyword search | Proven algorithm, no neural network needed |
| **sentence-transformers** | Cross-encoder reranker | Open-source, runs on CPU, high quality |
| **pypdf** | PDF parsing | Pure Python, no native dependencies |
| **python-docx** | DOCX parsing | Standard library for Word files |
| **Next.js 15** | Frontend framework | Server-side rendering, file-based routing |
| **React 19** | UI library | Component-based, reactive |
| **TypeScript** | Frontend language | Type safety prevents runtime bugs |
| **Tailwind CSS** | Styling | Utility-first, fast to build UI |
| **React Flow** | Visual workflow builder | Drag-and-drop graph UI |
| **Zustand** | State management | Lightweight alternative to Redux |
| **Docker** | Containerization | Run the backend anywhere consistently |

---

## 14. Complete File Map

```
RAG2/
│
├── 📄 .env                     # Your secret API keys (never commit this!)
├── 📄 .env.example             # Template showing what keys are needed
├── 📄 requirements.txt         # Python dependencies
├── 📄 Dockerfile               # How to build the backend into a Docker container
├── 📄 docker-compose.yml       # One command to run everything with Docker
│
├── 📂 app/                     # PYTHON BACKEND
│   │
│   ├── 📂 agents/              # The AI agents (the "brains")
│   │   ├── graph.py            # LangGraph: assembles all agents into a pipeline
│   │   ├── router.py           # Decides which agent to use for each query
│   │   ├── rag_agent.py        # Retrieves from your documents
│   │   ├── web_agent.py        # Searches the internet via Tavily
│   │   ├── memory_agent.py     # Uses conversation history
│   │   └── synthesizer.py      # Writes the final answer with citations
│   │
│   ├── 📂 api/
│   │   └── main.py             # FastAPI: all HTTP endpoints (/chat, /upload, etc.)
│   │
│   ├── 📂 rag/                 # The retrieval system
│   │   ├── document_processor.py  # Parses PDF/DOCX/TXT and splits into chunks
│   │   ├── embeddings.py          # Converts text ↔ vectors (numbers)
│   │   ├── vector_store.py        # ChromaDB interface for documents
│   │   ├── memory_store.py        # ChromaDB interface for long-term memories
│   │   ├── retriever.py           # Hybrid search: Semantic + BM25 + RRF
│   │   └── reranker.py            # Cross-encoder: picks the best 5 from top 30
│   │
│   ├── 📂 models/
│   │   └── schemas.py          # Pydantic data models (AgentState, ChatMessage, etc.)
│   │
│   ├── 📂 services/
│   │   └── workflow_executor.py   # Runs custom DAG workflows
│   │
│   └── 📂 utils/
│       ├── config.py           # Reads environment variables from .env
│       ├── llm_factory.py      # Builds the right LLM (Gemini/Groq/Ollama)
│       ├── long_term_memory.py # Extracts facts from conversations in background
│       ├── logger.py           # Structured JSON logging with latency tracking
│       └── cost.py             # Calculates API cost in USD
│
├── 📂 frontend/                # NEXT.JS FRONTEND
│   └── src/
│       ├── 📂 app/             # Pages (file-based routing)
│       │   ├── page.tsx        # Home/Dashboard
│       │   ├── chat/           # Chat interface
│       │   ├── documents/      # Document management
│       │   ├── benchmarks/     # LLM benchmark comparison
│       │   ├── resume/         # ATS resume analyzer
│       │   ├── workflow/       # Visual pipeline builder
│       │   ├── analytics/      # Usage statistics
│       │   └── settings/       # Provider configuration
│       │
│       ├── 📂 components/      # Reusable React UI components
│       ├── 📂 services/
│       │   └── api.ts          # All HTTP calls to the backend
│       ├── 📂 store/           # Zustand state management
│       └── 📂 types/           # TypeScript type definitions
│
├── 📂 chroma_db/               # ChromaDB data (auto-created, don't commit)
├── 📂 data/                    # Uploaded documents (temporary storage)
├── 📂 tests/                   # Pytest unit and integration tests
└── 📂 docs/                    # Additional documentation
```

---

## 15. How a Single Chat Message Flows Through the System

Let's trace exactly what happens when you type:

> *"What does our Q3 report say about hiring, and what are the latest industry trends?"*

This is a **hybrid** query — it asks about a document AND current trends.

### Step 1: Frontend sends the request
```
POST http://localhost:8000/chat
{
  "query": "What does our Q3 report say about hiring...",
  "session_id": "abc123"
}
```

### Step 2: FastAPI receives and validates
- Validates the request shape (is it valid JSON? Does it have a query?)
- Generates a unique `request_id` for logging
- Calls `orchestrator.run(query=..., session_id=...)`

### Step 3: LangGraph starts
- Builds initial `GraphState` with the query + conversation history

### Step 4: Memory Retriever Node
- Searches `long_term_memories` ChromaDB collection
- Finds: *"User prefers bullet-point answers"* (from a previous session)
- Adds this to state as `retrieved_memories`

### Step 5: Router Node
- Counts documents in knowledge base → 47 chunks found
- Asks Gemini: *"Route this query"*
- Gemini returns: `{"agent": "hybrid", "reasoning": "Query references 'Q3 report' (doc) and 'latest trends' (web)", "confidence": 0.92}`
- Sets `agent_type = "hybrid"` → will run BOTH rag_node and web_node

### Step 6: RAG Node + Web Node (run in parallel)

**RAG Node:**
- Semantic search: finds 30 chunks about "hiring" from Q3_Report.pdf
- BM25 search: finds 30 chunks matching keywords "Q3", "hiring"
- RRF: merges lists → top 30
- Cross-encoder: reranks → top 5 most relevant chunks
- Stores chunks in `retrieved_chunks` and `reranked_chunks`

**Web Node (simultaneously):**
- Calls Tavily: `search("latest industry hiring trends 2026")`
- Gets 8 web results with titles, URLs, and content
- Stores in `web_results`

### Step 7: Synthesizer Node
- Builds context block:
  ```
  ### RELEVANT LONG-TERM USER MEMORIES:
  - [PREFERENCE] User prefers bullet-point answers
  
  ### UPLOADED DOCUMENTS:
  Document Chunk 1 - Source: Q3_Report.pdf, Page 7
  Content: "Hiring goals include expanding the engineering team by 30%..."
  ...
  
  ### WEB SEARCH RESULTS:
  Web Source 1 - Title: Tech Hiring Trends 2026
  URL: https://example.com/hiring-trends
  Content: "AI skills are increasingly demanded..."
  ```
- Sends full context + question to Gemini
- Gemini writes a comprehensive answer with citations:
  ```
  ## Q3 Hiring Goals
  - Engineering team expansion: **+30%** [Source: Q3_Report.pdf, Page 7]
  - Open roles in ML and Backend [Source: Q3_Report.pdf, Page 9]
  
  ## Current Industry Trends
  - AI skills are the most sought-after [Source: https://example.com/hiring-trends]
  ```

### Step 8: Formatter Node
- Strips extra whitespace
- Deduplicates citations
- Calculates total latency: `routing: 800ms + rag: 1200ms + web: 600ms + synthesis: 2100ms = 4700ms`
- Appends final trace entry: *"✅ Pipeline complete | Agent: hybrid | Sources: 5 | Total: 4700ms"*

### Step 9: Back to FastAPI
- Saves conversation to session memory
- Triggers background long-term memory extraction
- Returns JSON response:

```json
{
  "answer": "## Q3 Hiring Goals\n- Engineering team...",
  "sources": [
    {"document": "Q3_Report.pdf", "page": 7},
    {"document": "Tech Hiring Trends 2026", "chunk_id": "https://..."}
  ],
  "agent_type": "hybrid",
  "latency_ms": {"routing": 800, "rag": 1200, "total": 4700},
  "routing_trace": [
    "🧠 Long-Term Memory: found 1 relevant memory",
    "⏳ Router received query (67 chars)",
    "📚 Knowledge base: 47 chunks | Conversation history: no",
    "→ Route: **Hybrid Workflow 🔀** | Confidence: 92%",
    "📚 RAG Agent: retrieved 30 chunks, reranked to top 5",
    "🌐 Web Search Agent: found 8 web results",
    "✨ Response Synthesizer: answer generated with 5 source(s)",
    "✅ Pipeline complete | Agent: hybrid | Sources: 5 | Total: 4700ms"
  ]
}
```

### Step 10: Frontend displays the answer
- Renders the markdown answer
- Shows citations as clickable chips
- Shows the routing trace as a collapsible "How did I get this answer?" panel

---

## 🎉 Summary

This project is an **enterprise-grade AI assistant** that:

1. **Stores your documents** as mathematical representations in a vector database
2. **Finds relevant passages** using a 3-stage hybrid search (semantic + keyword + reranking)  
3. **Routes queries intelligently** using an AI-powered classifier
4. **Searches the web** when needed for real-time information
5. **Remembers your conversations** both short-term and long-term
6. **Generates grounded answers** with exact citations back to sources
7. **Compares AI providers** side by side for quality and cost
8. **Analyzes resumes** against job descriptions
9. **Lets you build** custom AI pipelines visually

The key insight is that instead of asking an AI to "know everything," this system teaches it to **find the right information first, then answer** — making responses far more accurate and trustworthy.

---

*Generated: June 2026 | Project: TalentMind AI / Enterprise Agentic RAG Assistant*
