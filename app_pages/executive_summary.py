import streamlit as st

from components import has_data, render_executive_insights, render_no_data_notice

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>Executive Summary</h1>
            <p>AI-generated summary, KPI explanations, and recommendations for the currently loaded dataset.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not has_data():
    render_no_data_notice()
else:
    render_executive_insights()
