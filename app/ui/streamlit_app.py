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
                }
            )

        st.rerun()


# ── Page: Analytics ───────────────────────────────────────────────────────────

def render_analytics() -> None:
    st.markdown(
        '<div class="section-header">📊 Retrieval Analytics</div>',
        unsafe_allow_html=True,
    )

    data = api_get("/analytics")
    if not data or data.get("message"):
        st.info("No analytics data yet. Start chatting to see metrics!")
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Queries", data["total_queries"])
    col2.metric("Avg Total Latency", f"{data['avg_total_latency_ms']:.0f}ms")
    col3.metric("Avg Retrieval Latency", f"{data['avg_retrieval_latency_ms']:.0f}ms")
    top_src = data.get("top_sources", [])
    col4.metric("Unique Sources", len(top_src))

    st.divider()

    col_left, col_right = st.columns(2, gap="large")

    # ── Agent distribution pie ─────────────────────────────────────────────────
    with col_left:
        agent_dist = data.get("agent_distribution", {})
        if agent_dist:
            fig = px.pie(
                names=list(agent_dist.keys()),
                values=list(agent_dist.values()),
                title="Agent Routing Distribution",
                color_discrete_sequence=["#3b82f6", "#10b981", "#a855f7"],
                hole=0.45,
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Source frequency bar ───────────────────────────────────────────────────
    with col_right:
        if top_src:
            src_df = pd.DataFrame(top_src, columns=["Source", "Count"])
            fig2 = px.bar(
                src_df,
                x="Count",
                y="Source",
                orientation="h",
                title="Top Sources Used",
                color="Count",
                color_continuous_scale="Blues",
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                showlegend=False,
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Recent queries table ───────────────────────────────────────────────────
    st.markdown("#### 🕒 Recent Queries")
    recent = data.get("recent_metrics", [])
    if recent:
        rows = []
        for m in reversed(recent[-10:]):
            rows.append(
                {
                    "Query": m["query"][:60] + ("…" if len(m["query"]) > 60 else ""),
                    "Agent": m["agent_type"].upper(),
                    "Retrieved": m["num_retrieved"],
                    "Reranked": m["num_reranked"],
                    "Total (ms)": round(m["total_latency_ms"], 1),
                    "LLM (ms)": round(m.get("llm_latency_ms") or 0, 1),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Latency scatter ────────────────────────────────────────────────────────
    if recent:
        latency_data = [
            {
                "Query #": i + 1,
                "Total (ms)": round(m["total_latency_ms"], 1),
                "LLM (ms)": round(m.get("llm_latency_ms") or 0, 1),
                "Agent": m["agent_type"],
            }
            for i, m in enumerate(recent)
        ]
        lat_df = pd.DataFrame(latency_data)
        fig3 = px.line(
            lat_df,
            x="Query #",
            y=["Total (ms)", "LLM (ms)"],
            title="Latency Over Time",
            color_discrete_map={"Total (ms)": "#3b82f6", "LLM (ms)": "#a855f7"},
        )
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
        )
        st.plotly_chart(fig3, use_container_width=True)


# ── Main entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    init_session_state()
    page = render_sidebar()

    if page == "dashboard":
        render_dashboard()
    elif page == "chat":
        render_chat()
    elif page == "analytics":
        render_analytics()


if __name__ == "__main__":
    main()
