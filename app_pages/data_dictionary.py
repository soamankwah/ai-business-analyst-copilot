import streamlit as st

from components import has_data, render_no_data_notice, render_section_header

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>Data Dictionary</h1>
            <p>Column names, data types, and missing-value rates for the currently loaded dataset.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not has_data():
    render_no_data_notice()
else:
    profile = st.session_state["profile"]
    with st.container(border=True):
        render_section_header("📖", "Column Reference")
        st.caption(
            "Generated automatically from the dataset's schema — the same "
            "information shown under Datasets \u2192 Column Types & Missing Values."
        )
        st.dataframe(profile["columns"], use_container_width=True)
