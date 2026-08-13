"""
AI Business Analyst Copilot — Phase 1 MVP + Phase 2 AI features

Upload a CSV/XLSX (or use the bundled sample dataset) and get an
automatic profile, detected business columns, KPI cards, and a
3-chart dashboard (Phase 1 — no AI required). When Gemini is
configured, also get an executive insights panel (KPI explanations,
anomaly-grounded recommendations, executive summary) and a
conversational chat interface for natural-language questions over
the data (Phase 2).
"""

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


def render_profile(df, profile):
    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", f"{profile['n_rows']:,}")
    col2.metric("Columns", f"{profile['n_columns']:,}")
    col3.metric("Missing Cells", f"{profile['total_missing_pct']}%")

    st.subheader("Data Preview")
    st.dataframe(get_preview(df, 10), width="stretch")

    st.subheader("Column Types & Missing Values")
    st.dataframe(profile["columns"], width="stretch")


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
    st.dataframe(display_rows, width="stretch")


def render_kpis(df, semantic_columns):
    st.subheader("Key Metrics")
    kpis = compute_kpis(df, semantic_columns)
    cols = st.columns(min(len(kpis), 4) or 1)
    for i, kpi in enumerate(kpis):
        cols[i % len(cols)].metric(kpi["label"], kpi["value"])
    return kpis


def render_charts(df, semantic_columns):
    st.subheader("Dashboard")
    charts = generate_charts(df, semantic_columns)
    if not charts:
        st.info("Not enough data to generate charts.")
        return
    cols = st.columns(len(charts))
    for i, (title, fig) in enumerate(charts):
        with cols[i]:
            st.plotly_chart(fig, width="stretch")


def render_executive_insights(profile, kpis, anomalies):
    st.subheader("Executive Insights")

    if not config.AI_ENABLED:
        st.info(config.AI_DISABLED_REASON)
        return

    with st.expander("What's happening in this data", expanded=True):
        summary, error = generate_executive_summary(profile, kpis, anomalies)
        if error:
            st.warning(error)
        else:
            st.write(summary)

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


def render_chat(df):
    st.subheader("Ask a Question")

    if not config.AI_ENABLED:
        st.info(config.AI_DISABLED_REASON)
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.write(turn["content"])
            if turn.get("sql"):
                with st.expander("SQL used"):
                    st.code(turn["sql"], language="sql")
            if turn.get("result_df") is not None:
                st.dataframe(turn["result_df"], width="stretch")

    question = st.chat_input("Ask a business question about this data, e.g. 'which region has the most revenue?'")
    if not question:
        return

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
        st.dataframe(result["result_df"], width="stretch")

        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": display_text,
                "sql": result["sql"],
                "result_df": result["result_df"],
            }
        )


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
    profile = profile_dataframe(df)
    anomalies = detect_anomalies(df, semantic_columns)

    render_profile(df, profile)
    render_semantic_detection(semantic_columns)
    kpis = render_kpis(df, semantic_columns)
    render_charts(df, semantic_columns)

    st.markdown("---")
    render_executive_insights(profile, kpis, anomalies)

    st.markdown("---")
    render_chat(df)


if __name__ == "__main__":
    main()
