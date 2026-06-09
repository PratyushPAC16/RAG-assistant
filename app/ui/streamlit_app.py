"""
Enterprise Agentic RAG Assistant
Streamlit frontend — three-page app: Dashboard, Chat, and Analytics.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

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

# ── Session state initialisation ───────────────────────────────────────────────

def load_session_history_into_state(session_id: str) -> None:
    """Fetch conversation from API and load into Streamlit session state."""
    resp = api_get(f"/chat/session/{session_id}/export?format=json")
    if resp and "messages" in resp:
        st.session_state.session_id = session_id
        history = []
        for m in resp["messages"]:
            role = m["role"]
            content = m["content"]
            if role == "user":
                history.append({"role": "user", "content": content})
            else:
                agent = m.get("agent_type") or "rag"
                meta = m.get("metadata") or {}
                latency_ms = meta.get("latency_ms", {})
                total_ms = latency_ms.get("total", 0)
                latency_label = f"⏱ {total_ms:.0f}ms" if total_ms else ""
                
                history.append({
                    "role": "assistant",
                    "content": content,
                    "agent": agent,
                    "sources": meta.get("sources", []),
                    "latency": latency_label,
                    "routing_decision": meta.get("routing_decision"),
                    "routing_trace": meta.get("routing_trace", []),
                    "prompt_tokens": meta.get("prompt_tokens", 0),
                    "completion_tokens": meta.get("completion_tokens", 0),
                    "total_tokens": meta.get("total_tokens", 0),
                    "cost_usd": meta.get("cost_usd", 0.0),
                    "retrieved_memories": meta.get("retrieved_memories", []),
                })
        st.session_state.chat_history = history


def export_history_to_markdown(session_id: str, chat_history: list[dict]) -> str:
    """Format chat history as a Markdown document."""
    lines = [f"# Chat Conversation: {session_id}", ""]
    for i, turn in enumerate(chat_history, start=1):
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            lines.append(f"### Turn {i} - **User**")
        else:
            agent = str(turn.get("agent", "rag")).upper()
            latency = turn.get("latency", "")
            lines.append(f"### Turn {i} - **Assistant ({agent})** - *{latency}*")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


import json

def export_history_to_json(session_id: str, chat_history: list[dict]) -> str:
    """Format chat history as a JSON string."""
    data = {
        "session_id": session_id,
        "messages": chat_history
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def init_session_state() -> None:
    defaults = {
        "session_id": None,
        "chat_history": [],  # list[dict] with role, content, agent, sources, latency
        "page": "dashboard",
        "resume_analysis_result": None,
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
            "💼 Career Intelligence": "career_intelligence",
            "🧠 Memory": "memory_dashboard",
            "🔀 Workflow": "workflow",
            "📊 Analytics": "analytics",
            "⚡ LLM Benchmark": "benchmark",
        }
        
        page_vals = list(pages.values())
        default_idx = page_vals.index(st.session_state.page) if st.session_state.page in page_vals else 0
        
        selected_label = st.radio(
            "Navigation",
            list(pages.keys()),
            index=default_idx,
            label_visibility="collapsed",
        )
        page = pages[selected_label]
        st.session_state.page = page

        st.divider()

        # Session info
        if st.session_state.session_id:
            st.caption(f"Session: `{st.session_state.session_id[:8]}…`")

        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.session_state.page = "chat"
            st.rerun()

        st.divider()

        # Past Conversations list
        with st.expander("📁 Past Conversations", expanded=True):
            sessions_resp = api_get("/chat/sessions")
            if sessions_resp:
                for s in sessions_resp:
                    sid = s["session_id"]
                    title = s["title"]
                    msg_count = s.get("message_count", 0)
                    
                    display_title = title if len(title) <= 22 else f"{title[:20]}..."
                    label = f"{display_title} ({msg_count})"
                    
                    is_current = (st.session_state.session_id == sid)
                    button_type = "primary" if is_current else "secondary"
                    
                    col_btn, col_del = st.columns([5, 1.2])
                    if col_btn.button(label, key=f"sess_btn_{sid}", use_container_width=True, type=button_type):
                        load_session_history_into_state(sid)
                        st.session_state.page = "chat"
                        st.rerun()
                    
                    if col_del.button("🗑️", key=f"sess_del_{sid}", help="Delete this conversation"):
                        api_delete(f"/chat/session/{sid}")
                        if st.session_state.session_id == sid:
                            st.session_state.session_id = None
                            st.session_state.chat_history = []
                        st.rerun()
            else:
                st.caption("No past sessions.")

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

    # Table Header
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([3, 1, 1, 1, 1.5, 1.5])
    h_col1.markdown("**Filename**")
    h_col2.markdown("**Type**")
    h_col3.markdown("**Chunks**")
    h_col4.markdown("**Pages**")
    h_col5.markdown("**Size**")
    h_col6.markdown("**Actions**")
    st.markdown("<hr style='margin: 4px 0; border-color: #334155 !important;' />", unsafe_allow_html=True)

    # Table Rows
    for d in docs:
        doc_id = d["document_id"]
        filename = d["filename"]
        file_type = d["file_type"].upper()
        chunks = d["num_chunks"]
        pages = d.get("num_pages") or "—"
        size_kb = f"{round(d['file_size_bytes'] / 1024, 1)} KB"

        row_col1, row_col2, row_col3, row_col4, row_col5, row_col6 = st.columns([3, 1, 1, 1, 1.5, 1.5])
        row_col1.write(filename)
        row_col2.write(file_type)
        row_col3.write(str(chunks))
        row_col4.write(str(pages))
        row_col5.write(size_kb)

        # Action buttons
        btn_col1, btn_col2 = row_col6.columns(2)
        if btn_col1.button("🔄", key=f"reindex_{doc_id}", help=f"Reindex {filename}"):
            with st.spinner("Reindexing…"):
                result = api_post(f"/documents/{doc_id}/reindex", timeout=300.0)
            if result:
                st.success(f"✅ Reindexed '{filename}'")
                st.rerun()

        if btn_col2.button("🗑️", key=f"delete_{doc_id}", help=f"Delete {filename}"):
            with st.spinner("Deleting…"):
                result = api_delete(f"/documents/{doc_id}")
            if result:
                st.success(f"✅ Deleted '{filename}'")
                st.rerun()


# ── Page: Chat ────────────────────────────────────────────────────────────────

def render_chat() -> None:
    col_title, col_clear, col_exp_md, col_exp_json = st.columns([4.5, 1.5, 1.5, 1.5])
    with col_title:
        st.markdown(
            '<div class="section-header">💬 Agentic Chat</div>',
            unsafe_allow_html=True,
        )
    
    if st.session_state.session_id and st.session_state.chat_history:
        if col_clear.button("🗑️ Clear Chat", use_container_width=True, help="Delete and clear current conversation"):
            api_delete(f"/chat/session/{st.session_state.session_id}")
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.rerun()
            
        md_data = export_history_to_markdown(st.session_state.session_id, st.session_state.chat_history)
        col_exp_md.download_button(
            label="📥 Export MD",
            data=md_data,
            file_name=f"chat_{st.session_state.session_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True,
            help="Download chat history as Markdown",
        )
        
        json_data = export_history_to_json(st.session_state.session_id, st.session_state.chat_history)
        col_exp_json.download_button(
            label="📥 Export JSON",
            data=json_data,
            file_name=f"chat_{st.session_state.session_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
            help="Download chat history as JSON",
        )

    # Settings bar
    with st.expander("⚙️ Chat Settings & Document Filters", expanded=False):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            use_web = st.toggle("Allow Web Search", value=True)
            st.caption(
                "When enabled, the router may use Tavily web search "
                "for queries requiring current information."
            )
        with col_s2:
            # Load documents list for filtering
            docs_resp = api_get("/documents")
            doc_options = {}
            if docs_resp and docs_resp.get("documents"):
                doc_options = {d["filename"]: d["document_id"] for d in docs_resp["documents"]}
            
            if doc_options:
                selected_filenames = st.multiselect(
                    "Filter Search to Specific Documents",
                    options=list(doc_options.keys()),
                    default=[],
                    placeholder="Search all (Entire knowledge base)",
                )
                filter_ids = [doc_options[name] for name in selected_filenames]
            else:
                st.caption("No documents indexed yet to filter.")
                filter_ids = None

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

                # Retrieved Memories from Long-Term Memory
                retrieved_mems = turn.get("retrieved_memories", [])
                if retrieved_mems:
                    with st.expander("🧠 Retrieved Long-Term Memories", expanded=False):
                        mem_rows = []
                        for m in retrieved_mems:
                            mem_rows.append({
                                "Content": m.get("content"),
                                "Type": m.get("memory_type", "").upper(),
                                "Relevance Score": f"{m.get('score', 1.0):.4f}" if m.get("score") is not None else "1.0000",
                                "Source Session": m.get("session_id", "")[:8] + "...",
                            })
                        st.dataframe(pd.DataFrame(mem_rows), use_container_width=True, hide_index=True)

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
                "filter_document_ids": filter_ids if 'filter_ids' in locals() and filter_ids else None,
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
                    "retrieved_memories": result.get("retrieved_memories", []),
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
        '<div class="section-header">📊 Analytics Dashboard</div>',
        unsafe_allow_html=True,
    )

    # ── Fetch both data sources ───────────────────────────────────────────────
    data = api_get("/analytics/extended", timeout=15.0)
    if not data or data.get("total_queries", 0) == 0:
        st.info(
            "No analytics data yet. Ask some questions in the Chat page to populate this dashboard!"
        )
        # Still render document / memory sections if they have data
        if data:
            _render_doc_and_memory_cards(data)
        return

    total_q     = data.get("total_queries", 0)
    q_today     = data.get("queries_today", 0)
    avg_lat     = data.get("avg_total_latency_ms", 0.0)
    p95_lat     = data.get("p95_total_latency_ms", 0.0)
    total_cost  = data.get("total_cost_usd", 0.0)
    total_tok   = data.get("total_tokens", 0)
    ret_success = data.get("retrieval_success_rate", 0.0)
    most_agent  = data.get("most_used_agent", "N/A").upper()
    provider    = data.get("llm_provider", "N/A").upper()
    mem_total   = data.get("memory_metrics", {}).get("total_memories", 0)
    doc_total   = data.get("document_metrics", {}).get("total_documents", 0)
    chunk_total = data.get("document_metrics", {}).get("total_chunks_indexed", 0)

    # ── Hero KPI strip ────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("🔍 Total Queries",      f"{total_q:,}")
    k2.metric("📅 Queries Today",       f"{q_today:,}")
    k3.metric("⏱ Avg Latency",          f"{avg_lat:.0f} ms")
    k4.metric("📊 P95 Latency",         f"{p95_lat:.0f} ms")
    k5.metric("✅ Retrieval Success",   f"{ret_success:.1f}%")
    k6.metric("💰 Total Cost",          f"${total_cost:.4f}")
    k7.metric("🧠 Memories Stored",     f"{mem_total:,}")

    st.divider()

    # ── Secondary KPI strip ───────────────────────────────────────────────────
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("🤖 Most Used Agent",  most_agent)
    s2.metric("⚡ Active Provider",   provider)
    s3.metric("📂 Documents Indexed", f"{doc_total:,}")
    s4.metric("🗂 Total Chunks",       f"{chunk_total:,}")
    s5.metric("🪙 Total Tokens",       f"{total_tok:,.0f}")

    st.divider()

    # ── Tabbed sections ───────────────────────────────────────────────────────
    tab_overview, tab_latency, tab_retrieval, tab_tokens, tab_memory, tab_docs, tab_raw = st.tabs([
        "🏠 Overview",
        "⏱ Latency",
        "🔍 Retrieval",
        "🪙 Tokens & Cost",
        "🧠 Memory",
        "📂 Documents",
        "📋 Raw Data",
    ])

    _DARK_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        margin=dict(l=10, r=10, t=40, b=10),
    )

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 1 — OVERVIEW                                              ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_overview:
        col_agent, col_provider = st.columns(2, gap="large")

        # Agent distribution donut
        with col_agent:
            st.markdown("#### 🤖 Agent Usage Distribution")
            agent_dist = data.get("agent_distribution", {})
            if agent_dist:
                agent_color_map = {
                    "rag": "#10b981", "web": "#3b82f6",
                    "memory": "#a855f7", "hybrid": "#7c3aed",
                }
                fig_agent = go.Figure(go.Pie(
                    labels=[k.upper() for k in agent_dist.keys()],
                    values=list(agent_dist.values()),
                    hole=0.55,
                    marker_colors=[agent_color_map.get(k, "#64748b") for k in agent_dist.keys()],
                ))
                fig_agent.update_traces(textinfo="label+percent", hoverinfo="label+value+percent")
                fig_agent.update_layout(**_DARK_LAYOUT, title="Agent Routing Breakdown", height=320)
                st.plotly_chart(fig_agent, use_container_width=True)
                # Most-used callout
                top_agent = max(agent_dist, key=agent_dist.get)
                st.markdown(
                    f'<div style="text-align:center; font-size:0.85rem; color:#94a3b8;">Most Routed: '
                    f'<b style="color:#10b981">{top_agent.upper()}</b> '
                    f'({agent_dist[top_agent]:,} queries)</div>',
                    unsafe_allow_html=True,
                )

        # Provider usage donut
        with col_provider:
            st.markdown("#### ⚡ Provider Usage Distribution")
            prov_dist = data.get("provider_usage", {})
            if prov_dist:
                prov_color_map = {
                    "gemini": "#4f8ef7", "groq": "#10b981", "ollama": "#f59e0b",
                }
                fig_prov = go.Figure(go.Pie(
                    labels=[k.capitalize() for k in prov_dist.keys()],
                    values=list(prov_dist.values()),
                    hole=0.55,
                    marker_colors=[prov_color_map.get(k, "#64748b") for k in prov_dist.keys()],
                ))
                fig_prov.update_traces(textinfo="label+percent")
                fig_prov.update_layout(**_DARK_LAYOUT, title="LLM Provider Share", height=320)
                st.plotly_chart(fig_prov, use_container_width=True)

        st.divider()

        # Daily query volume + avg latency dual axis
        daily_trend = data.get("daily_trend", [])
        if daily_trend:
            st.markdown("#### 📅 Daily Query Volume & Average Latency")
            daily_df = pd.DataFrame(daily_trend)

            fig_daily = go.Figure()
            fig_daily.add_trace(go.Bar(
                x=daily_df["date"], y=daily_df["queries"],
                name="Queries", marker_color="#3b82f6", yaxis="y",
            ))
            if "avg_latency" in daily_df.columns:
                fig_daily.add_trace(go.Scatter(
                    x=daily_df["date"], y=daily_df["avg_latency"],
                    name="Avg Latency (ms)", mode="lines+markers",
                    marker_color="#f59e0b", yaxis="y2",
                ))
            fig_daily.update_layout(
                **_DARK_LAYOUT,
                height=340,
                barmode="group",
                yaxis=dict(title="Queries", titlefont_color="#3b82f6"),
                yaxis2=dict(title="Avg Latency (ms)", titlefont_color="#f59e0b",
                            overlaying="y", side="right"),
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_daily, use_container_width=True)

        st.divider()

        # Hourly heatmap
        hourly_counts = data.get("hourly_query_counts", [])
        if hourly_counts and any(h["count"] > 0 for h in hourly_counts):
            st.markdown("#### 🕐 Query Activity by Hour of Day")
            hours_df = pd.DataFrame(hourly_counts)
            fig_hourly = go.Figure(go.Bar(
                x=hours_df["hour"],
                y=hours_df["count"],
                marker=dict(
                    color=hours_df["count"],
                    colorscale="Blues",
                    showscale=True,
                    colorbar=dict(title="Queries"),
                ),
            ))
            fig_hourly.update_layout(
                **_DARK_LAYOUT, height=260,
                xaxis=dict(title="Hour of Day (UTC)", tickmode="linear", dtick=1),
                yaxis=dict(title="Query Count"),
            )
            st.plotly_chart(fig_hourly, use_container_width=True)

        # Query length distribution
        qlen_dist = data.get("query_length_distribution", {})
        if qlen_dist:
            st.divider()
            st.markdown("#### 🔤 Query Length Distribution")
            ql_col1, ql_col2 = st.columns([1.5, 1])
            with ql_col1:
                fig_qlen = go.Figure(go.Pie(
                    labels=list(qlen_dist.keys()),
                    values=list(qlen_dist.values()),
                    hole=0.45,
                    marker_colors=["#10b981", "#3b82f6", "#a855f7"],
                ))
                fig_qlen.update_layout(**_DARK_LAYOUT, height=280, title="Query Length Buckets")
                st.plotly_chart(fig_qlen, use_container_width=True)
            with ql_col2:
                st.markdown("**Query Length Stats**")
                st.metric("Avg Length", f"{data.get('avg_query_length', 0):.0f} chars")
                st.metric("Min Length", f"{data.get('min_query_length', 0)} chars")
                st.metric("Max Length", f"{data.get('max_query_length', 0)} chars")
                for bucket, cnt in qlen_dist.items():
                    pct = cnt / total_q * 100 if total_q else 0
                    st.progress(pct / 100, text=f"{bucket}: {cnt} ({pct:.0f}%)")

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 2 — LATENCY                                               ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_latency:
        st.markdown("### ⏱ Pipeline Stage Latency")

        # Stage waterfall bar chart
        stages = [
            ("Vector Search",       data.get("avg_retrieval_ms", 0) * 0.35, "#3b82f6"),
            ("BM25 Search",         data.get("avg_retrieval_ms", 0) * 0.35, "#0ea5e9"),
            ("RRF Fusion",          data.get("avg_retrieval_ms", 0) * 0.30, "#6366f1"),
            ("Cross-Encoder Rerank",data.get("avg_reranking_ms", 0),        "#a855f7"),
            ("LLM Generation",      data.get("avg_llm_ms", 0),              "#ec4899"),
        ]
        stage_df = pd.DataFrame(stages, columns=["Stage", "Avg ms", "Color"])
        fig_stages = go.Figure(go.Bar(
            x=stage_df["Stage"], y=stage_df["Avg ms"],
            marker_color=stage_df["Color"].tolist(),
            text=stage_df["Avg ms"].apply(lambda v: f"{v:.1f}ms"),
            textposition="outside",
        ))
        fig_stages.update_layout(
            **_DARK_LAYOUT, height=340,
            title="Average Latency Per Pipeline Stage (ms)",
            yaxis_title="ms", showlegend=False,
        )
        st.plotly_chart(fig_stages, use_container_width=True)

        # Latency KPI row
        lk1, lk2, lk3, lk4 = st.columns(4)
        lk1.metric("Avg Total",     f"{data.get('avg_total_latency_ms', 0):.0f} ms")
        lk2.metric("P95 Total",     f"{data.get('p95_total_latency_ms', 0):.0f} ms")
        lk3.metric("Avg Retrieval", f"{data.get('avg_retrieval_ms', 0):.0f} ms")
        lk4.metric("Avg LLM",       f"{data.get('avg_llm_ms', 0):.0f} ms")

        st.divider()

        # Per-query latency trend
        recent = data.get("recent_metrics", [])
        if recent:
            st.markdown("#### 📉 Latency Trend (Recent Queries)")
            lat_rows = [
                {
                    "Query #":        i + 1,
                    "Total (ms)":     round(m.get("total_latency_ms", 0), 1),
                    "Retrieval (ms)": round(m.get("retrieval_latency_ms", 0), 1),
                    "Reranking (ms)": round(m.get("reranking_latency_ms") or 0, 1),
                    "LLM (ms)":       round(m.get("llm_latency_ms") or 0, 1),
                }
                for i, m in enumerate(recent)
            ]
            lat_df = pd.DataFrame(lat_rows)
            fig_lat_trend = px.line(
                lat_df, x="Query #",
                y=["Total (ms)", "Retrieval (ms)", "Reranking (ms)", "LLM (ms)"],
                color_discrete_map={
                    "Total (ms)":     "#94a3b8",
                    "Retrieval (ms)": "#3b82f6",
                    "Reranking (ms)": "#a855f7",
                    "LLM (ms)":       "#ec4899",
                },
                markers=True,
            )
            fig_lat_trend.update_layout(**_DARK_LAYOUT, height=340)
            st.plotly_chart(fig_lat_trend, use_container_width=True)

            st.divider()
            # Scatter latency vs response length
            st.markdown("#### 🔵 Latency vs Response Length")
            scatter_rows = [
                {
                    "Total (ms)":     round(m.get("total_latency_ms", 0), 1),
                    "Completion Tok": m.get("completion_tokens", 0),
                    "Agent":          m.get("agent_type", "rag").upper(),
                }
                for m in recent
            ]
            sc_df = pd.DataFrame(scatter_rows)
            fig_scatter = px.scatter(
                sc_df, x="Completion Tok", y="Total (ms)", color="Agent",
                title="Total Latency vs Completion Tokens",
                color_discrete_map={"RAG": "#10b981", "WEB": "#3b82f6", "HYBRID": "#a855f7"},
            )
            fig_scatter.update_layout(**_DARK_LAYOUT, height=300)
            st.plotly_chart(fig_scatter, use_container_width=True)

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 3 — RETRIEVAL QUALITY                                     ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_retrieval:
        st.markdown("### 🔍 Retrieval Quality Metrics")

        rq1, rq2, rq3, rq4 = st.columns(4)
        rq1.metric("✅ Success Rate",       f"{data.get('retrieval_success_rate', 0):.1f}%")
        rq2.metric("📥 Avg Chunks Retr.",   f"{data.get('avg_chunks_retrieved', 0):.1f}")
        rq3.metric("📤 Avg Chunks Rerank.", f"{data.get('avg_chunks_reranked', 0):.1f}")
        rq4.metric("🔢 Avg Vector Hits",    f"{data.get('avg_vector_hits', 0):.1f}")

        st.divider()
        col_funnel, col_src = st.columns(2, gap="large")

        with col_funnel:
            st.markdown("#### 🔽 Retrieval Pipeline Funnel")
            funnel_stages = [
                ("Vector Search",   float(data.get("avg_vector_hits", 0))),
                ("BM25 Search",     float(data.get("avg_bm25_hits", 0))),
                ("RRF Fusion",      float(data.get("avg_chunks_retrieved", 0))),
                ("Reranked Chunks", float(data.get("avg_chunks_reranked", 0))),
            ]
            funnel_df = pd.DataFrame(funnel_stages, columns=["Stage", "Avg Chunks"])
            fig_funnel = px.funnel(
                funnel_df, y="Stage", x="Avg Chunks",
                color_discrete_sequence=["#3b82f6", "#6366f1", "#a855f7", "#ec4899"],
            )
            fig_funnel.update_layout(**_DARK_LAYOUT, height=320,
                                     title="Avg Chunks per Retrieval Stage")
            st.plotly_chart(fig_funnel, use_container_width=True)

        with col_src:
            top_sources = data.get("top_sources", [])
            if top_sources:
                st.markdown("#### 📚 Top Referenced Sources")
                src_df = pd.DataFrame(top_sources, columns=["Source", "Count"])
                fig_src = px.bar(
                    src_df, x="Count", y="Source", orientation="h",
                    color="Count", color_continuous_scale="Blues",
                    title="Most Referenced Document Sources",
                )
                fig_src.update_layout(
                    **_DARK_LAYOUT, height=320,
                    yaxis={"categoryorder": "total ascending"},
                    showlegend=False,
                )
                st.plotly_chart(fig_src, use_container_width=True)

        st.divider()

        # Score distributions
        recent = data.get("recent_metrics", [])
        if recent:
            st.markdown("#### 📈 Retrieval Score Distributions (Recent Queries)")
            score_rows = []
            for i, m in enumerate(recent[-15:]):
                rr = m.get("rerank_score_distribution", {})
                rf = m.get("rrf_score_distribution", {})
                score_rows.append({
                    "Query":        f"Q{i+1}",
                    "RRF Max":      rf.get("max_score") or 0,
                    "RRF Mean":     rf.get("mean_score") or 0,
                    "Rerank Max":   rr.get("max_score") or 0,
                    "Rerank Mean":  rr.get("mean_score") or 0,
                })
            sc_df = pd.DataFrame(score_rows)
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                fig_rrf = px.bar(sc_df, x="Query", y=["RRF Max", "RRF Mean"],
                                 barmode="group", title="RRF Fusion Scores",
                                 color_discrete_map={"RRF Max": "#3b82f6", "RRF Mean": "#93c5fd"})
                fig_rrf.update_layout(**_DARK_LAYOUT, height=300, xaxis_tickangle=-30)
                st.plotly_chart(fig_rrf, use_container_width=True)
            with col_r2:
                fig_rerank = px.bar(sc_df, x="Query", y=["Rerank Max", "Rerank Mean"],
                                    barmode="group", title="Cross-Encoder Rerank Scores",
                                    color_discrete_map={"Rerank Max": "#a855f7", "Rerank Mean": "#d8b4fe"})
                fig_rerank.update_layout(**_DARK_LAYOUT, height=300, xaxis_tickangle=-30)
                st.plotly_chart(fig_rerank, use_container_width=True)

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 4 — TOKENS & COST                                         ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_tokens:
        st.markdown("### 🪙 Token Usage & Cost Analysis")

        tk1, tk2, tk3, tk4 = st.columns(4)
        tk1.metric("📥 Total Prompt Tokens",     f"{data.get('total_prompt_tokens', 0):,}")
        tk2.metric("📤 Total Completion Tokens",  f"{data.get('total_completion_tokens', 0):,}")
        tk3.metric("📦 Total Tokens",             f"{data.get('total_tokens', 0):,}")
        tk4.metric("💰 Total Cost",               f"${data.get('total_cost_usd', 0):.5f}")
        tk5, tk6, _, _ = st.columns(4)
        tk5.metric("⚖️ Avg Tokens/Query",         f"{data.get('avg_total_tokens', 0):.0f}")
        tk6.metric("💵 Avg Cost/Query",           f"${data.get('avg_cost_usd', 0):.7f}")

        st.divider()

        daily_trend = data.get("daily_trend", [])
        if daily_trend:
            st.markdown("#### 📅 Daily Token & Cost Trends")
            daily_df = pd.DataFrame(daily_trend)
            col_tt1, col_tt2 = st.columns(2, gap="large")
            with col_tt1:
                fig_dtok = px.bar(daily_df, x="date", y="tokens",
                                  title="Daily Token Consumption",
                                  color_discrete_sequence=["#6366f1"])
                fig_dtok.update_layout(**_DARK_LAYOUT, height=280)
                st.plotly_chart(fig_dtok, use_container_width=True)
            with col_tt2:
                fig_dcost = px.line(daily_df, x="date", y="cost",
                                    title="Daily Estimated Cost (USD)",
                                    markers=True, color_discrete_sequence=["#ec4899"])
                fig_dcost.update_layout(**_DARK_LAYOUT, height=280)
                st.plotly_chart(fig_dcost, use_container_width=True)
            st.divider()

        recent = data.get("recent_metrics", [])
        if recent:
            st.markdown("#### 📉 Per-Query Token Usage (Recent)")
            tok_rows = [
                {
                    "Query #":           i + 1,
                    "Prompt Tokens":     m.get("prompt_tokens", 0),
                    "Completion Tokens": m.get("completion_tokens", 0),
                    "Total Tokens":      m.get("total_tokens", 0),
                    "Cost ($)":          m.get("cost_usd", 0.0),
                }
                for i, m in enumerate(recent)
            ]
            tok_df = pd.DataFrame(tok_rows)
            col_tc1, col_tc2 = st.columns(2, gap="large")
            with col_tc1:
                fig_tok_line = go.Figure()
                fig_tok_line.add_trace(go.Bar(
                    name="Prompt", x=tok_df["Query #"], y=tok_df["Prompt Tokens"],
                    marker_color="#3b82f6",
                ))
                fig_tok_line.add_trace(go.Bar(
                    name="Completion", x=tok_df["Query #"], y=tok_df["Completion Tokens"],
                    marker_color="#10b981",
                ))
                fig_tok_line.update_layout(**_DARK_LAYOUT, height=280,
                                           barmode="stack", title="Stacked Token Usage per Query",
                                           xaxis_title="Query #", yaxis_title="Tokens")
                st.plotly_chart(fig_tok_line, use_container_width=True)
            with col_tc2:
                fig_cost_q = px.area(tok_df, x="Query #", y="Cost ($)",
                                     title="Cost per Query (USD)",
                                     color_discrete_sequence=["#ec4899"])
                fig_cost_q.update_layout(**_DARK_LAYOUT, height=280)
                st.plotly_chart(fig_cost_q, use_container_width=True)

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 5 — MEMORY METRICS                                        ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_memory:
        st.markdown("### 🧠 Long-Term Memory Analytics")
        mem_metrics = data.get("memory_metrics", {})
        mem_total   = mem_metrics.get("total_memories", 0)
        mem_facts   = mem_metrics.get("facts", 0)
        mem_prefs   = mem_metrics.get("preferences", 0)
        mem_sums    = mem_metrics.get("summaries", 0)
        mem_by_type = mem_metrics.get("by_type", {})

        mk1, mk2, mk3, mk4 = st.columns(4)
        mk1.metric("🗂 Total Memories",   f"{mem_total:,}")
        mk2.metric("💡 Facts Stored",      f"{mem_facts:,}")
        mk3.metric("⭐ Preferences",       f"{mem_prefs:,}")
        mk4.metric("📝 Summaries",         f"{mem_sums:,}")

        st.divider()

        if mem_by_type:
            mc1, mc2 = st.columns([1, 1.4], gap="large")
            with mc1:
                st.markdown("#### 🍩 Memory Type Breakdown")
                mem_color_map = {
                    "fact": "#10b981", "preference": "#3b82f6",
                    "summary": "#a855f7", "unknown": "#64748b",
                }
                fig_mem = go.Figure(go.Pie(
                    labels=[k.capitalize() for k in mem_by_type.keys()],
                    values=list(mem_by_type.values()),
                    hole=0.55,
                    marker_colors=[mem_color_map.get(k, "#94a3b8") for k in mem_by_type.keys()],
                ))
                fig_mem.update_layout(**_DARK_LAYOUT, height=300, title="Memory by Type")
                st.plotly_chart(fig_mem, use_container_width=True)

            with mc2:
                st.markdown("#### 📊 Memory Distribution Details")
                if mem_total > 0:
                    for mtype, cnt in mem_by_type.items():
                        pct = cnt / mem_total * 100
                        color = mem_color_map.get(mtype, "#64748b")
                        st.markdown(
                            f'<div style="display:flex; justify-content:space-between; '
                            f'margin-bottom:6px;">'
                            f'<span style="color:{color};">● {mtype.capitalize()}</span>'
                            f'<span style="color:#94a3b8;">{cnt} ({pct:.1f}%)</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.progress(pct / 100)
                else:
                    st.info("No memories stored yet.")
        else:
            st.info("No long-term memories stored. Use the Chat to build memory!")

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 6 — DOCUMENT METRICS                                      ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_docs:
        st.markdown("### 📂 Document Knowledge Base Metrics")
        doc_metrics   = data.get("document_metrics", {})
        total_docs    = doc_metrics.get("total_documents", 0)
        total_chunks  = doc_metrics.get("total_chunks_indexed", 0)
        total_pages   = doc_metrics.get("total_pages_indexed", 0)
        avg_chunks    = doc_metrics.get("avg_chunks_per_doc", 0.0)
        ft_dist       = doc_metrics.get("file_type_distribution", {})
        doc_chunk_map = doc_metrics.get("document_chunk_distribution", {})

        dk1, dk2, dk3, dk4 = st.columns(4)
        dk1.metric("📁 Documents",      f"{total_docs:,}")
        dk2.metric("🗂 Total Chunks",    f"{total_chunks:,}")
        dk3.metric("📄 Total Pages",    f"{total_pages:,}")
        dk4.metric("⚖️ Avg Chunks/Doc", f"{avg_chunks:.1f}")

        st.divider()

        col_d1, col_d2 = st.columns(2, gap="large")

        with col_d1:
            if ft_dist:
                st.markdown("#### 📄 File Type Breakdown")
                ft_color_map = {"pdf": "#ec4899", "docx": "#3b82f6", "txt": "#10b981"}
                fig_ft = go.Figure(go.Pie(
                    labels=[k.upper() for k in ft_dist.keys()],
                    values=list(ft_dist.values()),
                    hole=0.5,
                    marker_colors=[ft_color_map.get(k.lower(), "#64748b") for k in ft_dist.keys()],
                ))
                fig_ft.update_layout(**_DARK_LAYOUT, height=300, title="Documents by File Type")
                st.plotly_chart(fig_ft, use_container_width=True)

        with col_d2:
            if doc_chunk_map:
                st.markdown("#### 📊 Chunks per Document")
                dc_df = pd.DataFrame(
                    list(doc_chunk_map.items()), columns=["Document", "Chunks"]
                ).sort_values("Chunks", ascending=True)
                fig_dc = px.bar(
                    dc_df, x="Chunks", y="Document", orientation="h",
                    title="Indexed Chunks per Document",
                    color="Chunks", color_continuous_scale="Purples",
                )
                fig_dc.update_layout(
                    **_DARK_LAYOUT, height=max(300, len(dc_df) * 36),
                    yaxis={"categoryorder": "total ascending"},
                    showlegend=False,
                )
                st.plotly_chart(fig_dc, use_container_width=True)

        # Top referenced sources
        top_sources = data.get("top_sources", [])
        if top_sources:
            st.divider()
            st.markdown("#### 📚 Most Referenced Sources (in Answers)")
            src_df = pd.DataFrame(top_sources, columns=["Source", "Count"])
            fig_srcs = px.bar(
                src_df, x="Count", y="Source", orientation="h",
                color="Count", color_continuous_scale="Blues",
            )
            fig_srcs.update_layout(
                **_DARK_LAYOUT, height=320,
                yaxis={"categoryorder": "total ascending"},
                showlegend=False,
            )
            st.plotly_chart(fig_srcs, use_container_width=True)

    # ╔════════════════════════════════════════════════════════════════╗
    # ║  TAB 7 — RAW DATA                                              ║
    # ╚════════════════════════════════════════════════════════════════╝
    with tab_raw:
        st.markdown("### 📋 Raw Query Pipeline Log (Last 20)")
        recent = data.get("recent_metrics", [])
        if recent:
            rows = []
            for m in reversed(recent):
                q = m.get("query", "")
                rows.append({
                    "Timestamp":   str(m.get("timestamp", ""))[:19],
                    "Query":       (q[:40] + "…") if len(q) > 40 else q,
                    "Agent":       m.get("agent_type", "").upper(),
                    "Vector Hits": m.get("num_vector_results", 0),
                    "BM25 Hits":   m.get("num_bm25_results", 0),
                    "Reranked":    m.get("num_reranked", 0),
                    "Prompt Tok":  m.get("prompt_tokens", 0),
                    "Comp Tok":    m.get("completion_tokens", 0),
                    "Cost":        f"${m.get('cost_usd', 0.0):.6f}",
                    "Rerank ms":   round(m.get("reranking_latency_ms") or 0, 1),
                    "LLM ms":      round(m.get("llm_latency_ms") or 0, 1),
                    "Total ms":    round(m.get("total_latency_ms", 0), 1),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No query records yet.")

        st.divider()
        st.markdown("### 📥 Export Analytics Data")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            import json
            payload_json = json.dumps(data, indent=2, default=str)
            st.download_button(
                "⬇️ Download Full Analytics JSON",
                data=payload_json,
                file_name="analytics_export.json",
                mime="application/json",
                use_container_width=True,
            )
        with exp_col2:
            if recent:
                import io
                csv_buf = pd.DataFrame(rows).to_csv(index=False)
                st.download_button(
                    "⬇️ Download Query Log CSV",
                    data=csv_buf,
                    file_name="query_log.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


def _render_doc_and_memory_cards(data: dict) -> None:
    """Render document and memory KPI cards even when there are no queries yet."""
    doc_metrics = data.get("document_metrics", {})
    mem_metrics = data.get("memory_metrics", {})
    if doc_metrics or mem_metrics:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📁 Documents Indexed", doc_metrics.get("total_documents", 0))
        c2.metric("🗂 Total Chunks",        doc_metrics.get("total_chunks_indexed", 0))
        c3.metric("🧠 Memories Stored",    mem_metrics.get("total_memories", 0))
        c4.metric("📝 Memory Types",        len(mem_metrics.get("by_type", {})))



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


# ── Page: Career Intelligence Analyzer ─────────────────────────────────────────

def render_career_intelligence() -> None:
    st.markdown(
        '<div class="section-header">💼 Career Intelligence Agent</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        Analyze your resume against any job description to assess your matching score, 
        uncover critical skill gaps, and get actionable recommendations.
        """
    )
    
    col_u1, col_u2 = st.columns(2, gap="large")
    with col_u1:
        resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="ci_resume_uploader")
    with col_u2:
        jd_file = st.file_uploader("Upload Job Description (PDF)", type=["pdf"], key="ci_jd_uploader")
        
    if resume_file and jd_file:
        if st.button("⚡ Run Fit Analysis", use_container_width=True, type="primary"):
            with st.spinner("Analyzing profile alignment with JD requirements..."):
                files = {
                    "resume": (resume_file.name, resume_file.getvalue(), "application/pdf"),
                    "jd": (jd_file.name, jd_file.getvalue(), "application/pdf"),
                }
                result = api_post("/analyze-resume", files=files, timeout=120.0)
                if result:
                    st.session_state.resume_analysis_result = result
                    st.success("Analysis complete!")
                    st.rerun()
                    
    if st.session_state.resume_analysis_result:
        res = st.session_state.resume_analysis_result
        
        # ── KPI Row ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Match Score", f"{res.get('match_score', 0)}%")
        c2.metric("Skill Match", f"{res.get('skill_match_pct', 0)}%")
        c3.metric("Project Match", f"{res.get('project_match_pct', 0)}%")
        c4.metric("Interview Readiness", f"{res.get('interview_readiness_score', 0)}%")
        
        st.divider()
        
        # ── Charts Row ──
        chart_col1, chart_col2 = st.columns([1, 1], gap="large")
        
        with chart_col1:
            # 1. Radar Chart
            st.markdown("#### 🕸 Profile Fit Radar")
            categories = ['Overall Fit', 'Skill Match', 'Project Match', 'Education Match', 'Interview Readiness']
            values = [
                res.get('match_score', 0),
                res.get('skill_match_pct', 0),
                res.get('project_match_pct', 0),
                res.get('education_match_pct', 0),
                res.get('interview_readiness_score', 0)
            ]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                fillcolor='rgba(59, 130, 246, 0.2)',
                line=dict(color='#3b82f6', width=2),
                marker=dict(color='#1d4ed8', size=6)
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        color='#94a3b8',
                        gridcolor='#334155',
                    ),
                    angularaxis=dict(
                        color='#e2e8f0',
                        gridcolor='#334155',
                    ),
                    bgcolor='rgba(0,0,0,0)'
                ),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=40, r=40, t=20, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with chart_col2:
            # 2. Skill Gap Visualization
            st.markdown("#### 📊 Skill Gaps & Alignment")
            skills = res.get("extracted_skills", [])
            if skills:
                names = [s.get("name") for s in skills]
                present = [1 if s.get("present") else 0 for s in skills]
                colors_list = ['#10b981' if p else '#ef4444' for p in present]
                labels = ['Present' if p else 'Missing' for p in present]
                
                fig_skills = go.Figure(go.Bar(
                    x=names,
                    y=[100] * len(skills),
                    marker_color=colors_list,
                    text=labels,
                    textposition='auto',
                    hoverinfo='x+text',
                ))
                fig_skills.update_layout(
                    yaxis=dict(visible=False),
                    xaxis=dict(tickangle=-45),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e2e8f0",
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=320,
                )
                st.plotly_chart(fig_skills, use_container_width=True)
            else:
                st.caption("No specific skills breakdown extracted.")
                
        st.divider()
        
        # ── Details & Recommendations Tabs ──
        tab_ins, tab_feat, tab_pdf = st.tabs(["🎯 Insights & Gaps", "📝 Extracted Profile Features", "📥 PDF Export"])
        
        with tab_ins:
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("##### 🟢 Strengths")
                for s in res.get("strengths", []):
                    st.markdown(f"- {s}")
            with t_col2:
                st.markdown("##### 🔴 Missing Skills & Gaps")
                for m in res.get("missing_skills", []):
                    st.markdown(f"- {m}")
                    
            st.write("")
            st.markdown("##### 💡 Actionable Recommendations")
            for r in res.get("recommendations", []):
                st.markdown(f"- {r}")
                
        with tab_feat:
            tf_col1, tf_col2 = st.columns(2)
            with tf_col1:
                st.markdown("##### 📚 Extracted Education")
                st.write(res.get("extracted_education", "Not specified."))
                st.markdown("##### 💼 Extracted Experience")
                st.write(res.get("extracted_experience", "Not specified."))
            with tf_col2:
                st.markdown("##### 🛠️ JD Core Requirements")
                for req in res.get("jd_requirements", []):
                    st.markdown(f"- {req}")
                st.markdown("##### 🚀 Extracted Projects")
                for p in res.get("extracted_projects", []):
                    st.markdown(f"- {p}")
                    
        with tab_pdf:
            st.markdown("##### Generate & Download PDF Report")
            st.write("Export a professionally compiled ReportLab PDF summarizing scores, skill gaps, and recommendations.")
            
            from app.utils.pdf_generator import generate_resume_analysis_pdf
            pdf_bytes = generate_resume_analysis_pdf(res)
            if pdf_bytes:
                res_name = resume_file.name if resume_file else "analysis"
                file_suffix = res_name.split('.')[0] if '.' in res_name else res_name
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"career_intel_report_{file_suffix}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.error("Failed to generate PDF report bytes.")


# ── Page: Long-Term Memory Dashboard ───────────────────────────────────────────

def render_memory_dashboard() -> None:
    st.markdown(
        '<div class="section-header">🧠 Long-Term Memory Dashboard</div>',
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        Long-Term Memory holds user preferences, extracted facts, and previous conversation summaries 
        persisted in ChromaDB. Matching memories are retrieved and injected into the LLM context 
        before document/web search retrieval.
        """
    )
    
    # Fetch all memories
    memories = api_get("/memories")
    if memories is None:
        memories = []
        
    total_memories = len(memories)
    facts_count = sum(1 for m in memories if m.get("memory_type") == "fact")
    pref_count = sum(1 for m in memories if m.get("memory_type") == "preference")
    sum_count = sum(1 for m in memories if m.get("memory_type") == "summary")
    
    # ── KPIs Row ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Memories", total_memories)
    c2.metric("Facts Stored", facts_count)
    c3.metric("Preferences Stored", pref_count)
    c4.metric("Turn Summaries", sum_count)
    
    st.divider()
    
    # ── Search & Test Retrieval Section ──
    st.markdown("### 🔍 Test Memory Retrieval")
    search_col1, search_col2 = st.columns([4, 1])
    test_query = search_col1.text_input("Enter a query to test what memories will be retrieved", placeholder="e.g. What is my project name?")
    search_btn = search_col2.button("🔍 Retrieve Memories", use_container_width=True)
    
    if test_query and (search_btn or test_query.strip()):
        with st.spinner("Retrieving matching memories..."):
            matched_mems = api_get(f"/memories/search?query={test_query}")
        if matched_mems:
            st.success(f"Found {len(matched_mems)} matching memories above the similarity threshold (0.45):")
            
            # Format and show as table
            match_rows = []
            for m in matched_mems:
                match_rows.append({
                    "Memory Content": m.get("content"),
                    "Type": m.get("memory_type", "").upper(),
                    "Similarity Score": f"{m.get('score', 0.0):.4f}",
                    "Session Source": m.get("session_id", "")[:8] + "...",
                    "Date Extracted": m.get("timestamp")[:16].replace("T", " ") if m.get("timestamp") else "N/A"
                })
            st.dataframe(pd.DataFrame(match_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No matching memories found for this query above the similarity threshold.")
            
    st.divider()
    
    # ── Stored Memories Table ──
    st.markdown("### 📋 Stored Memories in ChromaDB")
    if not memories:
        st.info("No long-term memories stored yet. Start chatting to extract memories!")
    else:
        # Show all memories table
        rows = []
        for m in memories:
            rows.append({
                "Memory ID": m.get("memory_id"),
                "Memory Content": m.get("content"),
                "Type": m.get("memory_type", "").upper(),
                "Session Source": m.get("session_id", "")[:8] + "...",
                "Date Extracted": m.get("timestamp")[:16].replace("T", " ") if m.get("timestamp") else "N/A"
            })
        
        df_mem = pd.DataFrame(rows)
        
        # Table Header
        th1, th2, th3, th4, th5 = st.columns([1.5, 5, 1.5, 2, 1.5])
        th1.markdown("**Memory ID**")
        th2.markdown("**Memory Content**")
        th3.markdown("**Type**")
        th4.markdown("**Date Extracted**")
        th5.markdown("**Action**")
        st.markdown("<hr style='margin: 4px 0; border-color: #334155 !important;' />", unsafe_allow_html=True)
        
        for idx, row in df_mem.iterrows():
            r1, r2, r3, r4, r5 = st.columns([1.5, 5, 1.5, 2, 1.5])
            r1.write(f"`{row['Memory ID']}`")
            r2.write(row["Memory Content"])
            r3.write(row["Type"])
            r4.write(row["Date Extracted"])
            
            if r5.button("🗑️", key=f"del_mem_{row['Memory ID']}", help=f"Delete memory {row['Memory ID']}"):
                with st.spinner("Deleting memory..."):
                    api_delete(f"/memories/{row['Memory ID']}")
                st.success("Memory deleted!")
                st.rerun()
                
        st.divider()
        
        # ── Danger Zone ──
        st.markdown("### ⚠️ Danger Zone")
        with st.container():
            st.markdown(
                """
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgb(239, 68, 68); border-radius: 8px; padding: 15px;">
                    <h5 style="color: rgb(239, 68, 68); margin-top:0;">Clear Long-Term Memory Store</h5>
                    <p style="font-size:0.85rem; color:#cbd5e1; margin-bottom:12px;">Wipe out all stored preferences, facts, and turn summaries from the ChromaDB collection. This action cannot be undone.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write("") # spacing
            if st.button("🚨 Clear All Memories", type="primary", use_container_width=True):
                with st.spinner("Clearing memories database..."):
                    api_delete("/memories")
                st.success("Memory database successfully cleared.")
                st.rerun()


# ── Page: LLM Benchmark Dashboard ────────────────────────────────────────────────────

_PROVIDER_COLORS = {
    "gemini": "#4f8ef7",
    "groq":   "#10b981",
    "ollama": "#f59e0b",
}
_PROVIDER_EMOJI = {
    "gemini": "🔵 Gemini",
    "groq":   "🟢 Groq",
    "ollama": "🟡 Ollama",
}


def _provider_badge(provider: str) -> str:
    emoji_map = {"gemini": "🔵", "groq": "🟢", "ollama": "🟡"}
    return f"{emoji_map.get(provider, '🧭')} {provider.capitalize()}"


def render_benchmark() -> None:
    st.markdown(
        '<div class="section-header">⚡ LLM Benchmark Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        Run any prompt across **Ollama (🟡 Local)**, **Groq (🟢 Cloud)**, and **Gemini (🔵 Cloud)**
        simultaneously. Compare latency, cost, token usage, response length,
        and LLM-graded faithfulness — then view the ranked leaderboard.
        """
    )

    if "benchmark_result" not in st.session_state:
        st.session_state.benchmark_result = None
    if "benchmark_history_cache" not in st.session_state:
        st.session_state.benchmark_history_cache = []

    # ── Input Panel ───────────────────────────────────────────────────────────
    with st.container():
        q_col, opt_col = st.columns([3, 1], gap="medium")
        with q_col:
            bench_query = st.text_area(
                "Benchmark Query",
                value="Explain the difference between RAG and fine-tuning for LLMs.",
                height=90,
                key="bench_query_input",
                label_visibility="collapsed",
                placeholder="Enter your benchmark prompt here…",
            )
        with opt_col:
            use_rag_toggle = st.toggle(
                "📚 Inject RAG Context",
                value=False,
                key="bench_rag_toggle",
                help="Retrieve document chunks from ChromaDB and inject them into every provider's prompt.",
            )
            temperature = st.slider(
                "Temperature", min_value=0.0, max_value=1.0,
                value=0.1, step=0.05, key="bench_temp_slider",
            )

        run_btn = st.button(
            "⚡ Run Benchmark Across All Providers",
            type="primary",
            use_container_width=True,
            key="bench_run_btn",
        )

    if run_btn:
        if not bench_query.strip():
            st.warning("Please enter a query before running the benchmark.")
        else:
            progress_bar = st.progress(0, text="Initializing concurrent benchmark runners…")
            with st.spinner("Running prompts on Gemini, Groq, and Ollama simultaneously…"):
                progress_bar.progress(25, text="🔵 Calling Gemini …")
                result = api_post(
                    f"/benchmark?query={bench_query}&use_rag={str(use_rag_toggle).lower()}&temperature={temperature}",
                    json={},
                )
                progress_bar.progress(85, text="Scoring and evaluating faithfulness…")
            progress_bar.progress(100, text="✅ Benchmark complete!")
            if result:
                st.session_state.benchmark_result = result
                # Refresh history
                hist = api_get("/benchmark/history", timeout=10.0)
                if hist:
                    st.session_state.benchmark_history_cache = hist.get("runs", [])
                st.success("Benchmark complete! Scroll down to view results.")
            else:
                st.error("Benchmark run failed. Check that the FastAPI backend is running.")

    res = st.session_state.benchmark_result
    if not res:
        st.info("🎯 Enter a query above and click **Run Benchmark** to see results.")
        _render_benchmark_history()
        return

    providers_data: dict = res.get("results", {})
    run_ts = res.get("timestamp", "")
    rag_on = res.get("use_rag", False)
    st.divider()

    # ── Leaderboard Table ──────────────────────────────────────────────────────
    st.markdown("### 🏆 Leaderboard")
    meta_col1, meta_col2 = st.columns([3, 1])
    meta_col1.caption(f"💬 **Query**: {res.get('query', '')[:120]}")
    meta_col2.caption(f"📡 RAG context: {'Enabled' if rag_on else 'Disabled'}")

    rows = []
    for pname, pdata in providers_data.items():
        rows.append({
            "Provider":          _provider_badge(pname),
            "Model":             pdata.get("model", "-"),
            "Latency (s)":       f"{pdata.get('latency_s', 0):.2f}s",
            "Total Tokens":      pdata.get("total_tokens", 0),
            "Cost (USD)":        f"${pdata.get('cost_usd', 0):.7f}",
            "Response Words":    pdata.get("response_length_words", 0),
            "Accuracy %":        f"{pdata.get('retrieval_accuracy', 0):.0f}%",
            "⭐ Score":           pdata.get("composite_score", 0),
            "Error":             pdata.get("error") or "",
        })

    # Sort by Score descending
    rows.sort(key=lambda x: x["⭐ Score"], reverse=True)
    df_lead = pd.DataFrame(rows)
    st.dataframe(df_lead, use_container_width=True, hide_index=True)

    st.divider()

    # ── Plotly Charts Grid ─────────────────────────────────────────────────────
    st.markdown("### 📊 Performance Charts")
    ch1, ch2 = st.columns(2, gap="large")
    ch3, ch4 = st.columns(2, gap="large")

    pnames  = list(providers_data.keys())
    lats    = [providers_data[p].get("latency_s", 0)         for p in pnames]
    costs   = [providers_data[p].get("cost_usd", 0)          for p in pnames]
    scores  = [providers_data[p].get("composite_score", 0)   for p in pnames]
    accurs  = [providers_data[p].get("retrieval_accuracy", 0) for p in pnames]
    p_toks  = [providers_data[p].get("prompt_tokens", 0)     for p in pnames]
    c_toks  = [providers_data[p].get("completion_tokens", 0) for p in pnames]
    colors_ = [_PROVIDER_COLORS.get(p, "#94a3b8")            for p in pnames]
    labels_ = [_provider_badge(p)                             for p in pnames]

    _CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )

    with ch1:
        st.markdown("#### ⏱ Latency (seconds)")
        fig_lat = go.Figure(go.Bar(
            x=labels_, y=lats, marker_color=colors_,
            text=[f"{v:.2f}s" for v in lats], textposition="auto",
        ))
        fig_lat.update_layout(**_CHART_LAYOUT, yaxis_title="Seconds")
        st.plotly_chart(fig_lat, use_container_width=True)

    with ch2:
        st.markdown("#### 💰 Estimated Cost (USD)")
        fig_cost = go.Figure(go.Bar(
            x=labels_, y=costs, marker_color=colors_,
            text=[f"${v:.6f}" for v in costs], textposition="auto",
        ))
        fig_cost.update_layout(**_CHART_LAYOUT, yaxis_title="USD")
        st.plotly_chart(fig_cost, use_container_width=True)

    with ch3:
        st.markdown("#### ⭐ Composite Score")
        fig_score = go.Figure(go.Bar(
            x=labels_, y=scores, marker_color=colors_,
            text=[f"{v:.1f}" for v in scores], textposition="auto",
        ))
        fig_score.update_layout(**_CHART_LAYOUT, yaxis=dict(range=[0, 105]), yaxis_title="Score")
        st.plotly_chart(fig_score, use_container_width=True)

    with ch4:
        st.markdown("#### 🧠 Token Usage")
        fig_tok = go.Figure()
        fig_tok.add_trace(go.Bar(
            name="Prompt",     x=labels_, y=p_toks,
            marker_color="#6366f1", text=p_toks, textposition="inside",
        ))
        fig_tok.add_trace(go.Bar(
            name="Completion", x=labels_, y=c_toks,
            marker_color="#10b981", text=c_toks, textposition="inside",
        ))
        fig_tok.update_layout(**_CHART_LAYOUT, barmode="stack", yaxis_title="Tokens")
        st.plotly_chart(fig_tok, use_container_width=True)

    # ── Faithfulness Accuracy Radar ───────────────────────────────────────────────
    st.divider()
    st.markdown("### 🎯 Retrieval Accuracy / Faithfulness")
    acc_col1, acc_col2 = st.columns([1, 1], gap="large")
    with acc_col1:
        fig_acc = go.Figure(go.Bar(
            x=labels_, y=accurs,
            marker_color=colors_,
            text=[f"{v:.1f}%" for v in accurs],
            textposition="auto",
        ))
        fig_acc.update_layout(
            **_CHART_LAYOUT,
            yaxis=dict(range=[0, 105], title="Accuracy %"),
            title="Faithfulness Score (LLM Graded)",
        )
        st.plotly_chart(fig_acc, use_container_width=True)
    with acc_col2:
        st.markdown("**Evaluator Reasoning**")
        for pname, pdata in providers_data.items():
            reasoning = pdata.get("evaluation_reasoning", "")
            score_v   = pdata.get("retrieval_accuracy", 0)
            color     = _PROVIDER_COLORS.get(pname, "#94a3b8")
            st.markdown(
                f"""
                <div style="border-left: 3px solid {color}; padding: 8px 12px; margin-bottom: 10px;
                            background: rgba(255,255,255,0.03); border-radius: 4px;">
                    <b style="color:{color};">{_provider_badge(pname)}</b>
                    &nbsp;<span style="font-size:0.9rem;">Accuracy: {score_v:.0f}%</span><br/>
                    <span style="font-size:0.85rem; color:#cbd5e1;">{reasoning}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Side-by-Side Response Comparison ──────────────────────────────────────────
    st.markdown("### 📝 Side-by-Side Response Comparison")
    comp_cols = st.columns(len(providers_data), gap="medium")
    for col, (pname, pdata) in zip(comp_cols, providers_data.items()):
        color = _PROVIDER_COLORS.get(pname, "#94a3b8")
        err   = pdata.get("error")
        with col:
            st.markdown(
                f"""
                <div style="border: 1px solid {color}44; border-radius: 10px; padding: 12px 14px;
                            background: rgba(255,255,255,0.02);">
                    <div style="font-size:1.05rem; font-weight:600; color:{color}; margin-bottom: 6px;">
                        {_provider_badge(pname)}
                    </div>
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 6px;">
                        {pdata.get('model', '-')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if err:
                st.error(f"Error: {err}")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Latency", f"{pdata.get('latency_s', 0):.2f}s")
                c2.metric("Score",   f"{pdata.get('composite_score', 0):.1f}")
                c3.metric("Words",   pdata.get("response_length_words", 0))

                c4, c5 = st.columns(2)
                c4.metric("Tokens",  pdata.get("total_tokens", 0))
                c5.metric("Cost",    f"${pdata.get('cost_usd', 0):.6f}")

                response_text = pdata.get("response", "")
                st.markdown(
                    f"""
                    <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
                                padding: 12px; margin-top: 8px; font-size: 0.83rem;
                                color: #e2e8f0; max-height: 400px; overflow-y: auto;
                                line-height: 1.55; white-space: pre-wrap;">
                        {response_text.replace('<', '&lt;').replace('>', '&gt;')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()
    _render_benchmark_history()


def _render_benchmark_history() -> None:
    """Collapsible section showing all past benchmark runs with reload support."""
    st.markdown("### 🗓 Benchmark History")

    hist_resp = api_get("/benchmark/history", timeout=10.0)
    hist_runs = (hist_resp or {}).get("runs", [])

    if not hist_runs:
        st.info("No benchmark history yet. Run your first benchmark above!")
        return

    st.caption(f"{len(hist_runs)} run(s) stored locally.")

    clear_col, _ = st.columns([1, 3])
    if clear_col.button("🗑 Clear Benchmark History", type="secondary", key="clear_bench_hist"):
        with st.spinner("Clearing…"):
            import httpx, os
            try:
                with httpx.Client(base_url=os.getenv("API_BASE_URL", "http://localhost:8000"), timeout=10.0) as cli:
                    cli.delete("/benchmark/history")
                st.session_state.benchmark_result = None
                st.success("History cleared.")
                st.rerun()
            except Exception as exc:
                st.error(f"Failed: {exc}")

    for i, run in enumerate(reversed(hist_runs)):
        ts  = run.get("timestamp", "")[:19].replace("T", " ")
        qry = run.get("query", "")[:80]
        rag = "📚 RAG" if run.get("use_rag") else ""
        with st.expander(f"📅 {ts} {rag} — {qry}…", expanded=(i == 0)):
            hist_results = run.get("results", {})

            # Mini leaderboard
            mini_rows = []
            for pname, pdata in hist_results.items():
                mini_rows.append({
                    "Provider":    _provider_badge(pname),
                    "Latency":     f"{pdata.get('latency_s', 0):.2f}s",
                    "Tokens":      pdata.get("total_tokens", 0),
                    "Cost":        f"${pdata.get('cost_usd', 0):.7f}",
                    "Accuracy %":  f"{pdata.get('retrieval_accuracy', 0):.0f}%",
                    "⭐ Score":    pdata.get("composite_score", 0),
                    "Error":       pdata.get("error") or "",
                })
            mini_rows.sort(key=lambda x: x["⭐ Score"], reverse=True)
            st.dataframe(pd.DataFrame(mini_rows), use_container_width=True, hide_index=True)

            if st.button("🔄 Load This Run", key=f"reload_hist_{i}", use_container_width=True):
                st.session_state.benchmark_result = run
                st.rerun()


# ── Main entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    init_session_state()
    page = render_sidebar()

    if page == "dashboard":
        render_dashboard()
    elif page == "chat":
        render_chat()
    elif page == "career_intelligence":
        render_career_intelligence()
    elif page == "memory_dashboard":
        render_memory_dashboard()
    elif page == "workflow":
        render_workflow()
    elif page == "analytics":
        render_analytics()
    elif page == "benchmark":
        render_benchmark()


if __name__ == "__main__":
    main()
