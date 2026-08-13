import streamlit as st

from components import has_data, render_profile, render_semantic_detection, render_upload

st.markdown(
    """
    <div class="sa-hero">
        <div>
            <h1>Datasets</h1>
            <p>Upload a file (or use the bundled sample) and review its profile and detected columns.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_upload()

if has_data():
    render_profile()
    render_semantic_detection()
