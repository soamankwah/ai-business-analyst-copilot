"""
Shared UI components for the AI Business Analyst Copilot.

Every function in this file is either:
  (a) moved verbatim from the previous single-page app.py (render_profile,
      render_semantic_detection, render_kpis, render_charts,
      render_executive_insights, render_chat, render_section_header,
      inject_custom_css), or
  (b) new plumbing needed only because the app is now multipage:
        - run_analysis() / ensure_analysis(): runs the SAME pipeline
          calls (detect_semantic_columns, profile_dataframe,
          compute_kpis, detect_anomalies) that main() used to run
          inline, and caches the results in st.session_state so every
          page sees the same data without recomputing on every nav
          click.
        - render_upload(): the file-upload widget, extracted out of
          the old render_sidebar() so it can live on the Datasets
          page instead of the sidebar.
        - suggested_questions(): builds chat suggestions ONLY from
          semantic_columns that were actually detected. No new AI
          calls — the resulting string is fed into the existing
          ask_question()/explain_answer() flow in render_chat().

No function from data_loader, data_profiler, semantic_detector,
kpi_engine, chart_engine, anomaly_detector, insights, or query_engine
was modified. They are only called, with the same arguments as before.
"""

from datetime import datetime
from pathlib import Path

import streamlit as st

import config
from anomaly_detector import detect_anomalies
from chart_engine import generate_charts
from data_loader import (
    get_row_count,
    load_dataframe_from_upload,
    load_sample_dataset,
)
from data_profiler import get_preview, profile_dataframe
from insights import (
    explain_answer,
    explain_kpis,
    generate_executive_summary,
    generate_recommendations,
)
from kpi_engine import compute_kpis
from query_engine import ask_question
from semantic_detector import detect_semantic_columns


# ---------------------------------------------------------------------
# Styling (unchanged from the single-page version)
# ---------------------------------------------------------------------

def inject_custom_css():
    """Load assets/style.css and inject it once per session. Presentation only."""
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def render_section_header(icon: str, title: str):
    """Small styled header used above each card — cosmetic only."""
    st.markdown(
        f"""
        <div class="sa-section-header">
            <div class="sa-icon">{icon}</div>
            <h3>{title}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Data loading / analysis pipeline
# Same calls as the old main(): detect_semantic_columns -> profile_dataframe
# -> detect_anomalies -> compute_kpis. Only difference: results are cached
# in st.session_state so Dashboard / Executive Summary / Data Dictionary /
# AI Copilot pages don't need to recompute (or re-derive differently) after
# a page switch.
# ---------------------------------------------------------------------

def load_data(use_sample, uploaded_file):
    if use_sample:
        return load_sample_dataset()
    if uploaded_file is not None:
        return load_dataframe_from_upload(uploaded_file)
    return None, None


def run_analysis(df, source_label: str = "Uploaded dataset"):
    """Run the exact same pipeline main() used to run inline, once, and
    stash results in session_state.

    source_label is display metadata only (the filename, or the sample
    dataset's label) — it does not affect any analysis call or result.
    Charts are computed here (once) and cached, rather than recomputed
    every time the Dashboard page renders, so the Home page can report
    a real "Charts Available" count without a duplicate generate_charts()
    call.
    """
    semantic_columns = detect_semantic_columns(df)
    profile = profile_dataframe(df)
    anomalies = detect_anomalies(df, semantic_columns)
    kpis = compute_kpis(df, semantic_columns)
    charts = generate_charts(df, semantic_columns)

    st.session_state["df"] = df
    st.session_state["semantic_columns"] = semantic_columns
    st.session_state["profile"] = profile
    st.session_state["anomalies"] = anomalies
    st.session_state["kpis"] = kpis
    st.session_state["charts"] = charts
    st.session_state["dataset_filename"] = source_label
    st.session_state["dataset_uploaded_at"] = datetime.now()
    # A fresh dataset means the old chat history / activity dedupe state
    # no longer refer to this data — reset them, same as a full page
    # reload would have done in the single-page version.
    st.session_state["chat_history"] = []
    st.session_state["_activity_seen"] = set()

    log_activity("Dataset uploaded", source_label)


def has_data() -> bool:
    return st.session_state.get("df") is not None


def render_no_data_notice():
    st.info("No dataset is loaded yet. Go to **Datasets** to upload a file or use the bundled sample.")


# ---------------------------------------------------------------------
# Activity log — real, session-scoped record of the four actions the
# Home page's "Recent Activity" section shows. Nothing here is
# fabricated: each entry is appended only at the moment the
# corresponding real action happens (upload completes, a chat question
# is asked, an executive summary is generated, the Dashboard page is
# opened). Capped so it can't grow unbounded.
# ---------------------------------------------------------------------

_ACTIVITY_LOG_MAX = 10


def log_activity(action: str, detail: str = ""):
    log = st.session_state.setdefault("activity_log", [])
    log.insert(0, {"action": action, "detail": detail, "timestamp": datetime.now()})
    del log[_ACTIVITY_LOG_MAX:]


def log_activity_once(dedupe_key: str, action: str, detail: str = ""):
    """Same as log_activity, but only fires the first time this
    dedupe_key is seen this session — used for events that would
    otherwise re-fire on every Streamlit rerun (e.g. viewing a page,
    or an expander that re-executes on each interaction)."""
    seen = st.session_state.setdefault("_activity_seen", set())
    if dedupe_key in seen:
        return
    seen.add(dedupe_key)
    log_activity(action, detail)


# ---------------------------------------------------------------------
# Upload widget (extracted from the old render_sidebar — same widgets,
# same load_data() call, now lives on the Datasets page body instead of
# the sidebar)
# ---------------------------------------------------------------------

def render_upload():
    with st.container(border=True):
        render_section_header("📤", "Upload Data")
        use_sample = st.checkbox("Use bundled sample dataset", value=False, key="use_sample_toggle")
        uploaded_file = None
        if not use_sample:
            uploaded_file = st.file_uploader(
                "Upload a CSV or XLSX file", type=list(config.ALLOWED_EXTENSIONS), key="dataset_uploader"
            )

        if use_sample or uploaded_file is not None:
            df, error = load_data(use_sample, uploaded_file)
            if error:
                st.error(error)
                return
            if df is None:
                st.error("No data could be loaded.")
                return

            # Only re-run the pipeline if this is actually a new dataset
            # (avoids re-analyzing on every widget interaction on this page).
            new_source_id = ("sample",) if use_sample else (uploaded_file.name, uploaded_file.size)
            if st.session_state.get("_data_source_id") != new_source_id:
                source_label = getattr(config, "SAMPLE_DATA_LABEL", "Sample dataset") if use_sample else uploaded_file.name
                run_analysis(df, source_label=source_label)
                st.session_state["_data_source_id"] = new_source_id

            try:
                row_count = get_row_count(df)
                st.caption(f"Ingested into DuckDB table `{config.DUCKDB_TABLE_NAME}` — {row_count:,} rows verified.")
            except Exception as e:  # noqa: BLE001
                st.warning(f"DuckDB verification skipped due to an error: {e}")
        else:
            st.caption("Upload a CSV/XLSX file, or check 'Use bundled sample dataset' to try it out.")


# ---------------------------------------------------------------------
# Section renderers — bodies unchanged from the single-page app.py.
# They now read df / semantic_columns / profile / kpis / anomalies from
# session_state (set by run_analysis()) instead of from local variables
# in main(), since each page is a separate script run.
# ---------------------------------------------------------------------

def render_profile():
    df = st.session_state["df"]
    profile = st.session_state["profile"]
    with st.container(border=True):
        render_section_header("🗂️", "Data Profile")
        col1, col2, col3 = st.columns(3)
        col1.metric("Rows", f"{profile['n_rows']:,}")
        col2.metric("Columns", f"{profile['n_columns']:,}")
        col3.metric("Missing Cells", f"{profile['total_missing_pct']}%")

        st.markdown("&nbsp;", unsafe_allow_html=True)
        st.subheader("Data Preview")
        st.dataframe(get_preview(df, 10), use_container_width=True)

        st.subheader("Column Types & Missing Values")
        st.dataframe(profile["columns"], use_container_width=True)


def render_semantic_detection():
    semantic_columns = st.session_state["semantic_columns"]
    with st.container(border=True):
        render_section_header("🏷️", "Detected Business Columns")
        any_detected = any(cols for cols in semantic_columns.values())
        if not any_detected:
            st.info("No business-specific columns were confidently detected from column names.")
            return

        display_rows = []
        for category, cols in semantic_columns.items():
            if cols:
                display_rows.append({"category": category, "columns": ", ".join(cols)})
        st.dataframe(display_rows, use_container_width=True)


def render_kpis():
    kpis = st.session_state["kpis"]
    with st.container(border=True):
        render_section_header("📈", "Key Metrics")
        cols = st.columns(min(len(kpis), 4) or 1)
        for i, kpi in enumerate(kpis):
            cols[i % len(cols)].metric(kpi["label"], kpi["value"])


def render_charts():
    # Reuse the charts computed once in run_analysis() (cached in
    # session_state) rather than calling generate_charts() again here —
    # avoids duplicating the same analytics work on every page render.
    charts = st.session_state.get("charts")
    if charts is None:
        df = st.session_state["df"]
        semantic_columns = st.session_state["semantic_columns"]
        charts = generate_charts(df, semantic_columns)
        st.session_state["charts"] = charts
    with st.container(border=True):
        render_section_header("📊", "Dashboard")
        if not charts:
            st.info("Not enough data to generate charts.")
            return
        cols = st.columns(len(charts))
        for i, (title, fig) in enumerate(charts):
            with cols[i]:
                st.plotly_chart(fig, use_container_width=True)


def render_executive_insights():
    profile = st.session_state["profile"]
    kpis = st.session_state["kpis"]
    anomalies = st.session_state["anomalies"]
    with st.container(border=True):
        render_section_header("✨", "Executive Insights")
        if not config.AI_ENABLED:
            st.info(config.AI_DISABLED_REASON)
            return

        with st.expander("What's happening in this data", expanded=True):
            summary, error = generate_executive_summary(profile, kpis, anomalies)
            if error:
                st.warning(error)
            else:
                st.write(summary)
                log_activity_once(
                    f"exec_summary:{st.session_state.get('_data_source_id')}",
                    "Executive summary generated",
                )

        with st.expander("What the key metrics mean", expanded=False):
            explanation, error = explain_kpis(kpis)
            if error:
                st.warning(error)
            else:
                st.write(explanation)

        with st.expander("Recommendations", expanded=False):
            recommendations, error = generate_recommendations(kpis, anomalies)
            if error:
                st.warning(error)
            else:
                st.write(recommendations)

        if anomalies["numeric_outliers"] or anomalies["period_spikes"]:
            with st.expander("Detected anomalies (raw)", expanded=False):
                for o in anomalies["numeric_outliers"]:
                    st.write(
                        f"**{o['column']}** — {o['outlier_count']} outliers "
                        f"({o['outlier_pct']}%), expected range {o['lower_bound']} to {o['upper_bound']}"
                    )
                for s in anomalies["period_spikes"]:
                    st.write(f"**{s['column']}** {s['direction']}d {abs(s['change_pct'])}% in {s['period']}")


# ---------------------------------------------------------------------
# Suggested questions for AI Copilot — built ONLY from semantic_columns
# that detect_semantic_columns() actually returned. No hardcoded
# business questions, no invented columns. If a category needed for a
# given suggestion wasn't detected, that suggestion is simply not
# generated. The resulting string is passed into the exact same
# ask_question()/explain_answer() flow as manually typed chat input —
# no new AI behavior.
# ---------------------------------------------------------------------

def _first_semantic_col(semantic_columns: dict, *name_fragments):
    """Return the first detected column whose category name matches one
    of name_fragments, or None if nothing matched. Shared by the AI
    Copilot suggestion chips and the Home page's AI Suggestions —
    both only ever surface a suggestion when the underlying column was
    actually detected by semantic_detector.detect_semantic_columns()."""
    for category, cols in semantic_columns.items():
        if not cols:
            continue
        cat_lower = str(category).lower()
        if any(frag in cat_lower for frag in name_fragments):
            return cols[0]
    return None


def suggested_questions(semantic_columns: dict) -> list[str]:
    def first_col(*name_fragments):
        return _first_semantic_col(semantic_columns, *name_fragments)

    revenue_col = first_col("revenue", "sales", "amount", "price")
    date_col = first_col("date", "time", "period")
    region_col = first_col("region", "location", "geo", "country", "state")
    product_col = first_col("product", "item", "sku", "category")
    customer_col = first_col("customer", "client")

    suggestions = []

    if revenue_col and date_col:
        suggestions.append(f"What is the trend of {revenue_col} over {date_col}?")
    if revenue_col and region_col:
        suggestions.append(f"Which {region_col} has the highest total {revenue_col}?")
    if revenue_col and product_col:
        suggestions.append(f"Which {product_col} generates the most {revenue_col}?")
    if customer_col and revenue_col:
        suggestions.append(f"Which {customer_col} contributes the most {revenue_col}?")
    if revenue_col and not (date_col or region_col or product_col or customer_col):
        suggestions.append(f"What is the total {revenue_col}?")

    return suggestions[:4]


# ---------------------------------------------------------------------
# Home page "AI Suggestions" — same detected-column basis as
# suggested_questions() above, but each suggestion routes to whichever
# existing page already produces that analysis, instead of funneling
# everything through chat (which would duplicate what Executive
# Summary already computes for the anomaly/summary cases).
# ---------------------------------------------------------------------

def home_ai_suggestions(semantic_columns: dict, anomalies: dict, kpis: list) -> list[dict]:
    def first_col(*name_fragments):
        return _first_semantic_col(semantic_columns, *name_fragments)

    revenue_col = first_col("revenue", "sales", "amount", "price")
    date_col = first_col("date", "time", "period")
    product_col = first_col("product", "item", "sku", "category")

    suggestions = []

    if revenue_col and date_col:
        suggestions.append(
            {
                "label": f"Analyze {revenue_col} trends",
                "page": "app_pages/ai_copilot.py",
                "question": f"What is the trend of {revenue_col} over {date_col}?",
            }
        )
    if revenue_col and product_col:
        suggestions.append(
            {
                "label": f"Identify top-performing {product_col}s",
                "page": "app_pages/ai_copilot.py",
                "question": f"Which {product_col} generates the most {revenue_col}?",
            }
        )
    if anomalies and (anomalies.get("numeric_outliers") or anomalies.get("period_spikes")):
        suggestions.append(
            {
                "label": "Detect anomalies",
                "page": "app_pages/executive_summary.py",
                "question": None,
            }
        )
    if kpis:
        suggestions.append(
            {
                "label": "Summarize key business metrics",
                "page": "app_pages/executive_summary.py",
                "question": None,
            }
        )

    return suggestions[:4]


def render_chat():
    df = st.session_state["df"]
    semantic_columns = st.session_state.get("semantic_columns", {})

    with st.container(border=True):
        render_section_header("💬", "Ask a Question")
        if not config.AI_ENABLED:
            st.info(config.AI_DISABLED_REASON)
            return

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        suggestions = suggested_questions(semantic_columns)
        pending_question = None
        if suggestions:
            st.caption("Suggested questions")
            chip_cols = st.columns(len(suggestions))
            for i, q in enumerate(suggestions):
                if chip_cols[i].button(q, key=f"suggested_q_{i}", use_container_width=True):
                    pending_question = q

        # A suggestion clicked on the Home page arrives here the same
        # way a chip click does — same variable, same downstream flow.
        home_question = st.session_state.pop("pending_home_question", None)
        if home_question:
            pending_question = home_question

        for turn in st.session_state.chat_history:
            with st.chat_message(turn["role"]):
                st.write(turn["content"])
                if turn.get("sql"):
                    with st.expander("SQL used"):
                        st.code(turn["sql"], language="sql")
                if turn.get("result_df") is not None:
                    st.dataframe(turn["result_df"], use_container_width=True)

        typed_question = st.chat_input("Ask a business question about this data, e.g. 'which region has the most revenue?'")
        question = pending_question or typed_question
        if not question:
            return

        log_activity("AI question asked", question)
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = ask_question(df, question)

            if not result["success"]:
                st.error(result["error"])
                if result["sql"]:
                    with st.expander("SQL that was attempted"):
                        st.code(result["sql"], language="sql")
                st.session_state.chat_history.append({"role": "assistant", "content": result["error"]})
                return

            answer_text, explain_error = explain_answer(question, result["result_df"])
            display_text = answer_text if answer_text else "Here's what the data shows:"
            st.write(display_text)
            if explain_error:
                st.caption(f"(Narrative explanation unavailable: {explain_error})")

            with st.expander("SQL used"):
                st.code(result["sql"], language="sql")
            st.dataframe(result["result_df"], use_container_width=True)

            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": display_text,
                    "sql": result["sql"],
                    "result_df": result["result_df"],
                }
            )
