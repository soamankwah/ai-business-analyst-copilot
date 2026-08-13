import streamlit as st

from components import has_data, render_chat, render_no_data_notice

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>AI Copilot</h1>
            <p>Ask natural-language questions about the currently loaded dataset.</p>
        </div>
        <div class="sa-hero-badge">⚡ Powered by Gemini</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not has_data():
    render_no_data_notice()
else:
    render_chat()
