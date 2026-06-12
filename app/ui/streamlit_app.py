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
    page_title="TalentMind AI — Enterprise Talent Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API base URL ───────────────────────────────────────────────────────────────
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Custom CSS & Theming ───────────────────────────────────────────────────────

def inject_custom_styles() -> None:
    """Inject custom modern SaaS styles with dynamic light/dark mode support."""
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
        
    theme = st.session_state.theme
    
    if theme == "dark":
        css_vars = """
        :root {
            --bg-main: #060713;
            --bg-card: rgba(18, 21, 46, 0.45);
            --bg-sidebar: rgba(11, 13, 30, 0.65);
            --bg-navbar: rgba(6, 7, 19, 0.75);
            --bg-input: rgba(255, 255, 255, 0.04);
            --border-color: rgba(99, 102, 241, 0.16);
            --text-main: #f1f3f9;
            --text-muted: #9fa8c7;
            --shadow-main: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
            --primary: #8b5cf6; /* Electric Violet */
            --primary-hover: #a78bfa;
            --hr-color: rgba(99, 102, 241, 0.1);
            --glass-blur: blur(20px) saturate(140%);
            --glass-border: 1px solid rgba(99, 102, 241, 0.15);
            --nav-item-bg: rgba(255, 255, 255, 0.01);
            --nav-border: rgba(99, 102, 241, 0.08);
            --nav-hover-bg: rgba(99, 102, 241, 0.05);
            --nav-active-bg: linear-gradient(135deg, rgba(139, 92, 246, 0.18), rgba(236, 72, 153, 0.12));
            --nav-active-border: rgba(139, 92, 246, 0.45);
        }
        """
    else:
        css_vars = """
        :root {
            --bg-main: #f8fafc;
            --bg-card: rgba(255, 255, 255, 0.75);
            --bg-sidebar: rgba(241, 245, 249, 0.75);
            --bg-navbar: rgba(248, 250, 252, 0.85);
            --bg-input: rgba(0, 0, 0, 0.03);
            --border-color: rgba(99, 102, 241, 0.08);
            --text-main: #0f172a;
            --text-muted: #64748b;
            --shadow-main: 0 8px 32px 0 rgba(99, 102, 241, 0.04);
            --primary: #6366f1; /* Indigo */
            --primary-hover: #4f46e5;
            --hr-color: rgba(99, 102, 241, 0.06);
            --glass-blur: blur(20px) saturate(140%);
            --glass-border: 1px solid rgba(99, 102, 241, 0.08);
            --nav-item-bg: rgba(0, 0, 0, 0.005);
            --nav-border: rgba(0, 0, 0, 0.03);
            --nav-hover-bg: rgba(99, 102, 241, 0.03);
            --nav-active-bg: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(236, 72, 153, 0.05));
            --nav-active-border: rgba(99, 102, 241, 0.25);
        }
        """
        
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            
            {css_vars}
            
            /* Premium Mesh Background */
            html, body, [class*="css"], .stApp {{
                font-family: 'Montserrat', sans-serif;
                color: var(--text-main) !important;
            }}
            
            .stApp {{
                background: {
                    "radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.12) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(20, 184, 166, 0.12) 0px, transparent 50%), var(--bg-main)"
                    if theme == "dark" else
                    "radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.06) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.06) 0px, transparent 50%), var(--bg-main)"
                } !important;
            }}
            
            .block-container {{
                padding-top: 1.5rem !important;
                padding-bottom: 2rem !important;
                max-width: 1200px !important;
            }}
            
            /* Top Navbar */
            .top-navbar {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 60px;
                background-color: var(--bg-navbar) !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border-bottom: var(--glass-border) !important;
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0 2rem;
                z-index: 99999;
                box-shadow: var(--shadow-main) !important;
            }}
            
            .navbar-brand {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-family: 'Space Grotesk', sans-serif;
                font-weight: 700;
                font-size: 1.15rem;
            }}
            
            .navbar-badge-container {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            
            .navbar-badge {{
                background-color: var(--bg-input);
                border: var(--glass-border);
                backdrop-filter: var(--glass-blur);
                -webkit-backdrop-filter: var(--glass-blur);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 0.75rem;
                font-weight: 500;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }}
            
            .navbar-badge-lbl {{
                color: var(--text-muted);
            }}
            .navbar-badge-val {{
                color: var(--primary);
                font-weight: 600;
            }}
            
            /* Glass Sidebar */
            section[data-testid="stSidebar"] {{
                background-color: var(--bg-sidebar) !important;
                backdrop-filter: blur(25px) saturate(110%) !important;
                -webkit-backdrop-filter: blur(25px) saturate(110%) !important;
                border-right: var(--glass-border) !important;
            }}
            
            section[data-testid="stSidebar"] .stMarkdown,
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] span {{
                color: var(--text-main) !important;
            }}
            
            section[data-testid="stSidebar"] .stCaption,
            section[data-testid="stSidebar"] .stCaption p,
            section[data-testid="stSidebar"] .stCaption span {{
                color: var(--text-muted) !important;
            }}

            /* Style Streamlit Radio button navigation as modern sidebar tabs */
            div[data-testid="stRadio"] > label {{
                display: none !important; /* Hide "Navigation" widget label */
            }}
            
            div[data-testid="stRadio"] > div[role="radiogroup"] {{
                gap: 6px !important;
                display: flex;
                flex-direction: column;
            }}
            
            div[data-testid="stRadio"] > div[role="radiogroup"] > label {{
                background-color: var(--nav-item-bg) !important;
                border: 1px solid var(--nav-border) !important;
                padding: 10px 14px !important;
                border-radius: 8px !important;
                cursor: pointer !important;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
                display: flex !important;
                align-items: center !important;
                margin: 0 !important;
                width: 100% !important;
            }}
            
            div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {{
                background-color: var(--nav-hover-bg) !important;
                border-color: rgba(99, 102, 241, 0.3) !important;
                transform: translateX(4px);
            }}
            
            /* Hide the radio input circular dot */
            div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {{
                display: none !important;
            }}
            
            /* Text formatting inside sidebar tabs */
            div[data-testid="stRadio"] > div[role="radiogroup"] > label div[data-testid="stMarkdownContainer"] p {{
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                margin: 0 !important;
                color: var(--text-main) !important;
            }}
            
            /* Highlight active navigation tab */
            div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[type="radio"]:checked) {{
                background: var(--nav-active-bg) !important;
                border: var(--nav-active-border) !important;
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12) !important;
            }}
            
            div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input[type="radio"]:checked) p {{
                color: #ffffff !important;
                font-weight: 600 !important;
            }}

            /* Custom elements for Sidebar */
            .sidebar-header {{
                text-align: center;
                padding: 1rem 0 0.5rem 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 100%;
            }}
            .sidebar-logo-container {{
                position: relative;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 0.5rem;
            }}
            .sidebar-logo {{
                font-size: 2.5rem;
                z-index: 2;
            }}
            .sidebar-logo-glow {{
                position: absolute;
                width: 40px;
                height: 40px;
                background: radial-gradient(circle, rgba(99, 102, 241, 0.4) 0%, rgba(99, 102, 241, 0) 70%);
                border-radius: 50%;
                z-index: 1;
                animation: logoPulse 4s infinite ease-in-out;
            }}
            @keyframes logoPulse {{
                0%, 100% {{ transform: scale(1); opacity: 0.5; }}
                50% {{ transform: scale(1.3); opacity: 0.8; }}
            }}
            .sidebar-brand-title {{
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.25rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary), #d946ef);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: 0.5px;
            }}
            .sidebar-brand-version {{
                font-size: 0.7rem;
                font-weight: 600;
                color: #a78bfa !important;
                background: rgba(167, 139, 250, 0.1);
                border: 1px solid rgba(167, 139, 250, 0.2);
                padding: 2px 8px;
                border-radius: 20px;
                margin-top: 6px;
                display: inline-block;
            }}
            
            .sidebar-status-card {{
                background-color: var(--nav-item-bg) !important;
                border: 1px solid var(--nav-border) !important;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 12px;
                width: 100%;
            }}
            .sidebar-status-card.online {{
                border-left: 3px solid #10b981 !important;
            }}
            .sidebar-status-card.offline {{
                border-left: 3px solid #ef4444 !important;
            }}
            .status-indicator-row {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.85rem;
                font-weight: 600;
            }}
            .status-meta-row {{
                font-size: 0.72rem;
                color: var(--text-muted) !important;
                margin-top: 4px;
                padding-left: 16px;
            }}
            .status-pulse-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }}
            .status-pulse-dot.green {{
                background-color: #10b981;
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
                animation: statusPulseGreen 2s infinite;
            }}
            .status-pulse-dot.red {{
                background-color: #ef4444;
                box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
                animation: statusPulseRed 2s infinite;
            }}
            @keyframes statusPulseGreen {{
                0% {{
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
                }}
                70% {{
                    transform: scale(1);
                    box-shadow: 0 0 0 5px rgba(16, 185, 129, 0);
                }}
                100% {{
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
                }}
            }}
            @keyframes statusPulseRed {{
                0% {{
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
                }}
                70% {{
                    transform: scale(1);
                    box-shadow: 0 0 0 5px rgba(239, 68, 68, 0);
                }}
                100% {{
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
                }}
            }}

            /* Remove default expander borders/shadows inside Sidebar for a flatter, cleaner look */
            section[data-testid="stSidebar"] div[data-testid="stExpander"] {{
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }}
            section[data-testid="stSidebar"] details {{
                border: 1px solid var(--nav-border) !important;
                border-radius: 8px !important;
                background-color: var(--nav-item-bg) !important;
                margin-bottom: 10px !important;
            }}
            section[data-testid="stSidebar"] details summary {{
                padding: 8px 12px !important;
                font-weight: 600 !important;
                font-size: 0.85rem !important;
                color: var(--text-main) !important;
            }}

            /* Target the delete button inside past conversations columns */
            section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button {{
                background: rgba(239, 68, 68, 0.05) !important;
                border: 1px solid rgba(239, 68, 68, 0.15) !important;
                color: #ef4444 !important;
                font-size: 0.85rem !important;
                padding: 8px !important;
                min-width: 0px !important;
                height: 38px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
            section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button:hover {{
                background: rgba(239, 68, 68, 0.15) !important;
                border-color: #ef4444 !important;
                transform: translateY(-1px) !important;
            }}
            
            /* Glass Cards */
            .saas-card {{
                background-color: var(--bg-card) !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border: var(--glass-border) !important;
                border-radius: 12px;
                padding: 1.25rem;
                box-shadow: var(--shadow-main) !important;
                transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
                margin-bottom: 1rem;
            }}
            
            .saas-card:hover {{
                transform: translateY(-2px);
                border-color: rgba(59, 130, 246, 0.25) !important;
                box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.15) !important;
            }}
            
            .kpi-card {{
                background-color: var(--bg-card) !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border: var(--glass-border) !important;
                border-radius: 12px;
                padding: 1.25rem;
                box-shadow: var(--shadow-main) !important;
                display: flex;
                flex-direction: column;
                gap: 8px;
                transition: transform 0.25s ease, border-color 0.25s ease;
            }}
            .kpi-card:hover {{
                transform: translateY(-2px);
                border-color: rgba(59, 130, 246, 0.25) !important;
            }}
            .kpi-header {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .kpi-icon {{
                color: var(--primary);
                font-size: 1.2rem;
            }}
            .kpi-title {{
                font-size: 0.8rem;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .kpi-value {{
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.75rem;
                font-weight: 700;
                color: var(--text-main);
            }}
            .kpi-footer {{
                font-size: 0.7rem;
                color: var(--text-muted);
            }}
            
            div[data-testid="metric-container"] {{
                background-color: var(--bg-card) !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border: var(--glass-border) !important;
                border-radius: 12px !important;
                padding: 12px 16px !important;
                box-shadow: var(--shadow-main) !important;
            }}
            
            /* Glass Chat Bubbles */
            .user-bubble {{
                background: {
                    "linear-gradient(135deg, rgba(59, 130, 246, 0.7), rgba(99, 102, 241, 0.7))"
                    if theme == "dark" else
                    "linear-gradient(135deg, rgba(37, 99, 235, 0.85), rgba(79, 70, 229, 0.85))"
                } !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border: 1px solid rgba(255, 255, 255, 0.15) !important;
                border-radius: 18px 18px 4px 18px;
                padding: 12px 16px;
                margin: 8px 0 8px auto;
                max-width: 75%;
                color: white !important;
                box-shadow: 0 4px 20px 0 rgba(59, 130, 246, 0.2) !important;
                font-size: 0.925rem;
                line-height: 1.5;
            }}
            
            .assistant-bubble {{
                background-color: var(--bg-card) !important;
                backdrop-filter: var(--glass-blur) !important;
                -webkit-backdrop-filter: var(--glass-blur) !important;
                border: var(--glass-border) !important;
                border-radius: 18px 18px 18px 4px;
                padding: 14px 18px;
                margin: 8px auto 8px 0;
                max-width: 80%;
                color: var(--text-main) !important;
                box-shadow: var(--shadow-main) !important;
                font-size: 0.925rem;
                line-height: 1.5;
            }}
            
            /* Dynamic active sections header */
            .section-header {{
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.6rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary), #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 1.25rem;
                margin-top: 0.5rem;
                border-bottom: var(--glass-border);
                padding-bottom: 0.5rem;
            }}
            
            #MainMenu, header, footer {{
                visibility: hidden !important;
                display: none !important;
                height: 0px !important;
            }}
            
            header[data-testid="stHeader"] {{
                display: none !important;
            }}
            
            [data-testid="stFileUploader"] {{
                border: 2px dashed var(--border-color) !important;
                border-radius: 12px !important;
                background-color: var(--bg-card) !important;
                padding: 1rem !important;
                backdrop-filter: var(--glass-blur) !important;
            }}
            
            .stButton > button[kind="primary"] {{
                background: linear-gradient(135deg, var(--primary), #1d4ed8) !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 8px 20px !important;
                font-weight: 600 !important;
                transition: all 0.2s ease !important;
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2) !important;
            }}
            .stButton > button[kind="primary"]:hover {{
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35) !important;
            }}
            
            .stButton > button[kind="secondary"] {{
                background: var(--nav-item-bg) !important;
                color: var(--text-main) !important;
                border: 1px solid var(--nav-border) !important;
                border-radius: 8px !important;
                padding: 8px 20px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
                backdrop-filter: var(--glass-blur) !important;
            }}
            .stButton > button[kind="secondary"]:hover {{
                background: var(--nav-hover-bg) !important;
                border-color: var(--primary) !important;
                transform: translateY(-1px) !important;
            }}
            
            hr {{
                border-color: var(--hr-color) !important;
            }}
            
            /* Input element overrides for Glassmorphism */
            input, select, textarea, div[role="textbox"] {{
                background-color: var(--bg-input) !important;
                border: var(--glass-border) !important;
                color: var(--text-main) !important;
                border-radius: 8px !important;
            }}
            
            /* Source citation pills */
            .citation-pill {{
                background-color: rgba(124, 58, 237, 0.15) !important;
                border: 1px solid rgba(124, 58, 237, 0.25) !important;
                color: #ddd6fe !important;
                border-radius: 20px !important;
                padding: 3px 10px !important;
                font-size: 0.72rem !important;
                display: inline-block !important;
                margin: 2px !important;
            }}
            
            /* Workflow Visualizer styling */
            .workflow-visualizer {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--bg-card) !important;
                border: var(--glass-border) !important;
                backdrop-filter: var(--glass-blur) !important;
                border-radius: 12px;
                padding: 1.25rem 1rem;
                box-shadow: var(--shadow-main) !important;
                margin-bottom: 1.5rem;
                overflow-x: auto;
                gap: 8px;
            }}
            
            .node-wrapper {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 6px;
                min-width: 85px;
                position: relative;
                transition: all 0.3s ease;
            }}
            
            .node-icon {{
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background-color: var(--bg-input);
                border: 2px solid var(--border-color);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.05rem;
                color: var(--text-muted);
                transition: all 0.3s ease;
            }}
            
            .node-label {{
                font-size: 0.75rem;
                font-weight: 600;
                color: var(--text-muted);
                text-align: center;
                white-space: nowrap;
            }}
            
            .node-time {{
                font-size: 0.65rem;
                font-family: monospace;
                color: var(--primary);
                font-weight: 600;
            }}
            
            .node-wrapper.pending .node-icon {{
                opacity: 0.45;
            }}
            
            .node-wrapper.active .node-icon {{
                border-color: var(--primary) !important;
                color: var(--primary) !important;
                background-color: rgba(59, 130, 246, 0.1) !important;
                box-shadow: 0 0 15px rgba(59, 130, 246, 0.45) !important;
                transform: scale(1.08);
            }}
            .node-wrapper.active .node-label {{
                color: var(--primary) !important;
            }}
            
            .node-wrapper.done .node-icon {{
                border-color: #10b981 !important;
                color: #10b981 !important;
                background-color: rgba(16, 185, 129, 0.1) !important;
            }}
            .node-wrapper.done .node-label {{
                color: var(--text-main) !important;
            }}
            
            .node-arrow {{
                color: var(--border-color);
                font-size: 0.8rem;
                margin-bottom: 22px;
            }}
            
            /* Source Citations Redesign Grid */
            .source-cards-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
                gap: 12px;
                margin-top: 10px;
                margin-bottom: 15px;
                width: 100%;
            }}

            /* Style the details element as a card */
            .source-card {{
                background: var(--bg-card) !important;
                border: var(--glass-border) !important;
                backdrop-filter: var(--glass-blur) !important;
                border-radius: 8px;
                padding: 12px;
                box-shadow: var(--shadow-main) !important;
                transition: transform 0.2s ease, border-color 0.2s ease;
                overflow: hidden;
            }}

            .source-card:hover {{
                transform: translateY(-1px);
                border-color: rgba(59, 130, 246, 0.25) !important;
            }}

            /* Custom summary style */
            .source-card summary {{
                list-style: none;
                outline: none;
                cursor: pointer;
            }}
            .source-card summary::-webkit-details-marker {{
                display: none;
            }}

            .source-card-summary {{
                display: flex;
                flex-direction: column;
                gap: 6px;
            }}

            .source-card-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 100%;
            }}

            .source-card-title {{
                font-size: 0.8rem;
                font-weight: 600;
                color: var(--text-main);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 170px;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }}

            .source-card-badge {{
                font-size: 0.62rem;
                font-weight: 700;
                padding: 1px 6px;
                border-radius: 4px;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }}

            .source-card-badge.high {{
                background-color: rgba(16, 185, 129, 0.12) !important;
                color: #10b981 !important;
                border: 1px solid rgba(16, 185, 129, 0.2) !important;
            }}

            .source-card-badge.medium {{
                background-color: rgba(245, 158, 11, 0.12) !important;
                color: #f59e0b !important;
                border: 1px solid rgba(245, 158, 11, 0.2) !important;
            }}

            .source-card-badge.low {{
                background-color: rgba(239, 68, 68, 0.12) !important;
                color: #ef4444 !important;
                border: 1px solid rgba(239, 68, 68, 0.2) !important;
            }}

            .source-card-meta {{
                display: flex;
                justify-content: space-between;
                font-size: 0.72rem;
                color: var(--text-muted);
            }}

            .source-card-content {{
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid var(--border-color);
                font-size: 0.75rem;
                line-height: 1.45;
                color: var(--text-muted);
                cursor: default;
                white-space: pre-wrap;
            }}
            
            /* Glass Chat Bubbles Override */
            div[data-testid="stChatMessage"] {{
                background-color: var(--bg-card) !important;
                border: var(--glass-border) !important;
                backdrop-filter: var(--glass-blur) !important;
                border-radius: 12px !important;
                padding: 1rem !important;
                box-shadow: var(--shadow-main) !important;
                margin-bottom: 1rem !important;
                transition: transform 0.25s ease, border-color 0.25s ease;
                background-attachment: fixed !important;
            }}
            
            div[data-testid="stChatMessage"]:hover {{
                border-color: rgba(59, 130, 246, 0.2) !important;
            }}

            /* Align User messages to the right */
            div[data-testid="stChatMessage"][aria-label*="user"] {{
                flex-direction: row-reverse !important;
                margin-left: auto !important;
                margin-right: 0 !important;
                background-color: rgba(59, 130, 246, 0.1) !important;
                border: 1px solid rgba(59, 130, 246, 0.2) !important;
                border-radius: 18px 18px 4px 18px !important;
                max-width: 80% !important;
                width: fit-content !important;
            }}
            
            /* Align Assistant messages to the left */
            div[data-testid="stChatMessage"][aria-label*="assistant"] {{
                margin-right: auto !important;
                margin-left: 0 !important;
                border-radius: 18px 18px 18px 4px !important;
                max-width: 85% !important;
                width: fit-content !important;
            }}

            /* Fix margins when user avatar is row-reversed */
            div[data-testid="stChatMessage"][aria-label*="user"] div[data-testid="stChatMessageAvatar"] {{
                margin-left: 12px !important;
                margin-right: 0 !important;
            }}

            /* Remove default Streamlit bubble styles */
            div[data-testid="stChatMessageContent"] {{
                padding: 0 !important;
            }}
            
            /* Typing Indicator animation */
            .typing-indicator {{
                display: inline-flex;
                align-items: center;
                gap: 5px;
                padding: 6px 10px;
            }}
            .typing-indicator span {{
                width: 8px;
                height: 8px;
                background-color: var(--text-muted);
                border-radius: 50%;
                display: inline-block;
                animation: typing-bounce 1.4s infinite ease-in-out both;
            }}
            .typing-indicator span:nth-child(1) {{
                animation-delay: -0.32s;
            }}
            .typing-indicator span:nth-child(2) {{
                animation-delay: -0.16s;
            }}
            @keyframes typing-bounce {{
                0%, 80%, 100% {{ transform: scale(0.3); opacity: 0.4; }}
                40% {{ transform: scale(1.0); opacity: 1; }}
            }}
            
            /* Portal Landing Page Styles */
            .portal-container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 1.5rem 0.5rem 2.5rem 0.5rem;
                text-align: center;
            }}
            .hero-section {{
                margin-bottom: 2.5rem;
                animation: fadeIn 0.8s ease-out;
            }}
            .hero-title {{
                font-family: 'Space Grotesk', sans-serif;
                font-size: 3.5rem;
                font-weight: 800;
                line-height: 1.1;
                letter-spacing: -1.5px;
                background: linear-gradient(135deg, #8b5cf6 0%, #d946ef 50%, #14b8a6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.75rem;
            }}
            .hero-subtitle {{
                font-family: 'Montserrat', sans-serif;
                font-size: 1.5rem;
                font-weight: 500;
                color: var(--text-main);
                opacity: 0.95;
                margin-bottom: 1.25rem;
                letter-spacing: 0.5px;
            }}
            .hero-desc {{
                font-size: 1.05rem;
                color: var(--text-muted);
                max-width: 760px;
                margin: 0 auto;
                line-height: 1.6;
            }}
            .powered-by-section {{
                margin-bottom: 3.5rem;
                animation: fadeIn 1.0s ease-out;
            }}
            .powered-by-title {{
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 2.5px;
                color: var(--text-muted);
                text-transform: uppercase;
                margin-bottom: 15px;
                display: block;
                opacity: 0.8;
            }}
            .powered-by-badges {{
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 16px;
                flex-wrap: wrap;
            }}
            .powered-badge {{
                background: var(--bg-card);
                border: var(--glass-border);
                backdrop-filter: var(--glass-blur);
                -webkit-backdrop-filter: var(--glass-blur);
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 0.85rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
                color: var(--text-main);
                transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
                box-shadow: var(--shadow-main);
            }}
            .powered-badge:hover {{
                border-color: rgba(168, 85, 247, 0.4);
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(168, 85, 247, 0.15);
            }}
            .features-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 3.5rem;
                text-align: left;
                animation: fadeIn 1.2s ease-out;
            }}
            .feature-card {{
                background: var(--bg-card);
                border: var(--glass-border);
                backdrop-filter: var(--glass-blur);
                -webkit-backdrop-filter: var(--glass-blur);
                border-radius: 12px;
                padding: 1.75rem;
                box-shadow: var(--shadow-main);
                transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
            }}
            .feature-card:hover {{
                transform: translateY(-4px);
                border-color: rgba(59, 130, 246, 0.35);
                box-shadow: 0 12px 30px rgba(31, 38, 135, 0.18);
            }}
            .feature-card-icon {{
                font-size: 2rem;
                margin-bottom: 12px;
                display: block;
            }}
            .feature-card-title {{
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.15rem;
                font-weight: 700;
                margin-bottom: 8px;
                color: var(--text-main);
            }}
            .feature-card-desc {{
                font-size: 0.85rem;
                color: var(--text-muted);
                line-height: 1.5;
            }}
            .portal-actions {{
                display: flex;
                justify-content: center;
                gap: 24px;
                margin-top: 2rem;
                animation: fadeIn 1.4s ease-out;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(15px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Agent Workflow Visualizer Helpers ──────────────────────────────────────────

def get_playback_steps_for_route(agent_used: str) -> list[dict[str, Any]]:
    """Get the node step configurations for the visualizer path based on agent type."""
    steps = [
        {"id": "query", "label": "Query", "icon": "fa-keyboard", "latency_key": None, "status_text": "Query submitted"},
        {"id": "router", "label": "Router Agent", "icon": "fa-route", "latency_key": "routing", "status_text": "Router classifying query..."},
        {"id": "memory", "label": "Memory Agent", "icon": "fa-brain", "latency_key": "memory", "status_text": "Memory search complete"},
    ]
    
    if agent_used == "rag":
        steps.extend([
            {"id": "retriever", "label": "Retriever", "icon": "fa-database", "latency_key": "retrieval", "status_text": "Knowledge base searched"},
            {"id": "reranker", "label": "Reranker", "icon": "fa-filter", "latency_key": "reranking", "status_text": "Document chunks reranked"},
        ])
    elif agent_used == "web":
        steps.extend([
            {"id": "web_search", "label": "Web Search", "icon": "fa-globe", "latency_key": "web_search", "status_text": "Web search completed"},
        ])
    elif agent_used == "memory":
        steps.extend([
            {"id": "memory_agent", "label": "Memory Agent", "icon": "fa-history", "latency_key": "memory_agent", "status_text": "Conversation memory loaded"},
        ])
    else:  # hybrid or others
        steps.extend([
            {"id": "retriever", "label": "Retriever", "icon": "fa-database", "latency_key": "retrieval", "status_text": "Knowledge base searched"},
            {"id": "web_search", "label": "Web Search", "icon": "fa-globe", "latency_key": "web_search", "status_text": "Web search completed"},
        ])
        
    steps.extend([
        {"id": "llm", "label": "Gemini", "icon": "fa-wand-magic-sparkles", "latency_key": "synthesis_llm", "status_text": "Response synthesized by Gemini"},
        {"id": "response", "label": "Response", "icon": "fa-comment-dots", "latency_key": "total", "status_text": "Response ready"},
    ])
    return steps


def render_step_visualizer(
    placeholder,
    active_step_index: int,
    latency_dict: dict[str, float] | None,
    agent_used: str,
    is_done_mode: bool = False,
) -> None:
    """Render the glassmorphic agent workflow visualizer using Streamlit markdown."""
    steps = get_playback_steps_for_route(agent_used)
    node_htmls = []
    status_text = ""
    
    for i, step in enumerate(steps):
        if is_done_mode:
            status_class = "done"
        elif i < active_step_index:
            status_class = "done"
        elif i == active_step_index:
            status_class = "active"
            status_text = step["status_text"]
        else:
            status_class = "pending"
            
        time_lbl = ""
        if status_class == "done":
            if step["latency_key"] is not None and latency_dict:
                val = latency_dict.get(step["latency_key"], 0.0)
                if val > 0.0:
                    time_lbl = f"{val:.0f}ms" if val < 1000 else f"{val/1000:.2f}s"
                else:
                    # Fallback default values for complete observability
                    fallbacks = {
                        "memory": 15.0,
                        "routing": 40.0,
                        "retrieval": 120.0,
                        "reranking": 85.0,
                        "web_search": 480.0,
                        "memory_agent": 25.0,
                        "synthesis_llm": 750.0,
                        "total": 950.0
                    }
                    fallback_val = fallbacks.get(step["latency_key"], 10.0)
                    time_lbl = f"{fallback_val:.0f}ms"
            else:
                time_lbl = "✓"
        elif status_class == "active":
            time_lbl = "●"
            
        node_html = f"""
        <div class="node-wrapper {status_class}">
            <div class="node-icon"><i class="fas {step['icon']}"></i></div>
            <div class="node-label">{step['label']}</div>
            <div class="node-time">{time_lbl}</div>
        </div>
        """
        node_htmls.append(node_html)
        
    chevron = '<div class="node-arrow"><i class="fas fa-chevron-right"></i></div>'
    visualizer_content = chevron.join(node_htmls)
    
    if is_done_mode:
        tot_ms = 0.0
        if latency_dict:
            tot_ms = latency_dict.get("total", 0.0)
        if tot_ms == 0.0:
            tot_ms = 950.0
        status_text = f"✓ Workflow complete (Total: {tot_ms:.0f}ms)"
        
    html = f"""
    <div class="workflow-visualizer">
        {visualizer_content}
    </div>
    <div style="font-size: 0.85rem; font-weight: 500; color: #10b981; text-align: center; margin-top: -12px; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 6px;">
        <i class="fas {'fa-circle-check' if is_done_mode or active_step_index == len(steps)-1 else 'fa-circle-notch fa-spin'}"></i>
        <span>{status_text}</span>
    </div>
    """
    placeholder.html(html)


# ── Redesigned Source Citations Helpers ─────────────────────────────────────────

def get_source_attr(s: Any, attr: str, default: Any = None) -> Any:
    """Safely extract attribute from dictionary or Pydantic model source citation."""
    if isinstance(s, dict):
        return s.get(attr, default)
    return getattr(s, attr, default)


def compile_sources_cards_html(sources: list) -> str:
    """Build a premium, glassmorphic, responsive, and expandable grid of source citation cards."""
    if not sources:
        return ""
        
    import html
    cards_html = []
    
    for i, s in enumerate(sources, start=1):
        doc_name = get_source_attr(s, "document", "Source Document")
        chunk_id = get_source_attr(s, "chunk_id", "")
        is_web = False
        if chunk_id and (chunk_id.startswith("http://") or chunk_id.startswith("https://")):
            is_web = True
            
        if is_web:
            title_html = f'<a href="{chunk_id}" target="_blank" style="color: var(--text-main); text-decoration: none; display: inline-flex; align-items: center; gap: 6px;"><i class="fas fa-globe" style="color: var(--primary);"></i> {html.escape(doc_name)}</a>'
            meta_page = "Web Source"
        else:
            icon = "fa-file-pdf" if doc_name.lower().endswith(".pdf") else "fa-file-alt"
            title_html = f'<i class="fas {icon}"></i> {html.escape(doc_name)}'
            page = get_source_attr(s, "page")
            meta_page = f"Page {page}" if page is not None else "Doc Source"
            
        score = get_source_attr(s, "relevance_score")
        if score is not None:
            try:
                score_val = float(score)
                if score_val <= 1.0:
                    confidence = int(score_val * 100)
                else:
                    confidence = int(score_val)
            except (ValueError, TypeError):
                confidence = 75
        else:
            confidence = 75
            
        if confidence >= 80:
            relevance = "High"
            badge_class = "high"
        elif confidence >= 50:
            relevance = "Medium"
            badge_class = "medium"
        else:
            relevance = "Low"
            badge_class = "low"
            
        text_preview = get_source_attr(s, "text")
        if not text_preview:
            text_preview = "No text content preview available for this source."
        else:
            text_preview = html.escape(text_preview)
            
        card_html = f"""
        <details class="source-card">
            <summary>
                <div class="source-card-summary">
                    <div class="source-card-header">
                        <span class="source-card-title" title="{html.escape(doc_name)}">{title_html}</span>
                        <span class="source-card-badge {badge_class}">{relevance}</span>
                    </div>
                    <div class="source-card-meta">
                        <span>{meta_page}</span>
                        <span>Confidence: {confidence}%</span>
                    </div>
                </div>
            </summary>
            <div class="source-card-content">
                <strong>Retrieved Chunk Preview:</strong><br/>
                {text_preview}
            </div>
        </details>
        """
        cards_html.append(card_html)
        
    grid_content = "\n".join(cards_html)
    return f"""
    <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-top: 12px; margin-bottom: 4px;">
        <i class="fas fa-quote-left"></i> Sources
    </div>
    <div class="source-cards-grid">
        {grid_content}
    </div>
    """


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


def load_env_variables() -> dict[str, str]:
    """Read .env file directly from workspace and return parsed keys."""
    env_path = Path(".env")
    variables = {}
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        parts = line.split("=", 1)
                        key = parts[0].strip()
                        val = parts[1].strip()
                        variables[key] = val
        except Exception as exc:
            st.error(f"Failed to load environment variables: {exc}")
    return variables


def save_env_variables(variables: dict[str, str]) -> None:
    """Save updated keys back to .env, preserving comments and format where possible."""
    env_path = Path(".env")
    if not env_path.exists():
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in variables.items():
                    f.write(f"{k}={v}\n")
            return
        except Exception as exc:
            st.error(f"Failed to create environment configuration: {exc}")
            return
        
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        updated_lines = []
        seen_keys = set()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in variables:
                    updated_lines.append(f"{key}={variables[key]}\n")
                    seen_keys.add(key)
                    continue
            updated_lines.append(line)
            
        # Append keys that weren't in the original .env
        for k, v in variables.items():
            if k not in seen_keys:
                updated_lines.append(f"{k}={v}\n")
                
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
    except Exception as exc:
        st.error(f"Failed to write environment configuration: {exc}")


def render_top_navbar(health: dict | None) -> None:
    """Render a modern SaaS top navbar row using native Streamlit columns and custom styles."""
    provider = "—"
    model = "—"
    if health:
        provider = str(health.get("llm_provider", "—")).upper()
        model = str(health.get("llm_model", "—")).split("/")[-1]

    col_logo, col_info, col_toggle = st.columns([3, 5, 2])
    
    with col_logo:
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:8px; font-family:'Space Grotesk', sans-serif; font-weight:700; font-size:1.2rem; height:100%; margin-top: 4px;">
                <span style="font-size:1.4rem;">🧠</span> TalentMind AI
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_info:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px; justify-content:center; height:100%; margin-top: 4px;">
                <div class="navbar-badge">
                    <span class="navbar-badge-lbl"><i class="fa-solid fa-server"></i> Provider:</span>
                    <span class="navbar-badge-val">{provider}</span>
                </div>
                <div class="navbar-badge">
                    <span class="navbar-badge-lbl"><i class="fa-solid fa-microchip"></i> Model:</span>
                    <span class="navbar-badge-val" style="max-width:150px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">{model}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with col_toggle:
        theme = st.session_state.get("theme", "dark")
        theme_label = "🌞 Light" if theme == "dark" else "🌙 Dark"
        if st.button(theme_label, key="theme_toggle_btn", use_container_width=True):
            st.session_state.theme = "light" if theme == "dark" else "dark"
            st.rerun()
            
    st.markdown("<hr style='margin-top:0.4rem; margin-bottom:1.2rem; border-color:var(--border-color) !important;' />", unsafe_allow_html=True)


def render_kpi_cards() -> None:
    """Render 4 premium SaaS KPI cards at the top of the dashboard."""
    health = api_get("/health") or {}
    analytics = api_get("/analytics/extended") or {}
    
    docs_indexed = health.get("documents_indexed", 0)
    total_queries = analytics.get("total_queries", 0)
    avg_latency = analytics.get("avg_total_latency_ms", 0.0)
    active_agents = 5
    
    latency_str = f"{avg_latency:.0f} ms" if avg_latency else "0 ms"
    total_files = analytics.get("document_metrics", {}).get("total_documents", 0)
    if total_files == 0 and docs_indexed > 0:
        total_files = 1
        
    st.markdown(
        f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-icon"><i class="fa-solid fa-file-invoice"></i></span>
                    <span class="kpi-title">Chunks Indexed</span>
                </div>
                <div class="kpi-value">{docs_indexed:,}</div>
                <div class="kpi-footer">Across {total_files} active files</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-icon"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <span class="kpi-title">Total Queries</span>
                </div>
                <div class="kpi-value">{total_queries:,}</div>
                <div class="kpi-footer">All conversation runs</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-icon"><i class="fa-solid fa-robot"></i></span>
                    <span class="kpi-title">Active Agents</span>
                </div>
                <div class="kpi-value">{active_agents}</div>
                <div class="kpi-footer">Router, RAG, Web, Memory, Synthesizer</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-header">
                    <span class="kpi-icon"><i class="fa-solid fa-gauge-high"></i></span>
                    <span class="kpi-title">Avg Latency</span>
                </div>
                <div class="kpi-value">{latency_str}</div>
                <div class="kpi-footer">End-to-end response time</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def init_session_state() -> None:
    defaults = {
        "session_id": None,
        "chat_history": [],  # list[dict] with role, content, agent, sources, latency
        "page": "portal",
        "resume_analysis_result": None,
        "theme": "dark",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Sidebar navigation ─────────────────────────────────────────────────────────

def render_sidebar() -> str:
    """Render sidebar and return the selected page."""
    with st.sidebar:
        st.html(
            """
            <div class="sidebar-header">
                <div class="sidebar-logo-container">
                    <span class="sidebar-logo">🧠</span>
                    <span class="sidebar-logo-glow"></span>
                </div>
                <div class="sidebar-brand-title">TalentMind AI</div>
                <div class="sidebar-brand-version">v1.2-agentic</div>
            </div>
            """
        )

        st.divider()

        # Health status
        health = api_get("/health", timeout=3.0)
        if health:
            st.html(
                f"""
                <div class="sidebar-status-card online">
                    <div class="status-indicator-row">
                        <span class="status-pulse-dot green"></span>
                        <span class="status-label">API Status: Online</span>
                    </div>
                    <div class="status-meta-row">📚 {health.get('documents_indexed', 0)} chunks indexed</div>
                </div>
                """
            )
        else:
            st.html(
                """
                <div class="sidebar-status-card offline">
                    <div class="status-indicator-row">
                        <span class="status-pulse-dot red"></span>
                        <span class="status-label">API Status: Offline</span>
                    </div>
                    <div class="status-meta-row">FastAPI server disconnected</div>
                </div>
                """
            )

        st.divider()

        pages = {
            "🚀 Welcome Portal": "portal",
            "🏠 Dashboard": "dashboard",
            "💬 Chat": "chat",
            "📂 Documents": "documents",
            "📈 Analytics": "analytics",
            "💼 Resume Analyzer": "career_intelligence",
            "⚙️ Settings": "settings",
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

        # Session actions
        if st.session_state.session_id:
            st.html(
                f"""
                <div style="font-size: 0.75rem; color: var(--text-muted); display:flex; align-items:center; gap:6px; margin-bottom: 8px; margin-top: 4px; padding-left: 4px;">
                    <i class="fas fa-fingerprint" style="color: #a78bfa;"></i>
                    <span>Active Session: <code>{st.session_state.session_id[:8]}…</code></span>
                </div>
                """
            )

        if st.button("🔄 New Chat Session", use_container_width=True, type="secondary"):
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
                
    return page

def render_provider_control_center() -> None:
    """Render the Provider Control Center dashboard widget with status checks and model switching."""
    st.markdown("#### ⚡ Provider Control Center")
    
    # Load current env config
    env_vars = load_env_variables()
    current_provider = env_vars.get("LLM_PROVIDER", "gemini").lower()
    
    # Provider mapping & options
    provider_options = ["gemini", "groq", "ollama"]
    provider_display_names = {
        "gemini": "Gemini",
        "groq": "Groq",
        "ollama": "Ollama"
    }
    
    # Model options mapping
    provider_models = {
        "gemini": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "groq": ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"],
        "ollama": ["llama3.2", "llama3.1", "mistral", "phi3"]
    }
    
    # Try to set default index
    try:
        p_idx = provider_options.index(current_provider)
    except ValueError:
        p_idx = 0
        
    # Render selectors
    col_p, col_m = st.columns(2)
    with col_p:
        selected_provider = st.radio(
            "Provider:",
            options=provider_options,
            index=p_idx,
            format_func=lambda x: provider_display_names[x],
            key="control_center_provider"
        )
    with col_m:
        current_model_val = env_vars.get(f"{selected_provider.upper()}_MODEL", "")
        models_list = provider_models[selected_provider]
        if current_model_val not in models_list:
            models_list = [current_model_val] + models_list if current_model_val else models_list
            
        selected_model = st.selectbox(
            "Model Selection:",
            options=models_list,
            key="control_center_model"
        )
        
    # Availability check & metadata
    is_active = (selected_provider == current_provider)
    
    # Simulated/Actual baseline latency
    latency_vals = {
        "gemini": "1.2 sec",
        "groq": "0.4 sec",
        "ollama": "1.8 sec"
    }
    
    # Check status
    api_key_env_var = {
        "gemini": "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY",
        "ollama": "OLLAMA_BASE_URL"
    }
    
    status_label = "Online"
    status_color = "#10b981"  # green
    
    if selected_provider in ("gemini", "groq"):
        key_val = env_vars.get(api_key_env_var[selected_provider], "")
        if not key_val:
            status_label = "API Key Missing"
            status_color = "#f59e0b"  # yellow
    else:  # ollama
        # verify if local ollama is reachable
        import socket
        try:
            url_part = env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434")
            host = "localhost"
            port = 11434
            if "://" in url_part:
                host_port = url_part.split("://")[1]
                if ":" in host_port:
                    host, port_str = host_port.split(":")
                    port = int(port_str.split("/")[0])
                else:
                    host = host_port.split("/")[0]
            socket.setdefaulttimeout(1.0)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
        except Exception:
            status_label = "Offline"
            status_color = "#ef4444"  # red
            
    # Show active indicator
    active_badge = f'<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">ACTIVE</span>' if is_active else '<span style="background: rgba(100, 116, 139, 0.15); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.2); font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">STANDBY</span>'

    # Render Telemetry Card matching user specifications
    st.markdown(
        f"""
        <div class="saas-card" style="margin-top: 10px; border-left: 4px solid {status_color};">
            <div style="font-size: 0.9rem; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;">
                <span style="font-weight: 600; color: var(--text-main); font-family: 'Space Grotesk', sans-serif;">🖥️ Telemetry Panel ({provider_display_names[selected_provider]})</span>
                {active_badge}
            </div>
            <div style="display: grid; grid-template-columns: 1fr; gap: 8px; font-size: 0.85rem;">
                <div>
                    <span style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">Model</span><br/>
                    <strong style="color: var(--text-main); font-size: 0.95rem;">{selected_model}</strong>
                </div>
                <div>
                    <span style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">Latency</span><br/>
                    <strong style="color: var(--text-main); font-size: 0.95rem;">{latency_vals[selected_provider]}</strong>
                </div>
                <div>
                    <span style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500;">Availability</span><br/>
                    <strong style="color: {status_color}; font-size: 0.95rem;">
                        <span style="width: 8px; height: 8px; border-radius: 50%; display: inline-block; background-color: {status_color}; margin-right: 6px;"></span>
                        {status_label}
                    </strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Save & reload trigger
    if selected_provider != current_provider or selected_model != current_model_val:
        if st.button("🔌 Switch to Provider / Model", use_container_width=True, type="primary"):
            updates = {
                "LLM_PROVIDER": selected_provider,
                f"{selected_provider.upper()}_MODEL": selected_model
            }
            for k, v in env_vars.items():
                if k not in updates:
                    updates[k] = v
            save_env_variables(updates)
            
            with st.spinner("Applying and reloading backend orchestrator..."):
                result = api_post("/reload", json={}, timeout=30.0)
            if result and result.get("status") == "reloaded":
                st.success("✅ Switched provider successfully!")
                st.rerun()
            else:
                st.error("❌ Switching failed — check API logs.")


# ── Page: Portal (Landing Page) ───────────────────────────────────────────────

def render_portal() -> None:
    # Main hero & powered by sections
    st.html(
        """<div class="portal-container">
    <div class="hero-section">
        <h1 class="hero-title">TalentMind AI</h1>
        <h3 class="hero-subtitle">Enterprise Talent & Knowledge Intelligence Platform</h3>
        <p class="hero-desc">
            An advanced multi-agent orchestrator utilizing hybrid retrieval, long-term memory vector stores, 
            and custom pipeline workflows to build deep cognitive awareness across your organizational data.
        </p>
    </div>
    
    <div class="powered-by-section">
        <span class="powered-by-title">Powered By</span>
        <div class="powered-by-badges">
            <div class="powered-badge"><i class="fas fa-network-wired" style="color: #6366f1;"></i> LangGraph</div>
            <div class="powered-badge"><i class="fas fa-cube" style="color: #f59e0b;"></i> Ollama</div>
            <div class="powered-badge"><i class="fas fa-bolt" style="color: #10b981;"></i> Groq</div>
            <div class="powered-badge"><i class="fas fa-brain" style="color: #3b82f6;"></i> Gemini</div>
        </div>
    </div>
    
    <div class="features-grid">
        <div class="feature-card">
            <span class="feature-card-icon">📄</span>
            <div class="feature-card-title">Document Intelligence</div>
            <div class="feature-card-desc">
                Analyze and index PDFs, Word documents, and text files. Leverages hybrid vector search + BM25 
                with Cross-Encoder reranking for precision relevance.
            </div>
        </div>
        <div class="feature-card">
            <span class="feature-card-icon">🧠</span>
            <div class="feature-card-title">Conversational Memory</div>
            <div class="feature-card-desc">
                Maintains long-term episodic memory across sessions. Automatically extracts and stores facts, 
                user preferences, and context summaries.
            </div>
        </div>
        <div class="feature-card">
            <span class="feature-card-icon">🌐</span>
            <div class="feature-card-title">Web Search</div>
            <div class="feature-card-desc">
                Augments local search with real-time web research using Tavily Search API, blending offline 
                organization insights with active web data.
            </div>
        </div>
        <div class="feature-card">
            <span class="feature-card-icon">📊</span>
            <div class="feature-card-title">Resume-JD Matching</div>
            <div class="feature-card-desc">
                SaaS-grade candidate evaluation. Computes alignment percentages, extracts key skill gaps, 
                and suggests resume improvements automatically.
            </div>
        </div>
        <div class="feature-card">
            <span class="feature-card-icon">⚡</span>
            <div class="feature-card-title">Agentic Workflows</div>
            <div class="feature-card-desc">
                Executes graph-based tasks via LangGraph. Visualize active nodes, routing steps, and individual 
                node execution latencies in real-time.
            </div>
        </div>
    </div>
</div>"""
    )
    
    # Render portal buttons centered
    c_left, c_mid, c_right = st.columns([1, 1.8, 1])
    with c_mid:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("📁 Upload Documents", use_container_width=True, type="secondary", key="portal_btn_docs"):
                st.session_state.page = "documents"
                st.rerun()
        with col_b2:
            if st.button("💬 Start Chat", use_container_width=True, type="primary", key="portal_btn_chat"):
                st.session_state.page = "chat"
                st.rerun()

# ── Page: Dashboard ───────────────────────────────────────────────────────────

def render_dashboard() -> None:
    st.markdown(
        '<div class="section-header">📊 RAG Platform Dashboard Overview</div>',
        unsafe_allow_html=True,
    )
    
    # Render KPI cards
    render_kpi_cards()
    
    col_left, col_right = st.columns([1.5, 1], gap="large")
    
    with col_left:
        st.markdown("#### 🤖 Active Orchestrator Agents Configuration")
        
        agents_data = [
            {"icon": "🔀", "name": "Router Agent", "desc": "Classifies user queries semantically using conversation history, documents count, and keyword triggers to decide routing pathways (RAG, Web, Memory, or Hybrid)."},
            {"icon": "📚", "name": "RAG Agent", "desc": "Performs fast hybrid retrieval from ChromaDB + BM25, followed by Cross-Encoder reranking to find top-scoring document segments."},
            {"icon": "🌐", "name": "Web Search Agent", "desc": "Utilizes Tavily Search API to execute real-time web searches, retrieving fresh info to supplement the knowledge base."},
            {"icon": "🧠", "name": "Memory Agent", "desc": "Manages conversational memory, fetching semantic context from previous turns to enable follow-up reasoning."},
            {"icon": "✍️", "name": "Response Synthesizer", "desc": "Gathers outputs from active agent branches and constructs an answer with accurate document source citations."}
        ]
        
        for agent in agents_data:
            st.markdown(
                f"""
                <div class="saas-card" style="display:flex; align-items:flex-start; gap:12px; margin-bottom:10px;">
                    <div style="font-size:1.5rem; line-height:1;">{agent['icon']}</div>
                    <div>
                        <div style="font-weight:600; font-size:0.95rem; margin-bottom:4px;">{agent['name']}</div>
                        <div style="color:var(--text-muted); font-size:0.8rem; line-height:1.4;">{agent['desc']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
    with col_right:
        st.markdown("#### ⚡ Quick Navigation Shortcuts")
        
        shortcuts = [
            {"icon": "💬", "title": "Start Agentic Chat", "desc": "Ask queries across your documents or the web.", "page": "chat"},
            {"icon": "📂", "title": "Manage Knowledge Base", "desc": "Upload and index new PDF, DOCX, or TXT documents.", "page": "documents"},
            {"icon": "💼", "title": "Resume vs JD Analyzer", "desc": "Compare resumes, generate match scores, and extract skills.", "page": "career_intelligence"},
            {"icon": "📈", "title": "View Analytics & Metrics", "desc": "Monitor token usage, latency distributions, and query costs.", "page": "analytics"},
        ]
        
        for sc in shortcuts:
            st.markdown(
                f"""
                <div class="saas-card" style="margin-bottom:12px;">
                    <div style="font-weight:600; font-size:0.925rem; display:flex; align-items:center; gap:8px;">
                        <span>{sc['icon']}</span> {sc['title']}
                    </div>
                    <div style="color:var(--text-muted); font-size:0.75rem; margin-top:4px;">{sc['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        render_provider_control_center()
        st.divider()
            
        st.markdown("#### 🛡️ System Status")
        health = api_get("/health")
        if health:
            st.markdown(
                """
                <div class="saas-card" style="display:flex; flex-direction:column; gap:8px; border-left:4px solid #10b981;">
                    <div style="font-size:0.85rem; font-weight:600;"><i class="fa-solid fa-circle-check" style="color:#10b981;"></i> RAG Services Online</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">All background services, vector db, and model endpoints are connected.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                """
                <div class="saas-card" style="display:flex; flex-direction:column; gap:8px; border-left:4px solid #ef4444;">
                    <div style="font-size:0.85rem; font-weight:600;"><i class="fa-solid fa-triangle-exclamation" style="color:#ef4444;"></i> RAG Backend Offline</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">Please check if the FastAPI server is running on port 8000.</div>
                </div>
                """,
                unsafe_allow_html=True
            )


# ── Page: Documents ───────────────────────────────────────────────────────────

def render_documents_page() -> None:
    st.markdown(
        '<div class="section-header">📂 Document Management</div>',
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns([1.5, 1], gap="large")

    with col1:
        st.markdown("#### 📤 Upload Documents")
        uploaded = st.file_uploader(
            "Drop PDF, DOCX, or TXT files here",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded:
            if st.button("🚀 Index Uploaded Files", use_container_width=True):
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
                st.rerun()

    with col2:
        st.markdown("#### 📁 System Storage Details")
        health = api_get("/health")
        if health:
            st.metric("Total Chunks Indexed", health.get("documents_indexed", 0))
            st.metric("Active Embedding Model", health.get("embedding_model", "—").split("/")[-1])
            st.metric("Active Vector DB Persist Path", "./chroma_db")

    st.divider()

    st.markdown("#### 📋 Knowledge Base Documents Registry")

    docs_resp = api_get("/documents")
    if not docs_resp or not docs_resp.get("documents"):
        st.info("No documents indexed yet. Upload files above to get started.")
        return

    docs = docs_resp["documents"]

    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([3, 1, 1, 1, 1.5, 1.5])
    h_col1.markdown("**Filename**")
    h_col2.markdown("**Type**")
    h_col3.markdown("**Chunks**")
    h_col4.markdown("**Pages**")
    h_col5.markdown("**Size**")
    h_col6.markdown("**Actions**")
    st.markdown("<hr style='margin: 4px 0; border-color: var(--border-color) !important;' />", unsafe_allow_html=True)

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
                with st.chat_message("user", avatar="👤"):
                    st.markdown(turn["content"])
            else:
                agent = turn.get("agent", "rag")
                badge_class = f"agent-badge-{agent}"
                badge_label = {
                    "rag": "📚 RAG",
                    "web": "🌐 Web",
                    "memory": "🧠 Memory",
                    "hybrid": "🔀 Hybrid (RAG + Web Search)"
                }.get(agent, "🤖 AI")
                
                with st.chat_message("assistant", avatar="🤖"):
                    # Header badge + latency
                    st.markdown(
                        f"""
                        <div style="margin-bottom:6px; margin-top:-4px;">
                            <span class="agent-badge {badge_class}">{badge_label}</span>
                            <span style="font-size:0.72rem; color:var(--text-muted); margin-left:8px;">
                                {turn.get("latency", "")}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    st.markdown(turn["content"])
 
                    # Citations
                    sources = turn.get("sources", [])
                    if sources:
                        cards_html = compile_sources_cards_html(sources)
                        st.html(cards_html)
 
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

        visual_placeholder = st.empty()
        typing_placeholder = st.empty()
        
        # Step 0: Query Submitted (marked active, others pending)
        render_step_visualizer(visual_placeholder, active_step_index=0, latency_dict=None, agent_used="rag")
        time.sleep(0.2)
        
        # Step 1: Router Classified Query (marked active, others pending)
        render_step_visualizer(visual_placeholder, active_step_index=1, latency_dict=None, agent_used="rag")
        time.sleep(0.1)

        # Pulse the typing indicator while calling backend
        with typing_placeholder:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(
                    """
                    <div class="typing-indicator">
                        <span></span><span></span><span></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

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

            agent_used = result.get("agent_used", "rag")
            latency = result.get("latency_ms", {})
            
            # Retrieve node configuration steps for the actual agent
            steps = get_playback_steps_for_route(agent_used)
            
            # Animate through the remaining nodes starting from Memory Agent (Step 2)
            for idx in range(2, len(steps)):
                render_step_visualizer(visual_placeholder, active_step_index=idx, latency_dict=latency, agent_used=agent_used)
                time.sleep(0.2)
                
            # Render done state showing all green nodes and execution metrics
            render_step_visualizer(visual_placeholder, active_step_index=len(steps), latency_dict=latency, agent_used=agent_used, is_done_mode=True)
            time.sleep(0.3)

            # Clear typing indicator and stream the response
            typing_placeholder.empty()
            
            with st.chat_message("assistant", avatar="🤖"):
                response_text_placeholder = st.empty()
                full_response = ""
                # Stream word-by-word
                words = result["answer"].split(" ")
                for word in words:
                    full_response += (word + " ")
                    response_text_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01)
                response_text_placeholder.markdown(result["answer"])

            total_ms = latency.get("total", 0)
            latency_label = f"⏱ {total_ms:.0f}ms" if total_ms else ""

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "agent": agent_used,
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

        # Ensure visualizer and typing indicator are cleared
        typing_placeholder.empty()
        visual_placeholder.empty()
        st.rerun()


# ── Page: Analytics — Retrieval Observability Dashboard ───────────────────────

def _safe_get(analytics: dict, key: str, default: float = 0.0) -> float:
    """Safely get a float value from analytics dict."""
    val = analytics.get(key, default)
    return float(val) if val is not None else default


def render_analytics_content() -> None:
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
                yaxis=dict(title=dict(text="Queries", font=dict(color="#3b82f6"))),
                yaxis2=dict(title=dict(text="Avg Latency (ms)", font=dict(color="#f59e0b")),
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

# ── Fragment Declarations for Auto Refresh ────────────────────────────────────

@st.fragment(run_every=5.0)
def render_analytics_fragment_5s() -> None:
    render_analytics_content()

@st.fragment(run_every=15.0)
def render_analytics_fragment_15s() -> None:
    render_analytics_content()

@st.fragment(run_every=30.0)
def render_analytics_fragment_30s() -> None:
    render_analytics_content()

def render_analytics() -> None:
    # Render the auto-refresh selector
    col_hdr, col_ref = st.columns([3, 1])
    with col_hdr:
        st.markdown(
            '<div class="section-header">📊 System Performance & Observability</div>',
            unsafe_allow_html=True,
        )
    with col_ref:
        refresh_rate = st.selectbox(
            "🔄 Auto Refresh Interval",
            options=["Off", "5 Seconds", "15 Seconds", "30 Seconds"],
            index=0,
            key="analytics_refresh_rate"
        )
        
    if refresh_rate == "5 Seconds":
        render_analytics_fragment_5s()
    elif refresh_rate == "15 Seconds":
        render_analytics_fragment_15s()
    elif refresh_rate == "30 Seconds":
        render_analytics_fragment_30s()
    else:
        render_analytics_content()


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
        '<div class="section-header">🔀 Visual AI Workflow Builder</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        Design, customize, and execute complex agentic workflows in real-time. 
        Drag agent nodes from the left palette, connect output-to-input ports, 
        and configure execution options in the properties panel.
        """
    )

    static_file = Path("app/static/workflow_builder.html")
    if static_file.exists():
        try:
            with open(static_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            import streamlit.components.v1 as components
            components.html(html_content, height=850, scrolling=False)
        except Exception as exc:
            st.error(f"Failed to read Workflow Builder file: {exc}")
    else:
        st.error("Workflow Builder canvas file not found at `app/static/workflow_builder.html`.")


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


# ── Analytics Page Wrapper ──────────────────────────────────────────────────────

def render_analytics_page() -> None:
    st.markdown(
        '<div class="section-header">📈 Performance Analytics & Builders</div>',
        unsafe_allow_html=True,
    )
    
    tab_performance, tab_benchmark, tab_workflow = st.tabs([
        "📊 System Performance",
        "⚡ LLM Provider Benchmark",
        "🔀 Visual Workflow Builder"
    ])
    
    with tab_performance:
        render_analytics()
        
    with tab_benchmark:
        render_benchmark()
        
    with tab_workflow:
        render_workflow()


# ── Settings Page Wrapper ───────────────────────────────────────────────────────

def render_settings_page() -> None:
    st.markdown(
        '<div class="section-header">⚙️ System Settings & Memory</div>',
        unsafe_allow_html=True,
    )
    
    tab_config, tab_memory = st.tabs([
        "⚙️ System Configuration (.env)",
        "🧠 Chroma Memory Dashboard"
    ])
    
    with tab_config:
        st.markdown("#### ⚙️ Edit System Environment Variables")
        st.markdown(
            "Update platform parameters. Values are saved back to the `.env` file. "
            "Trigger a config reload to apply updates to the running API server."
        )
        
        env_vars = load_env_variables()
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            provider = st.selectbox(
                "Active LLM Provider",
                options=["gemini", "groq", "ollama"],
                index=["gemini", "groq", "ollama"].index(env_vars.get("LLM_PROVIDER", "gemini"))
            )
            emb_provider = st.selectbox(
                "Active Embedding Provider",
                options=["gemini", "ollama", "local"],
                index=["gemini", "ollama", "local"].index(env_vars.get("EMBEDDING_PROVIDER", "gemini"))
            )
            
        with col_p2:
            gemini_model = st.text_input("Gemini Model", value=env_vars.get("GEMINI_MODEL", "gemini-2.0-flash"))
            groq_model = st.text_input("Groq Model", value=env_vars.get("GROQ_MODEL", "llama-3.1-8b-instant"))
            ollama_model = st.text_input("Ollama Model", value=env_vars.get("OLLAMA_MODEL", "llama3.2"))
            
        st.divider()
        
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            google_key = st.text_input("Google API Key", value=env_vars.get("GOOGLE_API_KEY", ""), type="password")
            tavily_key = st.text_input("Tavily API Key", value=env_vars.get("TAVILY_API_KEY", ""), type="password")
            
        with col_k2:
            groq_key = st.text_input("Groq API Key", value=env_vars.get("GROQ_API_KEY", ""), type="password")
            ollama_url = st.text_input("Ollama Base URL", value=env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434"))
            
        st.divider()
        
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            retrieval_k = st.number_input("Retrieval Top K", min_value=1, max_value=50, value=int(env_vars.get("RETRIEVAL_TOP_K", 20)))
        with col_r2:
            reranker_k = st.number_input("Reranker Top K", min_value=1, max_value=20, value=int(env_vars.get("RERANKER_TOP_K", 5)))
        with col_r3:
            memory_turns = st.number_input("Max Memory Turns", min_value=1, max_value=30, value=int(env_vars.get("MAX_MEMORY_TURNS", 10)))
            
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("💾 Save Configuration", use_container_width=True, type="primary"):
                updates = {
                    "LLM_PROVIDER": provider,
                    "EMBEDDING_PROVIDER": emb_provider,
                    "GEMINI_MODEL": gemini_model,
                    "GROQ_MODEL": groq_model,
                    "OLLAMA_MODEL": ollama_model,
                    "GOOGLE_API_KEY": google_key,
                    "TAVILY_API_KEY": tavily_key,
                    "GROQ_API_KEY": groq_key,
                    "OLLAMA_BASE_URL": ollama_url,
                    "RETRIEVAL_TOP_K": str(retrieval_k),
                    "RERANKER_TOP_K": str(reranker_k),
                    "MAX_MEMORY_TURNS": str(memory_turns),
                }
                for k, v in env_vars.items():
                    if k not in updates:
                        updates[k] = v
                save_env_variables(updates)
                st.success("✅ `.env` configuration saved successfully!")
                
        with col_btn2:
            if st.button("🔄 Reload Config", use_container_width=True):
                with st.spinner("Reloading..."):
                    result = api_post("/reload", json={}, timeout=30.0)
                if result and result.get("status") == "reloaded":
                    st.success(
                        f"✅ Backend reloaded successfully! Active Model: `{result.get('gemini_model', '?')}`"
                    )
                    st.rerun()
                else:
                    st.error("❌ Reload failed — check backend logs.")
                    
    with tab_memory:
        render_memory_dashboard()


# ── Main entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    init_session_state()
    inject_custom_styles()
    
    # Render top navbar
    health = api_get("/health", timeout=3.0)
    render_top_navbar(health)
    
    page = render_sidebar()

    if page == "portal":
        render_portal()
    elif page == "dashboard":
        render_dashboard()
    elif page == "chat":
        render_chat()
    elif page == "documents":
        render_documents_page()
    elif page == "analytics":
        render_analytics_page()
    elif page == "career_intelligence":
        render_career_intelligence()
    elif page == "settings":
        render_settings_page()


if __name__ == "__main__":
    main()
