# Enterprise Agentic RAG Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.4-FF6B35?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45-FF4B4B?style=for-the-badge&logo=streamlit)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.0-4A90D9?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

**A production-ready multi-agent Retrieval-Augmented Generation (RAG) platform.**

Upload documents → Ask questions → Get cited answers from a fleet of intelligent agents.

</div>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Port 8501)                      │
│        Dashboard │ Chat (with citations) │ Analytics             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend (Port 8000)                   │
│   POST /upload  │  POST /chat  │  GET /documents  │  GET /health│
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                  LangGraph Orchestrator                          │
│                                                                  │
│  START → [Router Agent] ──┬──► [RAG Agent]    ──┐               │
│                           ├──► [Web Agent]    ──┤──► [Formatter]│
│                           └──► [Memory Agent] ──┘      │        │
│                                                       END        │
└──────────────────────────────────────────────────────────────────┘

RAG Pipeline:
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
| **Document Processing** | PDF, DOCX, TXT with page-level metadata |
| **Embeddings** | Google Gemini `gemini-embedding-001` with batch + retry |
| **Vector Database** | ChromaDB with cosine similarity, persistent storage |
| **Keyword Search** | BM25Okapi for exact-match retrieval |
| **Hybrid Retrieval** | Reciprocal Rank Fusion (RRF) merging semantic + BM25 |
| **Reranking** | `cross-encoder/ms-marco-MiniLM-L6-v2` (Top 20 → Top 5) |
| **RAG Agent** | Retrieval + reranking + Gemini generation + citations |
| **Web Search Agent** | Tavily search + Gemini summarisation |
| **Memory Agent** | Per-session conversation history with follow-up support |
| **Router Agent** | Gemini-powered JSON classification with fallback rules |
| **LangGraph Workflow** | Typed state, conditional edges, formatter node |
| **FastAPI Backend** | 6 endpoints, Pydantic models, Swagger docs |
| **Streamlit UI** | Dashboard, Chat with badges, Analytics with Plotly |
| **Structured Logging** | JSON logs with request-ID tracing and latency |
| **Docker** | Multi-stage build, docker-compose one-command deploy |
| **Tests** | Unit + integration tests with mocked Gemini responses |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone and enter directory
git clone <repo> && cd enterprise-rag-assistant

# 2. Create .env with your API keys
cp .env.example .env
# Edit .env and fill in GOOGLE_API_KEY and TAVILY_API_KEY

# 3. Launch everything
docker compose up

# 4. Open in browser
# API docs:  http://localhost:8000/docs
# UI:        http://localhost:8501
```

### Option 2: Local Development

```bash
# 1. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
cp .env.example .env
# Edit .env and fill in API keys

# 4. Start FastAPI backend
python -m uvicorn app.api.main:app --reload --port 8000

# 5. Start Streamlit (new terminal)
streamlit run app/ui/streamlit_app.py --server.port 8501
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | ✅ | — | Google Gemini API key |
| `TAVILY_API_KEY` | ✅ | — | Tavily web search API key |
| `GEMINI_MODEL` | | `gemini-2.0-flash` | Generation model |
| `EMBEDDING_MODEL` | | `models/gemini-embedding-001` | Embedding model |
| `CHUNK_SIZE` | | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | | `200` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | | `20` | Chunks retrieved before reranking |
| `RERANKER_TOP_K` | | `5` | Chunks after reranking |
| `MAX_MEMORY_TURNS` | | `10` | Conversation turns to remember |
| `CHROMA_PERSIST_DIR` | | `./chroma_db` | ChromaDB storage path |
| `API_HOST` | | `0.0.0.0` | FastAPI host |
| `API_PORT` | | `8000` | FastAPI port |
| `LOG_LEVEL` | | `INFO` | Logging level |

---

## API Reference

### POST /upload
Upload and index a document.

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@report.pdf"
```

```json
{
  "document_id": "a1b2c3d4",
  "filename": "report.pdf",
  "num_chunks": 47,
  "num_pages": 12,
  "status": "indexed",
  "message": "Successfully indexed 47 chunks from 'report.pdf'."
}
```

### POST /chat
Ask a question.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Q3 revenue forecast?", "session_id": "abc123"}'
```

```json
{
  "answer": "Based on the Q3 report [Source: report.pdf, Page 8], the revenue forecast is...",
  "sources": [
    {"document": "report.pdf", "page": 8, "relevance_score": 0.94}
  ],
  "agent_used": "rag",
  "session_id": "abc123",
  "latency_ms": {"retrieval": 210.5, "reranking": 89.3, "llm": 1240.7, "total": 1560.5}
}
```

### GET /documents
List all indexed documents.

### DELETE /documents/{id}
Remove a document and its embeddings.

### GET /health
System health check.

### GET /analytics
Retrieval latency, agent distribution, top sources.

---

## Project Structure

```
enterprise-rag-assistant/
├── app/
│   ├── agents/
│   │   ├── graph.py          # LangGraph workflow
│   │   ├── rag_agent.py      # RAG pipeline agent
│   │   ├── web_agent.py      # Tavily web search agent
│   │   ├── memory_agent.py   # Conversation memory agent
│   │   └── router.py         # Query classification router
│   ├── rag/
│   │   ├── document_processor.py  # PDF/DOCX/TXT extraction
│   │   ├── embeddings.py          # Gemini embedding service
│   │   ├── vector_store.py        # ChromaDB wrapper
│   │   ├── retriever.py           # Hybrid BM25 + semantic retrieval
│   │   └── reranker.py            # Cross-encoder reranking
│   ├── api/
│   │   └── main.py           # FastAPI application
│   ├── ui/
│   │   └── streamlit_app.py  # Streamlit 3-page frontend
│   ├── models/
│   │   └── schemas.py        # All Pydantic models
│   └── utils/
│       ├── config.py         # Pydantic settings management
│       └── logger.py         # Structured JSON logging
├── tests/
│   ├── unit/
│   │   ├── test_document_processor.py
│   │   ├── test_retrieval.py
│   │   └── test_router.py
│   ├── integration/
│   │   └── test_api.py
│   └── conftest.py
├── data/                     # Uploaded documents (gitignored)
├── chroma_db/                # ChromaDB persistence (gitignored)
├── Dockerfile                # Multi-stage production build
├── docker-compose.yml        # One-command deployment
├── requirements.txt
├── pyproject.toml            # pytest configuration
├── .env.example
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

# With coverage
pytest --cov=app --cov-report=html
```

---

## Screenshots

| Dashboard | Chat | Analytics |
|---|---|---|
| *(Upload documents, view index status)* | *(Ask questions, see agent badge + citations)* | *(Latency charts, source frequency)* |

---

## Agent Routing Logic

```
Query arrives
     │
     ▼
Has "earlier", "you said", "before" + history?
     │ YES → Memory Agent
     │ NO
     ▼
Has "latest", "today", "current", "news"?
     │ YES → Web Search Agent
     │ NO
     ▼
Documents indexed?
     │ YES → RAG Agent
     │ NO  → Web Search Agent
```

The router uses Gemini for intelligent classification with a confidence score.
Falls back to keyword-based rules if LLM is unavailable.

---

## Future Improvements

- [ ] **Persistent document registry** — Replace in-memory dict with PostgreSQL/SQLite
- [ ] **Multi-tenancy** — User accounts and document namespacing
- [ ] **Streaming responses** — Server-Sent Events for real-time token streaming
- [ ] **FAISS hybrid** — Add FAISS as an alternative to ChromaDB for large corpora
- [ ] **Re-indexing** — Detect and re-process modified documents
- [ ] **Evaluation pipeline** — RAGAs metrics for retrieval quality tracking
- [ ] **Authentication** — JWT-based API security
- [ ] **Observability** — OpenTelemetry traces to Grafana/Jaeger
- [ ] **Query expansion** — HyDE (Hypothetical Document Embeddings) for better recall
- [ ] **Multi-modal** — Support image extraction from PDFs

---

## License

MIT — see [LICENSE](LICENSE)
