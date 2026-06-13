# Enterprise Agentic RAG Assistant / TalentMind AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![Next.js](https://img.shields.io/badge/Next.js-15.1-000000?style=for-the-badge&logo=nextdotjs)
![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=for-the-badge&logo=tailwindcss)
![LangGraph](https://img.shields.io/badge/LangGraph-0.4-FF6B35?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.0-4A90D9?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

**A production-ready multi-agent Retrieval-Augmented Generation (RAG) and Career Intelligence platform.**

Upload documents → Ask questions → Get cited answers from a fleet of intelligent agents, run provider benchmarks, build visual graphs, or analyze resumes.

</div>

---

## Architecture

```
┌──────────────────────────────────────┐
│       Next.js Frontend (Port 3000)   │
│ Dashboard │ Chat │ Workflows │ ATS   │
└──────────────────┬───────────────────┘
                   │
                   │ HTTP Requests
                   ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Backend (Port 8000)                            │
│   /chat   │   /upload   │   /documents   │   /health   │   /analytics   │   /reload   │
│   /analyze-resume    │    /memories    │    /benchmark    │    /workflows (CRUD)      │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────▼──────────────────────────────────────────┐
│                             LangGraph Orchestrator                                │
│                                                                                   │
│ START ──► [Memory Retriever Node] ──► [Router Node]                               │
│                                            │                                      │
│                ┌───────────────────────────┼───────────────────────────┐          │
│                ▼                           ▼                           ▼          │
│          [RAG Node]                  [Web Node]                  [Memory Node]    │
│          (ChromaDB + BM25)           (Tavily Search)             (Chat History)   │
│                │                           │                           │          │
│                └───────────────────────────┼───────────────────────────┘          │
│                                            ▼                                      │
│                                   [Synthesizer Node]                              │
│                                            │                                      │
│                                    [Formatter Node] ──► END                       │
└────────────────────────────────────────┬──────────────────────────────────────────┘
                                         │
                                  ┌──────┴──────┐
                                  ▼             ▼
                           ┌─────────────┐┌─────────────┐
                           │  ChromaDB   ││  ChromaDB   │
                           │(Vector Store││(Long-Term   │
                           │  Collection)││Memory Coll.)│
                           └─────────────┘└─────────────┘

RAG Agent Ingestion Pipeline:
  Document Upload
       │
  ┌────▼────┐     ┌──────────────┐     ┌─────────────┐
  │Document │────►│  ChromaDB    │     │   BM25      │
  │Processor│     │  (Semantic)  │     │  (Keyword)  │
  └─────────┘     └──────┬───────┘     └──────┬──────┘
                         │    RRF Fusion        │
                         └──────────┬───────────┘
                                    │ Top 20 chunks
                          ┌─────────▼──────────┐
                          │  Cross-Encoder      │
                          │  Reranker           │
                          └─────────┬──────────┘
                                    │ Top 5 chunks
                          ┌─────────▼──────────┐
                          │  Gemini LLM         │
                          │  (Answer + Cites)   │
                          └────────────────────┘
```

---

## Features

| Feature | Implementation |
|---|---|
| **Next.js UI Portal** | Modern TypeScript React interface with glassmorphic styling, Lucide icons, and Montserrat typography |
| **Career ATS Analyzer** | PDF Resume vs. Job Description (JD) comparison with match scores, skill gap analysis, and prep recommendations |
| **Visual Workflow Builder** | Dynamic custom DAG pipelines built via React Flow (nodes: router, rag, memory, web_search, llm, evaluator) |
| **Multi-Provider Benchmarks** | Concurrent prompt execution on Ollama, Groq, and Gemini, assessing speed, cost, and LLM-graded faithfulness |
| **Long-Term Memory** | Background thread extraction of conversation facts/preferences stored in a dedicated ChromaDB collection |
| **Hot-Swappable Providers** | Control Center to switch LLM settings (Ollama / Groq / Gemini) and refresh the active backend connection pool live |
| **Document Processing** | PDF, DOCX, TXT parsing, recursive character chunking, and page-level citation metadata mapping |
| **Embeddings & DB** | Gemini Embeddings paired with Cosine similarity distance in a persistent local ChromaDB instance |
| **Hybrid Search & Rerank** | Reciprocal Rank Fusion (RRF) combining semantic + BM25 keyword ranks, reranked by `ms-marco-MiniLM-L6-v2` |
| **LangGraph Orchestrator** | Typed state routing, parallel branching, conditional transitions, and formatting nodes |
| **FastAPI Backend** | Robust validation schemas, request-ID tracing middleware, JSON structured logging, and Swagger docs |

---

## Quick Start

### Option 1: Docker (FastAPI Backend)

```bash
# 1. Clone and enter directory
git clone <repo> && cd enterprise-rag-assistant

# 2. Create .env with your API keys
cp .env.example .env
# Edit .env and fill in GOOGLE_API_KEY and TAVILY_API_KEY

# 3. Launch backend
docker compose up

# 4. Open in browser
# API documentation:        http://localhost:8000/docs
```

### Option 2: Local Development (FastAPI & Next.js UI)

#### 1. Setup Backend environment
```bash
# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Configure environment keys
cp .env.example .env
# Edit .env and fill in API keys
```

#### 2. Start Services

* **FastAPI Backend (Terminal 1)**:
  ```bash
  python -m uvicorn app.api.main:app --reload --port 8000
  ```

* **Next.js React Frontend (Terminal 2)**:
  ```bash
  cd frontend
  npm install
  npm run dev
  # Next.js UI: http://localhost:3000
  ```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | ✅ | — | Google Gemini API key |
| `TAVILY_API_KEY` | ✅ | — | Tavily web search API key |
| `GROQ_API_KEY` | | — | Optional Groq provider API key |
| `LLM_PROVIDER` | | `gemini` | Active LLM endpoint (`gemini`, `groq`, `ollama`) |
| `EMBEDDING_PROVIDER`| | `gemini` | Active embedding endpoint (`gemini`, `local`, `ollama`) |
| `GEMINI_MODEL` | | `gemini-2.0-flash` | Gemini generation model version |
| `EMBEDDING_MODEL` | | `models/gemini-embedding-001` | Semantic embedding model version |
| `CHROMA_PERSIST_DIR` | | `./chroma_db` | ChromaDB persistence path |
| `API_HOST` | | `0.0.0.0` | FastAPI host interface |
| `API_PORT` | | `8000` | FastAPI port interface |

---

## API Reference

### POST `/chat`
Submit a question and get routed answers with citations.
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are our hiring goals?", "session_id": "session_123"}'
```

### POST `/analyze-resume`
Extract scores, skill gaps, and interview prep suggestions by comparing a PDF Resume with a PDF Job Description.
```bash
curl -X POST http://localhost:8000/analyze-resume \
  -F "resume=@my_resume.pdf" \
  -F "jd=@job_description.pdf"
```

### POST `/benchmark`
Concurrent prompt assessment across all configured LLM providers.
```bash
curl -X POST "http://localhost:8000/benchmark?query=Explain%20quantization&use_rag=true"
```

### POST `/workflows`
Save a visual DAG workflow configuration.
```json
{
  "workflow_id": "flow_123",
  "name": "Custom RAG Eval",
  "nodes": [{"id": "n1", "type": "rag", "config": {"top_k": 3}}],
  "edges": []
}
```

### POST `/reload`
Reload `.env` variables and reset database connectors without server reboot.

---

## Project Structure

```
enterprise-rag-assistant/
├── app/
│   ├── agents/
│   │   ├── graph.py            # LangGraph pipeline definition
│   │   ├── rag_agent.py        # Semantic + Keyword RAG Agent
│   │   ├── web_agent.py        # Tavily Search Agent
│   │   ├── memory_agent.py     # Conversation memory agent
│   │   ├── synthesizer.py      # LLM response aggregator
│   │   └── router.py           # Classifier router
│   ├── api/
│   │   └── main.py             # FastAPI API gateway and endpoints
│   ├── rag/
│   │   ├── document_processor.py # PDF/DOCX/TXT chunk splitters
│   │   ├── vector_store.py      # ChromaDB interface
│   │   └── memory_store.py      # Long-term memories collection store
│   └── services/
│       └── workflow_executor.py # Topological sort and custom DAG runner
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages: chat, benchmarks, ATS, workflows, logs
│   │   ├── components/         # React layout and visual DAG node widgets
│   │   ├── store/              # Zustand settings and workflow state management
│   │   └── types/              # TypeScript typings
│   ├── package.json
│   └── tailwind.config.ts
├── tests/                      # Pytest unit + integration suites
├── Dockerfile                  # Multi-stage production build script
├── docker-compose.yml          # One-command server orchestrations
└── README.md
```

---

## Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v
```

---

## Future Improvements

- [x] **Evaluation pipeline** — Integrated LLM faithfulness scoring (Benchmarks)
- [x] **Re-indexing** — Hot reprocessing API for existing documents
- [ ] **Persistent document registry** — Replace in-memory dictionaries with SQLite/PostgreSQL
- [ ] **Streaming responses** — Server-Sent Events (SSE) token flow UI rendering
- [ ] **Multi-tenancy** — Secure workspace isolation and user authentication

---

## License

MIT — see [LICENSE](LICENSE)
