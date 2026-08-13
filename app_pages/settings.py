import streamlit as st

import config
from components import render_section_header

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>Settings</h1>
            <p>Current AI provider status and configuration values from this deployment.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    render_section_header("🤖", "AI Provider")
    if config.AI_ENABLED:
        st.success(f"AI provider: Gemini ({config.GEMINI_MODEL})")
    else:
        st.warning(getattr(config, "AI_DISABLED_REASON", "AI features are currently disabled."))

with st.container(border=True):
    render_section_header("⚙️", "Data Ingestion")
    allowed_ext = getattr(config, "ALLOWED_EXTENSIONS", None)
    max_size = getattr(config, "MAX_FILE_SIZE_MB", None)
    table_name = getattr(config, "DUCKDB_TABLE_NAME", None)
    sample_label = getattr(config, "SAMPLE_DATA_LABEL", None)

    col1, col2 = st.columns(2)
    if allowed_ext is not None:
        col1.metric("Allowed file types", ", ".join(allowed_ext).upper())
    if max_size is not None:
        col2.metric("Max file size", f"{max_size} MB")
    if table_name is not None:
        st.write(f"**DuckDB table name:** `{table_name}`")
    if sample_label is not None:
        st.write(f"**Bundled sample dataset:** {sample_label}")
