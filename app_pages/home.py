import streamlit as st

import config
from components import has_data, home_ai_suggestions, render_section_header

# -----------------------------------------------------------------------
# Hero
# -----------------------------------------------------------------------

st.markdown(
    """
    <div class="sa-hero" style="margin-bottom:0.5rem;">
        <div>
            <p style="color:#4F46E5;font-weight:700;font-size:0.8rem;
                      letter-spacing:0.06em;text-transform:uppercase;margin:0 0 0.3rem 0;">
                SOA Analytics
            </p>
            <h1 style="font-size:1.9rem;margin-bottom:0.2rem;">Welcome back, Samuel 👋</h1>
            <p style="font-size:1.05rem;color:#0F172A;font-weight:600;margin:0 0 0.15rem 0;">
                AI Business Analytics Copilot
            </p>
            <p style="color:#64748B;margin:0;">
                Transform your business data into actionable insights using AI.
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------
# Quick Actions
# -----------------------------------------------------------------------

render_section_header("⚡", "Quick Actions")

qa_cols = st.columns(4)
quick_actions = [
    ("📁", "Upload Dataset", "Upload and analyze a new CSV or Excel dataset.", "app_pages/datasets.py"),
    ("🤖", "Ask AI Copilot", "Open the AI assistant to ask business questions.", "app_pages/ai_copilot.py"),
    ("📊", "Open Dashboard", "View KPIs, charts, and business performance.", "app_pages/dashboard.py"),
    ("📄", "Executive Summary", "Generate AI-powered executive insights.", "app_pages/executive_summary.py"),
]
for col, (icon, title, desc, page) in zip(qa_cols, quick_actions):
    with col:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="font-size:1.6rem;margin-bottom:0.4rem;">{icon}</div>
                <div style="font-weight:700;color:#0F172A;margin-bottom:0.3rem;">{title}</div>
                <div style="font-size:0.85rem;color:#64748B;min-height:2.6rem;">{desc}</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"qa_{title}", use_container_width=True):
                st.switch_page(page)

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Continue Working
# -----------------------------------------------------------------------

render_section_header("🔄", "Continue Working")

with st.container(border=True):
    if has_data():
        profile = st.session_state["profile"]
        filename = st.session_state.get("dataset_filename", "Current dataset")
        uploaded_at = st.session_state.get("dataset_uploaded_at")
        # Data completeness is the same total_missing_pct already shown
        # on the Datasets page's Data Profile card — just re-expressed
        # as a completeness percentage, not a new metric.
        completeness = round(100 - profile["total_missing_pct"], 1)

        info_cols = st.columns(5)
        info_cols[0].metric("Filename", filename)
        info_cols[1].metric("Rows", f"{profile['n_rows']:,}")
        info_cols[2].metric("Columns", f"{profile['n_columns']:,}")
        info_cols[3].metric("Uploaded", uploaded_at.strftime("%b %d, %I:%M %p") if uploaded_at else "—")
        info_cols[4].metric("Data Completeness", f"{completeness}%")

        st.markdown("&nbsp;", unsafe_allow_html=True)
        btn_cols = st.columns(4)
        if btn_cols[0].button("Continue Analysis", use_container_width=True):
            st.switch_page("app_pages/dashboard.py")
        if btn_cols[1].button("Ask AI", use_container_width=True):
            st.switch_page("app_pages/ai_copilot.py")
        if btn_cols[2].button("Open Dashboard", use_container_width=True):
            st.switch_page("app_pages/dashboard.py")
        if btn_cols[3].button("Generate Executive Summary", use_container_width=True):
            st.switch_page("app_pages/executive_summary.py")
    else:
        st.info("No dataset loaded yet. Upload a CSV or Excel file to get started.")
        if st.button("Upload a dataset", use_container_width=True):
            st.switch_page("app_pages/datasets.py")

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Two-column: Recent Activity | AI Suggestions
# -----------------------------------------------------------------------

left, right = st.columns(2)

with left:
    render_section_header("🕒", "Recent Activity")
    with st.container(border=True):
        activity_log = st.session_state.get("activity_log", [])
        if not activity_log:
            st.caption("Nothing has happened yet this session — actions you take will show up here.")
        else:
            for entry in activity_log:
                ts = entry["timestamp"].strftime("%I:%M %p")
                detail = f" — {entry['detail']}" if entry.get("detail") else ""
                st.markdown(
                    f"""<div style="padding:0.4rem 0;border-bottom:1px solid #F1F5F9;">
                            <span style="font-weight:600;color:#0F172A;">{entry['action']}</span>
                            <span style="color:#64748B;font-size:0.85rem;">{detail}</span>
                            <span style="float:right;color:#94A3B8;font-size:0.8rem;">{ts}</span>
                        </div>""",
                    unsafe_allow_html=True,
                )

with right:
    render_section_header("✨", "AI Suggestions")
    with st.container(border=True):
        if not has_data():
            st.caption("Upload a dataset to get AI-suggested next steps based on what's detected in your data.")
        else:
            semantic_columns = st.session_state.get("semantic_columns", {})
            anomalies = st.session_state.get("anomalies", {})
            kpis = st.session_state.get("kpis", [])
            suggestions = home_ai_suggestions(semantic_columns, anomalies, kpis)

            if not suggestions:
                st.caption("No AI suggestions available — not enough business columns were detected in this dataset.")
            else:
                for i, s in enumerate(suggestions):
                    if st.button(s["label"], key=f"home_suggestion_{i}", use_container_width=True):
                        if s["question"]:
                            st.session_state["pending_home_question"] = s["question"]
                        st.switch_page(s["page"])

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------
# Workspace Status — only real, already-computed values. No invented metrics.
# -----------------------------------------------------------------------

render_section_header("🖥️", "Workspace Status")

status_cols = st.columns(5)

with status_cols[0]:
    with st.container(border=True):
        st.caption("AI Provider")
        if config.AI_ENABLED:
            st.markdown(f"**{config.GEMINI_MODEL}**")
        else:
            st.markdown("**Disabled**")

with status_cols[1]:
    with st.container(border=True):
        st.caption("Dataset Loaded")
        st.markdown("**Yes**" if has_data() else "**No**")

with status_cols[2]:
    with st.container(border=True):
        st.caption("Detected Business Columns")
        if has_data():
            semantic_columns = st.session_state.get("semantic_columns", {})
            count = sum(len(cols) for cols in semantic_columns.values())
            st.markdown(f"**{count}**")
        else:
            st.markdown("**—**")

with status_cols[3]:
    with st.container(border=True):
        st.caption("Charts Available")
        charts = st.session_state.get("charts")
        st.markdown(f"**{len(charts)}**" if charts is not None else "**—**")

with status_cols[4]:
    with st.container(border=True):
        st.caption("Data Completeness")
        if has_data():
            profile = st.session_state["profile"]
            st.markdown(f"**{round(100 - profile['total_missing_pct'], 1)}%**")
        else:
            st.markdown("**—**")
