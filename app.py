"""
AI Business Analyst Copilot — entry point.

This file is intentionally thin: it configures the page, injects the
existing stylesheet (assets/style.css, unchanged), and wires up
Streamlit's native multipage navigation. All analysis logic and all
render_* functions live in components.py and are unchanged from the
single-page version — this file does not compute anything itself.
"""

import streamlit as st

from components import inject_custom_css

st.set_page_config(
    page_title="AI Business Analyst Copilot",
    page_icon="📊",
    layout="wide",
)

inject_custom_css()

pages = [
    st.Page("app_pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("app_pages/dashboard.py", title="Dashboard", icon="📊"),
    st.Page("app_pages/datasets.py", title="Datasets", icon="🗂️"),
    st.Page("app_pages/ai_copilot.py", title="AI Copilot", icon="💬"),
    st.Page("app_pages/executive_summary.py", title="Executive Summary", icon="✨"),
    st.Page("app_pages/data_dictionary.py", title="Data Dictionary", icon="📖"),
    st.Page("app_pages/settings.py", title="Settings", icon="⚙️"),
]

st.sidebar.markdown(
    """
    <div style="display:flex;align-items:center;gap:0.55rem;padding-bottom:0.75rem;
                margin-bottom:0.5rem;border-bottom:1px solid #E5E7EB;">
        <div style="width:32px;height:32px;border-radius:9px;
                    background:linear-gradient(135deg,#4F46E5,#2563EB);
                    display:flex;align-items:center;justify-content:center;
                    font-size:1rem;">📊</div>
        <span style="font-weight:800;font-size:1.02rem;color:#0F172A;">
            AI Business Analyst Copilot
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

nav = st.navigation(pages)
nav.run()
