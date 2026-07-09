from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter

from app.api.state import _document_registry, _retrieval_metrics
from app.utils.config import get_settings

router = APIRouter(tags=["Analytics"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.get(
    "/analytics",
    summary="Aggregated retrieval analytics",
)
async def get_analytics() -> dict:
    """
    Return aggregated analytics: latency statistics, source usage,
    agent routing distribution, and retrieval pipeline funnel stats.
    """
    if not _retrieval_metrics:
        return {"message": "No queries processed yet.", "metrics": []}

    total_queries = len(_retrieval_metrics)
    avg_total_ms = sum(m.total_latency_ms for m in _retrieval_metrics) / total_queries
    avg_retrieval_ms = sum(m.retrieval_latency_ms for m in _retrieval_metrics) / total_queries
    avg_vector_ms = sum(m.vector_search_latency_ms for m in _retrieval_metrics) / total_queries
    avg_bm25_ms = sum(m.bm25_search_latency_ms for m in _retrieval_metrics) / total_queries
    avg_rrf_ms = sum(m.rrf_fusion_latency_ms for m in _retrieval_metrics) / total_queries
    avg_reranking_ms = sum(
        m.reranking_latency_ms or 0.0 for m in _retrieval_metrics
    ) / total_queries
    avg_llm_ms = sum(
        m.llm_latency_ms or 0.0 for m in _retrieval_metrics
    ) / total_queries

    agent_counts: dict[str, int] = {}
    all_sources: list[str] = []
    for m in _retrieval_metrics:
        agent_counts[m.agent_type.value] = agent_counts.get(m.agent_type.value, 0) + 1
        all_sources.extend(m.sources_used)

    source_freq: dict[str, int] = {}
    for src in all_sources:
        source_freq[src] = source_freq.get(src, 0) + 1

    # Retrieval funnel averages
    avg_vector_hits = sum(m.num_vector_results for m in _retrieval_metrics) / total_queries
    avg_bm25_hits = sum(m.num_bm25_results for m in _retrieval_metrics) / total_queries
    avg_retrieved = sum(m.num_retrieved for m in _retrieval_metrics) / total_queries
    avg_reranked = sum(m.num_reranked for m in _retrieval_metrics) / total_queries

    # Daily query, token and cost trends
    today_date = datetime.now(timezone.utc).date()
    
    daily_stats = {}
    for m in _retrieval_metrics:
        d_str = m.timestamp.strftime("%Y-%m-%d") if isinstance(m.timestamp, datetime) else str(m.timestamp)[:10]
        if d_str not in daily_stats:
            daily_stats[d_str] = {"queries": 0, "tokens": 0, "cost": 0.0}
        daily_stats[d_str]["queries"] += 1
        daily_stats[d_str]["tokens"] += getattr(m, "total_tokens", 0)
        daily_stats[d_str]["cost"] += getattr(m, "cost_usd", 0.0)
    
    sorted_daily = sorted(daily_stats.items())
    daily_trend = [
        {
            "date": k, 
            "queries": v["queries"], 
            "tokens": v["tokens"], 
            "cost": round(v["cost"], 6)
        } for k, v in sorted_daily
    ]

    queries_today = daily_stats.get(today_date.strftime("%Y-%m-%d"), {}).get("queries", 0)

    total_prompt = sum(m.prompt_tokens for m in _retrieval_metrics)
    total_completion = sum(m.completion_tokens for m in _retrieval_metrics)
    total_tokens = sum(m.total_tokens for m in _retrieval_metrics)
    total_cost = sum(m.cost_usd for m in _retrieval_metrics)

    avg_prompt = total_prompt / total_queries
    avg_completion = total_completion / total_queries
    avg_total_tokens = total_tokens / total_queries
    avg_cost = total_cost / total_queries

    # Document chunk distribution
    doc_chunk_dist = {
        doc_rec.filename: doc_rec.num_chunks
        for doc_rec in _document_registry.values()
    }

    return {
        "total_queries": total_queries,
        "queries_today": queries_today,
        # ── Latency summary ──────────────────────────────────────
        "avg_total_latency_ms": round(avg_total_ms, 2),
        "avg_retrieval_latency_ms": round(avg_retrieval_ms, 2),
        "avg_vector_search_ms": round(avg_vector_ms, 2),
        "avg_bm25_search_ms": round(avg_bm25_ms, 2),
        "avg_rrf_fusion_ms": round(avg_rrf_ms, 2),
        "avg_reranking_ms": round(avg_reranking_ms, 2),
        "avg_llm_ms": round(avg_llm_ms, 2),
        # ── Token & Cost summary ─────────────────────────────────
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_prompt_tokens": round(avg_prompt, 2),
        "avg_completion_tokens": round(avg_completion, 2),
        "avg_total_tokens": round(avg_total_tokens, 2),
        "avg_cost_usd": round(avg_cost, 6),
        # ── Funnel summary ───────────────────────────────────────
        "avg_vector_hits": round(avg_vector_hits, 1),
        "avg_bm25_hits": round(avg_bm25_hits, 1),
        "avg_retrieved": round(avg_retrieved, 1),
        "avg_reranked": round(avg_reranked, 1),
        # ── Distribution ─────────────────────────────────────────
        "agent_distribution": agent_counts,
        "top_sources": sorted(source_freq.items(), key=lambda x: x[1], reverse=True)[:10],
        "document_chunk_distribution": doc_chunk_dist,
        "recent_metrics": [m.model_dump() for m in _retrieval_metrics[-20:]],
        "daily_trend": daily_trend,
    }


@router.get(
    "/retrieval-metrics",
    summary="Per-query retrieval pipeline metrics",
)
async def get_retrieval_metrics(limit: int = 50) -> dict:
    """
    Return detailed per-query retrieval pipeline metrics for the observability dashboard.
    """
    if not _retrieval_metrics:
        return {"message": "No queries processed yet.", "metrics": []}

    recent = _retrieval_metrics[-limit:]
    return {
        "total_logged": len(_retrieval_metrics),
        "returned": len(recent),
        "metrics": [m.model_dump() for m in recent],
    }


@router.get(
    "/analytics/extended",
    summary="Extended analytics: provider, memory, document, and retrieval-quality metrics",
)
async def get_extended_analytics() -> dict:
    """
    Return additional analytic dimensions not in /analytics:
    - Provider usage distribution (derived from agent + LLM config)
    - Memory metrics (total stored, by type, growth over time)
    - Document metrics (total docs, total chunks, file-type breakdown)
    - Retrieval success rate (queries where chunks > 0)
    - Query length distribution
    - Hourly query volume heatmap
    - Session engagement depth
    """
    from app.memory.memory_store import get_memory_store

    out: dict = {}

    # ── 1. Provider usage ─────────────────────────────────────────────────────
    llm_provider = settings.llm_provider.lower()
    total_q = len(_retrieval_metrics)
    out["llm_provider"] = llm_provider
    out["total_queries"] = total_q

    out["provider_usage"] = {llm_provider: total_q} if total_q else {}

    # ── 2. Agent usage ────────────────────────────────────────────────────────
    agent_counts: dict[str, int] = {}
    for m in _retrieval_metrics:
        k = m.agent_type.value
        agent_counts[k] = agent_counts.get(k, 0) + 1
    out["agent_distribution"] = agent_counts
    out["most_used_agent"] = max(agent_counts, key=agent_counts.get) if agent_counts else "N/A"

    # ── 3. Latency summary ────────────────────────────────────────────────────
    if total_q:
        out["avg_total_latency_ms"]   = round(sum(m.total_latency_ms for m in _retrieval_metrics) / total_q, 2)
        out["avg_retrieval_ms"]       = round(sum(m.retrieval_latency_ms for m in _retrieval_metrics) / total_q, 2)
        out["avg_reranking_ms"]       = round(sum(m.reranking_latency_ms or 0 for m in _retrieval_metrics) / total_q, 2)
        out["avg_llm_ms"]             = round(sum(m.llm_latency_ms or 0 for m in _retrieval_metrics) / total_q, 2)
        out["p95_total_latency_ms"]   = 0.0
        sorted_lats = sorted(m.total_latency_ms for m in _retrieval_metrics)
        if sorted_lats:
            idx = int(0.95 * len(sorted_lats))
            out["p95_total_latency_ms"] = round(sorted_lats[min(idx, len(sorted_lats)-1)], 2)
    else:
        out.update({k: 0.0 for k in (
            "avg_total_latency_ms", "avg_retrieval_ms",
            "avg_reranking_ms", "avg_llm_ms", "p95_total_latency_ms"
        )})

    # ── 4. Retrieval quality metrics ──────────────────────────────────────────
    if total_q:
        successful = sum(1 for m in _retrieval_metrics if m.num_reranked > 0)
        out["retrieval_success_rate"]  = round(successful / total_q * 100, 1)
        out["avg_chunks_retrieved"]    = round(sum(m.num_retrieved for m in _retrieval_metrics) / total_q, 1)
        out["avg_chunks_reranked"]     = round(sum(m.num_reranked for m in _retrieval_metrics) / total_q, 1)
        out["avg_vector_hits"]         = round(sum(m.num_vector_results for m in _retrieval_metrics) / total_q, 1)
        out["avg_bm25_hits"]           = round(sum(m.num_bm25_results for m in _retrieval_metrics) / total_q, 1)
    else:
        out.update({k: 0.0 for k in (
            "retrieval_success_rate", "avg_chunks_retrieved",
            "avg_chunks_reranked", "avg_vector_hits", "avg_bm25_hits"
        )})

    # ── 5. Token & cost ───────────────────────────────────────────────────────
    total_prompt     = sum(m.prompt_tokens for m in _retrieval_metrics)
    total_completion = sum(m.completion_tokens for m in _retrieval_metrics)
    total_tokens     = sum(m.total_tokens for m in _retrieval_metrics)
    total_cost       = sum(m.cost_usd for m in _retrieval_metrics)
    out["total_prompt_tokens"]     = total_prompt
    out["total_completion_tokens"] = total_completion
    out["total_tokens"]            = total_tokens
    out["total_cost_usd"]          = round(total_cost, 6)
    out["avg_cost_usd"]            = round(total_cost / total_q, 8) if total_q else 0.0
    out["avg_total_tokens"]        = round(total_tokens / total_q, 1) if total_q else 0.0

    # ── 6. Query length distribution ─────────────────────────────────────────
    if _retrieval_metrics:
        qlens = [m.query_length for m in _retrieval_metrics]
        out["avg_query_length"]  = round(sum(qlens) / len(qlens), 1)
        out["max_query_length"]  = max(qlens)
        out["min_query_length"]  = min(qlens)
        out["query_length_distribution"] = {
            "short (<50 chars)":   sum(1 for l in qlens if l < 50),
            "medium (50–150)":     sum(1 for l in qlens if 50 <= l < 150),
            "long (>150 chars)":   sum(1 for l in qlens if l >= 150),
        }
    else:
        out["avg_query_length"] = out["max_query_length"] = out["min_query_length"] = 0
        out["query_length_distribution"] = {}

    # ── 7. Hourly query volume heatmap (0–23) ────────────────────────────────
    hourly: dict[int, int] = {h: 0 for h in range(24)}
    for m in _retrieval_metrics:
        try:
            h = int(m.timestamp.strftime("%H"))
            hourly[h] = hourly.get(h, 0) + 1
        except Exception:
            pass
    out["hourly_query_counts"] = [{"hour": h, "count": hourly[h]} for h in range(24)]

    # ── 8. Daily trend ────────────────────────────────────────────────────────
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_stats: dict[str, dict] = {}
    for m in _retrieval_metrics:
        d = m.timestamp.strftime("%Y-%m-%d") if isinstance(m.timestamp, datetime) else str(m.timestamp)[:10]
        if d not in daily_stats:
            daily_stats[d] = {"queries": 0, "tokens": 0, "cost": 0.0, "latency_sum": 0.0}
        daily_stats[d]["queries"]     += 1
        daily_stats[d]["tokens"]      += m.total_tokens
        daily_stats[d]["cost"]        += m.cost_usd
        daily_stats[d]["latency_sum"] += m.total_latency_ms
    out["daily_trend"] = [
        {
            "date":        d,
            "queries":     v["queries"],
            "tokens":      v["tokens"],
            "cost":        round(v["cost"], 6),
            "avg_latency": round(v["latency_sum"] / v["queries"], 1) if v["queries"] else 0.0,
        }
        for d, v in sorted(daily_stats.items())
    ]
    out["queries_today"] = daily_stats.get(today_str, {}).get("queries", 0)

    # ── 9. Top referenced sources ─────────────────────────────────────────────
    source_freq: dict[str, int] = {}
    for m in _retrieval_metrics:
        for src in m.sources_used:
            source_freq[src] = source_freq.get(src, 0) + 1
    out["top_sources"] = sorted(source_freq.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── 10. Memory memories ───────────────────────────────────────────────────
    try:
        store   = get_memory_store()
        all_mem = store.list_all_memories()
        mem_by_type: dict[str, int] = {}
        for mem in all_mem:
            t = mem.get("memory_type", "unknown")
            mem_by_type[t] = mem_by_type.get(t, 0) + 1
        out["memory_metrics"] = {
            "total_memories":    len(all_mem),
            "by_type":           mem_by_type,
            "facts":             mem_by_type.get("fact", 0),
            "preferences":       mem_by_type.get("preference", 0),
            "summaries":         mem_by_type.get("summary", 0),
        }
    except Exception as exc:
        logger.warning(f"Failed to load memory metrics: {exc}")
        out["memory_metrics"] = {"total_memories": 0, "by_type": {}, "facts": 0, "preferences": 0, "summaries": 0}

    # ── 11. Document metrics ──────────────────────────────────────────────────
    docs      = list(_document_registry.values())
    file_type_dist: dict[str, int] = {}
    total_chunks  = 0
    total_pages   = 0
    for doc in docs:
        ft = doc.file_type.value if hasattr(doc.file_type, "value") else str(doc.file_type)
        file_type_dist[ft] = file_type_dist.get(ft, 0) + 1
        total_chunks += doc.num_chunks
        total_pages  += doc.num_pages or 0
    out["document_metrics"] = {
        "total_documents":       len(docs),
        "total_chunks_indexed":  total_chunks,
        "total_pages_indexed":   total_pages,
        "avg_chunks_per_doc":    round(total_chunks / len(docs), 1) if docs else 0.0,
        "file_type_distribution": file_type_dist,
        "document_chunk_distribution": {
            d.filename: d.num_chunks for d in docs
        },
    }

    # ── 12. Recent metrics table (last 20) ────────────────────────────────────
    out["recent_metrics"] = [m.model_dump() for m in _retrieval_metrics[-20:]]

    return out
