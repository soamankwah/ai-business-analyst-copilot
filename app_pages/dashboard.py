import streamlit as st

from components import has_data, log_activity_once, render_charts, render_kpis, render_no_data_notice

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>Dashboard</h1>
            <p>Key metrics and analytics charts for the currently loaded dataset.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not has_data():
    render_no_data_notice()
else:
    log_activity_once(f"dashboard_viewed:{st.session_state.get('_data_source_id')}", "Dashboard viewed")
    render_kpis()
    render_charts()
