# ============================================================
# Enterprise Agentic RAG Assistant — Dockerfile
# Multi-stage build: builder + slim production image
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (layer caching)
COPY requirements.txt .

# Install dependencies into a prefix directory for copying
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Production image ─────────────────────────────────
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="Enterprise Agentic RAG Assistant"
LABEL org.opencontainers.image.description="Multi-agent RAG platform with LangGraph, ChromaDB, and Gemini"
LABEL org.opencontainers.image.version="1.0.0"

# Install runtime system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r raguser && useradd -r -g raguser raguser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/
COPY .env.example .env.example

# Create required directories with correct permissions
RUN mkdir -p /app/data /app/chroma_db /app/logs \
    && chown -R raguser:raguser /app

# Switch to non-root user
USER raguser

# Expose ports
EXPOSE 8000 8501

# Health check for the FastAPI server
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run FastAPI (overridden by docker-compose for Streamlit)
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
