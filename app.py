"""
AI Business Analyst Copilot — Phase 1 MVP

Upload a CSV/XLSX (or use the bundled sample dataset) and get an
automatic profile, detected business columns, KPI cards, and a
3-chart dashboard. Fully usable without any AI provider configured.
"""

import streamlit as st

import config
from chart_engine import generate_charts
from data_loader import (
    get_row_count,
    load_dataframe_from_upload,
    load_sample_dataset,
)
from data_profiler import get_preview, profile_dataframe
from kpi_engine import compute_kpis
from semantic_detector import detect_semantic_columns

st.set_page_config(page_title="AI Business Analyst Copilot", layout="wide")


def render_ai_status():
    if config.AI_ENABLED:
        st.sidebar.success(f"AI provider: Gemini ({config.GEMINI_MODEL})")
    else:
        st.sidebar.warning(config.AI_DISABLED_REASON)


def render_sidebar():
    st.sidebar.title("AI Business Analyst Copilot")
    render_ai_status()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Data")
    use_sample = st.sidebar.checkbox("Use bundled sample dataset", value=False)
    uploaded_file = None
    if not use_sample:
        uploaded_file = st.sidebar.file_uploader("Upload a CSV or XLSX file", type=list(config.ALLOWED_EXTENSIONS))

    return use_sample, uploaded_file


def load_data(use_sample, uploaded_file):
    if use_sample:
        return load_sample_dataset()
    if uploaded_file is not None:
        return load_dataframe_from_upload(uploaded_file)
    return None, None


def render_profile(df):
    profile = profile_dataframe(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", f"{profile['n_rows']:,}")
    col2.metric("Columns", f"{profile['n_columns']:,}")
    col3.metric("Missing Cells", f"{profile['total_missing_pct']}%")

    st.subheader("Data Preview")
    st.dataframe(get_preview(df, 10), use_container_width=True)

    st.subheader("Column Types & Missing Values")
    st.dataframe(profile["columns"], use_container_width=True)


def render_semantic_detection(semantic_columns):
    st.subheader("Detected Business Columns")
    any_detected = any(cols for cols in semantic_columns.values())
    if not any_detected:
        st.info("No business-specific columns were confidently detected from column names.")
        return

    display_rows = []
    for category, cols in semantic_columns.items():
        if cols:
            display_rows.append({"category": category, "columns": ", ".join(cols)})
    st.dataframe(display_rows, use_container_width=True)


def render_kpis(df, semantic_columns):
    st.subheader("Key Metrics")
    kpis = compute_kpis(df, semantic_columns)
    cols = st.columns(min(len(kpis), 4) or 1)
    for i, kpi in enumerate(kpis):
        cols[i % len(cols)].metric(kpi["label"], kpi["value"])


def render_charts(df, semantic_columns):
    st.subheader("Dashboard")
    charts = generate_charts(df, semantic_columns)
    if not charts:
        st.info("Not enough data to generate charts.")
        return
    cols = st.columns(len(charts))
    for i, (title, fig) in enumerate(charts):
        with cols[i]:
            st.plotly_chart(fig, use_container_width=True)


def main():
    use_sample, uploaded_file = render_sidebar()

    st.title("AI Business Analyst Copilot")
    st.caption("Upload business data to get an instant profile, KPIs, and dashboard.")

    if not use_sample and uploaded_file is None:
        st.info("Upload a CSV/XLSX file, or check 'Use bundled sample dataset' in the sidebar to try it out.")
        return

    df, error = load_data(use_sample, uploaded_file)

    if error:
        st.error(error)
        return
    if df is None:
        st.error("No data could be loaded.")
        return

    try:
        row_count = get_row_count(df)
        st.caption(f"Ingested into DuckDB table `{config.DUCKDB_TABLE_NAME}` — {row_count:,} rows verified.")
    except Exception as e:  # noqa: BLE001
        st.warning(f"DuckDB verification skipped due to an error: {e}")

    semantic_columns = detect_semantic_columns(df)

    render_profile(df)
    render_semantic_detection(semantic_columns)
    render_kpis(df, semantic_columns)
    render_charts(df, semantic_columns)


if __name__ == "__main__":
    main()
