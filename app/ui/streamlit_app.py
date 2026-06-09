"""
Enterprise Agentic RAG Assistant
Streamlit frontend — three-page app: Dashboard, Chat, and Analytics.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page configuration (must be first Streamlit call) ─────────────────────────
st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API base URL ───────────────────────────────────────────────────────────────
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    /* ── Global fonts & colours ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Sidebar ── */
    .css-1d391kg { background: #0f172a; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* ── Main background ── */
    .stApp { background: #0a0f1e; color: #e2e8f0; }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* ── Chat message bubbles ── */
    .user-bubble {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        border-radius: 18px 18px 4px 18px;
        padding: 14px 18px;
        margin: 8px 0;
        margin-left: 20%;
        color: white;
        box-shadow: 0 4px 12px rgba(59,130,246,0.3);
    }
    .assistant-bubble {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 18px 18px 18px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        margin-right: 20%;
        color: #e2e8f0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }

    /* ── Citation pills ── */
    .citation-pill {
        display: inline-block;
        background: linear-gradient(135deg, #7c3aed, #4c1d95);
        color: white;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        margin: 2px;
        border: 1px solid #8b5cf6;
    }

    /* ── Agent badge ── */
    .agent-badge-rag  { background: #065f46; color: #6ee7b7; border: 1px solid #059669; }
    .agent-badge-web  { background: #1e3a5f; color: #7dd3fc; border: 1px solid #0284c7; }
    .agent-badge-memory { background: #4a1942; color: #f0abfc; border: 1px solid #a855f7; }
    .agent-badge-hybrid { background: #5b21b6; color: #ddd6fe; border: 1px solid #7c3aed; }
    .agent-badge {
        border-radius: 8px; padding: 2px 10px;
        font-size: 0.72rem; font-weight: 600;
        display: inline-block; margin-left: 8px;
    }

    /* ── Primary button ── */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white; border: none; border-radius: 10px;
        padding: 8px 24px; font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb, #1e40af);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(59,130,246,0.4);
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        border: 2px dashed #334155 !important;
        border-radius: 12px !important;
        background: #1e293b !important;
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.5rem; font-weight: 700;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }

    /* ── Status indicator ── */
    .status-dot {
        display: inline-block; width: 8px; height: 8px;
        border-radius: 50%; margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .status-dot.green { background: #10b981; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* ── Divider ── */
    hr { border-color: #1e293b !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ── API helpers ────────────────────────────────────────────────────────────────

def api_get(path: str, timeout: float = 10.0) -> dict[str, Any] | None:
    """Make a GET request to the FastAPI backend."""
    try:
        with httpx.Client(base_url=API_BASE, timeout=timeout) as client:
            r = client.get(path)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        st.error(f"API error ({path}): {exc}")
        return None


def api_post(
    path: str, json: dict | None = None, files=None, timeout: float = 120.0
) -> dict[str, Any] | None:
    """Make a POST request to the FastAPI backend."""
    try:
        with httpx.Client(base_url=API_BASE, timeout=timeout) as client:
            if files:
                r = client.post(path, files=files)
            else:
                r = client.post(path, json=json)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"API error: {detail}")
        return None
    except Exception as exc:
        st.error(f"Connection error: {exc}")
        return None


def api_delete(path: str, timeout: float = 30.0) -> dict[str, Any] | None:
    """Make a DELETE request to the FastAPI backend."""
    try:
        with httpx.Client(base_url=API_BASE, timeout=timeout) as client:
            r = client.delete(path)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        return None


# ── Session state initialisation ───────────────────────────────────────────────

def init_session_state() -> None:
    defaults = {
        "session_id": None,
        "chat_history": [],  # list[dict] with role, content, agent, sources, latency
        "page": "dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Sidebar navigation ─────────────────────────────────────────────────────────

def render_sidebar() -> str:
    """Render sidebar and return the selected page."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0;">
                <div style="font-size: 2.5rem;">🧠</div>
                <div style="font-size: 1.1rem; font-weight: 700; 
                     background: linear-gradient(135deg, #60a5fa, #a78bfa);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    Enterprise RAG
                </div>
                <div style="font-size: 0.7rem; color: #64748b;">Agentic Assistant v1.0</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Health status
        health = api_get("/health", timeout=3.0)
        if health:
            st.markdown(
                f'<span class="status-dot green"></span>'
                f'<span style="font-size:0.85rem;">API Online</span>',
                unsafe_allow_html=True,
            )
            st.caption(f"📚 {health.get('documents_indexed', 0)} chunks indexed")
        else:
            st.markdown(
                '<span class="status-dot" style="background:#ef4444;"></span>'
                '<span style="font-size:0.85rem;">API Offline</span>',
                unsafe_allow_html=True,
            )

        st.divider()

        pages = {
            "🏠 Dashboard": "dashboard",
            "💬 Chat": "chat",
            "🔀 Workflow": "workflow",
            "📊 Analytics": "analytics",
        }
        selected_label = st.radio(
            "Navigation",
            list(pages.keys()),
            label_visibility="collapsed",
        )
        page = pages[selected_label]

        st.divider()

        # Session info
        if st.session_state.session_id:
            st.caption(f"Session: `{st.session_state.session_id[:8]}…`")

        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.rerun()

        st.divider()

        # ── API Key reload ──────────────────────────────────
        with st.expander("🔑 Apply New API Key", expanded=False):
            st.caption(
                "After updating `GOOGLE_API_KEY` in your `.env` file, "
                "click below to reload without restarting the server."
            )
            if st.button("🔄 Reload Config", use_container_width=True, type="primary"):
                with st.spinner("Reloading…"):
                    result = api_post("/reload", json={}, timeout=30.0)
                if result and result.get("status") == "reloaded":
                    st.success(
                        f"✅ Reloaded! Model: `{result.get('gemini_model', '?')}`"
                    )
                elif result is None:
                    st.error("Reload failed — check server logs for details.")

    return page


# ── Page: Dashboard ───────────────────────────────────────────────────────────

def render_dashboard() -> None:
    st.markdown(
        '<div class="section-header">📂 Document Dashboard</div>',
        unsafe_allow_html=True,
    )

    # ── Upload section ─────────────────────────────────────────────────────────
    col1, col2 = st.columns([1.4, 1], gap="large")

    with col1:
        st.markdown("#### 📤 Upload Documents")
        uploaded = st.file_uploader(
            "Drop PDF, DOCX, or TXT files here",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded:
            if st.button("🚀 Index Documents", use_container_width=True):
                progress = st.progress(0)
                status_placeholder = st.empty()
                for i, f in enumerate(uploaded):
                    status_placeholder.info(f"Processing **{f.name}**…")
                    result = api_post(
                        "/upload",
                        files={"file": (f.name, f.getvalue(), f.type or "application/octet-stream")},
                        timeout=300.0,
                    )
                    if result:
                        st.success(
                            f"✅ **{f.name}** — {result['num_chunks']} chunks indexed"
                        )
                    progress.progress((i + 1) / len(uploaded))
                status_placeholder.empty()
                st.balloons()

    with col2:
        st.markdown("#### 🔑 Quick Stats")
        health = api_get("/health")
        if health:
            st.metric("Chunks Indexed", health.get("documents_indexed", 0))
            st.metric("LLM Model", health.get("llm_model", "—"))
            st.metric("Embedding Model", health.get("embedding_model", "—").split("/")[-1])

    st.divider()

    # ── Documents table ────────────────────────────────────────────────────────
    st.markdown("#### 📋 Indexed Documents")

    docs_resp = api_get("/documents")
    if not docs_resp or not docs_resp.get("documents"):
        st.info("No documents indexed yet. Upload files above to get started.")
        return

    docs = docs_resp["documents"]
    df = pd.DataFrame(
        [
            {
                "Document": d["filename"],
                "Type": d["file_type"].upper(),
                "Chunks": d["num_chunks"],
                "Pages": d.get("num_pages", "—"),
                "Size (KB)": round(d["file_size_bytes"] / 1024, 1),
                "Status": d["status"],
                "Indexed At": (
                    d["indexed_at"][:16].replace("T", " ") if d.get("indexed_at") else "—"
                ),
                "ID": d["document_id"],
            }
            for d in docs
        ]
    )

    st.dataframe(
        df.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    # Delete controls
    with st.expander("🗑️ Delete a Document"):
        doc_options = {d["filename"]: d["document_id"] for d in docs}
        selected_doc = st.selectbox("Select document to delete", list(doc_options.keys()))
        if st.button("Delete", type="secondary"):
            doc_id = doc_options[selected_doc]
            result = api_delete(f"/documents/{doc_id}")
            if result:
                st.success(f"✅ Deleted '{selected_doc}' ({result['chunks_deleted']} chunks removed)")
                st.rerun()


# ── Page: Chat ────────────────────────────────────────────────────────────────

def render_chat() -> None:
    st.markdown(
        '<div class="section-header">💬 Agentic Chat</div>',
        unsafe_allow_html=True,
    )

    # Settings bar
    with st.expander("⚙️ Chat Settings", expanded=False):
        use_web = st.toggle("Allow Web Search", value=True)
        st.caption(
            "When enabled, the router may use Tavily web search "
            "for queries requiring current information."
        )

    # ── Chat history ───────────────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                """
                <div style="text-align:center; padding: 3rem; color: #475569;">
                    <div style="font-size: 3rem;">🤖</div>
                    <div style="font-size: 1.1rem; font-weight: 600;">Ask anything about your documents</div>
                    <div style="font-size: 0.85rem; margin-top: 0.5rem;">
                        Upload documents on the Dashboard, then start chatting.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        for turn in st.session_state.chat_history:
            if turn["role"] == "user":
                st.markdown(
                    f'<div class="user-bubble">👤 {turn["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                agent = turn.get("agent", "rag")
                badge_class = f"agent-badge-{agent}"
                badge_label = {
                    "rag": "📚 RAG",
                    "web": "🌐 Web",
                    "memory": "🧠 Memory",
                    "hybrid": "🔀 Hybrid (RAG + Web Search)"
                }.get(agent, "🤖 AI")
                # Header badge + latency
                st.markdown(
                    f"""
                    <div style="margin-bottom:4px;">
                        <span class="agent-badge {badge_class}">{badge_label}</span>
                        <span style="font-size:0.72rem; color:#64748b; margin-left:8px;">
                            {turn.get("latency", "")}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # Render the answer as markdown so quota/error messages display
                # with proper links, bold text, and bullet points
                with st.container():
                    st.markdown(
                        f'<div class="assistant-bubble">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(turn["content"])
                    st.markdown("</div>", unsafe_allow_html=True)

                # Citations
                sources = turn.get("sources", [])
                if sources:
                    pills = "".join(
                        f'<span class="citation-pill">'
                        f'📄 {s["document"]}'
                        f'{" · p." + str(s["page"]) if s.get("page") else ""}'
                        f"</span>"
                        for s in sources
                    )
                    st.markdown(
                        f'<div style="margin-top:8px; margin-left:4px;">{pills}</div>',
                        unsafe_allow_html=True,
                    )

                # Routing Observability Trace
                routing_decision = turn.get("routing_decision")
                routing_trace = turn.get("routing_trace", [])
                if routing_decision or routing_trace:
                    with st.expander("🔀 Routing Observability Trace", expanded=False):
                        if routing_decision:
                            conf_pct = int(routing_decision.get("confidence", 1.0) * 100)
                            fallback = " (rule-based fallback)" if routing_decision.get("fallback_used") else ""
                            st.markdown(f"**Target Agent:** `{routing_decision.get('agent', 'unknown').upper()}` | **Confidence:** `{conf_pct}%`{fallback}")
                            if routing_decision.get("reasoning"):
                                st.markdown(f"*Reasoning:* {routing_decision.get('reasoning')}")
                        
                        # Token & Cost Metrics
                        prompt_tok = turn.get("prompt_tokens", 0) or result.get("prompt_tokens", 0) if 'result' in locals() else turn.get("prompt_tokens", 0)
                        comp_tok = turn.get("completion_tokens", 0) or result.get("completion_tokens", 0) if 'result' in locals() else turn.get("completion_tokens", 0)
                        tot_tok = turn.get("total_tokens", 0) or result.get("total_tokens", 0) if 'result' in locals() else turn.get("total_tokens", 0)
                        c_usd = turn.get("cost_usd", 0.0) or result.get("cost_usd", 0.0) if 'result' in locals() else turn.get("cost_usd", 0.0)
                        if tot_tok > 0:
                            st.markdown(f"**Tokens used:** `{tot_tok}` (Prompt: `{prompt_tok}`, Completion: `{comp_tok}`) | **Estimated Cost:** `${c_usd:.6f}`")

                        if routing_trace:
                            st.markdown("**Execution Trace Steps:**")
                            for step in routing_trace:
                                st.markdown(f"- {step}")

    # ── Input bar ──────────────────────────────────────────────────────────────
    query = st.chat_input("Ask about your documents, current events, or follow up on previous answers…")

    if query and query.strip():
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": query})

        with st.spinner("🤔 Thinking…"):
            payload = {
                "query": query,
                "session_id": st.session_state.session_id,
                "use_web_search": use_web,
            }
            result = api_post("/chat", json=payload, timeout=120.0)

        if result:
            # Update session_id from response
            st.session_state.session_id = result.get("session_id")

            latency = result.get("latency_ms", {})
            total_ms = latency.get("total", 0)
            latency_label = f"⏱ {total_ms:.0f}ms" if total_ms else ""

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "agent": result.get("agent_used", "rag"),
                    "sources": result.get("sources", []),
                    "latency": latency_label,
                    "routing_decision": result.get("routing_decision"),
                    "routing_trace": result.get("routing_trace", []),
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "total_tokens": result.get("total_tokens", 0),
                    "cost_usd": result.get("cost_usd", 0.0),
                }
            )

        st.rerun()


# ── Page: Analytics — Retrieval Observability Dashboard ───────────────────────

def _safe_get(analytics: dict, key: str, default: float = 0.0) -> float:
    """Safely get a float value from analytics dict."""
    val = analytics.get(key, default)
    return float(val) if val is not None else default


def render_analytics() -> None:
    st.markdown(
        '<div class="section-header">📊 Retrieval Observability Dashboard</div>',
        unsafe_allow_html=True,
    )

    data = api_get("/analytics")
    if not data or data.get("message"):
        st.info(
            "No analytics data yet. Ask some questions in the Chat page to populate this dashboard!"
        )
        return

    total_q = data.get("total_queries", 0)
    q_today = data.get("queries_today", 0)
    total_cost = _safe_get(data, "total_cost_usd")
    total_tok = _safe_get(data, "total_tokens")

    # ── Row 1: KPI cards ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Queries", f"{total_q:,}")
    c2.metric("Queries Today", f"{q_today:,}")
    c3.metric("Avg Response Latency", f"{_safe_get(data, 'avg_total_latency_ms'):.0f} ms")
    c4.metric("Total Cost", f"${total_cost:.4f}")
    c5.metric("Total Tokens", f"{total_tok:,.0f}")

    st.divider()

    # ── Row 2: Retrieval funnel + Agent distribution ───────────────────────────
    col_funnel, col_agent = st.columns(2, gap="large")

    with col_funnel:
        st.markdown("#### 🔽 Retrieval Funnel")
        funnel_stages = [
            ("Vector Search", int(_safe_get(data, "avg_vector_hits"))),
            ("BM25 Search", int(_safe_get(data, "avg_bm25_hits"))),
            ("After RRF Fusion", int(_safe_get(data, "avg_retrieved"))),
            ("After Reranking", int(_safe_get(data, "avg_reranked"))),
        ]
        funnel_df = pd.DataFrame(funnel_stages, columns=["Stage", "Avg Chunks"])
        fig_funnel = px.funnel(
            funnel_df,
            y="Stage",
            x="Avg Chunks",
            title="Average Chunks per Pipeline Stage",
            color_discrete_sequence=["#3b82f6", "#6366f1", "#a855f7", "#ec4899"],
        )
        fig_funnel.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_agent:
        st.markdown("#### 🤖 Agent Routing Distribution")
        agent_dist = data.get("agent_distribution", {})
        if agent_dist:
            color_map = {
                "rag": "#10b981",
                "web": "#3b82f6",
                "memory": "#a855f7",
                "hybrid": "#7c3aed",
            }
            colors = [color_map.get(k, "#64748b") for k in agent_dist.keys()]
            fig_pie = px.pie(
                names=[k.upper() for k in agent_dist.keys()],
                values=list(agent_dist.values()),
                title="Agent Usage Breakdown",
                color_discrete_sequence=colors,
                hole=0.5,
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── Daily Trends (Queries & Costs) ──
    daily_trend = data.get("daily_trend", [])
    if daily_trend:
        st.markdown("#### 📅 Daily Volume & Cost Trends")
        daily_df = pd.DataFrame(daily_trend)
        
        col_t1, col_t2 = st.columns(2, gap="large")
        with col_t1:
            fig_q_trend = px.bar(
                daily_df,
                x="date",
                y="queries",
                title="Daily Query Volume",
                labels={"queries": "Number of Queries", "date": "Date"},
                color_discrete_sequence=["#3b82f6"],
            )
            fig_q_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
            )
            st.plotly_chart(fig_q_trend, use_container_width=True)
            
        with col_t2:
            fig_cost_trend = px.line(
                daily_df,
                x="date",
                y="cost",
                title="Daily Estimated LLM Cost (USD)",
                labels={"cost": "Cost (USD)", "date": "Date"},
                color_discrete_sequence=["#10b981"],
                markers=True,
            )
            fig_cost_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
            )
            st.plotly_chart(fig_cost_trend, use_container_width=True)

        st.divider()

    # ── Row 3: Per-stage latency waterfall ────────────────────────────────────
    st.markdown("#### ⏱ Pipeline Stage Latency Breakdown")
    stages = [
        ("Vector Search", _safe_get(data, "avg_vector_search_ms"), "#3b82f6"),
        ("BM25 Search", _safe_get(data, "avg_bm25_search_ms"), "#0ea5e9"),
        ("RRF Fusion", _safe_get(data, "avg_rrf_fusion_ms"), "#6366f1"),
        ("Cross-Encoder Rerank", _safe_get(data, "avg_reranking_ms"), "#a855f7"),
        ("LLM Generation", _safe_get(data, "avg_llm_ms"), "#ec4899"),
    ]
    stage_df = pd.DataFrame(stages, columns=["Stage", "Avg Latency (ms)", "Color"])
    fig_bar = px.bar(
        stage_df,
        x="Stage",
        y="Avg Latency (ms)",
        title="Avg Latency per Pipeline Stage (ms)",
        color="Stage",
        color_discrete_sequence=[s[2] for s in stages],
        text="Avg Latency (ms)",
    )
    fig_bar.update_traces(texttemplate="%{text:.1f}ms", textposition="outside")
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        showlegend=False,
        margin=dict(t=50, b=20),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # ── Row 4: Score distributions from recent queries ─────────────────────────
    recent = data.get("recent_metrics", [])
    if recent:
        st.markdown("#### 📈 Score Distributions (Recent Queries)")

        # Build per-query score data
        rerank_maxes, rrf_maxes, rerank_means, rrf_means = [], [], [], []
        query_labels = []
        for i, m in enumerate(recent[-15:]):
            rr = m.get("rerank_score_distribution", {})
            rf = m.get("rrf_score_distribution", {})
            rerank_maxes.append(rr.get("max_score") or 0)
            rerank_means.append(rr.get("mean_score") or 0)
            rrf_maxes.append(rf.get("max_score") or 0)
            rrf_means.append(rf.get("mean_score") or 0)
            q = m.get("query", "")[:30]
            query_labels.append(f"Q{i+1}: {q}")

        score_df = pd.DataFrame({
            "Query": query_labels,
            "RRF Max": rrf_maxes,
            "RRF Mean": rrf_means,
            "Rerank Max": rerank_maxes,
            "Rerank Mean": rerank_means,
        })

        col_rrf, col_rerank = st.columns(2)
        with col_rrf:
            fig_rrf = px.bar(
                score_df,
                x="Query",
                y=["RRF Max", "RRF Mean"],
                barmode="group",
                title="RRF Fusion Scores",
                color_discrete_map={"RRF Max": "#3b82f6", "RRF Mean": "#93c5fd"},
            )
            fig_rrf.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                xaxis_tickangle=-30,
                legend_title_text="",
            )
            st.plotly_chart(fig_rrf, use_container_width=True)

        with col_rerank:
            fig_rerank = px.bar(
                score_df,
                x="Query",
                y=["Rerank Max", "Rerank Mean"],
                barmode="group",
                title="Cross-Encoder Rerank Scores",
                color_discrete_map={"Rerank Max": "#a855f7", "Rerank Mean": "#d8b4fe"},
            )
            fig_rerank.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                xaxis_tickangle=-30,
                legend_title_text="",
            )
            st.plotly_chart(fig_rerank, use_container_width=True)

    st.divider()

    # ── Row 5: Latency and Token Usage/Cost trends ────────────────────────────
    if recent:
        tab_lat, tab_tok = st.tabs(["📉 Latency Trend", "🪙 Token & Cost Trend"])
        
        with tab_lat:
            st.markdown("#### 📉 Latency Trend (Recent Queries)")
            latency_data = []
            for i, m in enumerate(recent):
                latency_data.append({
                    "Query #": i + 1,
                    "Total (ms)": round(m.get("total_latency_ms", 0), 1),
                    "Retrieval (ms)": round(m.get("retrieval_latency_ms", 0), 1),
                    "Reranking (ms)": round(m.get("reranking_latency_ms") or 0, 1),
                    "LLM (ms)": round(m.get("llm_latency_ms") or 0, 1),
                })
            lat_df = pd.DataFrame(latency_data)
            fig_trend = px.line(
                lat_df,
                x="Query #",
                y=["Total (ms)", "Retrieval (ms)", "Reranking (ms)", "LLM (ms)"],
                title="Per-Stage Latency Over Time",
                color_discrete_map={
                    "Total (ms)": "#64748b",
                    "Retrieval (ms)": "#3b82f6",
                    "Reranking (ms)": "#a855f7",
                    "LLM (ms)": "#ec4899",
                },
                markers=True,
            )
            fig_trend.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with tab_tok:
            st.markdown("#### 🪙 Token & Cost Trend (Recent Queries)")
            token_data = []
            for i, m in enumerate(recent):
                token_data.append({
                    "Query #": i + 1,
                    "Prompt Tokens": m.get("prompt_tokens", 0),
                    "Completion Tokens": m.get("completion_tokens", 0),
                    "Total Tokens": m.get("total_tokens", 0),
                    "Cost ($)": m.get("cost_usd", 0.0),
                })
            tok_df = pd.DataFrame(token_data)
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                fig_tok = px.line(
                    tok_df,
                    x="Query #",
                    y=["Prompt Tokens", "Completion Tokens", "Total Tokens"],
                    title="Token Usage Over Time",
                    color_discrete_map={
                        "Prompt Tokens": "#3b82f6",
                        "Completion Tokens": "#10b981",
                        "Total Tokens": "#a855f7",
                    },
                    markers=True,
                )
                fig_tok.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                )
                st.plotly_chart(fig_tok, use_container_width=True)
                
            with col_t2:
                fig_cost = px.line(
                    tok_df,
                    x="Query #",
                    y="Cost ($)",
                    title="Estimated Cost per Query (USD)",
                    color_discrete_sequence=["#ec4899"],
                    markers=True,
                )
                fig_cost.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e2e8f0",
                )
                st.plotly_chart(fig_cost, use_container_width=True)

    st.divider()

    # ── Row 6: Per-query table ────────────────────────────────────────────────
    if recent:
        st.markdown("#### 🗒 Per-Query Retrieval Pipeline Table")
        rows = []
        for m in reversed(recent[-20:]):
            rows.append({
                "Query": (m.get("query", "")[:40] + "…") if len(m.get("query", "")) > 40 else m.get("query", ""),
                "Agent": m.get("agent_type", "").upper(),
                "Vector Hits": m.get("num_vector_results", 0),
                "BM25 Hits": m.get("num_bm25_results", 0),
                "Reranked": m.get("num_reranked", 0),
                "Prompt Tok": m.get("prompt_tokens", 0),
                "Comp Tok": m.get("completion_tokens", 0),
                "Cost": f"${m.get('cost_usd', 0.0):.5f}",
                "Rerank (ms)": round(m.get("reranking_latency_ms") or 0, 1),
                "LLM (ms)": round(m.get("llm_latency_ms") or 0, 1),
                "Total (ms)": round(m.get("total_latency_ms", 0), 1),
            })
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    # ── Row 7: Top sources ────────────────────────────────────────────────────
    top_src = data.get("top_sources", [])
    if top_src:
        st.markdown("#### 📚 Top Sources Used")
        src_df = pd.DataFrame(top_src, columns=["Source", "Count"])
        fig_src = px.bar(
            src_df,
            x="Count",
            y="Source",
            orientation="h",
            title="Most Referenced Sources",
            color="Count",
            color_continuous_scale="Blues",
        )
        fig_src.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_src, use_container_width=True)



# ── Page: Workflow Observability ────────────────────────────────────────────────

def render_workflow() -> None:
    st.markdown(
        '<div class="section-header">🔀 LangGraph Workflow Observability</div>',
        unsafe_allow_html=True,
    )

    # 1. Fetch graph visualization from backend API
    graph_data = api_get("/graph")
    
    col_left, col_right = st.columns([2, 3], gap="large")

    with col_left:
        st.markdown("### 🕸 Topology & Configuration")
        st.markdown(
            """
            This multi-agent RAG application uses **LangGraph** to construct a stateful workflow. 
            A query progresses through the nodes below based on intelligent routing:
            
            1. **Router Agent** (`router_node`): Classifies incoming queries based on semantic intent, history context, and document index size.
            2. **RAG Agent** (`rag_node`): Performs hybrid retrieval (ChromaDB + BM25 keyword search) followed by Cross-Encoder reranking.
            3. **Web Search Agent** (`web_node`): Searches the web via Tavily API to fetch real-time context.
            4. **Memory Agent** (`memory_node`): Pulls context from conversation history for follow-up questions.
            5. **Response Synthesizer** (`synthesizer_node`): Consolidates contexts from all active branches to formulate a response.
            6. **Response Formatter** (`formatter_node`): Cleans structure, resolves citations, and logs latency metrics.
            """
        )
        
        st.markdown("### 📊 Active Agents Description")
        st.info(
            "💡 **Parallel Fan-out**: The Router can trigger parallel execution of both **RAG** and **Web Search** "
            "agents (Hybrid mode) and merge their results dynamically before synthesis."
        )

    with col_right:
        st.markdown("### 🗺 Live Graph Visualization")
        if graph_data and "mermaid" in graph_data:
            mermaid_code = graph_data["mermaid"]
            import base64
            # Clean up diagram string if it has fences
            clean_code = mermaid_code.strip()
            if clean_code.startswith("```mermaid"):
                clean_code = clean_code[10:]
            if clean_code.startswith("```"):
                clean_code = clean_code[3:]
            if clean_code.endswith("```"):
                clean_code = clean_code[:-3]
            clean_code = clean_code.strip()

            # Prepend theme configuration
            theme_config = "%%{init: {'theme': 'dark', 'themeVariables': { 'background': '#0a0f1e', 'primaryColor': '#3b82f6', 'lineColor': '#64748b' }}}%%\n"
            full_mermaid = theme_config + clean_code
            
            b64_str = base64.b64encode(full_mermaid.encode("utf-8")).decode("utf-8")
            image_url = f"https://mermaid.ink/img/{b64_str}"
            
            try:
                st.image(image_url, caption="LangGraph Workflow Diagram", use_container_width=True)
            except Exception as e:
                st.warning("Failed to render diagram image from mermaid.ink. Displaying raw diagram structure:")
                st.code(clean_code, language="mermaid")
        else:
            st.error("Could not fetch graph topology from API.")

    st.divider()

    # Recent Routing Decisions table
    st.markdown("### 🔀 Recent Routing Decisions (Global)")
    analytics = api_get("/analytics")
    if analytics and "recent_metrics" in analytics:
        recent = analytics["recent_metrics"]
        if recent:
            rows = []
            for m in reversed(recent):
                agent = m.get("agent_type", "unknown").upper()
                badge = {
                    "RAG": "📚 RAG",
                    "WEB": "🌐 WEB",
                    "MEMORY": "🧠 MEMORY",
                    "HYBRID": "🔀 HYBRID",
                }.get(agent, f"🤖 {agent}")

                rows.append({
                    "Timestamp": m.get("timestamp")[:19].replace("T", " ") if m.get("timestamp") else "N/A",
                    "User Query": m.get("query"),
                    "Routed Agent": badge,
                    "Total Latency": f"{m.get('total_latency_ms', 0):.0f} ms",
                    "Reranked Chunks": m.get("num_reranked", 0),
                    "Web Results": m.get("num_web_results", 0) if "num_web_results" in m else ("Yes" if agent in ("WEB", "HYBRID") else "No"),
                })
            
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No query routing records found yet. Try asking some queries in the Chat page!")
    else:
        st.info("No query routing records found yet.")


# ── Main entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    init_session_state()
    page = render_sidebar()

    if page == "dashboard":
        render_dashboard()
    elif page == "chat":
        render_chat()
    elif page == "workflow":
        render_workflow()
    elif page == "analytics":
        render_analytics()


if __name__ == "__main__":
    main()
